"""Small validated configuration and exact user-owned demo grants."""

import os
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

from dotenv import dotenv_values


class AppError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


USERS = {"analyst_a": 0, "analyst_b": 1}


def timeout_for(remaining, cap):
    seconds = min(cap, remaining()) if remaining else cap
    if seconds <= 0:
        raise AppError("turn_budget", "Turn deadline reached before external access.")
    return seconds


@dataclass(frozen=True)
class Settings:
    runtime: Path = field(default_factory=lambda: Path(".runtime"))
    api_key: str = field(default="", repr=False)
    project: str = ""
    model: str = "google/gemini-3.8-flash"
    budget_usd: Decimal = Decimal("5")
    turn_seconds: float = 60

    def __post_init__(self):
        if not self.budget_usd.is_finite() or not 0 < self.budget_usd <= 5:
            raise AppError(
                "configuration", "Model budget must be positive and at most USD 5."
            )
        if not 0 < self.turn_seconds <= 60:
            raise AppError(
                "configuration", "Turn budget must be positive and at most 60 seconds."
            )
        if not self.model.startswith("google/gemini-") or ":" in self.model:
            raise AppError(
                "configuration",
                "Use an explicit pinned Google Gemini model ID, without routing suffixes.",
            )

    @classmethod
    def load(cls):
        values = {**dotenv_values(".env"), **os.environ}
        try:
            return cls(
                runtime=Path(values.get("RUNTIME_DIR") or ".runtime"),
                api_key=values.get("OPENROUTER_API_KEY") or "",
                project=values.get("GOOGLE_CLOUD_PROJECT") or "",
                model=values.get("OPENROUTER_MODEL") or "google/gemini-3.8-flash",
                budget_usd=Decimal(values.get("OPENROUTER_BUDGET_USD") or "5"),
            )
        except (ValueError, InvalidOperation):
            raise AppError(
                "configuration",
                "Invalid local configuration; check the documented settings.",
            ) from None
