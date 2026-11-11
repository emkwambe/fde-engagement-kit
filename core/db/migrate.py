"""Apply deploy/sql/*.sql in order, then the engagement's own DDL, and create the read-only agent role.

Usage:  uv run python -m core.db.migrate --engagement demo-logistics

Two kinds of SQL (Sprint 01, kit-generic):
  deploy/sql/NNN_*.sql            the KIT's schemas and tables (kb, agent, etl). Append-only, applied once each.
  sources.tables[].schema_sql     the ENGAGEMENT's operational tables, in its own schema (e.g. `field`), from files in
                                  its folder. Recorded as "<engagement>/<file>" in schema_migrations, applied once each.
(deploy/sql/003 still creates demo-logistics' ops tables: it predates schema_sql and applied migrations are never edited.)
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

from psycopg import sql

from core.config import load_engagement, resolve_path
from core.config.loader import REPO_ROOT
from core.config.schema import EngagementConfig
from core.db.connection import connect

SQL_DIR = REPO_ROOT / "deploy" / "sql"


def apply_migrations(embedding_dim: int) -> list[str]:
    applied: list[str] = []
    files = sorted(SQL_DIR.glob("*.sql"))
    with connect(vector=False) as conn:
        # 001 creates the extension + migrations table, so always run it first and idempotently.
        conn.execute(files[0].read_text(encoding="utf-8"))
        done = {r[0] for r in conn.execute("SELECT filename FROM public.schema_migrations")}
        for f in files:
            if f.name in done:
                continue
            ddl = f.read_text(encoding="utf-8").replace("{{EMBEDDING_DIM}}", str(embedding_dim))
            conn.execute(ddl)
            conn.execute("INSERT INTO public.schema_migrations(filename) VALUES (%s)", (f.name,))
            applied.append(f.name)
        conn.commit()
    return applied


def apply_engagement_sql(cfg: EngagementConfig) -> list[str]:
    """Apply the engagement's own DDL files once each, in the order listed in engagement.yaml."""
    applied: list[str] = []
    files = [f for src in cfg.sources.tables for f in src.schema_sql]
    if not files:
        return applied
    with connect(vector=False) as conn:
        done = {r[0] for r in conn.execute("SELECT filename FROM public.schema_migrations")}
        for rel in files:
            name = f"{cfg.engagement.name}/{Path(rel).name}"
            if name in done:
                continue
            conn.execute(resolve_path(rel).read_text(encoding="utf-8"))
            conn.execute("INSERT INTO public.schema_migrations(filename) VALUES (%s)", (name,))
            applied.append(name)
        conn.commit()
    return applied


def ensure_readonly_role(role: str = "agent_ro", schemas: tuple[str, ...] = ("ops",)) -> None:
    """Agent's SQL tool connects as this role: SELECT on the engagement's schema(s) only, read-only, 5 s timeout
    (NFR-06). One role serves every engagement in a shared dev database, so it can read each engagement's schema;
    a real customer gets its own database (Sprint 01 known limitation)."""
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", role) or not all(re.fullmatch(r"[a-z_][a-z0-9_]*", x) for x in schemas):
        raise ValueError("invalid role or schema name")
    password = os.environ.get("AGENT_RO_PASSWORD", "agent_ro")
    ident = sql.Identifier(role)
    with connect(vector=False) as conn:
        exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
        stmt = "ALTER ROLE {} WITH LOGIN PASSWORD {}" if exists else "CREATE ROLE {} LOGIN PASSWORD {}"
        conn.execute(sql.SQL(stmt).format(ident, sql.Literal(password)))
        conn.execute(sql.SQL("REVOKE ALL ON SCHEMA kb, agent, etl FROM {}").format(ident))
        for schema in schemas:
            s = sql.Identifier(schema)
            conn.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(s))
            for q in ("GRANT USAGE ON SCHEMA {s} TO {r}",
                      "GRANT SELECT ON ALL TABLES IN SCHEMA {s} TO {r}",
                      "ALTER DEFAULT PRIVILEGES IN SCHEMA {s} GRANT SELECT ON TABLES TO {r}"):
                conn.execute(sql.SQL(q).format(s=s, r=ident))
        for q in ("ALTER ROLE {} SET default_transaction_read_only = on", "ALTER ROLE {} SET statement_timeout = '5s'"):
            conn.execute(sql.SQL(q).format(ident))
        conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engagement", default=os.environ.get("ENGAGEMENT", "demo-logistics"))
    args = parser.parse_args()
    cfg = load_engagement(args.engagement)
    applied = apply_migrations(cfg.embeddings.dimensions) + apply_engagement_sql(cfg)
    schemas = tuple(dict.fromkeys(["ops", *([cfg.tools.sql.schema_] if cfg.tools.sql else [])]))
    ensure_readonly_role(schemas=schemas)
    print(f"migrations applied: {applied or 'none (up to date)'}; role agent_ro ready (SELECT on {', '.join(schemas)})")


if __name__ == "__main__":
    main()
