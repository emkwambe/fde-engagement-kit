"""Coastline Climate Services (fictional): synthetic, deterministic, deliberately messy field-service data.

ENGAGEMENT-OWNED (engagement.yaml -> sources.tables[].seed_script). Standard library only, so it also runs on its own:
    python engagements/coastline-hvac/extensions/seed.py <out_dir>
Same seed number -> byte-identical CSV exports (customers, technicians, equipment, work_orders).

Mess injected on purpose (the ETL must handle it): plan values with odd casing/spaces, ~4% US-format timestamps,
on_call as yes/no/Y/N/TRUE, 3 exact duplicate work orders, 1 work order for a customer that does not exist (CU-404),
1 customer with an unknown plan ("Gold").
Anchors used by the golden set (dates in November 2026, UTC):
  CU-004 Premium | CU-012 Basic | CU-020 Plus | CU-007 Plus
  WO-5003 dispatched routine, technician T-04
  WO-5017 CU-004 emergency, opened 11-02 08:00, responded 15:00: 7 h vs 4 h SLA = 3 h late -> 1 block -> 15% of $149
  WO-5040 CU-004 emergency OPEN after hours, heat pump (residential)      -> on-call T-02, fee $0
  WO-5041 CU-012 emergency OPEN after hours, rooftop unit (commercial)    -> on-call T-05, fee $150
  WO-5042 CU-020 emergency OPEN after hours, refrigerant leak (refrigeration) -> on-call T-07, fee $75
  WO-5060 CU-007 routine, responded after 60 h vs 48 h SLA = 12 h late -> 3 blocks -> 30% of $89
"""

from __future__ import annotations

import csv
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

SEED = 20261111
ANCHOR = datetime(2026, 11, 10, 18, 0, tzinfo=UTC)  # "now" for the dataset
PLANS = {"Basic": 0.5, "Plus": 0.3, "Premium": 0.2}
SLA_HOURS = {("Basic", "emergency"): 24, ("Basic", "routine"): 72, ("Plus", "emergency"): 8,
             ("Plus", "routine"): 48, ("Premium", "emergency"): 4, ("Premium", "routine"): 24}
CITIES = ["Wilmington", "Myrtle Beach", "Charleston"]
KINDS = {"furnace": "residential", "heat pump": "residential", "central AC": "residential",
         "rooftop unit": "commercial", "boiler": "commercial", "walk-in cooler": "refrigeration"}
TECHS = [("T-01", "Avery Cole", "residential", "no"), ("T-02", "Blake Diaz", "residential", "yes"),
         ("T-03", "Casey Ford", "commercial", "N"), ("T-04", "Devon Gray", "residential", "no"),
         ("T-05", "Emery Hale", "commercial", "Y"), ("T-06", "Finley Ives", "refrigeration", "no"),
         ("T-07", "Gray Jensen", "refrigeration", "TRUE"), ("T-08", "Harper Kim", "commercial", "no")]
NAME_A = ["Harbor", "Dune", "Palmetto", "Tidewater", "Seaside", "Marsh", "Pelican", "Oak"]
NAME_B = ["Bistro", "Dental", "Apartments", "Bakery", "Clinic", "Residence", "Market", "Studios"]
PINNED_PLANS = {"CU-004": "Premium", "CU-007": "Plus", "CU-012": "Basic", "CU-020": "Plus"}


