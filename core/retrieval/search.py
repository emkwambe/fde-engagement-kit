"""Retrieval over kb.chunks.  >>> YOU IMPLEMENT search (Day 1, task 3, skill S-06) <<<

Spec: docs/specs/day-01-rag-core.md#task-3--search
Tests: tests/day01/test_search.py
"""

from __future__ import annotations

from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    document_id: str
    title: str
    section: str
    text: str
    score: float       # ranking score, higher = better (vector mode: = similarity; hybrid: RRF score)
    similarity: float  # cosine similarity of this chunk to the query (1 - cosine distance), always set


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
    raise NotImplementedError("Day 1 task 3: implement search — see docs/specs/day-01-rag-core.md")
