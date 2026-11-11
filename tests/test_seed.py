import csv

from tests.helpers import generate_logistics


def _read(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_seed_is_deterministic(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    generate_logistics(a)
    generate_logistics(b)
    for name in ("customers.csv", "orders.csv", "shipments.csv"):
        assert (a / name).read_bytes() == (b / name).read_bytes()


def test_seed_contains_golden_anchors_and_mess(tmp_path):
    generate_logistics(tmp_path)
    orders = _read(tmp_path / "orders.csv")
    ships = {s["shipment_id"]: s for s in _read(tmp_path / "shipments.csv")}
    o1043 = next(o for o in orders if o["order_id"] == "ORD-1043")
    assert o1043["customer_id"] == "C-007"
    assert ships["SHP-2207"]["last_status"].startswith("Arrived at hub")
    ids = [o["order_id"] for o in orders]
    assert len(ids) - len(set(ids)) == 5  # duplicates injected
    assert any(o["customer_id"] == "C-404" for o in orders)  # orphan injected
