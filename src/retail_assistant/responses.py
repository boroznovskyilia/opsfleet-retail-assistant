"""Validated model replies and deterministic evidence presentation."""

import json

from .policy import schema
from .privacy import scrub

FINAL_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "analyst_reply",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "kind": {
                    "type": "string",
                    "enum": ["analysis", "clarification", "schema", "refusal"],
                },
                "summary": {"type": "string"},
                "hypotheses": {"type": "array", "items": {"type": "string"}},
                "actions": {"type": "array", "items": {"type": "string"}},
                "evidence_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["kind", "summary", "hypotheses", "actions", "evidence_ids"],
        },
    },
}


def table_text(result):
    rows = result["rows"]
    title = f"Evidence {result['query_id']} | {result['period']['start']} through {result['period']['end']} UTC | {result['scope']}"
    if not rows:
        return (
            title
            + "\nNo publishable rows satisfy both the filters and privacy policy. No filters were relaxed."
        )
    keys = list(rows[0])
    output = [title, " | ".join(keys), " | ".join("---" for _ in keys)]
    for row in rows:
        output.append(" | ".join(str(row.get(k, "")) for k in keys))
    if result.get("truncated"):
        output.append(
            "Display truncated to 100 rows; this is not a complete list or a global total."
        )
    if result.get("requested_limit"):
        output.append(
            f"Requested top/subset limit: {result['requested_limit']}; not an exhaustive total."
        )
    if len(rows) > 8:
        output.append(
            "Interpretation receives the first 8 rows as a bounded sample; the table above contains all displayed rows."
        )
    if result.get("ranking_exception"):
        output.append(
            "Individual ranking exception: pseudonymous reference and amount only; not anonymous aggregates."
        )
    output.append("SQL: " + result["sql"])
    return "\n".join(output)


def parse_reply(content, evidence, report_requested):
    value = json.loads(content or "")
    if (
        not isinstance(value, dict)
        or set(value) != {"kind", "summary", "hypotheses", "actions", "evidence_ids"}
        or value["kind"] not in {"analysis", "clarification", "schema", "refusal"}
        or not isinstance(value["summary"], str)
        or not value["summary"].strip()
        or len(value["summary"]) > 2500
    ):
        raise ValueError("Invalid reply shape")
    for name in ("hypotheses", "actions", "evidence_ids"):
        if (
            not isinstance(value[name], list)
            or len(value[name]) > 4
            or any(
                not isinstance(v, str) or not v.strip() or len(v) > 1000
                for v in value[name]
            )
        ):
            raise ValueError("Invalid reply fields")
    if not set(value["evidence_ids"]) <= {r["query_id"] for r in evidence}:
        raise ValueError("Unknown evidence")
    if value["kind"] == "analysis" and (
        not value["evidence_ids"] or (report_requested and not value["actions"])
    ):
        raise ValueError("Analysis needs evidence; requested reports also need actions")
    return value


def render_answer(
    final,
    *,
    evidence,
    metadata,
    previews,
    issues,
    methods,
    period,
    schema_seen,
    deletion_requested,
):
    parts = list(metadata) + [table_text(r) for r in evidence]
    if final and not deletion_requested:
        if final["kind"] == "analysis" and evidence and final["evidence_ids"]:
            parts.append(
                "Interpretation (grounded in the evidence above):\n"
                + scrub(final["summary"])
            )
            for field, title in [
                ("hypotheses", "Hypotheses, not proven causes:"),
                ("actions", "Proposed actions and validation:"),
            ]:
                if final[field]:
                    parts.append(
                        title + "\n" + "\n".join("- " + scrub(v) for v in final[field])
                    )
        elif final["kind"] == "schema" and schema_seen:
            parts.append(
                "Available sources: orders, order_items, products, users. Permitted logical sales dimensions and metrics:\n"
                + json.dumps(schema(), indent=2)
            )
        elif final["kind"] == "clarification":
            parts.append(scrub(final["summary"]))
        elif final["kind"] == "refusal":
            parts.append(
                "I can analyze permitted retail sales and manage your owned reports. External facts, PII and unsupported metrics are unavailable."
            )
    parts.extend(json.dumps(p, indent=2) for p in previews)
    if deletion_requested and not previews:
        parts.append(
            "No deletion occurred. Specify a literal phrase or use /delete conversation; confirmation always requires /confirm ACTION_ID."
        )
    if not parts:
        parts.append(
            "Please specify an inclusive analysis period (YYYY-MM-DD through YYYY-MM-DD)."
            if period is None
            else "No source-grounded answer could be completed. Check configuration or narrow the question; no findings were invented."
        )
    if issues:
        parts.append(
            "Limitations: "
            + ", ".join(dict.fromkeys(issues))
            + ". Available evidence is preserved; ask to continue if needed."
        )
    if methods:
        parts.append(
            "Educational methodology: "
            + ", ".join(sorted(methods))
            + " (not historical factual evidence)."
        )
    return "\n\n".join(parts)
