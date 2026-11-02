"""Retrieval of linked educational trios, never a source of current facts."""

import json
from importlib.resources import files

from ..config import AppError

# shortcut: complete tiny catalogue in context; index it when it exceeds the prompt budget.
EXAMPLES = json.loads(files("retail_assistant").joinpath("golden.json").read_text())


class GoldenKnowledge:
    def __init__(self):
        self.selected = set()

    def catalogue(self):
        return [
            {"id": e["id"], "question": e["question"]}
            for e in EXAMPLES
            if e["scope"] == "generic"
        ]

    def retrieve(self, ids):
        if (
            not isinstance(ids, list)
            or len(ids) > 3
            or any(not isinstance(i, str) for i in ids)
            or len(set(ids)) != len(ids)
        ):
            raise AppError(
                "invalid_tool", "Choose up to three distinct catalogue method IDs."
            )
        examples = [e for e in EXAMPLES if e["id"] in ids and e["scope"] == "generic"]
        if len(examples) != len(ids):
            raise AppError("invalid_tool", "Unknown or unauthorized method ID.")
        self.selected.update(ids)
        return {
            "trios": examples,
            "match_found": bool(examples),
            "provenance": "Educational methodology only; not historical factual evidence.",
        }
