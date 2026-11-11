"""Scan an engagement's documents for prompt-injection text and PII, before (or after) ingesting them.

An FDE runs this on every new batch of customer documents: findings go to the customer as a data-quality
report ("this file contains text aimed at AI assistants - please remove it at the source").

Usage:  uv run python scripts/scan_docs.py            (ENGAGEMENT from .env, default demo-logistics)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import load_engagement, resolve_path  # noqa: E402
from core.guardrails import find_injection, redact  # noqa: E402


def main() -> None:
    cfg = load_engagement(os.environ.get("ENGAGEMENT", "demo-logistics"))
    files: list[Path] = []
    for src in cfg.sources.documents:
        folder = resolve_path(src.path)
        for pattern in src.include:
            files += sorted(folder.glob(pattern))
    findings = 0
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace") if path.suffix in {".md", ".txt"} else ""
        for n, line in enumerate(text.splitlines(), start=1):
            hits = find_injection(line)
            _, pii = redact(line, ["email", "phone", "ssn"])
            if hits:
                findings += 1
                print(f"INJECTION  {path.name}:{n}  matched: {hits}")
            if pii:
                findings += 1
                print(f"PII        {path.name}:{n}  {pii}")
    print(f"\nScanned {len(files)} file(s): {findings} finding(s).")


if __name__ == "__main__":
    main()
