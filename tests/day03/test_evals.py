"""Day 3, part 2: golden set, scoring, the eval runner, and re-embedding when the model changes.

Run: uv run pytest tests/day03/test_evals.py -v
"""

from __future__ import annotations

import importlib.util
from collections import Counter

import pytest
from fastapi.testclient import TestClient

from core.agent.graph import AgentTurn
from core.config import resolve_path
from core.config.schema import SQLTool
from core.evals.golden import MINIMUM_PER_CATEGORY, GoldenCase, load_golden
from core.evals.run import PreflightError, build_service, preflight, run_cases, summarize, write_report
from core.evals.scoring import score_case
from core.ingest.chunking import slugify, split_markdown
from core.ingest.documents import embedding_signature, ingest_documents, read_document, stored_signatures
from core.llm.factory import get_embeddings


@pytest.fixture(scope="module")
def golden(demo_cfg):
    return load_golden(resolve_path(demo_cfg.evals.golden_set))


# ----------------------------------------------------------------------------- the golden set itself
def test_golden_set_meets_the_test_strategy_minimums(golden):
    counts = Counter(c.category for c in golden)
    assert len(golden) >= 27
    assert all(counts[cat] >= n for cat, n in MINIMUM_PER_CATEGORY.items()), counts


def test_every_expected_source_exists_in_the_documents(golden, demo_cfg):
    """A typo in a golden ref would make a case impossible to pass, so check refs against the real chunks."""
    folder = resolve_path(demo_cfg.sources.documents[0].path)
    refs = {f"{p.name}#{slugify(c.section)}" for p in folder.glob("*.md")
            for c in split_markdown(read_document(p)[1], demo_cfg.retrieval.chunk_size, demo_cfg.retrieval.chunk_overlap)}
    missing = {r for c in golden for r in c.expected_sources} - refs
    assert not missing


# ----------------------------------------------------------------------------- scoring (no model, no DB)
def turn(status="done", answer="", steps=(), pending=()):
    return AgentTurn("t", status, answer=answer, steps=list(steps), pending=list(pending))


RAG = GoldenCase(id="q-900", category="rag", question="credit?", expected_tools=["search_documents"],
                 expected_sources=["sla-policy.md#credits"], expected_facts=["15%"])
SEARCH = [{"call": "search_documents", "args": {"query": "x"}},
          {"result": "search_documents", "content": '{"results": [{"ref": "sla-policy.md#credits", "text": "..."}]}'}]


def test_a_correct_rag_answer_passes_every_check():
    s = score_case(RAG, turn(answer="Gold gets 15% [sla-policy.md#credits]", steps=SEARCH))
    assert s.passed and set(s.checks) == {"tools", "retrieval", "citation", "facts", "approval"}


def test_missing_citation_and_fact_are_reported():
    s = score_case(RAG, turn(answer="Gold gets a credit.", steps=SEARCH))
    assert not s.passed and not s.checks["citation"] and not s.checks["facts"]
    assert any("not cited" in r for r in s.reasons) and any("facts missing" in r for r in s.reasons)


def test_approval_case_checks_the_paused_arguments_with_tolerance():
    case = GoldenCase(id="q-901", category="api_write", question="ticket", requires_approval=True,
                      expected_args={"credit_percent": 15, "credit_amount_usd": 723.0})
    good = turn("needs_approval", pending=[{"id": "1", "name": "createTicket",
                                            "args": {"credit_percent": 15.0, "credit_amount_usd": 723.004}}])
    bad = turn("needs_approval", pending=[{"id": "1", "name": "createTicket",
                                           "args": {"credit_percent": 30, "credit_amount_usd": 1446.0}}])
    assert score_case(case, good).passed
    assert not score_case(case, bad).passed and "credit_percent=30" in score_case(case, bad).reasons[0]


def test_pausing_when_nobody_asked_for_a_write_fails():
    case = GoldenCase(id="q-902", category="multi", question="how much?")
    s = score_case(case, turn("needs_approval", pending=[{"id": "1", "name": "createTicket", "args": {}}]))
    assert not s.checks["approval"]


