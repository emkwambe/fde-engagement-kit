"""Day 2, part 1: the mock ERP behaves like a real, protected legacy API.

Run: uv run pytest tests/day02/test_mock_erp.py -v
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from tests.helpers import generate_logistics

ERP_DIR = Path("services/mock-erp")
AUTH = {"Authorization": "Bearer test-token"}


def _load_module():
    spec = importlib.util.spec_from_file_location("mock_erp_app", ERP_DIR / "app.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def client(tmp_path):
    generate_logistics(tmp_path / "tables")
    erp = _load_module()
    app = erp.create_app(shipments_csv=tmp_path / "tables" / "shipments.csv",
                         tickets_file=tmp_path / "tickets.json", token="test-token")
    with TestClient(app) as c:
        yield c


VALID_TICKET = {"order_id": "ORD-1043", "customer_id": "C-007", "days_late": 3, "credit_percent": 15,
                "credit_amount_usd": 723.0, "reason": "Gold SLA credit, 3 days late", "priority": "P2"}


def test_health_needs_no_token(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["shipments_loaded"] == 500


def test_business_endpoints_require_token(client):
    assert client.get("/shipments/SHP-2207").status_code == 401
    assert client.get("/shipments/SHP-2207", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.post("/tickets", json=VALID_TICKET).status_code == 401


def test_get_shipment(client):
    r = client.get("/shipments/SHP-2207", headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["order_id"] == "ORD-1207"
    assert body["last_status"] == "Arrived at hub - Charlotte, NC"
    assert client.get("/shipments/shp-2207", headers=AUTH).status_code == 200  # case-insensitive id
    assert client.get("/shipments/SHP-0000", headers=AUTH).status_code == 404


def test_list_shipments_filters(client):
    by_order = client.get("/shipments", params={"order_id": "ORD-1043"}, headers=AUTH).json()
    assert [s["shipment_id"] for s in by_order] == ["SHP-2043"]
    at_hub = client.get("/shipments", params={"status_contains": "charlotte", "limit": 5}, headers=AUTH).json()
    assert at_hub and all("charlotte" in s["last_status"].lower() for s in at_hub)


def test_create_and_get_ticket(client, tmp_path):
    r = client.post("/tickets", json=VALID_TICKET, headers={**AUTH, "X-Client": "pytest"})
    assert r.status_code == 201
    ticket = r.json()
    assert ticket["ticket_id"] == "TCK-0001" and ticket["status"] == "open" and ticket["created_by"] == "pytest"
    assert client.get(f"/tickets/{ticket['ticket_id']}", headers=AUTH).json()["credit_amount_usd"] == 723.0
    assert (tmp_path / "tickets.json").exists(), "tickets must persist to disk"


@pytest.mark.parametrize("field,value", [("credit_percent", 50), ("days_late", 0),
                                         ("order_id", "1043"), ("reason", "x")])
def test_ticket_validation_rejects_bad_input(client, field, value):
    bad = {**VALID_TICKET, field: value}
    assert client.post("/tickets", json=bad, headers=AUTH).status_code == 422


def test_committed_spec_matches_the_app():
    """Contract test: the spec the agent reads must be exactly what the service serves."""
    committed = yaml.safe_load((ERP_DIR / "openapi.yaml").read_text(encoding="utf-8"))
    ops = {op["operationId"] for path in committed["paths"].values() for op in path.values()}
    assert {"getShipment", "listShipments", "createTicket", "getTicket"} <= ops
    erp = _load_module()
    assert committed == yaml.safe_load(yaml.safe_dump(erp.create_app(load_data=False).openapi(), sort_keys=False)), \
        "openapi.yaml is out of date. Run: .\\tasks.ps1 erp-spec"
