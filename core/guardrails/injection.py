"""Prompt-injection filter (T-01 indirect, T-02 direct).

Indirect injection: a document, ticket or API response contains text written FOR the AI, e.g. a line
telling "AI assistants" to ignore their instructions and take an action. If that text reaches the model
inside a tool result, a weak model may obey it.

neutralize() removes every LINE that matches one of the patterns below and puts a visible marker in its
place, so the model (and a human reading the logs) can see that something was removed and why.
Matching is case-insensitive and tolerant of extra spaces. False positives cost little (one line of a
document is hidden); false negatives are caught by the other layers (system prompt, approvals).
"""

from __future__ import annotations

import re

MARKER = "[removed by guardrail: this line tried to give instructions to the AI]"

_RAW = [
    r"\bignore\s+(?:all\s+|any\s+)?(?:of\s+)?(?:the\s+|your\s+|my\s+)?(?:previous|prior|above|earlier|preceding|your|these|those)?\s*"
    r"(?:instructions|rules|prompts?|guidelines|directions)\b",
    r"\bdisregard\s+(?:all\s+|any\s+)?(?:the\s+|your\s+)?(?:previous|prior|above|earlier)?\s*(?:instructions|rules|prompts?|guidelines)\b",
    r"\bforget\s+(?:all\s+|everything\s+|your\s+)?(?:previous\s+|prior\s+)?(?:instructions|rules|you\s+were\s+told)\b",
    r"\b(?:note|message|instructions?)\s+(?:to|for)\s+(?:all\s+)?(?:ai|llm|the\s+ai|language\s+model)s?\b"
    r"(?:\s+(?:assistants?|agents?|models?|systems?))?",
    r"\byou\s+are\s+now\s+(?:a|an|in)\b",
    r"\b(?:reveal|show|print|repeat|output)\s+(?:me\s+)?(?:your|the)\s+(?:system\s+|hidden\s+|initial\s+)?(?:prompt|instructions)\b",
    r"\bact\s+as\s+(?:an?\s+)?(?:unrestricted|jailbroken|developer\s+mode|admin(?:istrator)?)\b",
]
PATTERNS = [re.compile(p, re.IGNORECASE) for p in _RAW]


def find_injection(text: str) -> list[str]:
    """Every matched phrase, in order. Empty list = nothing suspicious."""
    return [m.group(0) for p in PATTERNS for m in p.finditer(text)]


def neutralize(text: str) -> tuple[str, int]:
    """Replace each line containing an injection phrase with MARKER. Returns (text, lines removed)."""
    removed = 0
    lines = []
    for line in text.splitlines(keepends=True):
        if find_injection(line):
            removed += 1
            lines.append(MARKER + ("\n" if line.endswith("\n") else ""))
        else:
            lines.append(line)
    return "".join(lines), removed
