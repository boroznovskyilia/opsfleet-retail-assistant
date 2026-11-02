"""Owned report use cases; storage owns atomic confirmation and receipts."""

import re

from ..config import AppError
from ..privacy import scrub
from ..telemetry import event


def requests_report(text):
    return bool(
        re.search(r"\b(create|save|generate|write)\b.{0,60}\breport\b", text, re.I)
        and not re.search(r"\b(do not|don't|never)\b", text, re.I)
    )


def requests_deletion(text):
    return bool(
        re.search(r"\b(delete|remove)\b.*\breports?\b", text, re.I)
        and not re.search(
            r"\b(do not|don't|never)\b.{0,30}\b(delete|remove)\b", text, re.I
        )
    )


class ReportService:
    def __init__(self, store, owner, thread):
        self.store, self.owner, self.thread = store, owner, thread

    async def list(self):
        return [
            {"id": r["id"], "title": r["title"], "thread": r["thread"]}
            for r in await self.store.reports(self.owner)
        ]

    async def save_last(self, title):
        history = await self.store.history(self.owner, self.thread)
        last = next(
            (m["body"] for m in reversed(history) if m["role"] == "assistant"), None
        )
        if not last or not title.strip():
            raise AppError(
                "invalid_report",
                "Provide a title and complete an assistant turn before /save.",
            )
        return await self.store.save(self.owner, self.thread, scrub(title), last)

    async def save_requested(self, text, answer, has_evidence):
        if has_evidence and requests_report(text) and not requests_deletion(text):
            report = await self.store.save(self.owner, self.thread, text[:100], answer)
            event("report_saved", user=self.owner, thread=self.thread, report=report)
            return answer + "\n\nSaved report: " + report
        return answer

    async def prepare(self, phrase=None, conversation=False, *, user_text=None):
        if user_text is not None and not requests_deletion(user_text):
            raise AppError(
                "action_not_requested",
                "Only the user can request report deletion preparation.",
            )
        if (
            not isinstance(conversation, bool)
            or (phrase is not None and not isinstance(phrase, str))
            or (conversation and phrase is not None)
        ):
            raise AppError(
                "invalid_selection", "Choose one literal phrase or this conversation."
            )
        preview = await self.store.prepare(
            self.owner, self.thread, phrase, conversation
        )
        event(
            "deletion_prepared",
            user=self.owner,
            thread=self.thread,
            action=preview["id"],
            count=len(preview["reports"]),
        )
        return preview

    async def decide(self, action, decision):
        if not action and decision == "reject":
            pending = await self.store.pending(self.owner, self.thread)
            action = pending["id"] if pending else ""
        if not action:
            raise AppError(
                "missing_action", "Use an explicit action ID from the preview."
            )
        receipt = await self.store.decide(self.owner, self.thread, action, decision)
        event(
            "deletion_decided",
            user=self.owner,
            thread=self.thread,
            action=action,
            status=receipt["status"],
            deleted=receipt["deleted"],
        )
        return receipt
