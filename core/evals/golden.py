"""The golden set: questions written with the customer, each with what a correct run must show.

One JSON object per line in engagements/<name>/evals/golden.jsonl. Every field except id/category/question
is optional; a check only runs when its field is set (see scoring.py).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["rag", "sql", "api_read", "api_write", "multi", "red_team"]
MINIMUM_PER_CATEGORY: dict[str, int] = {"rag": 8, "sql": 5, "api_read": 3, "api_write": 3, "multi": 3, "red_team": 5}


class GoldenCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^q-\d{3}$")
    category: Category
    question: str = Field(min_length=3)
    expected_tools: list[str] = []          # must ALL be called (any order; more is fine)
    expected_sources: list[str] = []        # refs that search_documents must return AND the answer must cite
    expected_facts: list[str] = []          # must ALL appear in the answer (case-insensitive); "a|b" = either
    must_not: list[str] = []                # must NOT appear in any tool name, tool argument or the answer
    requires_approval: bool = False         # the run must pause for a human (and not before)
    expected_args: dict[str, Any] = {}      # subset of the paused call's arguments (numbers within 0.01)
    expect_refusal: bool = False            # no tool may run at all
    notes: str = ""


def load_golden(path: Path) -> list[GoldenCase]:
    cases = [GoldenCase.model_validate(json.loads(line))
             for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [c.id for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate case ids in {path.name}")
    return cases
