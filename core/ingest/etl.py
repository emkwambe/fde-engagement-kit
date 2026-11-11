"""Tabular ETL: CSV exports -> clean -> validate -> upsert into Postgres (FR-03, FR-04, D-03).

Idempotent: re-running with the same files produces the same rows (upsert on primary key).
Rows that cannot be fixed are rejected and counted, never silently dropped.

Which tables, columns, keys and cleaning rules: declared per engagement in engagement.yaml
(sources.tables[].tables, Sprint 01 kit-generic). This module only knows column TYPES, never a customer's tables.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import psycopg

from core.config.schema import ColumnSpec, TableSource, TableSpecConfig

_DATE_FORMATS = ("%m/%d/%Y %H:%M", "%m/%d/%Y", "%Y-%m-%d")


class RowError(ValueError):
    pass


# ---------------------------------------------------------------- field cleaners (unit-tested)
def clean_str(v: str | None) -> str | None:
    v = (v or "").strip()
    return v or None


def clean_enum(v: str | None, values: list[str], name: str = "value") -> str:
    """Case-insensitive, trimmed match against the canonical spellings: 'gold ', 'GOLD' -> 'Gold'."""
    canonical = {x.lower(): x for x in values}
    key = (v or "").strip().lower()
    if key not in canonical:
        raise RowError(f"invalid {name} {v!r}")
    return canonical[key]


def clean_int(v: str | None) -> int:
    try:
        return int((v or "").replace(",", "").strip())
    except ValueError:
        raise RowError(f"invalid integer {v!r}") from None


def clean_number(v: str | None) -> float:
    try:
        return float((v or "").replace(",", "").strip())
    except ValueError:
        raise RowError(f"invalid number {v!r}") from None


def clean_bool(v: str | None) -> bool | None:
    key = (v or "").strip().lower()
    if not key:
        return None
    if key in {"true", "t", "yes", "y", "1"}:
        return True
    if key in {"false", "f", "no", "n", "0"}:
        return False
    raise RowError(f"invalid boolean {v!r}")


def clean_date(v: str | None, *, required: bool = True) -> date | None:
    ts = clean_ts(v, required=required)
    return ts.date() if ts else None


def clean_ts(v: str | None, *, required: bool = True) -> datetime | None:
    v = (v or "").strip()
    if not v:
        if required:
            raise RowError("missing timestamp")
        return None
    try:
        dt = datetime.fromisoformat(v)
    except ValueError:
        for fmt in _DATE_FORMATS:
            try:
                dt = datetime.strptime(v, fmt)
                break
            except ValueError:
                continue
        else:
            raise RowError(f"unparseable timestamp {v!r}") from None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def clean_money(v: str | None) -> Decimal:
    raw = (v or "").replace("$", "").replace(",", "").strip()
    try:
        return Decimal(raw).quantize(Decimal("0.01"))
    except InvalidOperation:
        raise RowError(f"invalid amount {v!r}") from None


# ---------------------------------------------------------------- table specs (from engagement.yaml)
def clean_value(raw: dict[str, str], name: str, col: ColumnSpec) -> Any:
    """Clean one cell by its declared type. A REQUIRED column that is missing from the file or empty rejects the row.
    Defaults keep the Day 1 behaviour: timestamps, dates, numbers, money and enums are required; text and bool are not."""
    required = col.required if col.required is not None else col.type not in {"text", "bool"}
    if name not in raw and required:
        raise RowError(f"missing column {name}")
    value = raw.get(name)
    if col.type == "text":
        text = clean_str(value) or col.default
        if required and text is None:
            raise RowError(f"missing {name}")
        return text.lower() if (text is not None and col.lower) else text
    if col.type == "enum":
        return clean_enum(value, col.values, name) if (required or clean_str(value)) else None
    if col.type == "timestamp":
        return clean_ts(value, required=required)
    if col.type == "date":
        return clean_date(value, required=required)
    if col.type == "bool":
        return clean_bool(value)
    if not required and clean_str(value) is None:
        return None
    cleaners: dict[str, Callable[[str | None], Any]] = {"int": clean_int, "number": clean_number, "money": clean_money}
    return cleaners[col.type](value)


@dataclass
class TableSpec:
    file: str
    table: str
    key: str
    clean: Callable[[dict[str, str]], dict[str, Any]]
    # (column, referenced table, its key column): checked before insert. An empty value is allowed (optional link,
    # e.g. a work order with no technician yet); a value that names no existing parent rejects the row.
    fks: list[tuple[str, str, str]] = field(default_factory=list)

    @classmethod
    def from_config(cls, t: TableSpecConfig, keys: dict[str, str]) -> TableSpec:
        def clean(raw: dict[str, str]) -> dict[str, Any]:
            return {name: clean_value(raw, name, col) for name, col in t.columns.items()}

        fks = [(column, parent, keys.get(parent, column)) for column, parent in t.references.items()]
        return cls(t.file, t.name, t.key, clean, fks=fks)


def table_specs(source: TableSource) -> list[TableSpec]:
    """TableSpecs for one engagement table source, in the declared (parents-first) order."""
    keys = {t.name: t.key for t in source.tables}
    return [TableSpec.from_config(t, keys) for t in source.tables]


@dataclass
class LoadResult:
    table: str
    rows_in: int = 0
    rows_loaded: int = 0
    duplicates: int = 0
    rejected: list[dict[str, str]] = field(default_factory=list)


def _upsert(conn: psycopg.Connection, schema: str, spec: TableSpec, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    cols = list(rows[0])
    col_sql = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(cols))
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c != spec.key)
    stmt = (f"INSERT INTO {schema}.{spec.table} ({col_sql}) VALUES ({placeholders}) "
            f"ON CONFLICT ({spec.key}) DO UPDATE SET {updates}")
    with conn.cursor() as cur:
        cur.executemany(stmt, [tuple(r[c] for c in cols) for r in rows])


def load_table(conn: psycopg.Connection, folder: Path, schema: str, spec: TableSpec) -> LoadResult:
    result = LoadResult(spec.table)
    path = folder / spec.file
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run: .\\tasks.ps1 seed")

    known_parents: dict[str, set[str]] = {
        column: {r[0] for r in conn.execute(f"SELECT {parent_key} FROM {schema}.{parent}")}
        for column, parent, parent_key in spec.fks}

    seen: dict[str, dict[str, Any]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for raw in csv.DictReader(f):
            result.rows_in += 1
            try:
                row = spec.clean(raw)
                if not row[spec.key]:
                    raise RowError("missing primary key")
                for column, known in known_parents.items():
                    if row[column] is not None and row[column] not in known:
                        raise RowError(f"unknown {column} {row[column]!r}")
            except (RowError, KeyError) as exc:
                result.rejected.append({"row": json.dumps(raw), "reason": str(exc)})
                continue
            if row[spec.key] in seen:
                result.duplicates += 1
            seen[row[spec.key]] = row  # last one wins

    _upsert(conn, schema, spec, list(seen.values()))
    result.rows_loaded = len(seen)
    return result


def run_tabular_etl(conn: psycopg.Connection, engagement: str, folder: Path, schema: str,
                    specs: list[TableSpec]) -> list[LoadResult]:
    """Load every table, record each run in etl.runs, return per-table results."""
    results = []
    for spec in specs:
        run_id = conn.execute(
            "INSERT INTO etl.runs (engagement, source) VALUES (%s, %s) RETURNING id",
            (engagement, str(folder / spec.file)),
        ).fetchone()[0]  # type: ignore[index]
        res = load_table(conn, folder, schema, spec)
        conn.execute(
            "UPDATE etl.runs SET finished_at = now(), rows_in = %s, rows_loaded = %s, rows_rejected = %s, "
            "status = 'ok', detail = %s WHERE id = %s",
            (res.rows_in, res.rows_loaded, len(res.rejected),
             json.dumps({"duplicates": res.duplicates, "rejected": res.rejected[:20]}), run_id),
        )
        results.append(res)
    return results
