"""Day 2, part 2: tools generated from the ERP's OpenAPI spec + the read-only SQL tool.

Run: uv run pytest tests/day02/test_toolgen.py -v
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from core.config.schema import OpenAPIAuth, OpenAPITool, SQLTool
from core.toolgen.openapi import tools_from_openapi
from core.toolgen.registry import build_tools, requires_approval
from core.toolgen.sql import SQLRejected, run_query, sql_tool, validate_sql
from tests.helpers import generate_logistics

SPEC = Path("services/mock-erp/openapi.yaml")
OPS = ["getShipment", "listShipments", "createTicket", "getTicket"]


@pytest.fixture
def erp_client(tmp_path):
    spec = importlib.util.spec_from_file_location("mock_erp_app_tg", "services/mock-erp/app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    generate_logistics(tmp_path / "tables")
    app = module.create_app(shipments_csv=tmp_path / "tables" / "shipments.csv",
                            tickets_file=tmp_path / "tickets.json", token="tok")
    with TestClient(app) as client:
        yield client


@pytest.fixture
def api_cfg():
    return OpenAPITool(spec=str(SPEC), base_url="http://testserver",
                       auth=OpenAPIAuth(type="bearer", token="tok"), include_operations=OPS)


def _tools(api_cfg, client):
    return {t.name: t for t in tools_from_openapi(api_cfg, SPEC, client=client)}


# ----------------------------------------------------------------------------- generation
def test_one_tool_per_operation_with_approval_flags(api_cfg, erp_client):
    tools = _tools(api_cfg, erp_client)
    assert sorted(tools) == sorted(OPS)
    assert requires_approval(tools["createTicket"]) is True
    assert not any(requires_approval(tools[n]) for n in ("getShipment", "listShipments", "getTicket"))
    assert "REQUIRES HUMAN APPROVAL" in tools["createTicket"].description


def test_auth_headers_are_never_tool_arguments(api_cfg, erp_client):
    for tool in _tools(api_cfg, erp_client).values():
        assert not {"authorization", "x-client"} & {a.lower() for a in tool.args}


def test_contract_rules_are_copied_into_arguments(api_cfg, erp_client):
    props = _tools(api_cfg, erp_client)["createTicket"].args
    assert props["credit_percent"]["maximum"] == 35
    assert props["order_id"]["pattern"] == r"^ORD-\d+$"
    assert set(props["priority"]["enum"]) == {"P1", "P2", "P3", "P4"}


# ----------------------------------------------------------------------------- calling
def test_get_shipment_calls_the_real_api(api_cfg, erp_client):
    out = json.loads(_tools(api_cfg, erp_client)["getShipment"].invoke({"shipment_id": "SHP-2207"}))
    assert out["last_status"] == "Arrived at hub - Charlotte, NC"


def test_list_shipments_passes_query_params(api_cfg, erp_client):
    out = json.loads(_tools(api_cfg, erp_client)["listShipments"].invoke({"order_id": "ORD-1043"}))
    assert [s["shipment_id"] for s in out] == ["SHP-2043"]


def test_http_errors_come_back_as_data_not_crashes(api_cfg, erp_client):
    out = json.loads(_tools(api_cfg, erp_client)["getShipment"].invoke({"shipment_id": "SHP-0000"}))
    assert out == {"error": "Shipment SHP-0000 not found", "status": 404}


def test_create_ticket_sends_body_and_identifies_the_agent(api_cfg, erp_client):
    args = {"order_id": "ORD-1043", "customer_id": "C-007", "days_late": 3, "credit_percent": 15,
            "credit_amount_usd": 723.0, "reason": "Gold SLA credit, 3 days late", "priority": "P2"}
    out = json.loads(_tools(api_cfg, erp_client)["createTicket"].invoke(args))
    assert out["ticket_id"] == "TCK-0001" and out["created_by"] == "fde-agent"


def test_bad_arguments_never_leave_our_side(api_cfg, erp_client):
    args = {"order_id": "ORD-1043", "customer_id": "C-007", "days_late": 3, "credit_percent": 50,
            "credit_amount_usd": 723.0, "reason": "too generous"}
    with pytest.raises(ValidationError):
        _tools(api_cfg, erp_client)["createTicket"].invoke(args)
    assert erp_client.get("/health").json()["tickets"] == 0


def test_registry_builds_all_tools_from_engagement_config(demo_cfg, erp_client):
    tools = build_tools(demo_cfg, http_client=erp_client, sql_schema_text="orders(order_id text)")
    assert [t.name for t in tools] == ["query_ops_db", *[t.name for t in tools[1:]]]
    assert {t.name for t in tools} == {"query_ops_db", *OPS}


# ----------------------------------------------------------------------------- SQL guard (no DB needed)
@pytest.mark.parametrize("query", [
    "SELECT * FROM orders", "select count(*) from orders;", "WITH x AS (SELECT 1) SELECT * FROM x",
    "SELECT order_id FROM sla_breaches -- late ones",
])
def test_validate_sql_accepts_reads(query):
    assert validate_sql(query)


@pytest.mark.parametrize("query,reason", [
    ("DELETE FROM orders", "only SELECT"),
    ("SELECT 1; DROP TABLE orders", "one statement"),
    ("WITH d AS (DELETE FROM orders RETURNING *) SELECT * FROM d", "DELETE"),
    ("SELECT pg_sleep(10)", "PG_SLEEP"),
    ("", "empty"),
])
def test_validate_sql_rejects_writes_and_tricks(query, reason):
    with pytest.raises(SQLRejected, match=reason):
        validate_sql(query)


# ----------------------------------------------------------------------------- SQL tool (needs Postgres)
@pytest.fixture
def ro_cfg(migrated_db, conn, demo_cfg):
    from core.config import resolve_path
    from core.ingest.etl import run_tabular_etl
    from tests.helpers import logistics_specs

    folder = resolve_path(demo_cfg.sources.tables[0].path)
    generate_logistics(folder)
    run_tabular_etl(conn, "demo-logistics", folder, "ops", logistics_specs())
    conn.commit()
    return SQLTool(dsn=migrated_db.replace("fde:fde@", "agent_ro:agent_ro@"), schema="ops", row_limit=5)


@pytest.mark.db
def test_sql_tool_answers_data_questions(ro_cfg):
    out = run_query(ro_cfg, "SELECT order_id, tier, days_late FROM sla_breaches WHERE order_id = 'ORD-1043'")
    assert out["rows"] == [["ORD-1043", "Gold", 3]]


@pytest.mark.db
def test_sql_tool_enforces_row_limit(ro_cfg):
    out = run_query(ro_cfg, "SELECT order_id FROM orders")
    assert out["row_count"] == 5 and out["truncated"] is True


@pytest.mark.db
def test_sql_tool_describes_tables_and_returns_errors_as_data(ro_cfg):
    tool = sql_tool(ro_cfg)
    assert "orders(" in tool.description and "sla_breaches(" in tool.description
    assert "query rejected" in tool.invoke({"query": "DELETE FROM orders"})
    assert "database error" in tool.invoke({"query": "SELECT * FROM no_such_table"})
