"""Explicit English periods only; unsupported periods are clarified, never guessed."""

import calendar
import re
from datetime import date, datetime, timedelta, timezone

from .config import AppError


def validate(start, end):
    try:
        a, b = date.fromisoformat(start), date.fromisoformat(end)
        if a > b or b.year >= 9999:
            raise ValueError
        return {"start": a.isoformat(), "end": b.isoformat()}
    except (ValueError, TypeError):
        raise AppError(
            "invalid_period", "Use an ordered inclusive YYYY-MM-DD start/end range."
        ) from None


def month(year, number):
    return validate(
        date(year, number, 1).isoformat(),
        date(year, number, calendar.monthrange(year, number)[1]).isoformat(),
    )


def extract(text, today=None):
    today = today or datetime.now(timezone.utc).date()
    dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text)
    if dates:
        if len(dates) > 2:
            raise AppError(
                "ambiguous_period",
                "Use one explicit analysis range; group by date to compare subperiods.",
            )
        if len(dates) == 1 and re.search(
            r"\b(since|from|until|before|after)\b", text, re.I
        ):
            raise AppError(
                "ambiguous_period", "Specify both inclusive start and end dates."
            )
        return validate(dates[0], dates[-1])
    named_months = re.findall(
        r"\b(?:" + "|".join(calendar.month_name[1:]) + r")\b", text, re.I
    )
    quarters = re.findall(r"\bQ[1-4]\b", text, re.I)
    if len(named_months) + len(quarters) > 1:
        raise AppError(
            "ambiguous_period",
            "For multiple named periods, specify one combined ISO start/end range and request a breakdown.",
        )
    q = re.search(r"\bQ([1-4])\s+(20\d{2})\b", text, re.I)
    if q:
        start = (int(q[1]) - 1) * 3 + 1
        return validate(f"{q[2]}-{start:02d}-01", month(int(q[2]), start + 2)["end"])
    for number, name in enumerate(calendar.month_name):
        if not number:
            continue
        m = re.search(r"\b" + name + r"\s+(20\d{2})\b", text, re.I)
        if m:
            return month(int(m[1]), number)
    if re.search(r"\blast month\b", text, re.I):
        last = today.replace(day=1) - timedelta(days=1)
        return month(last.year, last.month)
    if re.search(r"\bthis month\b", text, re.I):
        return validate(today.replace(day=1).isoformat(), today.isoformat())
    if re.search(r"\blast quarter\b", text, re.I):
        end = date(today.year, ((today.month - 1) // 3) * 3 + 1, 1) - timedelta(days=1)
        return validate(date(end.year, end.month - 2, 1).isoformat(), end.isoformat())
    if (
        named_months
        or quarters
        or re.search(
            r"\b(last|next|previous|this)\s+(?:\d+\s+)?(?:days?|weeks?|months?|quarters?|years?)\b",
            text,
            re.I,
        )
    ):
        raise AppError(
            "ambiguous_period",
            "Specify an inclusive ISO date range or a named month/quarter with year.",
        )
    return None
