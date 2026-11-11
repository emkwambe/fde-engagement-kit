"""Run the golden set through the agent and write a scored report (Day 3, part 2).

Usage (from PowerShell):
  .\\tasks.ps1 eval                                    fake model (FAKE_LLM=1 in .env): checks the harness
  $env:FAKE_LLM='0'; uv run python -m core.evals.run   the real model: this is the quality gate
  ... --case q-004 --case q-019                        only some cases

Every case runs in a fresh conversation, through AgentService (so guardrails apply), with in-memory
checkpoints and NO audit rows: evals never leave pending approvals or tickets behind, because paused
writes are scored and then simply abandoned (never approved).

Gate (real model only): overall pass rate >= evals.threshold AND red-team pass rate = 100%.
Exit code 1 when the gate fails, so CI can block a merge. With the fake model the score describes the
fake's fixed script, not quality, so the run always exits 0.

Provider quotas: when the provider says the DAILY quota is used up, the run stops, the remaining cases
are marked "not run" (not failed), and the report is INCOMPLETE (exit code 3). Finish later with
  uv run python -m core.evals.run --resume <that report .json> [--rerun q-018]
which keeps the finished results and runs only the rest (plus edited cases and any --rerun ids).
Org/account ids are masked in reports.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from core.agent.graph import AgentTurn, agent_model, agent_tools, build_agent, run_config, system_prompt
from core.agent.service import AgentService
from core.config import load_engagement, resolve_path
from core.config.schema import EngagementConfig
from core.db.connection import connect
from core.evals.golden import GoldenCase, load_golden
from core.evals.scoring import CaseScore, score_case
from core.ingest.documents import embedding_signature, stored_signatures
from core.llm.factory import get_embeddings

# USD per 1M tokens (input, output). Source: docs/12-cost-estimate.md, prices checked 2026-11-09.
PRICES: dict[str, tuple[float, float]] = {"gpt-6-luna": (0.10, 0.50), "gpt-6.1-terra": (1.00, 5.00)}


@dataclass
class CaseRun:
    score: CaseScore
    turn: AgentTurn
    seconds: float
    tokens_in: int
    tokens_out: int
    error: str = ""
    not_run: bool = False   # stopped by a provider quota before this case could run
    resumed: bool = False   # result reused from an earlier (incomplete) report


DAILY_QUOTA_MARKERS = ("per day", "insufficient_quota")


def is_daily_quota(exc: BaseException) -> bool:
    """True when retrying today is pointless: the provider's daily request/credit quota is used up."""
    return "RateLimit" in type(exc).__name__ and any(m in str(exc) for m in DAILY_QUOTA_MARKERS)


def mask_ids(text: str) -> str:
    """Reports are committed to git: never include account identifiers from provider error messages."""
    return re.sub(r"\b(org|proj|user)-[A-Za-z0-9]{6,}", r"\1-***", text)


def prompt_version(cfg: EngagementConfig) -> str:
    """The label of the agent prompt this run used. Resumed results must come from the same label."""
    return system_prompt(cfg)[1]


def prompt_sha(cfg: EngagementConfig) -> str:
    """Fingerprint of the exact prompt text the model saw, so a version label can be checked, not just trusted."""
    return hashlib.sha256(system_prompt(cfg)[0].format(customer=cfg.engagement.customer).encode()).hexdigest()[:12]


class PreflightError(RuntimeError):
    """Something the eval depends on is not ready. The message says how to fix it."""


def preflight(cfg: EngagementConfig, http_client: httpx.Client | None = None) -> None:
    """Fail fast with a clear message instead of scoring a broken setup."""
    try:
        with connect(vector=False) as conn:
            signatures = stored_signatures(conn, cfg.engagement.name)
    except Exception as exc:
        raise PreflightError(f"Database not reachable ({exc.__class__.__name__}). Run: .\\tasks.ps1 up") from exc
    wanted = embedding_signature(cfg)
    if signatures != {wanted}:
        raise PreflightError(
            f"Documents are embedded with {sorted(signatures) or 'nothing'}, but this run uses {wanted}. "
            "Re-ingest the documents with the same FAKE_LLM setting as this run:  uv run python -m core.ingest.run --docs-only"
            "  (for the real model, run  $env:FAKE_LLM='0'  first, in the same window)")
    for api in cfg.tools.openapi:
        try:
            (http_client or httpx).get(f"{api.base_url.rstrip('/')}/health", timeout=3)  # type: ignore[attr-defined]
        except httpx.HTTPError as exc:
            raise PreflightError(f"{api.base_url} not reachable. Start the mock ERP: .\\tasks.ps1 erp") from exc


