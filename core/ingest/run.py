"""Run all ingestion for an engagement: tabular ETL, then documents into pgvector.

Usage:  uv run python -m core.ingest.run --engagement demo-logistics [--tables-only | --docs-only]
"""

from __future__ import annotations

import argparse
import os

from core.config import load_engagement, resolve_path
from core.db.connection import connect
from core.ingest.etl import run_tabular_etl
from core.llm.factory import get_embeddings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engagement", default=os.environ.get("ENGAGEMENT", "demo-logistics"))
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--tables-only", action="store_true")
    group.add_argument("--docs-only", action="store_true")
    args = parser.parse_args()
    cfg = load_engagement(args.engagement)

    with connect() as conn:
        if not args.docs_only:
            for src in cfg.sources.tables:
                if src.type != "csv":
                    raise NotImplementedError(f"Table source type '{src.type}' arrives later.")
                for r in run_tabular_etl(conn, cfg.engagement.name, resolve_path(src.path), src.target_schema):
                    print(f"[etl] {r.table:<10} in={r.rows_in:<4} loaded={r.rows_loaded:<4} "
                          f"duplicates={r.duplicates:<3} rejected={len(r.rejected)}")
                    for rej in r.rejected[:5]:
                        print(f"        rejected: {rej['reason']}")
            conn.commit()

        if not args.tables_only:
            from core.ingest.documents import ingest_documents

            try:
                stats = ingest_documents(conn, cfg, get_embeddings(cfg.embeddings))
            except NotImplementedError as exc:
                print(f"[docs] skipped: {exc}")
                return
            conn.commit()
            print(f"[docs] seen={stats.documents_seen} skipped={stats.documents_skipped} "
                  f"chunks_upserted={stats.chunks_upserted}")


if __name__ == "__main__":
    main()
