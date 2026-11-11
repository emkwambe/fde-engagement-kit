"""Tabular ETL: CSV exports -> clean -> validate -> upsert into Postgres (FR-03, FR-04, D-03).

Idempotent: re-running with the same files produces the same rows (upsert on primary key).
Rows that cannot be fixed are rejected and counted, never silently dropped.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import psycopg

VALID_TIERS = {"standard": "Standard", "silver": "Silver", "gold": "Gold", "platinum": "Platinum"}
_DATE_FORMATS = ("%m/%d/%Y %H:%M", "%m/%d/%Y", "%Y-%m-%d")


class RowError(ValueError):
    pass


# ---------------------------------------------------------------- field cleaners (unit-tested)
def clean_str(v: str | None) -> str | None:
    v = (v or "").strip()
    return v or None


def clean_tier(v: str | None) -> str:
    key = (v or "").strip().lower()
    if key not in VALID_TIERS:
        raise RowError(f"invalid tier {v!r}")
    return VALID_TIERS[key]


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


# ---------------------------------------------------------------- table specs
@dataclass
class TableSpec:
    file: str
    table: str
    key: str
    clean: Callable[[dict[str, str]], dict[str, Any]]
    fk: tuple[str, str] | None = None  # (column, referenced table) checked before insert


def _customer(r: dict[str, str]) -> dict[str, Any]:
    return {"customer_id": clean_str(r["customer_id"]), "name": clean_str(r["name"]),
            "tier": clean_tier(r["tier"]), "region": clean_str(r.get("region")),
            "email": clean_str(r.get("email")), "phone": clean_str(r.get("phone"))}


def _order(r: dict[str, str]) -> dict[str, Any]:
    return {"order_id": clean_str(r["order_id"]), "customer_id": clean_str(r["customer_id"]),
            "created_at": clean_ts(r["created_at"]), "promised_at": clean_ts(r["promised_at"]),
            "delivered_at": clean_ts(r.get("delivered_at"), required=False),
            "status": (clean_str(r["status"]) or "unknown").lower(), "value_usd": clean_money(r["value_usd"])}


def _shipment(r: dict[str, str]) -> dict[str, Any]:
    return {"shipment_id": clean_str(r["shipment_id"]), "order_id": clean_str(r["order_id"]),
            "carrier": clean_str(r["carrier"]), "origin": clean_str(r.get("origin")),
            "destination": clean_str(r.get("destination")),
            "last_scan_at": clean_ts(r.get("last_scan_at"), required=False),
            "last_status": clean_str(r.get("last_status"))}


# Load order matters: parents before children.
LOGISTICS_TABLES = [
    TableSpec("customers.csv", "customers", "customer_id", _customer),
    TableSpec("orders.csv", "orders", "order_id", _order, fk=("customer_id", "customers")),
    TableSpec("shipments.csv", "shipments", "shipment_id", _shipment, fk=("order_id", "orders")),
]


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

    known_parents: set[str] = set()
    if spec.fk:
        col, parent = spec.fk
        parent_key = next(s.key for s in LOGISTICS_TABLES if s.table == parent)
        known_parents = {r[0] for r in conn.execute(f"SELECT {parent_key} FROM {schema}.{parent}")}

    seen: dict[str, dict[str, Any]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for raw in csv.DictReader(f):
            result.rows_in += 1
            try:
                row = spec.clean(raw)
                if not row[spec.key]:
                    raise RowError("missing primary key")
                if spec.fk and row[spec.fk[0]] not in known_parents:
                    raise RowError(f"unknown {spec.fk[0]} {row[spec.fk[0]]!r}")
            except (RowError, KeyError) as exc:
                result.rejected.append({"row": json.dumps(raw), "reason": str(exc)})
                continue
            if row[spec.key] in seen:
                result.duplicates += 1
            seen[row[spec.key]] = row  # last one wins

    _upsert(conn, schema, spec, list(seen.values()))
    result.rows_loaded = len(seen)
    return result


def run_tabular_etl(conn: psycopg.Connection, engagement: str, folder: Path, schema: str = "ops",
                    specs: list[TableSpec] | None = None) -> list[LoadResult]:
    """Load every table, record each run in etl.runs, return per-table results."""
    results = []
    for spec in specs or LOGISTICS_TABLES:
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
