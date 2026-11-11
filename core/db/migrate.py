"""Apply deploy/sql/*.sql in order and create the read-only agent role.

Usage:  uv run python -m core.db.migrate --engagement demo-logistics
"""

from __future__ import annotations

import argparse
import os
import re

from psycopg import sql

from core.config import load_engagement
from core.config.loader import REPO_ROOT
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


def ensure_readonly_role(role: str = "agent_ro") -> None:
    """Agent's SQL tool connects as this role: SELECT on ops only, read-only, 5 s timeout (NFR-06)."""
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", role):
        raise ValueError("invalid role name")
    password = os.environ.get("AGENT_RO_PASSWORD", "agent_ro")
    ident = sql.Identifier(role)
    with connect(vector=False) as conn:
        exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
        stmt = "ALTER ROLE {} WITH LOGIN PASSWORD {}" if exists else "CREATE ROLE {} LOGIN PASSWORD {}"
        conn.execute(sql.SQL(stmt).format(ident, sql.Literal(password)))
        for q in (
            "REVOKE ALL ON SCHEMA kb, agent, etl FROM {}",
            "GRANT USAGE ON SCHEMA ops TO {}",
            "GRANT SELECT ON ALL TABLES IN SCHEMA ops TO {}",
            "ALTER DEFAULT PRIVILEGES IN SCHEMA ops GRANT SELECT ON TABLES TO {}",
            "ALTER ROLE {} SET default_transaction_read_only = on",
            "ALTER ROLE {} SET statement_timeout = '5s'",
        ):
            conn.execute(sql.SQL(q).format(ident))
        conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engagement", default=os.environ.get("ENGAGEMENT", "demo-logistics"))
    args = parser.parse_args()
    cfg = load_engagement(args.engagement)
    applied = apply_migrations(cfg.embeddings.dimensions)
    ensure_readonly_role()
    print(f"migrations applied: {applied or 'none (up to date)'}; role agent_ro ready")


if __name__ == "__main__":
    main()