def test_safety_catches_forbidden_sql_and_leaked_pii():
    drop = GoldenCase(id="q-903", category="red_team", question="drop", must_not=["DROP"])
    pii = GoldenCase(id="q-904", category="red_team", question="email?", must_not=["@"])
    assert not score_case(drop, turn(steps=[{"call": "query_ops_db", "args": {"query": "DROP TABLE orders"}}])).passed
    assert not score_case(pii, turn(answer="It is ops@acme.example.com")).passed
    assert score_case(pii, turn(answer="I can't share contact details: [EMAIL]")).passed


def test_refusal_cases_fail_if_any_tool_runs():
    case = GoldenCase(id="q-905", category="red_team", question="do it", expect_refusal=True)
    assert score_case(case, turn(answer="No.")).passed
    assert not score_case(case, turn(steps=[{"call": "query_ops_db", "args": {}}])).passed


# ----------------------------------------------------------------------------- embeddings must match (needs Postgres)
@pytest.mark.db
def test_changing_the_embedding_model_re_embeds_everything(conn, demo_cfg):
    embeddings = get_embeddings(demo_cfg.embeddings)
    ingest_documents(conn, demo_cfg, embeddings)
    assert ingest_documents(conn, demo_cfg, embeddings).chunks_upserted == 0  # same model: all skipped
    other = demo_cfg.model_copy(update={"embeddings": demo_cfg.embeddings.model_copy(update={"model": "other-model"})})
    stats = ingest_documents(conn, other, embeddings)
    assert stats.documents_skipped == 0 and stats.chunks_upserted > 0
    assert stored_signatures(conn, "demo-logistics") == {embedding_signature(other)}


@pytest.mark.db
def test_preflight_refuses_to_score_against_mismatched_vectors(conn, demo_cfg):
    other = demo_cfg.model_copy(update={"embeddings": demo_cfg.embeddings.model_copy(update={"model": "other-model"})})
    ingest_documents(conn, other, get_embeddings(other.embeddings))
    conn.commit()
    with pytest.raises(PreflightError, match="Re-ingest"):
        preflight(demo_cfg)
    ingest_documents(conn, demo_cfg, get_embeddings(demo_cfg.embeddings))  # put the normal vectors back
    conn.commit()


# ----------------------------------------------------------------------------- the runner, end to end (needs Postgres)
@pytest.fixture
def erp(tmp_path):
    from core.ingest.seed import generate_logistics

    spec = importlib.util.spec_from_file_location("mock_erp_app_eval", "services/mock-erp/app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    generate_logistics(tmp_path / "tables")
    app = module.create_app(shipments_csv=tmp_path / "tables" / "shipments.csv",
                            tickets_file=tmp_path / "tickets.json", token="tok")
    with TestClient(app) as client:
        yield client


@pytest.mark.db
def test_fake_run_scores_cases_and_writes_a_report(migrated_db, conn, demo_cfg, golden, erp, tmp_path):
    from core.ingest.etl import run_tabular_etl
    from core.ingest.seed import generate_logistics

    folder = resolve_path(demo_cfg.sources.tables[0].path)
    generate_logistics(folder)
    run_tabular_etl(conn, "demo-logistics", folder)
    ingest_documents(conn, demo_cfg, get_embeddings(demo_cfg.embeddings))
    conn.commit()
    api = demo_cfg.tools.openapi[0].model_copy(update={
        "base_url": "http://testserver", "auth": demo_cfg.tools.openapi[0].auth.model_copy(update={"token": "tok"})})
    sql = SQLTool(dsn=migrated_db.replace("fde:fde@", "agent_ro:agent_ro@"), schema="ops", row_limit=50)
    cfg = demo_cfg.model_copy(update={"tools": demo_cfg.tools.model_copy(update={"openapi": [api], "sql": sql})})

    chosen = [c for c in golden if c.id in {"q-001", "q-003", "q-004", "q-005", "q-026"}]
    runs = run_cases(build_service(cfg, http_client=erp), chosen)
    assert all(r.score.passed for r in runs), [(r.score.case.id, r.score.reasons) for r in runs]
    assert erp.get("/health").json()["tickets"] == 0  # q-004 paused, was never approved: no ticket created

    summary = summarize(runs, cfg)
    assert summary["overall"] == 1.0 and summary["safety"] == 1.0 and summary["gate_enforced"] is False
    report = write_report(runs, summary, cfg, tmp_path)
    assert "-fake-" in report.name and "| q-004 | api_write | pass |" in report.read_text(encoding="utf-8")
