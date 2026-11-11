"""Day 3, part 2: lessons from the first real-model eval runs (DC-016).

Run 1 against gpt-6-luna: every model call failed with HTTP 400 "Unsupported parameter: 'temperature'".
Run 2: the account's daily request quota (50/day) ran out after 18 cases, and q-018 failed an exact-wording
fact check. Its stored answer revealed a real bug: the model returns content as a LIST of blocks, and the
agent showed users str(list). These tests pin the fixes: temperature is opt-in, answers are plain text,
crashes are reported first, a daily quota stops the run cleanly (cases marked NOT RUN, resumable),
account ids are masked in reports, and facts accept alternative wordings ("a|b") and curly quotes.

Run: uv run pytest tests/day03/test_model_params.py -v
"""

from __future__ import annotations

from typing import Any

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import InMemorySaver

from core.agent.graph import AgentTurn, agent_tools, ask, build_agent
from core.config.schema import LLMConfig
from core.evals.golden import GoldenCase
from core.evals.run import build_service, case_hash, load_previous, mask_ids, run_cases, summarize, write_report
from core.evals.scoring import score_case
from core.llm.factory import get_chat_model, get_embeddings

BLOCKS = [{"type": "text", "text": "Shipment **SHP-0000** wasn\u2019t found, so I can\u2019t retrieve its status.",
           "annotations": [], "id": "msg_123", "phase": "final_answer"}]


class BlockContentChat(BaseChatModel):
    """Answers like gpt-6-luna does: content is a list of blocks, not a string."""

    @property
    def _llm_type(self) -> str:
        return "block-content-fake"

    def bind_tools(self, tools: Any, **kwargs: Any) -> BlockContentChat:  # type: ignore[override]
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=BLOCKS))])


class OpenAIRateLimitError(Exception):
    """Stand-in with the same class name the provider client raises."""


def _payload_keys(cfg: LLMConfig) -> set[str]:
    model = get_chat_model(cfg)
    return set(model._get_request_payload([("user", "hi")]).keys())  # type: ignore[attr-defined]


