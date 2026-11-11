"""Split documents into retrieval chunks.  >>> YOU IMPLEMENT split_markdown (Day 1, task 1, skill S-05) <<<

Spec: docs/specs/day-01-rag-core.md#task-1--chunking
Tests: tests/day01/test_chunking.py   (run: uv run pytest tests/day01/test_chunking.py -v)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache


@lru_cache(maxsize=1)
def _encoder():  # type: ignore[no-untyped-def]
    try:
        import tiktoken

        return tiktoken.get_encoding("cl100k_base")
    except Exception:  # offline and no cached encoding: fall back to an approximation
        return None


def count_tokens(text: str) -> int:
    """Token count used for chunk sizing. Provided — use it, don't change it."""
    enc = _encoder()
    return len(enc.encode(text)) if enc else max(1, len(text) // 4)


def slugify(section: str) -> str:
    """'Credits per Tier' -> 'credits-per-tier'. Provided; citations use it."""
    return re.sub(r"[^a-z0-9]+", "-", section.lower()).strip("-")


@dataclass(frozen=True)
class Chunk:
    text: str      # the chunk text that gets embedded and shown as context
    section: str   # nearest markdown heading above this text ("" if none)
    ordinal: int   # 0, 1, 2 ... in document order


def split_markdown(text: str, chunk_size: int = 800, chunk_overlap: int = 100) -> list[Chunk]:
    """Split markdown into chunks of at most `chunk_size` tokens.

    Requirements (all checked by tests):
      1. Never cut across a heading: each chunk belongs to exactly one section (# / ## / ### heading).
      2. Prefer paragraph boundaries; only split inside a paragraph when it alone exceeds chunk_size.
      3. No chunk exceeds chunk_size tokens (count_tokens).
      4. Consecutive chunks of the SAME section share ~chunk_overlap tokens of context.
      5. No empty chunks; ordinals are 0..n-1 in document order; same input -> same output.
      6. Every word of the input body text appears in at least one chunk (nothing dropped).

    Hint: first split into (section, paragraphs) blocks, then pack paragraphs greedily.
    """
    raise NotImplementedError("Day 1 task 1: implement split_markdown — see docs/specs/day-01-rag-core.md")
