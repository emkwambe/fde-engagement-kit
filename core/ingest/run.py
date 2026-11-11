"""Run all ingestion for an engagement: tabular ETL, then documents into pgvector.

Usage:  uv run python -m core.ingest.run --engagement demo-logistics [--tables-only | --docs-only]
The same work is available to admins over HTTP as POST /ingest (core/api/main.py), via run_ingestion().
"""

from __future__ import annotations

import argparse
import os
from typing import Any

from core.config import load_engagement, resolve_path
from core.config.schema import EngagementConfig
from core.db.connection import connect
from core.ingest.etl import run_tabular_etl
from core.llm.factory import get_embeddings


def run_ingestion(cfg: EngagementConfig, *, tables: bool = True, docs: bool = True) -> dict[str, Any]:
    """Load the engagement's tables and documents; return the counts (the CLI prints them, /ingest returns them).
    Each part commits on its own, like the CLI always did: a document failure never undoes a finished table load."""
    result: dict[str, Any] = {"engagement": cfg.engagement.name, "tables": [], "documents": None}
    with connect() as conn:
        if tables:
            for src in cfg.sources.tables:
                if src.type != "csv":
                    raise NotImplementedError(f"Table source type '{src.type}' arrives later.")
                for r in run_tabular_etl(conn, cfg.engagement.name, resolve_path(src.path), src.target_schema):
                    result["tables"].append({"table": r.table, "rows_in": r.rows_in, "rows_loaded": r.rows_loaded,
                                             "duplicates": r.duplicates, "rejected": len(r.rejected),
                                             "rejected_reasons": [rej["reason"] for rej in r.rejected[:5]]})
            conn.commit()
        if docs:
            from core.ingest.documents import embedding_signature, ingest_documents

            stats = ingest_documents(conn, cfg, get_embeddings(cfg.embeddings))
            conn.commit()
            result["documents"] = {"seen": stats.documents_seen, "skipped": stats.documents_skipped,
                                   "chunks_upserted": stats.chunks_upserted, "embedding": embedding_signature(cfg)}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engagement", default=os.environ.get("ENGAGEMENT", "demo-logistics"))
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--tables-only", action="store_true")
    group.add_argument("--docs-only", action="store_true")
    args = parser.parse_args()
    cfg = load_engagement(args.engagement)

    try:
        result = run_ingestion(cfg, tables=not args.docs_only, docs=not args.tables_only)
    except NotImplementedError as exc:
        print(f"[docs] skipped: {exc}")
        return
    for t in result["tables"]:
        print(f"[etl] {t['table']:<10} in={t['rows_in']:<4} loaded={t['rows_loaded']:<4} "
              f"duplicates={t['duplicates']:<3} rejected={t['rejected']}")
        for reason in t["rejected_reasons"]:
            print(f"        rejected: {reason}")
    d = result["documents"]
    if d is not None:
        print(f"[docs] seen={d['seen']} skipped={d['skipped']} chunks_upserted={d['chunks_upserted']}")


if __name__ == "__main__":
    main()