def test_temperature_is_not_sent_unless_configured(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-used")  # building the request needs a key, not the network
    assert "temperature" not in _payload_keys(LLMConfig(provider="openai", model="gpt-6-luna"))
    assert "temperature" in _payload_keys(LLMConfig(provider="openai", model="some-model", temperature=0))


def test_demo_engagement_leaves_temperature_unset(demo_cfg):
    assert demo_cfg.llm.temperature is None


def test_a_crashing_case_is_reported_with_the_crash_first(demo_cfg):
    service = build_service(demo_cfg, sql_schema_text="x(y int)")

    def broken_chat(*args, **kwargs):
        raise RuntimeError("Error code: 400 - Unsupported parameter")

    service.chat = broken_chat  # type: ignore[method-assign]
    case = GoldenCase(id="q-950", category="rag", question="anything", expected_tools=["search_documents"])
    run = run_cases(service, [case])[0]
    assert not run.score.passed and run.score.checks["no_crash"] is False
    assert run.score.reasons[0].startswith("CRASH RuntimeError: Error code: 400")


def test_a_fact_can_accept_alternative_wordings():
    case = GoldenCase(id="q-951", category="api_read", question="status?", expected_facts=["not found|does not exist"])
    assert score_case(case, AgentTurn("t", "done", answer="SHP-0000 does not exist in the ERP.")).passed
    assert not score_case(case, AgentTurn("t", "done", answer="It is in Charlotte.")).passed


def test_account_ids_are_masked():
    text = "Rate limit reached in organization org-Ab12Cd34Ef56Gh78Ij90Kl12 on requests per day"
    assert mask_ids(text) == "Rate limit reached in organization org-*** on requests per day"


# ----------------------------------------------------------------------------- daily quota: stop, report, resume
CASES = [GoldenCase(id=f"q-96{i}", category="red_team", question=f"question {i}", must_not=["createTicket"])
         for i in range(3)]


def _quota_after(service, ok_calls: int):
    real_chat, calls = service.chat, {"n": 0}

    def chat(thread_id, message, user="anonymous"):
        calls["n"] += 1
        if calls["n"] > ok_calls:
            raise OpenAIRateLimitError("Error code: 429 - organization org-abcdef123456 requests per day (RPD): Limit 50")
        return real_chat(thread_id, message, user=user)

    service.chat = chat  # type: ignore[method-assign]
    return service


def test_daily_quota_stops_the_run_and_marks_the_rest_not_run(demo_cfg, tmp_path):
    service = _quota_after(build_service(demo_cfg, sql_schema_text="x(y int)"), ok_calls=1)
    runs = run_cases(service, CASES)
    assert [r.not_run for r in runs] == [False, True, True]
    summary = summarize(runs, demo_cfg)
    assert (summary["ran"], summary["not_run"], summary["complete"], summary["gate_passed"]) == (1, 2, False, False)
    text = write_report(runs, summary, demo_cfg, tmp_path).read_text(encoding="utf-8")
    assert "INCOMPLETE" in text and "NOT RUN" in text and "org-***" in text and "abcdef123456" not in text


def test_resume_reuses_finished_cases_and_runs_only_the_rest(demo_cfg, tmp_path):
    first = run_cases(_quota_after(build_service(demo_cfg, sql_schema_text="x(y int)"), ok_calls=1), CASES)
    report = write_report(first, summarize(first, demo_cfg), demo_cfg, tmp_path)
    previous = load_previous(report.with_suffix(".json"), CASES, demo_cfg)
    assert list(previous) == ["q-960"] and previous["q-960"].resumed

    todo = [c for c in CASES if c.id not in previous]
    fresh = {r.score.case.id: r for r in run_cases(build_service(demo_cfg, sql_schema_text="x(y int)"), todo)}
    runs = [previous.get(c.id) or fresh[c.id] for c in CASES]
    summary = summarize(runs, demo_cfg)
    assert (summary["ran"], summary["not_run"], summary["resumed"], summary["complete"]) == (3, 0, 1, True)


def test_resume_refuses_results_from_another_model(demo_cfg, tmp_path):
    runs = run_cases(build_service(demo_cfg, sql_schema_text="x(y int)"), CASES[:1])
    report = write_report(runs, summarize(runs, demo_cfg), demo_cfg, tmp_path)
    other = demo_cfg.model_copy(update={"llm": demo_cfg.llm.model_copy(update={"model": "another-model"})})
    with pytest.raises(ValueError, match="same model and prompt"):
        load_previous(report.with_suffix(".json"), CASES, other)


def test_resume_reruns_edited_cases_and_explicit_reruns(demo_cfg, tmp_path):
    runs = run_cases(build_service(demo_cfg, sql_schema_text="x(y int)"), CASES)
    path = write_report(runs, summarize(runs, demo_cfg), demo_cfg, tmp_path).with_suffix(".json")
    edited = [CASES[0].model_copy(update={"must_not": ["createTicket", "DROP"]}), *CASES[1:]]
    assert case_hash(edited[0]) != case_hash(CASES[0])
    assert list(load_previous(path, edited, demo_cfg)) == ["q-961", "q-962"]          # edited case runs again
    assert list(load_previous(path, CASES, demo_cfg, rerun=("q-962",))) == ["q-960", "q-961"]


# ----------------------------------------------------------------------------- answers must be plain text
def test_answers_from_content_block_models_are_plain_text(demo_cfg):
    tools = agent_tools(demo_cfg, get_embeddings(demo_cfg.embeddings), sql_schema_text="x(y int)")
    agent = build_agent(demo_cfg, tools, BlockContentChat(), checkpointer=InMemorySaver())
    turn = ask(agent, demo_cfg, "t-blocks", "What is the status of shipment SHP-0000?")
    assert turn.answer == "Shipment **SHP-0000** wasn\u2019t found, so I can\u2019t retrieve its status."
    assert "'type'" not in turn.answer and "msg_123" not in turn.answer


def test_curly_quotes_count_as_straight_ones():
    case = GoldenCase(id="q-952", category="api_read", question="status?", expected_facts=["wasn't found"])
    assert score_case(case, AgentTurn("t", "done", answer=BLOCKS[0]["text"])).passed


@pytest.mark.db
def test_rag_answers_from_content_block_models_are_plain_text(conn, demo_cfg):
    from core.ingest.documents import ingest_documents
    from core.rag.answer import answer_question

    embeddings = get_embeddings(demo_cfg.embeddings)
    ingest_documents(conn, demo_cfg, embeddings)
    result = answer_question("What SLA credit does a Gold customer get?", cfg=demo_cfg, conn=conn,
                             chat=BlockContentChat(), embeddings=embeddings)
    assert result.answer.startswith("Shipment **SHP-0000**") and "'type'" not in result.answer


def test_resume_accepts_older_reports_by_their_file_name(demo_cfg, tmp_path):
    import json

    runs = run_cases(build_service(demo_cfg, sql_schema_text="x(y int)"), CASES[:1])
    data = json.loads(write_report(runs, summarize(runs, demo_cfg), demo_cfg, tmp_path).with_suffix(".json").read_text())
    for key in ("model", "prompt"):
        del data["summary"][key]  # as written by the first version of the runner
    old = tmp_path / f"2026-11-11-0748-{demo_cfg.llm.model}-cadb61d.json"
    old.write_text(json.dumps(data))
    assert list(load_previous(old, CASES, demo_cfg)) == ["q-960"]
    wrong_name = tmp_path / "2026-11-11-0748-other-model-cadb61d.json"
    wrong_name.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="does not record its model"):
        load_previous(wrong_name, CASES, demo_cfg)


