"""Task 3 — search. Needs Postgres. Run: uv run pytest tests/day01/test_search.py -v"""

import pytest

from core.llm.factory import HashingFakeEmbeddings
from core.retrieval.search import search

pytestmark = [pytest.mark.day01, pytest.mark.db]

Q = "What credit per day late does a Gold tier customer get, and what is the maximum credit?"


def _run(conn, cfg, query, hybrid, top_k=5, engagement=None):
    vec = HashingFakeEmbeddings(cfg.embeddings.dimensions).embed_query(query)
    return search(conn, engagement=engagement or cfg.engagement.name, query_text=query,
                  query_vector=vec, top_k=top_k, hybrid=hybrid)


@pytest.mark.parametrize("hybrid", [False, True])
def test_finds_the_credits_section(conn, ingested, hybrid):
    results = _run(conn, ingested, Q, hybrid)
    refs = [(r.document_id, r.section) for r in results[:3]]
    assert ("sla-policy.md", "Credits") in refs, f"top 3 were {refs}"


@pytest.mark.parametrize("hybrid", [False, True])
def test_result_shape_and_order(conn, ingested, hybrid):
    results = _run(conn, ingested, Q, hybrid, top_k=4)
    assert len(results) == 4
    assert [r.score for r in results] == sorted((r.score for r in results), reverse=True)
    assert all(-1.0 <= r.similarity <= 1.0 for r in results)
    assert all(r.title and r.text and r.chunk_id.startswith(r.document_id) for r in results)
    if not hybrid:
        assert all(abs(r.score - r.similarity) < 1e-6 for r in results)


def test_only_returns_the_requested_engagement(conn, ingested):
    assert _run(conn, ingested, Q, False, engagement="some-other-customer") == []


def test_user_text_cannot_inject_sql(conn, ingested):
    _run(conn, ingested, "'; DROP TABLE kb.chunks; --", True)
    assert conn.execute("SELECT count(*) FROM kb.chunks").fetchone()[0] > 0
