"""Document ingestion: read -> chunk -> embed -> store in pgvector (Day 1, task 2, skills S-05/S-06).

Spec: docs/specs/day-01-rag-core.md#task-2--document-ingestion
Tests: tests/day01/test_ingest_documents.py

For each file:
  1. read it and hash the full text
  2. if the stored hash for this document is the same -> skip (no re-embedding, no cost)
  3. otherwise chunk it, embed ALL its chunks in one batch call
  4. delete the old document row (ON DELETE CASCADE removes its old chunks), insert the new rows.
     Rows are keyed by (engagement, id) - see deploy/sql/005_kb_engagement_keys.sql
The caller owns the transaction: nothing here commits.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import psycopg
from langchain_core.embeddings import Embeddings

from core.config.schema import EngagementConfig
from core.ingest.chunking import Chunk, split_markdown


def content_hash(text: str) -> str:
    """sha256 hex of the text; used for idempotency (FR-04)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_document(path: Path) -> tuple[str, str]:
    """Return (title, text) for .md, .txt and .pdf files."""
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        text = path.read_text(encoding="utf-8")
    elif suffix == ".pdf":
        from pypdf import PdfReader

        text = "\n\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    else:
        raise ValueError(f"Unsupported document type: {path.name}")
    title = next((ln.lstrip("# ").strip() for ln in text.splitlines() if ln.startswith("# ")), path.stem)
    return title, text


def list_document_files(cfg: EngagementConfig) -> list[Path]:
    """All files matched by sources.documents (local type only for now), sorted."""
    from core.config import resolve_path

    files: set[Path] = set()
    for src in cfg.sources.documents:
        if src.type != "local":
            raise NotImplementedError(f"Document source type '{src.type}' arrives later (backlog).")
        root = resolve_path(src.path)
        for pattern in src.include:
            files.update(p for p in root.glob(pattern) if p.is_file())
    return sorted(files)


@dataclass
class IngestStats:
    documents_seen: int = 0
    documents_skipped: int = 0   # unchanged since last run (same content hash and embedding model)
    chunks_upserted: int = 0


def embedding_signature(cfg: EngagementConfig) -> str:
    """Which model made the vectors, e.g. 'openai/text-embedding-3-small/1536' (Day 3).
    Vectors from different models live in different 'spaces': comparing them gives nonsense scores."""
    e = cfg.embeddings
    return f"{e.provider}/{e.model}/{e.dimensions}"


def stored_signatures(conn: psycopg.Connection, engagement: str) -> set[str]:
    """Embedding signatures of the documents currently stored for an engagement (empty = nothing ingested)."""
    rows = conn.execute("SELECT DISTINCT coalesce(metadata->>'embedding', 'unknown') FROM kb.documents "
                        "WHERE engagement = %s", (engagement,)).fetchall()
    return {r[0] for r in rows}


def _stored_state(conn: psycopg.Connection, doc_id: str, engagement: str) -> tuple[str, str] | None:
    row = conn.execute(
        "SELECT content_hash, coalesce(metadata->>'embedding', '') FROM kb.documents WHERE id = %s AND engagement = %s",
        (doc_id, engagement),
    ).fetchone()
    return (row[0], row[1]) if row else None


def _replace_document(
    conn: psycopg.Connection,
    *,
    doc_id: str,
    engagement: str,
    title: str,
    source_uri: str,
    doc_hash: str,
    chunks: list[Chunk],
    vectors: list[list[float]],
    signature: str,
) -> None:
    """Delete the old version (chunks go with it via ON DELETE CASCADE) and insert the new one.
    Rows are keyed by (engagement, id), so other engagements' copies of the same file are untouched."""
    conn.execute("DELETE FROM kb.documents WHERE engagement = %s AND id = %s", (engagement, doc_id))
    conn.execute(
        "INSERT INTO kb.documents (id, engagement, title, source_uri, content_hash, metadata) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (doc_id, engagement, title, source_uri, doc_hash, json.dumps({"chunks": len(chunks), "embedding": signature})),
    )
    rows = [
        (
            f"{doc_id}#{chunk.ordinal}",
            doc_id,
            engagement,
            chunk.section,
            chunk.ordinal,
            chunk.text,
            np.asarray(vector, dtype=np.float32),
            content_hash(chunk.text),
        )
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO kb.chunks "
            "(id, document_id, engagement, section, ordinal, text, embedding, content_hash) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            rows,
        )


def ingest_documents(conn: psycopg.Connection, cfg: EngagementConfig, embeddings: Embeddings) -> IngestStats:
    """Ingest every document of the engagement into kb.documents and kb.chunks.

    Requirements (checked by tests):
      1. document id = file name (e.g. 'sla-policy.md'); engagement = cfg.engagement.name.
      2. Unchanged documents (same content hash AND same embedding model as stored) are skipped:
         no re-embedding. Switching embedding model (e.g. FAKE_LLM=1 -> 0) re-embeds everything (Day 3).
      3. Changed documents replace ALL their old chunks (no stale chunks left behind).
      4. chunk id = f"{document_id}#{ordinal}"; store section, ordinal, text, embedding, content_hash.
      5. Embed chunks in batches (embeddings.embed_documents), not one API call per chunk.
      6. Chunk with cfg.retrieval.chunk_size / chunk_overlap.
      7. Return accurate IngestStats. Caller commits the transaction.
    """
    stats = IngestStats()
    engagement = cfg.engagement.name
    expected_dims = cfg.embeddings.dimensions
    signature = embedding_signature(cfg)

    for path in list_document_files(cfg):
        stats.documents_seen += 1
        doc_id = path.name
        title, text = read_document(path)
        doc_hash = content_hash(text)

        if _stored_state(conn, doc_id, engagement) == (doc_hash, signature):
            stats.documents_skipped += 1
            continue

        chunks = split_markdown(text, cfg.retrieval.chunk_size, cfg.retrieval.chunk_overlap)
        vectors = embeddings.embed_documents([c.text for c in chunks]) if chunks else []
        if any(len(v) != expected_dims for v in vectors):
            raise ValueError(
                f"Embedding size mismatch for {doc_id}: model returned "
                f"{len(vectors[0])} dims, config/table expect {expected_dims}."
            )

        _replace_document(
            conn,
            doc_id=doc_id,
            engagement=engagement,
            title=title,
            source_uri=str(path),
            doc_hash=doc_hash,
            chunks=chunks,
            vectors=vectors,
            signature=signature,
        )
        stats.chunks_upserted += len(chunks)

    return stats
