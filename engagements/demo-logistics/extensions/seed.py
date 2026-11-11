"""Northwind Logistics (fictional): synthetic, deterministic, deliberately messy operational data (risk R-11).

ENGAGEMENT-OWNED (Sprint 01, kit-generic): this file belongs to demo-logistics, not to core/. core.ingest.seed finds it
through engagement.yaml (sources.tables[].seed_script) and calls generate(out_dir). It uses the standard library only,
so it also runs on its own, e.g. inside the mock ERP's image build:
    python engagements/demo-logistics/extensions/seed.py <out_dir>

Writes CSV exports. Same seed -> byte-identical files.
Mess injected on purpose (the ETL must handle it):
  * tier values with odd casing/whitespace ("gold ", "GOLD"), plus one invalid tier ("Bronze")
  * ~3% of timestamps in US format "MM/DD/YYYY HH:MM" instead of ISO 8601
  * money as "$1,234.50" strings in ~5% of rows
  * 5 exact duplicate order rows
  * 1 order pointing at a customer that does not exist
Anchor records used by the golden set:
  * ORD-1043: Gold customer, delivered exactly 3 days late
  * SHP-2207: in transit, last scan at the Charlotte hub
"""

from __future__ import annotations

import csv
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

SEED = 20261109
ANCHOR = datetime(2026, 11, 7, 17, 0, tzinfo=UTC)  # "today" for the dataset
SLA_DAYS = {"Standard": 5, "Silver": 4, "Gold": 3, "Platinum": 2}
TIER_WEIGHTS = {"Standard": 0.45, "Silver": 0.30, "Gold": 0.18, "Platinum": 0.07}
CARRIERS = ["UPS Freight", "FedEx Ground", "XPO", "Estes", "Old Dominion", "Regional Express"]
CITIES = ["Charlotte, NC", "Raleigh, NC", "Atlanta, GA", "Richmond, VA", "Columbia, SC",
          "Nashville, TN", "Greensboro, NC", "Savannah, GA", "Knoxville, TN", "Durham, NC"]
COMPANY_A = ["Blue", "Pine", "Summit", "Harbor", "Iron", "Maple", "Atlas", "Cedar", "River", "North"]
COMPANY_B = ["Supply", "Foods", "Medical", "Retail", "Industrial", "Outfitters", "Pharma", "Hardware"]


def _ts(rng: random.Random, dt: datetime) -> str:
    if rng.random() < 0.03:
        return dt.strftime("%m/%d/%Y %H:%M")  # messy US format
    return dt.isoformat()


def _money(rng: random.Random, value: float) -> str:
    return f"${value:,.2f}" if rng.random() < 0.05 else f"{value:.2f}"


def _messy_tier(rng: random.Random, tier: str) -> str:
    r = rng.random()
    if r < 0.08:
        return tier.upper()
    if r < 0.16:
        return f"{tier.lower()} "
    return tier


def generate(out_dir: Path, n_customers: int = 40, n_orders: int = 500) -> dict[str, int]:
    rng = random.Random(SEED)
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- customers -----------------------------------------------------------------------------
    customers: list[dict[str, str]] = []
    tiers: dict[str, str] = {}
    for i in range(1, n_customers + 1):
        cid = f"C-{i:03d}"
        tier = rng.choices(list(TIER_WEIGHTS), weights=list(TIER_WEIGHTS.values()))[0]
        if cid == "C-007":
            tier = "Gold"
        tiers[cid] = tier
        name = f"{rng.choice(COMPANY_A)} {rng.choice(COMPANY_B)} {i}"
        slug = name.lower().replace(" ", "")
        customers.append({
            "customer_id": cid, "name": name, "tier": _messy_tier(rng, tier),
            "region": rng.choice(CITIES).split(", ")[1],
            "email": f"ops@{slug}.example.com", "phone": f"555-01{i:02d}",
        })
    customers.append({"customer_id": "C-041", "name": "Legacy Bronze Account", "tier": "Bronze",
                      "region": "NC", "email": "ap@legacybronze.example.com", "phone": "555-0199"})

    # --- orders + shipments --------------------------------------------------------------------
    orders: list[dict[str, str]] = []
    shipments: list[dict[str, str]] = []
    start = ANCHOR - timedelta(days=68)
    for n in range(1, n_orders + 1):
        oid = f"ORD-{1000 + n}"
        cid = f"C-{rng.randint(1, n_customers):03d}"
        tier = tiers[cid]
        created = start + timedelta(minutes=rng.randint(0, 66 * 24 * 60))
        promised = created + timedelta(days=SLA_DAYS[tier])
        r = rng.random()
        if r < 0.72:
            delivered: datetime | None = promised - timedelta(hours=rng.randint(0, 36))
        elif r < 0.93:
            delivered = promised + timedelta(days=rng.randint(1, 5), hours=rng.randint(0, 5))
        else:
            delivered = None
        if delivered and delivered > ANCHOR:
            delivered = None

        if oid == "ORD-1043":  # golden-set anchor
            cid, tier = "C-007", "Gold"
            created = datetime(2026, 10, 25, 9, 30, tzinfo=UTC)
            promised = created + timedelta(days=3)
            delivered = promised + timedelta(days=3)

        status = "delivered" if delivered else "in_transit"
        value = round(rng.uniform(150, 9_500), 2) if oid != "ORD-1043" else 4820.00
        orders.append({
            "order_id": oid, "customer_id": cid, "created_at": _ts(rng, created),
            "promised_at": _ts(rng, promised), "delivered_at": _ts(rng, delivered) if delivered else "",
            "status": status, "value_usd": _money(rng, value),
        })

        sid = f"SHP-{2000 + n}"
        origin, dest = rng.sample(CITIES, 2)
        last_scan = delivered or min(ANCHOR, created + timedelta(days=rng.randint(1, 4)))
        last_status = "Delivered" if delivered else rng.choice(
            ["In transit", "Arrived at hub", "Out for delivery", "Delayed - weather"])
        if sid == "SHP-2207":
            orders[-1]["delivered_at"], orders[-1]["status"] = "", "in_transit"
            dest, last_status = "Charlotte, NC", "Arrived at hub - Charlotte, NC"
            last_scan = ANCHOR - timedelta(hours=6)
        shipments.append({
            "shipment_id": sid, "order_id": oid, "carrier": rng.choice(CARRIERS),
            "origin": origin, "destination": dest, "last_scan_at": _ts(rng, last_scan),
            "last_status": last_status,
        })

    orders.extend(dict(o) for o in rng.sample(orders, 5))  # exact duplicates
    orders.append({"order_id": "ORD-9999", "customer_id": "C-404", "created_at": ANCHOR.isoformat(),
                   "promised_at": (ANCHOR + timedelta(days=3)).isoformat(), "delivered_at": "",
                   "status": "in_transit", "value_usd": "120.00"})  # orphan FK

    for fname, rows in (("customers.csv", customers), ("orders.csv", orders), ("shipments.csv", shipments)):
        with (out_dir / fname).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)

    return {"customers": len(customers), "orders": len(orders), "shipments": len(shipments)}


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "data" / "tables"
    print(f"seeded demo-logistics: {generate(target)}")