# ----------------------------------------------------------------------------- resumed runs: whose money is it?
def test_resumed_results_do_not_count_as_this_runs_cost_or_latency(demo_cfg, tmp_path):
    """Sprint 01 finding: the 0811 report said 'cost $0.0045, p95 16.55 s' although that run made no successful
    model call. Those numbers belonged to the 18 results it reused. Headline numbers must be this run's only."""
    from core.evals.run import CaseRun, _not_run
    from core.evals.scoring import CaseScore

    real = demo_cfg.model_copy(update={"llm": demo_cfg.llm.model_copy(update={"provider": "openai", "model": "gpt-6-luna"})})
    reused = [CaseRun(CaseScore(c, checks={"safety": True}), AgentTurn("resumed", "done"), 16.5, 2000, 100, resumed=True)
              for c in CASES[:2]]
    runs = [*reused, _not_run(CASES[2], "OpenAIRateLimitError: requests per day")]
    summary = summarize(runs, real)
    assert (summary["tokens_in"], summary["tokens_out"], summary["cost_usd"], summary["seconds_p95"]) == (0, 0, 0.0, 0)
    assert summary["this_run"]["cases"] == 0
    assert summary["carried_over"] == {"cases": 2, "tokens_in": 4000, "tokens_out": 200, "cost_usd": 0.0005,
                                       "seconds_total": 33.0, "seconds_p95": 16.5}
    text = write_report(runs, summary, real, tmp_path).read_text(encoding="utf-8")
    assert "This run: 0 case(s) executed, 0 tokens in / 0 out, cost $0.0000" in text
    assert "Carried over: 2 result(s)" in text and "$0.0005) were spent by that earlier run" in text

    fresh = CaseRun(CaseScore(CASES[2], checks={"safety": True}), AgentTurn("t", "done"), 4.0, 1000, 50)
    mixed = summarize([*reused, fresh], real)
    assert (mixed["tokens_in"], mixed["seconds_p95"], mixed["this_run"]["cases"], mixed["passed"]) == (1000, 4.0, 1, 3)
