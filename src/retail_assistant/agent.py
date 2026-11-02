"""Conversation orchestration and a bounded LangGraph model/tool loop."""

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import TypedDict

# No external tracing of prompts is authorized for this local prototype.
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
from langgraph.graph import END, START, StateGraph

from . import periods
from .config import AppError
from .privacy import PRIVATE_REQUEST, scrub
from .prompts import SYSTEM
from .responses import FINAL_SCHEMA, parse_reply, render_answer
from .services.analysis import AnalysisService
from .services.knowledge import GoldenKnowledge
from .services.reports import ReportService, requests_deletion, requests_report
from .store import uid
from .telemetry import event
from .tools import TOOLS, ToolExecutor, parse_call, validate_calls


class State(TypedDict):
    messages: list
    stop: bool


@dataclass
class TurnBudget:
    seconds: float
    started: float = field(default_factory=time.monotonic)
    model_calls: int = 0
    tool_calls: int = 0
    repair_used: bool = False

    def remaining(self):
        return self.seconds - (time.monotonic() - self.started)

    def start_model(self):
        if self.model_calls >= 6 or self.remaining() <= 0:
            raise AppError("turn_budget", "Model/turn budget exhausted.")
        self.model_calls += 1

    def start_tool(self):
        if self.tool_calls >= 8 or self.remaining() <= 0:
            raise AppError("turn_budget", "Tool/turn budget exhausted.")
        self.tool_calls += 1

    def repair(self, code):
        if code in {"invalid_model_output", "invalid_sql"} and not self.repair_used:
            self.repair_used = True
            return True
        return False


def build_messages(owner, period, text, previous, catalogue):
    context = {
        "user": owner,
        "period": period,
        "report_requested": requests_report(text),
        "golden_catalogue": catalogue,
        "completed_previous_turns": previous[-6:],
    }
    messages = [
        {
            "role": "system",
            "content": SYSTEM + "\nServer context: " + json.dumps(context),
        },
        {"role": "user", "content": text},
    ]
    # Drop complete older turns without losing policy, the current question or evidence.
    while (
        len(json.dumps(messages).encode()) > 16000
        and context["completed_previous_turns"]
    ):
        context["completed_previous_turns"] = context["completed_previous_turns"][2:]
        messages[0]["content"] = SYSTEM + "\nServer context: " + json.dumps(context)
    return messages


