"""Task 2 — document ingestion. Needs Postgres (.\\tasks.ps1 up). Run: uv run pytest tests/day01/test_ingest_documents.py -v"""

import pytest

from core.ingest.documents import ingest_documents
from tests.day01.conftest import CountingEmbeddings, clear_engagement, make_cfg

pytestmark = [pytest.mark.day01, pytest.mark.db]


def _write_docs(folder):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "a.md").write_text("# Doc A\n\n## One\n\nAlpha text one.\n\n## Two\n\nAlpha text two.\n")
    (folder / "b.md").write_text("# Doc B\n\nBeta text only.\n")


def _chunk_rows(conn, engagement):
    return conn.execute(
        "SELECT id, document_id, section, ordinal, content_hash, vector_dims(embedding) "
        "FROM kb.chunks WHERE engagement = %s ORDER BY id", (engagement,)).fetchall()


def test_first_ingest_stores_documents_and_chunks(conn, demo_cfg, tmp_path):
    _write_docs(tmp_path / "docs")
    cfg = make_cfg(demo_cfg, tmp_path / "docs")
    clear_engagement(conn, cfg.engagement.name)
    emb = CountingEmbeddings(cfg.embeddings.dimensions)
    stats = ingest_documents(conn, cfg, emb)
    conn.commit()

    assert (stats.documents_seen, stats.documents_skipped) == (2, 0)
    rows = _chunk_rows(conn, cfg.engagement.name)
    assert stats.chunks_upserted == len(rows) >= 3
    assert {r[1] for r in rows} == {"a.md", "b.md"}
    assert all(r[0] == f"{r[1]}#{r[3]}" for r in rows), "chunk id must be '<document_id>#<ordinal>'"
    assert all(r[5] == cfg.embeddings.dimensions for r in rows)
    assert emb.document_calls <= 2, "embed in batches (at most one call per document)"
    titles = dict(conn.execute("SELECT id, title FROM kb.documents WHERE engagement = %s",
                               (cfg.engagement.name,)).fetchall())
    assert titles == {"a.md": "Doc A", "b.md": "Doc B"}
    clear_engagement(conn, cfg.engagement.name)


def test_reingest_is_idempotent_and_skips_unchanged(conn, demo_cfg, tmp_path):
    _write_docs(tmp_path / "docs")
    cfg = make_cfg(demo_cfg, tmp_path / "docs")
    clear_engagement(conn, cfg.engagement.name)
    ingest_documents(conn, cfg, CountingEmbeddings(cfg.embeddings.dimensions))
    conn.commit()
    before = _chunk_rows(conn, cfg.engagement.name)

    emb = CountingEmbeddings(cfg.embeddings.dimensions)
    stats = ingest_documents(conn, cfg, emb)
    conn.commit()
    assert (stats.documents_seen, stats.documents_skipped, stats.chunks_upserted) == (2, 2, 0)
    assert emb.texts_embedded == 0, "unchanged documents must not be re-embedded"
    assert _chunk_rows(conn, cfg.engagement.name) == before
    clear_engagement(conn, cfg.engagement.name)


def test_changed_document_replaces_old_chunks(conn, demo_cfg, tmp_path):
    docs = tmp_path / "docs"
    _write_docs(docs)
    cfg = make_cfg(demo_cfg, docs)
    clear_engagement(conn, cfg.engagement.name)
    ingest_documents(conn, cfg, CountingEmbeddings(cfg.embeddings.dimensions))
    conn.commit()

    (docs / "a.md").write_text("# Doc A\n\nCompletely rewritten single section.\n")
    stats = ingest_documents(conn, cfg, CountingEmbeddings(cfg.embeddings.dimensions))
    conn.commit()
    assert stats.documents_skipped == 1
    a_rows = [r for r in _chunk_rows(conn, cfg.engagement.name) if r[1] == "a.md"]
    assert len(a_rows) == 1, "stale chunks from the old version of a.md were left behind"
    text = conn.execute("SELECT text FROM kb.chunks WHERE id = 'a.md#0' AND engagement = %s",
                        (cfg.engagement.name,)).fetchone()[0]
    assert "rewritten" in text
    clear_engagement(conn, cfg.engagement.name)
