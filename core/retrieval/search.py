"""Retrieval over kb.chunks (Day 1, task 3, skill S-06).

Spec: docs/specs/day-01-rag-core.md#task-3--search
Tests: tests/day01/test_search.py

Two modes:
  * vector - rank chunks by cosine distance to the query embedding (pgvector `<=>`, HNSW index).
  * hybrid - ALSO rank chunks by Postgres full-text search, then fuse the two rankings with
             Reciprocal Rank Fusion (RRF):  score(chunk) = sum over rankings of 1 / (K + rank).
             RRF only uses ranks, so the two very different score scales never need normalizing.
Why hybrid: vectors match meaning ("late delivery" ~ "delayed shipment"); full-text matches exact
tokens that embeddings blur (order IDs, product codes, policy names).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import psycopg

RRF_K = 60            # standard RRF constant; dampens the advantage of the very top ranks
CANDIDATE_FACTOR = 4  # each ranking contributes top_k * 4 candidates before fusion


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    document_id: str
    title: str
    section: str
    text: str
    score: float       # ranking score, higher = better (vector mode: = similarity; hybrid: RRF score)
    similarity: float  # cosine similarity of this chunk to the query (1 - cosine distance), always set


_VECTOR_SQL = """
SELECT c.id, c.document_id, d.title, c.section, c.text,
       1 - (c.embedding <=> %(qvec)s) AS similarity
FROM kb.chunks c
JOIN kb.documents d ON d.engagement = c.engagement AND d.id = c.document_id
WHERE c.engagement = %(engagement)s
ORDER BY c.embedding <=> %(qvec)s
LIMIT %(top_k)s
"""

_HYBRID_SQL = """
WITH vec AS (
    SELECT c.id, row_number() OVER (ORDER BY c.embedding <=> %(qvec)s) AS rnk
    FROM kb.chunks c
    WHERE c.engagement = %(engagement)s
    ORDER BY c.embedding <=> %(qvec)s
    LIMIT %(candidates)s
),
fts AS (
    SELECT c.id, row_number() OVER (ORDER BY ts_rank_cd(c.tsv, q.query) DESC, c.id) AS rnk
    FROM kb.chunks c, websearch_to_tsquery('english', %(qtext)s) AS q(query)
    WHERE c.engagement = %(engagement)s AND c.tsv @@ q.query
    ORDER BY ts_rank_cd(c.tsv, q.query) DESC, c.id
    LIMIT %(candidates)s
),
fused AS (
    SELECT id, sum(1.0 / (%(rrf_k)s + rnk)) AS score
    FROM (SELECT id, rnk FROM vec UNION ALL SELECT id, rnk FROM fts) AS both_rankings
    GROUP BY id
)
SELECT c.id, c.document_id, d.title, c.section, c.text,
       f.score,
       1 - (c.embedding <=> %(qvec)s) AS similarity
FROM fused f
JOIN kb.chunks c    ON c.engagement = %(engagement)s AND c.id = f.id
JOIN kb.documents d ON d.engagement = c.engagement AND d.id = c.document_id
ORDER BY f.score DESC, similarity DESC, c.id
LIMIT %(top_k)s
"""


def search(
    conn: psycopg.Connection,
    *,
    engagement: str,
    query_text: str,
    query_vector: list[float],
    top_k: int = 5,
    hybrid: bool = False,
) -> list[SearchResult]:
    """Return the top_k most relevant chunks for this engagement, best first.

    Requirements (checked by tests):
      1. Only chunks where engagement = `engagement`.
      2. Vector mode: order by cosine distance (pgvector operator <=>); score = similarity = 1 - distance.
      3. Hybrid mode: combine vector ranking with full-text ranking on the tsv column
         (websearch_to_tsquery) using Reciprocal Rank Fusion: score = sum(1 / (60 + rank)).
         `similarity` is still the chunk's cosine similarity (compute it for every returned chunk).
      4. Join kb.documents to fill `title`.
      5. Use query parameters, never string-format user text into SQL.
    """
    if top_k <= 0:
        return []
    params = {
        "qvec": np.asarray(query_vector, dtype=np.float32),
        "qtext": query_text,
        "engagement": engagement,
        "top_k": top_k,
        "candidates": top_k * CANDIDATE_FACTOR,
        "rrf_k": RRF_K,
    }

    if not hybrid:
        rows = conn.execute(_VECTOR_SQL, params).fetchall()
        return [
            SearchResult(chunk_id=r[0], document_id=r[1], title=r[2] or r[1], section=r[3] or "",
                         text=r[4], score=float(r[5]), similarity=float(r[5]))
            for r in rows
        ]

    rows = conn.execute(_HYBRID_SQL, params).fetchall()
    return [
        SearchResult(chunk_id=r[0], document_id=r[1], title=r[2] or r[1], section=r[3] or "",
                     text=r[4], score=float(r[5]), similarity=float(r[6]))
        for r in rows
    ]
