"""Day 2, part 4: /chat runs the agent, approvals over HTTP, and the audit trail.

Run: uv run pytest tests/day02/test_approvals_api.py -v
The API's agent is swapped for one wired to an in-process mock ERP, so no second window is needed.
"""

from __future__ import annotations

import importlib.util
import uuid

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

import core.api.main as api
from core.agent.graph import agent_model, agent_tools, build_agent
from core.agent.service import AgentService
from core.config.schema import SQLTool
from core.db.connection import connect
from core.ingest.seed import generate_logistics
from core.llm.factory import get_embeddings

TICKET_REQUEST = "Open a credit ticket for ORD-1043 for the amount the policy allows."


@pytest.fixture
def erp(tmp_path):
    spec = importlib.util.spec_from_file_location("mock_erp_app_api", "services/mock-erp/app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    generate_logistics(tmp_path / "tables")
    app = module.create_app(shipments_csv=tmp_path / "tables" / "shipments.csv",
                            tickets_file=tmp_path / "tickets.json", token="tok")
    with TestClient(app) as client:
        yield client


@pytest.fixture
def client(migrated_db, conn, demo_cfg, erp):
    """The real API app, with its agent pointed at the in-process ERP and the read-only DB role."""
    from core.config import resolve_path
    from core.ingest.etl import run_tabular_etl

    folder = resolve_path(demo_cfg.sources.tables[0].path)
    generate_logistics(folder)
    run_tabular_etl(conn, "demo-logistics", folder)
    conn.commit()
    openapi = demo_cfg.tools.openapi[0].model_copy(update={
        "base_url": "http://testserver", "auth": demo_cfg.tools.openapi[0].auth.model_copy(update={"token": "tok"})})
    sql = SQLTool(dsn=migrated_db.replace("fde:fde@", "agent_ro:agent_ro@"), schema="ops", row_limit=50)
    cfg = demo_cfg.model_copy(update={"tools": demo_cfg.tools.model_copy(update={"openapi": [openapi], "sql": sql})})
    tools = agent_tools(cfg, get_embeddings(cfg.embeddings), http_client=erp)
    agent = build_agent(cfg, tools, agent_model(cfg), checkpointer=InMemorySaver())
    with TestClient(api.app) as c:
        api.state["service"] = AgentService(cfg, agent, db=lambda: connect(vector=False))
        yield c


@pytest.fixture
def thread(migrated_db):
    """A fresh thread id; its approval and audit rows are deleted afterwards so /approvals stays clean."""
    thread_id = f"t-api-{uuid.uuid4().hex[:8]}"
    yield thread_id
    with connect(vector=False) as c:
        c.execute("DELETE FROM agent.approvals WHERE thread_id = %s", (thread_id,))
        c.execute("DELETE FROM agent.audit_log WHERE thread_id = %s", (thread_id,))


# ----------------------------------------------------------------------------- no database needed
def test_health_reports_checkpointer_and_validates_input():
    with TestClient(api.app) as c:
        body = c.get("/health").json()
        assert body["engagement"] == "demo-logistics" and "checkpointer" in body
        assert c.post("/chat", json={"thread_id": "t", "message": ""}).status_code == 422
        assert c.post("/chat", json={"thread_id": "bad id!", "message": "hi"}).status_code == 422
        assert c.get("/").status_code == 200 and "Approve" in c.get("/").text


# ----------------------------------------------------------------------------- approval over HTTP
@pytest.mark.db
def test_chat_pauses_and_lists_the_pending_approval(client, thread):
    r = client.post("/chat", json={"thread_id": thread, "message": TICKET_REQUEST, "user": "ana"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "needs_approval" and body["pending"][0]["name"] == "createTicket"
    mine = [a for a in client.get("/approvals").json() if a["thread_id"] == thread]
    assert len(mine) == 1 and mine[0]["args"]["credit_amount_usd"] == 723.0


@pytest.mark.db
def test_chat_on_a_waiting_thread_is_a_conflict(client, thread):
    client.post("/chat", json={"thread_id": thread, "message": TICKET_REQUEST})
    r = client.post("/chat", json={"thread_id": thread, "message": "hello?"})
    assert r.status_code == 409 and "waiting" in r.json()["detail"]


@pytest.mark.db
def test_approve_runs_the_write_once(client, erp, thread):
    client.post("/chat", json={"thread_id": thread, "message": TICKET_REQUEST})
    r = client.post(f"/approvals/{thread}/approve", json={"by": "ana"})
    assert r.status_code == 200 and "Created ticket" in r.json()["answer"]
    again = client.post(f"/approvals/{thread}/approve", json={"by": "ana"})  # double click
    assert again.status_code == 409
    assert erp.get("/health").json()["tickets"] == 1
    assert all(a["thread_id"] != thread for a in client.get("/approvals").json())


@pytest.mark.db
def test_reject_needs_a_reason_and_never_writes(client, erp, thread):
    client.post("/chat", json={"thread_id": thread, "message": TICKET_REQUEST})
    assert client.post(f"/approvals/{thread}/reject", json={"by": "ana"}).status_code == 422
    r = client.post(f"/approvals/{thread}/reject", json={"by": "ana", "reason": "duplicate"})
    assert r.status_code == 200 and "NOT created" in r.json()["answer"]
    assert erp.get("/health").json()["tickets"] == 0


@pytest.mark.db
def test_approvals_table_records_who_decided(client, thread):
    client.post("/chat", json={"thread_id": thread, "message": TICKET_REQUEST})
    client.post(f"/approvals/{thread}/approve", json={"by": "ana"})
    with connect(vector=False) as c:
        row = c.execute("SELECT tool, status, decided_by, decided_at IS NOT NULL FROM agent.approvals "
                        "WHERE thread_id = %s", (thread,)).fetchone()
    assert row == ("createTicket", "approved", "ana", True)


@pytest.mark.db
def test_audit_log_tells_the_whole_story_without_storing_prompts(client, thread):
    client.post("/chat", json={"thread_id": thread, "message": TICKET_REQUEST, "user": "ana"})
    client.post(f"/approvals/{thread}/approve", json={"by": "ana"})
    events = client.get(f"/threads/{thread}/audit").json()
    assert [e["event"] for e in events] == [
        "user_message", "tool_call", "tool_result", "tool_call", "tool_result", "tool_call", "approval_requested",
        "approval_decided", "tool_result", "answer"]
    assert len({e["trace_id"] for e in events}) == 2  # one trace per HTTP request
    first = events[0]["detail"]
    assert first["user"] == "ana" and "sha256" in first and "text" not in first  # log_prompts: false
