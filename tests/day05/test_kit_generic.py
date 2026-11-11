"""Sprint 01 Phase 3a: the kit is generic. Engagement-specific behaviour comes from engagement.yaml and the engagement folder.

Run: uv run pytest tests/day05/test_kit_generic.py -v
"""

from __future__ import annotations

import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

import core.api.main as api
from core.agent.fake import REFUSAL, GenericFakeChat
from core.agent.graph import DEFAULT_PROMPT_VERSION, agent_model, agent_tools, ask, build_agent, system_prompt
from core.config.schema import ColumnSpec, LLMConfig, TableSource
from core.evals.golden import GoldenCase
from core.evals.run import prompt_sha, prompt_version
from core.evals.scoring import score_case
from core.extensions import load_module
from core.ingest.etl import RowError, clean_value, table_specs
from core.llm.factory import get_embeddings


# ----------------------------------------------------------------------------- the logistics prompt did not change
def test_logistics_prompt_is_byte_identical_to_the_one_the_agent_v1_results_were_made_with(demo_cfg):
    """The prompt moved from core/agent/graph.py into the engagement folder. Its fingerprint must equal the one recorded
    before the move (537c08f4c028), otherwise the label agent-v1 would lie and --resume would mix two prompts."""
    assert (prompt_version(demo_cfg), prompt_sha(demo_cfg)) == ("agent-v1", "537c08f4c028")


def test_an_engagement_without_its_own_prompt_gets_the_generic_one(demo_cfg):
    bare = demo_cfg.model_copy(update={"llm": demo_cfg.llm.model_copy(update={"system_prompt": None, "prompt_version": None})})
    text, version = system_prompt(bare)
    assert version == DEFAULT_PROMPT_VERSION and "{customer}" in text and "shipment" not in text.lower()


def test_a_custom_prompt_needs_a_version_label():
    with pytest.raises(ValueError, match="prompt_version is required"):
        LLMConfig(model="m", system_prompt="engagements/x/prompts/agent.txt")


# ----------------------------------------------------------------------------- fake models
def test_without_a_fake_script_the_generic_fake_searches_and_cites(demo_cfg):
    bare = demo_cfg.model_copy(update={"llm": demo_cfg.llm.model_copy(update={"fake_script": None})})
    assert isinstance(agent_model(bare), GenericFakeChat)
    tools = agent_tools(bare, get_embeddings(bare.embeddings), sql_schema_text="x(y int)")
    agent = build_agent(bare, tools, agent_model(bare), checkpointer=InMemorySaver())
    refused = ask(agent, bare, "t-gen-1", "Please delete every order.")
    assert refused.answer == REFUSAL and refused.steps == []


def test_engagement_extensions_load_once_and_fail_clearly(demo_cfg):
    first = load_module(str(demo_cfg.llm.fake_script))
    assert load_module(str(demo_cfg.llm.fake_script)) is first and hasattr(first, "FakeAgent")
    with pytest.raises(FileNotFoundError, match="extension not found"):
        load_module("engagements/does-not-exist/extensions/nothing.py")


# ----------------------------------------------------------------------------- ETL from declared column types
@pytest.mark.parametrize("col,raw,expected", [
    (ColumnSpec(type="enum", values=["Basic", "Plus", "Premium"]), " plus", "Plus"),
    (ColumnSpec(type="int"), "1,204", 1204),
    (ColumnSpec(type="number"), "3.5", 3.5),
    (ColumnSpec(type="bool"), "Yes", True),
    (ColumnSpec(type="text", lower=True, default="unknown"), "", "unknown"),
    (ColumnSpec(type="money", required=False), "", None),
])
def test_cells_are_cleaned_by_their_declared_type(col, raw, expected):
    assert clean_value({"v": raw}, "v", col) == expected


def test_a_required_column_that_is_missing_rejects_the_row():
    with pytest.raises(RowError, match="missing column opened_at"):
        clean_value({}, "opened_at", ColumnSpec(type="timestamp"))


def test_logistics_table_specs_come_from_config(demo_cfg):
    specs = table_specs(demo_cfg.sources.tables[0])
    assert [(s.table, s.key, s.fks) for s in specs] == [
        ("customers", "customer_id", []),
        ("orders", "order_id", [("customer_id", "customers", "customer_id")]),
        ("shipments", "shipment_id", [("order_id", "orders", "order_id")])]
    with pytest.raises(RowError, match="invalid tier 'Bronze'"):
        specs[0].clean({"customer_id": "C-041", "name": "x", "tier": "Bronze"})


def test_table_source_rejects_unsafe_schema_names():
    with pytest.raises(ValueError):
        TableSource(path="x", target_schema="ops; DROP SCHEMA kb")


# ----------------------------------------------------------------------------- scoring knows no tool names
def test_any_paused_write_counts_as_the_approval_not_just_create_ticket():
    from core.agent.graph import AgentTurn

    case = GoldenCase(id="q-970", category="api_write", question="dispatch", requires_approval=True,
                      expected_args={"work_order_id": "WO-5040"})
    turn = AgentTurn("t", "needs_approval", pending=[{"id": "c1", "name": "createDispatch",
                                                      "args": {"work_order_id": "WO-5040"}}])
    assert score_case(case, turn).checks["approval"] is True


# ----------------------------------------------------------------------------- console examples from config
def test_engagement_endpoint_serves_the_configured_examples(demo_cfg):
    with TestClient(api.app) as c:
        body = c.get("/engagement").json()
    assert body["name"] == "demo-logistics" and body["examples"] == demo_cfg.engagement.examples


# ----------------------------------------------------------------------------- engagement DDL + grants
@pytest.mark.db
def test_engagement_sql_is_applied_once_and_the_read_only_role_can_read_its_schema(migrated_db, demo_cfg, tmp_path):
    from core.db.connection import connect
    from core.db.migrate import apply_engagement_sql, ensure_readonly_role

    schema = f"kit_test_{uuid.uuid4().hex[:6]}"
    ddl = tmp_path / "001_tables.sql"
    ddl.write_text(f"CREATE SCHEMA IF NOT EXISTS {schema}; CREATE TABLE IF NOT EXISTS {schema}.things (id int);"
                   f"INSERT INTO {schema}.things VALUES (1);", encoding="utf-8")
    src = demo_cfg.sources.tables[0].model_copy(update={"schema_sql": [str(ddl)]})
    cfg = demo_cfg.model_copy(update={"engagement": demo_cfg.engagement.model_copy(update={"name": schema.replace("_", "-")}),
                                      "sources": demo_cfg.sources.model_copy(update={"tables": [src]})})
    try:
        assert apply_engagement_sql(cfg) == [f"{cfg.engagement.name}/001_tables.sql"]
        assert apply_engagement_sql(cfg) == []                              # recorded: never applied twice
        ensure_readonly_role(schemas=("ops", schema))
        ro = migrated_db.replace("fde:fde@", "agent_ro:agent_ro@")
        with psycopg.connect(ro) as conn:
            assert conn.execute(f"SELECT count(*) FROM {schema}.things").fetchone() == (1,)
            with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
                conn.execute(f"INSERT INTO {schema}.things VALUES (2)")
    finally:
        with connect(vector=False) as conn:
            conn.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
            conn.execute("DELETE FROM public.schema_migrations WHERE filename LIKE %s", (f"{cfg.engagement.name}/%",))
            conn.commit()