def _usage(service: AgentService, thread_id: str) -> tuple[int, int]:
    messages = service.agent.get_state(run_config(service.cfg, thread_id)).values.get("messages", [])
    tokens_in = tokens_out = 0
    for m in messages:
        usage = getattr(m, "usage_metadata", None) if isinstance(m, AIMessage) else None
        if usage:
            tokens_in += usage.get("input_tokens", 0)
            tokens_out += usage.get("output_tokens", 0)
    return tokens_in, tokens_out


def _not_run(case: GoldenCase, why: str) -> CaseRun:
    score = CaseScore(case, reasons=[f"NOT RUN: {why}"])
    return CaseRun(score, AgentTurn("not-run", "done"), 0.0, 0, 0, not_run=True)


def run_cases(service: AgentService, cases: list[GoldenCase]) -> list[CaseRun]:
    runs: list[CaseRun] = []
    batch = uuid.uuid4().hex[:6]
    for i, case in enumerate(cases):
        thread_id = f"eval-{batch}-{case.id}"
        start = time.perf_counter()
        error = ""
        try:
            turn = service.chat(thread_id, case.question, user="eval")
        except Exception as exc:  # a crash is a failed case, not a crashed eval
            if is_daily_quota(exc):  # nothing more can run today: stop, and say so instead of failing cases
                why = mask_ids(f"{type(exc).__name__}: {exc}")[:160]
                runs += [_not_run(c, why) for c in cases[i:]]
                break
            turn, error = AgentTurn(thread_id, "done", answer=""), mask_ids(f"{exc.__class__.__name__}: {exc}")
        seconds = time.perf_counter() - start
        score = score_case(case, turn)
        if error:  # the crash is the root cause, so it goes first; the other reasons are its symptoms
            score.checks["no_crash"] = False
            score.reasons.insert(0, f"CRASH {error[:200]}")
        runs.append(CaseRun(score, turn, seconds, *_usage(service, thread_id), error=error))
    return runs


def case_hash(case: GoldenCase) -> str:
    """Fingerprint of a golden case: if the case was edited since a run, that old result is not reused."""
    return hashlib.sha256(case.model_dump_json().encode()).hexdigest()[:12]


def load_previous(path: Path, cases: list[GoldenCase], cfg: EngagementConfig,
                  rerun: tuple[str, ...] = ()) -> dict[str, CaseRun]:
    """Finished results from an earlier report (same model and prompt), keyed by case id.
    Not reused: cases that crashed or did not run, cases edited since (different case_hash), and `rerun` ids."""
    data = json.loads(path.read_text(encoding="utf-8"))
    meta = data.get("summary", {})
    if "model" not in meta:  # reports written before model/prompt were recorded: the file name holds the model
        if f"-{cfg.llm.model}-" not in path.name:
            raise ValueError(f"{path.name} does not record its model and its name does not contain '{cfg.llm.model}'.")
        meta = {**meta, "model": f"{cfg.llm.provider}/{cfg.llm.model}", "prompt": prompt_version(cfg)}
    if (meta.get("model"), meta.get("prompt")) != (f"{cfg.llm.provider}/{cfg.llm.model}", prompt_version(cfg)):
        raise ValueError(f"{path.name} was made with {meta.get('model')} / {meta.get('prompt')}; "
                         "results can only be resumed with the same model and prompt version.")
    by_id = {c.id: c for c in cases}
    previous: dict[str, CaseRun] = {}
    for item in data.get("cases", []):
        case = by_id.get(item["id"])
        unfinished = item.get("not_run") or item.get("error") or item["checks"].get("no_crash") is False
        edited = "case_hash" in item and item["case_hash"] != case_hash(case) if case else True
        if case is None or unfinished or edited or case.id in rerun:
            continue  # these run again
        score = CaseScore(case, checks=item["checks"], reasons=item["reasons"])
        turn = AgentTurn("resumed", item["status"], answer=item["answer"], pending=item["pending"],
                         steps=[{"call": t, "args": {}} for t in item["tools"]])
        previous[case.id] = CaseRun(score, turn, item["seconds"], item["tokens_in"], item["tokens_out"], resumed=True)
    return previous


# ----------------------------------------------------------------------------- summary + report
def _usage_totals(runs: list[CaseRun], price: tuple[float, float] | None) -> dict[str, Any]:
    tokens_in, tokens_out = sum(r.tokens_in for r in runs), sum(r.tokens_out for r in runs)
    seconds = sorted(r.seconds for r in runs)
    return {
        "cases": len(runs), "tokens_in": tokens_in, "tokens_out": tokens_out,
        "cost_usd": round((tokens_in * price[0] + tokens_out * price[1]) / 1e6, 4) if price else None,
        "seconds_total": round(sum(seconds), 2),
        "seconds_p95": round(seconds[max(0, int(len(seconds) * 0.95) - 1)], 2) if seconds else 0,
    }


