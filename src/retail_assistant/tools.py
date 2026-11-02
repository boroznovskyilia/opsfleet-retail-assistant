"""Tool contracts and dispatch into application services."""

import json

from .config import AppError
from .telemetry import event


def tool(name, description, properties=None, required=None):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties or {},
                "required": required or [],
                "additionalProperties": False,
            },
        },
    }


TOOLS = [
    tool(
        "get_schema",
        "Get permitted source structure, sales metric definitions and SQL rules.",
    ),
    tool(
        "list_products",
        "Read a bounded sample of permitted product names/IDs; not sales analysis.",
    ),
    tool(
        "search_golden",
        "Select relevant educational analyst methods from the complete catalogue in context; never execute their sample SQL.",
        {"method_ids": {"type": "array", "items": {"type": "string"}, "maxItems": 3}},
        ["method_ids"],
    ),
    tool(
        "run_sql",
        "Execute a guarded flat SELECT FROM sales using exact metric aliases. Requires a server-established period; code adds scope and privacy checks.",
        {"sql": {"type": "string"}},
        ["sql"],
    ),
    tool("list_reports", "List only this user's saved report IDs/titles."),
    tool(
        "prepare_delete",
        "Prepare an owned report preview only; never confirms. Use literal phrase OR current_conversation=true.",
        {
            "phrase": {"type": ["string", "null"]},
            "current_conversation": {"type": "boolean"},
        },
        ["phrase", "current_conversation"],
    ),
]


def validate_calls(calls):
    if (
        not isinstance(calls, list)
        or not 1 <= len(calls) <= 4
        or any(
            not isinstance(c, dict)
            or c.get("type") != "function"
            or not isinstance(c.get("id"), str)
            or not c["id"]
            for c in calls
        )
        or len({c["id"] for c in calls}) != len(calls)
    ):
        raise AppError("invalid_model_output", "Invalid tool call structure.")


def parse_call(call):
    function = call.get("function")
    if not isinstance(function, dict):
        raise AppError("invalid_tool", "Invalid tool function structure.")
    name, arguments = function.get("name"), function.get("arguments")
    if not isinstance(arguments, str) or len(arguments.encode()) > 12000:
        raise AppError("invalid_tool", "Invalid bounded tool arguments.")
    args = json.loads(arguments)
    spec = next(
        (t["function"]["parameters"] for t in TOOLS if t["function"]["name"] == name),
        None,
    )
    if spec is None or not isinstance(args, dict) or set(args) != set(spec["required"]):
        raise AppError("invalid_tool", "Unknown tool or argument fields.")
    return name, args


class ToolExecutor:
    def __init__(self, analysis, knowledge, reports, user_text, progress, trace):
        self.analysis, self.knowledge, self.reports = analysis, knowledge, reports
        self.user_text, self.progress, self.trace = user_text, progress, trace
        self.metadata, self.previews = [], []

    async def invoke(self, name, args):
        self.progress(
            {
                "run_sql": "Querying scoped completed sales...",
                "search_golden": "Retrieving educational analyst methodology...",
                "prepare_delete": "Preparing an owned report preview; nothing is deleted.",
            }.get(name, "Reading permitted metadata...")
        )
        if name == "get_schema":
            data = self.analysis.get_schema()
        elif name == "list_products":
            data = await self.analysis.products()
            self.metadata.append(
                "Permitted product catalogue (sample, not sales):\n"
                + json.dumps(data, default=str)
            )
        elif name == "search_golden":
            data = self.knowledge.retrieve(args["method_ids"])
        elif name == "run_sql":
            data = await self.analysis.query(args["sql"])
        elif name == "list_reports":
            data = (await self.reports.list())[:100]
            self.metadata.append(
                "Owned report library (first 100; deletion searches the full owned set):\n"
                + json.dumps(data)
            )
        elif name == "prepare_delete":
            preview = await self.reports.prepare(
                args["phrase"], args["current_conversation"], user_text=self.user_text
            )
            self.previews.append(preview)
            # Full confirmation terms go to the user; the model only needs the operation status.
            data = {
                "action_id": preview["id"],
                "count": len(preview["reports"]),
                "requires_cli_confirmation": True,
                "deleted": 0,
            }
        else:
            raise AppError("invalid_tool", "Tool is unavailable.")
        event("tool_completed", **self.trace, tool=name)
        return data
