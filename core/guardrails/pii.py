"""PII redaction (NFR-07): replace personal data with labels before it reaches the model or the logs.

Which kinds are redacted is set per engagement in engagement.yaml -> guardrails.pii_redaction.
Order matters: SSN (123-45-6789) is checked before phone, so it is not half-matched as a phone number.
Patterns are deliberately narrow so business identifiers survive: ORD-1043, SHP-2207, C-007 and
dates like 2026-11-07 are NOT touched.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

PATTERNS: dict[str, re.Pattern[str]] = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(r"(?<![\w-])(?:\+?1[-.\s]?)?(?:\(\d{3}\)\s?|\d{3}[-.\s])?\d{3}[-.\s]\d{4}(?![\w-])"),
}
LABELS = {"ssn": "[SSN]", "email": "[EMAIL]", "phone": "[PHONE]"}


def redact(text: str, kinds: Sequence[str]) -> tuple[str, dict[str, int]]:
    """Return (redacted text, {kind: how many were replaced}) for the requested kinds."""
    counts: dict[str, int] = {}
    for kind in ("ssn", "email", "phone"):  # fixed order, see module docstring
        if kind in kinds:
            text, n = PATTERNS[kind].subn(LABELS[kind], text)
            if n:
                counts[kind] = n
    return text, counts