def summarize(runs: list[CaseRun], cfg: EngagementConfig) -> dict[str, Any]:
    """Pass rates use every finished result (fresh + reused). Money and time do NOT mix the two:
    the headline tokens / cost / latency are what THIS run spent ("this_run"); reused results keep their
    original numbers under "carried_over", so a resumed run never reports someone else's spend (Sprint 01)."""
    by_category: dict[str, list[bool]] = defaultdict(list)
    by_check: dict[str, list[bool]] = defaultdict(list)
    not_run = [r for r in runs if r.not_run]
    runs = [r for r in runs if not r.not_run]  # rates only count cases that actually ran
    for r in runs:
        by_category[r.score.case.category].append(r.score.passed)
        for name, ok in r.score.checks.items():
            by_check[name].append(ok)
    rate = lambda xs: round(sum(xs) / len(xs), 3) if xs else None  # noqa: E731
    price = PRICES.get(cfg.llm.model) if cfg.llm.provider != "fake" else None  # fakes cost nothing: n/a
    this_run = _usage_totals([r for r in runs if not r.resumed], price)
    carried = _usage_totals([r for r in runs if r.resumed], price)
    overall = rate([r.score.passed for r in runs]) or 0.0
    safety = rate(by_category.get("red_team", []))
    real = cfg.llm.provider != "fake"
    complete = not not_run
    gate = complete and overall >= cfg.evals.threshold and (safety is None or safety == 1.0)
    return {
        "model": f"{cfg.llm.provider}/{cfg.llm.model}", "prompt": prompt_version(cfg), "prompt_sha": prompt_sha(cfg),
        "cases": len(runs) + len(not_run), "ran": len(runs), "not_run": len(not_run), "complete": complete,
        "resumed": sum(r.resumed for r in runs), "passed": sum(r.score.passed for r in runs), "overall": overall,
        "threshold": cfg.evals.threshold, "safety": safety, "gate_passed": gate, "gate_enforced": real,
        "by_category": {k: rate(v) for k, v in sorted(by_category.items())},
        "by_check": {k: rate(v) for k, v in sorted(by_check.items())},
        # headline numbers = this run only
        "tokens_in": this_run["tokens_in"], "tokens_out": this_run["tokens_out"], "cost_usd": this_run["cost_usd"],
        "seconds_total": this_run["seconds_total"], "seconds_p95": this_run["seconds_p95"],
        "this_run": this_run, "carried_over": carried,
    }


def _git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "nogit"


def _money(value: float | None) -> str:
    return "n/a" if value is None else f"${value:.4f}"


def write_report(runs: list[CaseRun], summary: dict[str, Any], cfg: EngagementConfig, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    model = cfg.llm.model if cfg.llm.provider != "fake" else "fake"
    name = f"{stamp}-{model}-{_git_sha()}"
    pct = lambda v: "-" if v is None else f"{v:.0%}"  # noqa: E731
    lines = [
        f"# Eval report: {cfg.engagement.name}", "",
        f"- Date: {datetime.now():%Y-%m-%d %H:%M}  |  git: `{_git_sha()}`  |  "
        f"prompt: `{prompt_version(cfg)}` (sha `{prompt_sha(cfg)}`)",
        f"- Model: `{cfg.llm.provider}/{cfg.llm.model}`  |  embeddings: `{embedding_signature(cfg)}`",
        f"- **Overall: {summary['passed']}/{summary['ran']} = {pct(summary['overall'])}** "
        f"(threshold {pct(summary['threshold'])})  |  **Safety (red team): {pct(summary['safety'])}**"
        + (f"  |  {summary['resumed']} result(s) reused from an earlier run" if summary["resumed"] else ""),
        f"- Gate: **{'INCOMPLETE' if not summary['complete'] else 'PASS' if summary['gate_passed'] else 'FAIL'}**"
        + (f" ({summary['not_run']} case(s) not run: provider quota; finish with --resume)" if not summary["complete"]
           else "" if summary["gate_enforced"] else " (not enforced: fake model, this checks the harness only)"),
        f"- This run: {summary['this_run']['cases']} case(s) executed, {summary['tokens_in']:,} tokens in / "
        f"{summary['tokens_out']:,} out, cost " + _money(summary["cost_usd"])
        + f", time {summary['seconds_total']} s total, p95 {summary['seconds_p95']} s per case",
        *([f"- Carried over: {summary['carried_over']['cases']} result(s) reused from an earlier report; their "
           f"tokens ({summary['carried_over']['tokens_in']:,} in / {summary['carried_over']['tokens_out']:,} out, "
           + _money(summary["carried_over"]["cost_usd"]) + ") were spent by that earlier run, not this one"]
          if summary["resumed"] else []),
        "",
        "| Category | Pass rate |", "|---|---|",
        *[f"| {k} | {pct(v)} |" for k, v in summary["by_category"].items()], "",
        "| Check | Pass rate |", "|---|---|",
        *[f"| {k} | {pct(v)} |" for k, v in summary["by_check"].items()], "",
        "| Case | Category | Result | Tools called | Seconds | Why it failed |", "|---|---|---|---|---|---|",
    ]
    for r in runs:
        tools = ", ".join(s["call"] for s in r.turn.steps if "call" in s) or "-"
        result = "NOT RUN" if r.not_run else ("pass" if r.score.passed else "FAIL") + ("*" if r.resumed else "")
        lines.append(f"| {r.score.case.id} | {r.score.case.category} | {result} | "
                     f"{tools} | {r.seconds:.1f} | {'; '.join(r.score.reasons).replace('|', '/')} |")
    if summary["resumed"]:
        lines += ["", "\\* reused from an earlier run of the same model and prompt (--resume)."]
    path = out_dir / f"{name}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    detail = [{"id": r.score.case.id, "case_hash": case_hash(r.score.case), "passed": r.score.passed,
               "checks": r.score.checks, "reasons": r.score.reasons,
               "not_run": r.not_run, "error": r.error, "resumed": r.resumed,
               "status": r.turn.status, "answer": r.turn.answer, "pending": r.turn.pending,
               "tools": [s["call"] for s in r.turn.steps if "call" in s], "seconds": round(r.seconds, 2),
               "tokens_in": r.tokens_in, "tokens_out": r.tokens_out} for r in runs]
    (out_dir / f"{name}.json").write_text(json.dumps({"summary": summary, "cases": detail}, indent=2), encoding="utf-8")
    return path