def _ts(rng: random.Random, dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.strftime("%m/%d/%Y %H:%M") if rng.random() < 0.04 else dt.isoformat()


def _messy(rng: random.Random, plan: str) -> str:
    r = rng.random()
    return plan.upper() if r < 0.08 else f" {plan.lower()}" if r < 0.15 else plan


def generate(out_dir: Path, n_customers: int = 30, n_orders: int = 120) -> dict[str, int]:
    rng = random.Random(SEED)
    out_dir.mkdir(parents=True, exist_ok=True)

    customers, plans = [], {}
    for i in range(1, n_customers + 1):
        cid = f"CU-{i:03d}"
        plan = PINNED_PLANS.get(cid) or rng.choices(list(PLANS), weights=list(PLANS.values()))[0]
        plans[cid] = plan
        name = f"{rng.choice(NAME_A)} {rng.choice(NAME_B)} {i}"
        customers.append({"customer_id": cid, "name": name, "plan": _messy(rng, plan), "city": rng.choice(CITIES),
                          "email": f"office@{name.lower().replace(' ', '')}.example.com", "phone": f"555-02{i:02d}",
                          "contract_start": (ANCHOR - timedelta(days=rng.randint(60, 900))).date().isoformat()})
    customers.append({"customer_id": "CU-031", "name": "Legacy Gold Account", "plan": "Gold", "city": "Wilmington",
                      "email": "ap@legacygold.example.com", "phone": "555-0299", "contract_start": "2023-04-01"})

    technicians = [{"tech_id": t, "name": n, "skill": s, "on_call": oc, "epa_608": "yes" if s == "refrigeration" else "no"}
                   for t, n, s, oc in TECHS]

    equipment, by_customer = [], {}
    eq = 1000
    for cid in plans:
        for _ in range(rng.randint(1, 2)):
            eq += 1
            kind = rng.choice(list(KINDS))
            equipment.append({"equipment_id": f"EQ-{eq}", "customer_id": cid, "kind": kind,
                              "installed_on": (ANCHOR - timedelta(days=rng.randint(100, 3000))).date().isoformat()})
            by_customer.setdefault(cid, []).append((f"EQ-{eq}", kind))
    # anchor equipment with the kinds the dispatch cases need
    for cid, kind in (("CU-004", "heat pump"), ("CU-012", "rooftop unit"), ("CU-020", "walk-in cooler")):
        eq += 1
        equipment.append({"equipment_id": f"EQ-{eq}", "customer_id": cid, "kind": kind, "installed_on": "2022-05-10"})
        by_customer[cid].append((f"EQ-{eq}", kind))

    orders = []
    start = ANCHOR - timedelta(days=45)
    for n in range(1, n_orders + 1):
        wid = f"WO-{5000 + n}"
        cid = f"CU-{rng.randint(1, n_customers):03d}"
        equipment_id, kind = rng.choice(by_customer[cid])
        priority = "emergency" if rng.random() < 0.3 else "routine"
        opened = start + timedelta(minutes=rng.randint(0, 44 * 24 * 60))
        sla = SLA_HOURS[(plans[cid], priority)]
        r = rng.random()
        responded: datetime | None = opened + timedelta(hours=rng.uniform(0.5, sla * (0.9 if r < 0.8 else 1.6)))
        if responded and responded > ANCHOR:
            responded = None
        status = "closed" if responded and rng.random() < 0.85 else ("dispatched" if responded else "open")
        tech = rng.choice(TECHS)[0] if status != "open" else ""
        after_hours = "yes" if opened.hour >= 18 or opened.hour < 7 else "no"
        row = {"work_order_id": wid, "customer_id": cid, "equipment_id": equipment_id, "priority": priority,
               "opened_at": opened, "responded_at": responded, "status": status, "tech_id": tech,
               "after_hours": after_hours, "summary": f"{kind} - {'no heat' if priority == 'emergency' else 'service'}"}
        anchors = {
            "WO-5003": dict(customer_id="CU-010", priority="routine", status="dispatched", tech_id="T-04",
                            opened_at=ANCHOR - timedelta(hours=20), responded_at=ANCHOR - timedelta(hours=2)),
            "WO-5017": dict(customer_id="CU-004", priority="emergency", status="closed", tech_id="T-02",
                            opened_at=datetime(2026, 11, 2, 8, 0, tzinfo=UTC),
                            responded_at=datetime(2026, 11, 2, 15, 0, tzinfo=UTC), after_hours="no"),
            "WO-5040": dict(customer_id="CU-004", priority="emergency", status="open", tech_id="",
                            opened_at=ANCHOR + timedelta(hours=4), responded_at=None, after_hours="yes",
                            summary="heat pump - no heat, outdoor 34 F"),
            "WO-5041": dict(customer_id="CU-012", priority="emergency", status="open", tech_id="",
                            opened_at=ANCHOR + timedelta(hours=4, minutes=20), responded_at=None, after_hours="yes",
                            summary="rooftop unit - no cooling in server room"),
            "WO-5042": dict(customer_id="CU-020", priority="emergency", status="open", tech_id="",
                            opened_at=ANCHOR + timedelta(hours=4, minutes=40), responded_at=None, after_hours="yes",
                            summary="walk-in cooler - suspected refrigerant leak"),
            "WO-5060": dict(customer_id="CU-007", priority="routine", status="closed", tech_id="T-01",
                            opened_at=datetime(2026, 11, 3, 9, 0, tzinfo=UTC),
                            responded_at=datetime(2026, 11, 5, 21, 0, tzinfo=UTC), after_hours="no"),
        }
        if wid in anchors:
            row.update(anchors[wid])
            kinds = {"WO-5040": "heat pump", "WO-5041": "rooftop unit", "WO-5042": "walk-in cooler"}
            cust_eq = by_customer[row["customer_id"]]
            row["equipment_id"] = next((e for e, k in cust_eq if k == kinds.get(wid)), cust_eq[0][0])
        orders.append(row)

    out_orders = [{**o, "opened_at": _ts(rng, o["opened_at"]), "responded_at": _ts(rng, o["responded_at"])}
                  for o in orders]
    out_orders.extend(dict(o) for o in rng.sample(out_orders[60:], 3))  # exact duplicates (never anchors)
    out_orders.append({"work_order_id": "WO-9999", "customer_id": "CU-404", "equipment_id": "EQ-0000",
                       "priority": "routine", "opened_at": ANCHOR.isoformat(), "responded_at": "", "status": "open",
                       "tech_id": "", "after_hours": "no", "summary": "orphan row from an old import"})

    files = {"customers.csv": customers, "technicians.csv": technicians, "equipment.csv": equipment,
             "work_orders.csv": out_orders}
    for fname, rows in files.items():
        with (out_dir / fname).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    return {name.removesuffix(".csv"): len(rows) for name, rows in files.items()}


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "data" / "tables"
    print(f"seeded coastline-hvac: {generate(target)}")
