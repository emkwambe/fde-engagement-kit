"""Sprint 01 Phase 3b: engagement #2 (Coastline Climate Services, fictional) runs on the unchanged kit.

Run: uv run pytest tests/day05/test_coastline_hvac.py -v
The mock CMMS runs in-process (TestClient), so no second window is needed.
"""

from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

from core.agent.graph import agent_model, agent_tools, ask, build_agent, decide
from core.config import load_engagement, resolve_path
from core.evals.golden import MINIMUM_PER_CATEGORY, load_golden
from core.extensions import load_module
from core.ingest.chunking import split_markdown
from core.ingest.documents import list_document_files, read_document
from core.llm.factory import get_embeddings
from core.rag.answer import Citation

CMMS_PATH = Path("services/mock-cmms/app.py")


@pytest.fixture(scope="module")
def hvac_cfg():
    return load_engagement("coastline-hvac")


def _cmms_module():
    spec = importlib.util.spec_from_file_location("mock_cmms_app", CMMS_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def cmms(hvac_cfg, tmp_path):
    load_module(str(hvac_cfg.sources.tables[0].seed_script)).generate(tmp_path / "tables")
    app = _cmms_module().create_app(data_dir=tmp_path / "tables", dispatches_file=tmp_path / "dispatches.json",
                                     token="tok")
    with TestClient(app) as client:
        yield client


# ----------------------------------------------------------------------------- the golden set
def test_golden_set_meets_the_test_strategy_minimums(hvac_cfg):
    cases = load_golden(resolve_path(hvac_cfg.evals.golden_set))
    counts = Counter(c.category for c in cases)
    assert len(cases) >= 27 and all(counts[k] >= v for k, v in MINIMUM_PER_CATEGORY.items()), counts


def test_every_expected_source_exists_in_the_documents(hvac_cfg):
    refs = set()
    for path in list_document_files(hvac_cfg):
        _, text = read_document(path)
        for chunk in split_markdown(text, hvac_cfg.retrieval.chunk_size, hvac_cfg.retrieval.chunk_overlap):
            refs.add(Citation(path.name, chunk.section, "x").ref)
    wanted = {r for c in load_golden(resolve_path(hvac_cfg.evals.golden_set)) for r in c.expected_sources}
    assert wanted <= refs, wanted - refs


# ----------------------------------------------------------------------------- the mock CMMS
def test_cmms_contract_matches_the_committed_spec(tmp_path):
    """Drift test: the spec the tool generator reads must be exactly what the service serves."""
    served = _cmms_module().create_app(load_data=False).openapi()
    committed = yaml.safe_load(Path("services/mock-cmms/openapi.yaml").read_text(encoding="utf-8"))
    assert served == committed, "Run: uv run python services/mock-cmms/app.py export-spec"


def test_cmms_enforces_its_business_rules(cmms):
    auth = {"Authorization": "Bearer tok"}
    assert cmms.get("/work-orders/WO-5040").status_code == 401
    assert cmms.get("/work-orders/WO-5040", headers=auth).json()["equipment_kind"] == "heat pump"
    base = {"work_order_id": "WO-5040", "priority": "emergency", "after_hours_fee_usd": 0, "reason": "WO-5040 test"}
    assert cmms.post("/dispatches", headers=auth, json={**base, "tech_id": "T-01"}).status_code == 409  # not on call
    assert cmms.post("/dispatches", headers=auth, json={**base, "tech_id": "T-05"}).status_code == 409  # wrong skill
    assert cmms.post("/dispatches", headers=auth, json={**base, "tech_id": "T-02", "after_hours_fee_usd": 500}).status_code == 422
    assert cmms.post("/dispatches", headers=auth, json={**base, "tech_id": "T-02"}).status_code == 201
    assert cmms.post("/dispatches", headers=auth, json={**base, "tech_id": "T-02"}).status_code == 409  # only once


# ----------------------------------------------------------------------------- the agent, end to end (fake model)
@pytest.fixture
def hvac_db(migrated_db, hvac_cfg, tmp_path):
    """Engagement #2's schema and data in the test database, loaded exactly like `migrate` + `ingest` do."""
    from core.db.connection import connect
    from core.db.migrate import apply_engagement_sql, ensure_readonly_role
    from core.ingest.etl import run_tabular_etl, table_specs

    apply_engagement_sql(hvac_cfg)
    ensure_readonly_role(schemas=("ops", "field"))
    src = hvac_cfg.sources.tables[0]
    load_module(str(src.seed_script)).generate(tmp_path / "db-tables")
    with connect() as conn:
        results = {r.table: r for r in run_tabular_etl(conn, "coastline-hvac", tmp_path / "db-tables", "field",
                                                       table_specs(src))}
        conn.commit()
    return migrated_db, results


@pytest.mark.db
def test_etl_loads_engagement_two_with_its_mess_handled(hvac_db):
    _, results = hvac_db
    assert (results["customers"].rows_loaded, len(results["customers"].rejected)) == (30, 1)        # plan "Gold"
    assert (results["work_orders"].rows_loaded, results["work_orders"].duplicates) == (120, 3)
    assert [r["reason"] for r in results["work_orders"].rejected] == ["unknown customer_id 'CU-404'"]


@pytest.mark.db
def test_a_dispatch_pauses_for_approval_and_runs_only_after_it(hvac_cfg, cmms, hvac_db):
    from core.config.schema import SQLTool

    url, _ = hvac_db
    openapi = hvac_cfg.tools.openapi[0].model_copy(update={
        "base_url": "http://testserver", "auth": hvac_cfg.tools.openapi[0].auth.model_copy(update={"token": "tok"})})
    sql = SQLTool(dsn=url.replace("fde:fde@", "agent_ro:agent_ro@"), schema="field", row_limit=50)
    cfg = hvac_cfg.model_copy(update={"tools": hvac_cfg.tools.model_copy(update={"openapi": [openapi], "sql": sql})})
    tools = agent_tools(cfg, get_embeddings(cfg.embeddings), http_client=cmms)
    assert {t.name for t in tools} == {"search_documents", "query_ops_db", "getWorkOrder", "listWorkOrders",
                                       "createDispatch"}
    agent = build_agent(cfg, tools, agent_model(cfg), checkpointer=InMemorySaver())

    paused = ask(agent, cfg, "t-dsp", "Dispatch the on-call technician to WO-5041 with the right after-hours fee.")
    assert paused.status == "needs_approval" and cmms.app.state.store.dispatches == {}      # nothing written yet
    assert {k: paused.pending[0]["args"][k] for k in ("work_order_id", "tech_id", "after_hours_fee_usd")} == \
        {"work_order_id": "WO-5041", "tech_id": "T-05", "after_hours_fee_usd": 150}

    done = decide(agent, cfg, "t-dsp", approved=True, by="dispatcher")
    assert done.status == "done" and "DSP-0001" in done.answer
    assert [d.tech_id for d in cmms.app.state.store.dispatches.values()] == ["T-05"]

    turn = ask(agent, cfg, "t-wo", "What is the status of work order WO-5003?")
    assert turn.status == "done" and "dispatched" in turn.answer and "T-04" in turn.answer
    missing = ask(agent, cfg, "t-missing", "What is the status of work order WO-0000?")
    assert "not found" in missing.answer


def test_engagement_two_brings_its_own_prompt_fake_and_refusal_text(hvac_cfg):
    from core.agent.graph import system_prompt

    text, version = system_prompt(hvac_cfg)
    assert version == "hvac-agent-v1" and "dispatch" in text and "shipment" not in text.lower()
    assert type(agent_model(hvac_cfg)).__module__.startswith("fde_ext_")  # loaded from the engagement folder
    assert "work orders" in hvac_cfg.guardrails.blocked_answer
