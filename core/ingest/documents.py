"""Document ingestion: read -> chunk -> embed -> store in pgvector.

read_document() and content_hash() are provided.
>>> YOU IMPLEMENT ingest_documents (Day 1, task 2, skills S-05/S-06) <<<

Spec: docs/specs/day-01-rag-core.md#task-2--document-ingestion
Tests: tests/day01/test_ingest_documents.py
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import psycopg
from langchain_core.embeddings import Embeddings

from core.config.schema import EngagementConfig


def content_hash(text: str) -> str:
    """Provided. sha256 hex of the text; used for idempotency (FR-04)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_document(path: Path) -> tuple[str, str]:
    """Provided. Return (title, text) for .md, .txt and .pdf files."""
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
    """Provided. All files matched by sources.documents (local type only for now), sorted."""
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
    documents_skipped: int = 0   # unchanged since last run (same content hash)
    chunks_upserted: int = 0


def ingest_documents(conn: psycopg.Connection, cfg: EngagementConfig, embeddings: Embeddings) -> IngestStats:
    """Ingest every document of the engagement into kb.documents and kb.chunks.

    Requirements (checked by tests):
      1. document id = file name (e.g. 'sla-policy.md'); engagement = cfg.engagement.name.
      2. Unchanged documents (same content hash as stored) are skipped: no re-embedding.
      3. Changed documents replace ALL their old chunks (no stale chunks left behind).
      4. chunk id = f"{document_id}#{ordinal}"; store section, ordinal, text, embedding, content_hash.
      5. Embed chunks in batches (embeddings.embed_documents), not one API call per chunk.
      6. Chunk with cfg.retrieval.chunk_size / chunk_overlap.
      7. Return accurate IngestStats. Caller commits the transaction.
    """
    raise NotImplementedError("Day 1 task 2: implement ingest_documents — see docs/specs/day-01-rag-core.md")
