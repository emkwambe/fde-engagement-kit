"""Split documents into retrieval chunks (Day 1, task 1, skill S-05).

Spec: docs/specs/day-01-rag-core.md#task-1--chunking
Tests: tests/day01/test_chunking.py   (run: uv run pytest tests/day01/test_chunking.py -v)

How it works, in three steps:
  1. Parse   - walk the lines and group them into blocks of (section heading, [paragraphs]).
  2. Split   - any single paragraph longer than the budget is cut into word-based pieces.
  3. Pack    - fill chunks greedily with whole paragraphs/pieces; when the next piece would not fit,
               close the chunk and start the next one with the last ~chunk_overlap tokens of it.
Overlap never crosses a heading, so every chunk belongs to exactly one section.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

_HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")  # "## Credits" -> "Credits"


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


# --------------------------------------------------------------------------- step 1: parse
def _parse_blocks(text: str) -> list[tuple[str, list[str]]]:
    """Group lines into (section, [paragraphs]). A heading starts a new section;
    a blank line ends a paragraph. Sections with no body text are dropped."""
    blocks: list[tuple[str, list[str]]] = []
    section = ""
    paragraphs: list[str] = []
    current: list[str] = []  # lines of the paragraph being built

    def close_paragraph() -> None:
        if current:
            paragraphs.append("\n".join(current).strip())
            current.clear()

    def close_section() -> None:
        close_paragraph()
        body = [p for p in paragraphs if p]
        if body:
            blocks.append((section, body))

    for line in text.splitlines():
        heading = _HEADING.match(line)
        if heading:
            close_section()
            section = heading.group(1).strip()
            paragraphs = []
        elif not line.strip():
            close_paragraph()
        else:
            current.append(line.rstrip())
    close_section()
    return blocks


# --------------------------------------------------------------------------- step 2: split long paragraphs
def _split_long_paragraph(paragraph: str, limit: int) -> list[str]:
    """Cut a paragraph that is over `limit` tokens into word-based pieces of <= limit tokens."""
    pieces: list[str] = []
    words: list[str] = []
    for word in paragraph.split():
        if words and count_tokens(" ".join([*words, word])) > limit:
            pieces.append(" ".join(words))
            words = []
        words.append(word)
    if words:
        pieces.append(" ".join(words))
    return pieces


# --------------------------------------------------------------------------- step 3: pack with overlap
def _overlap_tail(text: str, budget: int) -> str:
    """The longest run of whole words at the END of `text` that fits in `budget` tokens."""
    if budget <= 0:
        return ""
    tail: list[str] = []
    for word in reversed(text.split()):
        if count_tokens(" ".join([word, *tail])) > budget:
            break
        tail.insert(0, word)
    return " ".join(tail)


def _join(a: str, b: str) -> str:
    return f"{a}\n\n{b}" if a and b else (a or b)


def _pack_section(pieces: list[str], chunk_size: int, chunk_overlap: int) -> list[str]:
    """Greedy packing of pieces into chunks of <= chunk_size tokens, with overlap between them."""
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        candidate = _join(current, piece)
        if not current or count_tokens(candidate) <= chunk_size:
            current = candidate
            continue

        # `piece` doesn't fit: close the current chunk, start the next with overlap + piece.
        chunks.append(current)
        overlap = _overlap_tail(current, chunk_overlap)
        current = _join(overlap, piece)
        # Overlap + piece can still be too big; shrink the overlap until it fits.
        while count_tokens(current) > chunk_size and overlap:
            overlap = " ".join(overlap.split()[1:])
            current = _join(overlap, piece)
    if current:
        chunks.append(current)
    return chunks


# --------------------------------------------------------------------------- public API
def split_markdown(text: str, chunk_size: int = 800, chunk_overlap: int = 100) -> list[Chunk]:
    """Split markdown into chunks of at most `chunk_size` tokens.

    Requirements (all checked by tests):
      1. Never cut across a heading: each chunk belongs to exactly one section (# / ## / ### heading).
      2. Prefer paragraph boundaries; only split inside a paragraph when it alone exceeds chunk_size.
      3. No chunk exceeds chunk_size tokens (count_tokens).
      4. Consecutive chunks of the SAME section share ~chunk_overlap tokens of context.
      5. No empty chunks; ordinals are 0..n-1 in document order; same input -> same output.
      6. Every word of the input body text appears in at least one chunk (nothing dropped).
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if not 0 <= chunk_overlap < chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and smaller than chunk_size")

    # Pieces cut from a long paragraph leave room for the overlap that will be prepended to them,
    # so "overlap + piece" still fits and the overlap isn't squeezed out.
    piece_limit = max(1, chunk_size - chunk_overlap)

    out: list[Chunk] = []
    for section, paragraphs in _parse_blocks(text):
        pieces: list[str] = []
        for paragraph in paragraphs:
            if count_tokens(paragraph) <= chunk_size:
                pieces.append(paragraph)
            else:
                pieces.extend(_split_long_paragraph(paragraph, piece_limit))
        for chunk_text in _pack_section(pieces, chunk_size, chunk_overlap):
            if chunk_text.strip():
                out.append(Chunk(text=chunk_text, section=section, ordinal=len(out)))
    return out