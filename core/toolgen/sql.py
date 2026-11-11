"""Read-only SQL tool over the customer's operational data (Day 2, part 2, FR-08).

Three layers of safety, so no single mistake can damage data:
  1. validate_sql()  - only ONE statement, starting with SELECT or WITH, no write keywords.
  2. row limit       - every query is wrapped so it can never return more than row_limit rows.
  3. agent_ro role   - the database account itself is read-only with a 5 s timeout (migrate.py).
The tool description includes the live table/column list, so the model writes correct SQL.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import psycopg
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from core.config.schema import SQLTool

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|merge|drop|alter|create|truncate|grant|revoke|copy|call|do|execute|"
    r"vacuum|analyze|refresh|lock|set|reset|comment|security|pg_sleep)\b",
    re.IGNORECASE,
)


class SQLRejected(ValueError):
    """The query was refused before reaching the database."""


def validate_sql(query: str) -> str:
    """Return the cleaned query or raise SQLRejected with a reason the model can understand."""
    q = re.sub(r"--[^\n]*|/\*.*?\*/", " ", query, flags=re.S).strip().rstrip(";").strip()
    if not q:
        raise SQLRejected("empty query")
    if ";" in q:
        raise SQLRejected("only one statement is allowed")
    if not re.match(r"^(select|with)\b", q, re.IGNORECASE):
        raise SQLRejected("only SELECT (or WITH ... SELECT) queries are allowed")
    bad = FORBIDDEN.search(q)
    if bad:
        raise SQLRejected(f"keyword not allowed in a read-only query: {bad.group(0).upper()}")
    return q


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


def describe_schema(cfg: SQLTool) -> str:
    """'orders(order_id text, customer_id text, ...)' lines for the tables the tool may read."""
    sql = """SELECT table_name, string_agg(column_name || ' ' || data_type, ', ' ORDER BY ordinal_position)
             FROM information_schema.columns WHERE table_schema = %s
             GROUP BY table_name ORDER BY table_name"""
    with psycopg.connect(cfg.dsn, connect_timeout=5) as conn:
        rows = conn.execute(sql, (cfg.schema_,)).fetchall()
    allowed = set(cfg.tables)
    return "\n".join(f"{t}({cols})" for t, cols in rows if not allowed or t in allowed)


def run_query(cfg: SQLTool, query: str) -> dict[str, Any]:
    q = validate_sql(query)
    wrapped = f"SELECT * FROM ({q}) AS agent_query LIMIT {cfg.row_limit + 1}"
    with psycopg.connect(cfg.dsn, connect_timeout=5, options=f"-c search_path={cfg.schema_}") as conn:
        conn.read_only = True
        cur = conn.execute(wrapped)
        columns = [d.name for d in cur.description or []]
        rows = cur.fetchall()
    truncated = len(rows) > cfg.row_limit
    rows = rows[: cfg.row_limit]
    return {"columns": columns, "rows": [[_jsonable(v) for v in r] for r in rows],
            "row_count": len(rows), "truncated": truncated}


class QueryArgs(BaseModel):
    query: str = Field(description="One read-only PostgreSQL SELECT statement over the listed tables")


def sql_tool(cfg: SQLTool, schema_text: str | None = None) -> StructuredTool:
    """Build the query_ops_db tool. schema_text can be passed in (tests) or is read from the DB."""
    tables = schema_text if schema_text is not None else describe_schema(cfg)

    def query_ops_db(query: str) -> str:
        try:
            return json.dumps(run_query(cfg, query))
        except SQLRejected as exc:
            return json.dumps({"error": f"query rejected: {exc}"})
        except psycopg.Error as exc:
            return json.dumps({"error": f"database error: {str(exc).splitlines()[0]}"})

    description = (
        f"Run ONE read-only SQL SELECT on the customer's operational data (schema '{cfg.schema_}'). "
        f"At most {cfg.row_limit} rows are returned. Tables:\n{tables}"
    )
    return StructuredTool.from_function(
        func=query_ops_db, name="query_ops_db", description=description, args_schema=QueryArgs,
        metadata={"source": "sql", "method": "SELECT", "path": cfg.schema_, "requires_approval": False},
    )
