"""Task 1 — chunking. Run: uv run pytest tests/day01/test_chunking.py -v"""

import re
from pathlib import Path

import pytest

from core.ingest.chunking import count_tokens, split_markdown

pytestmark = pytest.mark.day01

SENT = "The carrier scanned the pallet at the regional hub before loading it onto the trailer."


def _doc() -> str:
    long_para = " ".join(f"{SENT} Sentence {i} alphaword." for i in range(60))
    return (
        "# Handbook\n\nIntro paragraph about the handbook.\n\n"
        f"## Alpha Section\n\n{long_para}\n\nShort closing alphaword paragraph.\n\n"
        "## Beta Section\n\nbetaword one.\n\nbetaword two with more text.\n\n"
        "### Gamma Detail\n\ngammaword details here.\n"
    )


def _words(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z0-9]+", text.lower()))


def test_returns_chunks_with_sections_and_ordinals():
    chunks = split_markdown(_doc(), chunk_size=120, chunk_overlap=20)
    assert chunks, "no chunks returned"
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))
    assert {"Handbook", "Alpha Section", "Beta Section", "Gamma Detail"} <= {c.section for c in chunks}
    assert all(c.text.strip() for c in chunks), "empty chunk"


def test_no_chunk_exceeds_size():
    for size in (60, 120, 300):
        for c in split_markdown(_doc(), chunk_size=size, chunk_overlap=size // 5):
            assert count_tokens(c.text) <= size, f"{count_tokens(c.text)} > {size} in chunk {c.ordinal}"


def test_chunks_never_cross_sections():
    markers = {"Alpha Section": "alphaword", "Beta Section": "betaword", "Gamma Detail": "gammaword"}
    for c in split_markdown(_doc(), chunk_size=120, chunk_overlap=20):
        for section, word in markers.items():
            if word in c.text:
                assert c.section == section, f"'{word}' found in chunk of section {c.section!r}"


def test_consecutive_chunks_in_a_section_overlap():
    chunks = [c for c in split_markdown(_doc(), chunk_size=120, chunk_overlap=30) if c.section == "Alpha Section"]
    assert len(chunks) >= 3, "the long Alpha section should need several chunks"
    for prev, nxt in zip(chunks, chunks[1:], strict=False):
        tail = " ".join(prev.text.split()[-3:])
        assert tail in nxt.text, f"chunk {nxt.ordinal} doesn't start with overlap from chunk {prev.ordinal}"


def test_zero_overlap_is_allowed():
    chunks = split_markdown(_doc(), chunk_size=120, chunk_overlap=0)
    assert len(chunks) >= 3


def test_nothing_is_dropped():
    doc = _doc()
    body = "\n".join(ln for ln in doc.splitlines() if not ln.startswith("#"))
    covered = set().union(*(_words(c.text) for c in split_markdown(doc, chunk_size=120, chunk_overlap=20)))
    missing = _words(body) - covered
    assert not missing, f"words lost: {sorted(missing)[:10]}"


def test_deterministic():
    assert split_markdown(_doc(), 120, 20) == split_markdown(_doc(), 120, 20)


def test_real_policy_document_keeps_credits_section_whole():
    text = Path("engagements/demo-logistics/data/docs/sla-policy.md").read_text(encoding="utf-8")
    chunks = split_markdown(text, chunk_size=800, chunk_overlap=100)
    credits = [c for c in chunks if c.section == "Credits"]
    assert len(credits) == 1 and "5%" in credits[0].text and "25%" in credits[0].text