class Agent:
    def __init__(self, settings, store, warehouse, model, progress=None):
        self.settings, self.store = settings, store
        self.warehouse, self.model = warehouse, model
        self.progress = progress or (lambda message: None)

    async def turn(self, owner, thread, text):
        await self.store.thread(owner, thread)
        text = scrub(text)
        if len(text.encode()) > 6000:
            raise AppError("input_budget", "Message is too large; narrow the question.")
        period = periods.extract(text)
        if period:
            await self.store.period(owner, thread, period)
        period = await self.store.period(owner, thread)
        previous = await self.store.history(owner, thread)
        await self.store.append(owner, thread, "user", text)
        request = uid()
        trace = {"user": owner, "thread": thread, "request": request}
        event("turn_started", **trace)
        early = await self._local_reply(owner, thread, text)
        if early:
            answer, issues = early
            await self.store.append(owner, thread, "assistant", answer)
            event(
                "turn_completed",
                **trace,
                model_calls=0,
                tool_calls=0,
                queries=0,
                partial=bool(issues),
            )
            return {
                "text": answer,
                "evidence": [],
                "request_id": request,
                "issues": issues,
            }

        budget = TurnBudget(self.settings.turn_seconds)
        analysis = AnalysisService(
            owner, period, self.warehouse, self.store, budget.remaining, trace
        )
        knowledge = GoldenKnowledge()
        reports = ReportService(self.store, owner, thread)
        tools = ToolExecutor(analysis, knowledge, reports, text, self.progress, trace)
        messages = build_messages(owner, period, text, previous, knowledge.catalogue())
        final, issues = await self._research(
            messages, tools, budget, trace, requests_report(text)
        )
        answer = render_answer(
            final,
            evidence=analysis.results,
            metadata=tools.metadata,
            previews=tools.previews,
            issues=issues,
            methods=knowledge.selected,
            period=period,
            schema_seen=analysis.schema_seen,
            deletion_requested=requests_deletion(text),
        )
        answer = await reports.save_requested(text, answer, bool(analysis.results))
        await self.store.append(owner, thread, "assistant", answer)
        event(
            "turn_completed",
            **trace,
            model_calls=budget.model_calls,
            tool_calls=budget.tool_calls,
            queries=analysis.query_attempts,
            partial=bool(issues),
        )
        return {
            "text": answer,
            "evidence": analysis.results,
            "request_id": request,
            "issues": issues,
        }

    async def _local_reply(self, owner, thread, text):
        pending = await self.store.pending(owner, thread)
        if pending and text.strip().lower() in {"yes", "confirm", "sure", "go ahead"}:
            return (
                "Nothing was deleted. Use /confirm "
                + pending["id"]
                + " or /reject "
                + pending["id"]
                + " for the saved preview. Library deletion retains chat history.",
                [],
            )
        if PRIVATE_REQUEST.search(text) or re.search(
            r"\b(weather|forecast|president|medical advice)\b|ignore.{0,30}(instructions|policy|rules)",
            text,
            re.I,
        ):
            return (
                "I can analyze permitted retail sales using aggregates or restricted pseudonymous rankings. "
                "I cannot disclose personal data, override access rules or supply external facts.",
                ["scope_refused"],
            )
        return None

    async def _research(self, messages, tools, budget, trace, report_requested):
        final, issues = None, []

        async def think(state):
            nonlocal final
            try:
                budget.start_model()
                self.progress("Planning the next bounded analysis step...")
                finalize = (
                    budget.model_calls == 6
                    or budget.tool_calls >= 8
                    or tools.analysis.exhausted
                )
                allowed_tools = [] if finalize else TOOLS
                model_messages = state["messages"]
                if finalize:
                    model_messages = model_messages + [
                        {
                            "role": "system",
                            "content": "The research budget is complete. Do not request tools. Compose the final JSON from verified evidence now, including report actions when requested. State missing coverage and privacy/sampling limitations explicitly; do not invent findings.",
                        }
                    ]
                reply = await self.model.call(
                    model_messages, allowed_tools, budget.remaining, trace, FINAL_SCHEMA
                )
                if reply.get("tool_calls"):
                    if finalize:
                        raise ValueError(
                            "Tools are unavailable during final composition"
                        )
                    validate_calls(reply["tool_calls"])
                    return {"messages": state["messages"] + [reply], "stop": False}
                final = parse_reply(
                    reply.get("content"), tools.analysis.results, report_requested
                )
                issues[:] = [code for code in issues if code != "invalid_model_output"]
                return {"messages": state["messages"] + [reply], "stop": True}
            except (ValueError, TypeError, KeyError):
                error = AppError(
                    "invalid_model_output",
                    "Return the exact final JSON contract; use only successful evidence IDs. Requested reports need proposed actions with validation.",
                )
            except AppError as caught:
                error = caught
            except Exception as unexpected:
                event(
                    "model_internal_error",
                    **trace,
                    error_class=type(unexpected).__name__,
                )
                error = AppError(
                    "model_internal_error",
                    "Model operation failed; verified evidence is preserved.",
                )
            issues.append(error.code)
            event("model_step_failed", **trace, error=error.code)
            if budget.repair(error.code):
                return {
                    "messages": state["messages"]
                    + [{"role": "user", "content": str(error)}],
                    "stop": False,
                }
            return {"stop": True}

        async def execute(state):
            outputs, stop = [], False
            for call in state["messages"][-1]["tool_calls"]:
                try:
                    budget.start_tool()
                    name, args = parse_call(call)
                    data = await tools.invoke(name, args)
                    if name == "run_sql":
                        issues[:] = [
                            code
                            for code in issues
                            if code not in {"invalid_sql", "missing_schema"}
                        ]
                except (ValueError, TypeError, KeyError):
                    data = {
                        "error": "invalid_tool",
                        "message": "Use the documented tool argument types.",
                    }
                    issues.append("invalid_tool")
                except AppError as error:
                    issues.append(error.code)
                    data = {"error": error.code, "message": str(error)}
                    event("tool_failed", **trace, error=error.code)
                    if not budget.repair(error.code) and error.code not in {
                        "missing_schema",
                        "invalid_tool",
                        "action_not_requested",
                        "query_budget",
                        "scan_budget",
                    }:
                        # Exhausted tools still need paired replies before final composition.
                        stop = error.code != "turn_budget" or budget.remaining() <= 0
                except Exception as unexpected:
                    event(
                        "tool_internal_error",
                        **trace,
                        error_class=type(unexpected).__name__,
                    )
                    issues.append("tool_internal_error")
                    data = {
                        "error": "tool_internal_error",
                        "message": "Tool failed; existing verified evidence and reports are preserved.",
                    }
                    stop = True
                outputs.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": json.dumps(data, default=str),
                    }
                )
                if stop:
                    break
            return {"messages": state["messages"] + outputs, "stop": stop}

        graph = StateGraph(State)
        graph.add_node("model", think)
        graph.add_node("tools", execute)
        graph.add_edge(START, "model")
        graph.add_conditional_edges(
            "model",
            lambda s: (
                END
                if s["stop"]
                else ("tools" if s["messages"][-1].get("tool_calls") else "model")
            ),
        )
        graph.add_conditional_edges("tools", lambda s: END if s["stop"] else "model")
        await graph.compile().ainvoke(
            {"messages": messages, "stop": False},
            config={"recursion_limit": 24, "callbacks": []},
        )
        return final, issues