def build_service(cfg: EngagementConfig, http_client: httpx.Client | None = None, **tool_kwargs: Any) -> AgentService:
    tools = agent_tools(cfg, get_embeddings(cfg.embeddings), http_client=http_client, **tool_kwargs)
    agent = build_agent(cfg, tools, agent_model(cfg), checkpointer=InMemorySaver())
    return AgentService(cfg, agent, db=None)  # db=None: evals write no approvals/audit rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the golden-set evaluation.")
    parser.add_argument("--engagement", default=os.environ.get("ENGAGEMENT", "demo-logistics"))
    parser.add_argument("--case", action="append", default=[], help="run only this case id (repeatable)")
    parser.add_argument("--resume", type=Path, help="report .json of an incomplete run: reuse its finished cases")
    parser.add_argument("--rerun", action="append", default=[], help="with --resume: run this case id again anyway")
    args = parser.parse_args()

    cfg = load_engagement(args.engagement)
    golden_path = resolve_path(cfg.evals.golden_set)
    cases = [c for c in load_golden(golden_path) if not args.case or c.id in args.case]
    previous = load_previous(args.resume, cases, cfg, tuple(args.rerun)) if args.resume else {}
    try:
        preflight(cfg)
    except PreflightError as exc:
        print(f"PREFLIGHT FAILED: {exc}")
        return 2
    todo = [c for c in cases if c.id not in previous]
    print(f"Running {len(todo)} case(s) with {cfg.llm.provider}/{cfg.llm.model}"
          + (f" ({len(previous)} reused from {args.resume.name})" if previous else "") + " ...")
    fresh = {r.score.case.id: r for r in run_cases(build_service(cfg), todo)}
    runs = [previous.get(c.id) or fresh[c.id] for c in cases]
    for r in runs:
        result = "NOT RUN" if r.not_run else ("pass" if r.score.passed else "FAIL") + ("*" if r.resumed else " ")
        print(f"  {r.score.case.id} {r.score.case.category:<9} {result:<7} {r.seconds:5.1f}s  {'; '.join(r.score.reasons)[:110]}")
    summary = summarize(runs, cfg)
    report = write_report(runs, summary, cfg, golden_path.parent / "reports")
    print(f"\nOverall {summary['passed']}/{summary['ran']} = {summary['overall']:.0%} "
          f"(threshold {summary['threshold']:.0%}) | safety {summary['safety'] if summary['safety'] is not None else '-'} "
          f"| cost this run {_money(summary['cost_usd'])}"
          + (f" (+ {summary['resumed']} result(s) carried over, already paid)" if summary["resumed"] else ""))
    print(f"Report: {report.relative_to(resolve_path('.'))}")
    if not summary["complete"]:
        print(f"INCOMPLETE: {summary['not_run']} case(s) not run (provider quota). When the quota resets, finish with:")
        print(f"  uv run python -m core.evals.run --resume {report.with_suffix('.json').relative_to(resolve_path('.'))}")
        return 3
    if not summary["gate_enforced"]:
        print("Gate not enforced (fake model): this run checks the harness, not answer quality.")
        return 0
    print(f"GATE {'PASSED' if summary['gate_passed'] else 'FAILED'}")
    return 0 if summary["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
