# Status Report - Day 3 (2026-11-11)

**Overall:** At risk (quality gate not yet measured on a complete real run: provider quota)

| Milestone | Planned | Status | Note |
|---|---|---|---|
| M0 | Day 0 | Done | |
| M1 | Day 1 | Done | Cited answers with a no-answer gate |
| M2 | Day 2 | Done | Agent with SQL + generated API tools; writes pause for approval |
| M3 | Day 3 | Partly | Guardrails done (part 1); eval harness done and run on the real model (part 2); 18/18 finished real cases pass, 9 not run (quota). Observability is Sprint 01 Phase 1 |
| M4 | Day 4 | Not started | |
| M5 | Day 5 | Not started | |

## Done today
- Part 1 (`cadb61d`): guardrails - PII redaction, injection filter on every tool result and RAG chunk, input blocking, audit of blocks (note 14, DC-015).
- Part 2: eval harness (`core/evals/`), 27-case golden set meeting every category minimum, six checks, Markdown + JSON reports, real-vs-fake gate.
- Three real runs against `gpt-6-luna` found and fixed three bugs: `temperature` HTTP 400 (0739), content-block answers shown as `str(list)` (q-018 in 0748), quota failures scored as crashes (0748). Each fix has a test.
- Runner fix found in Sprint 01: a resumed report counted reused results' cost and latency as its own (0811). Now "this run" and "carried over" are separate.
- Teaching note 15, docs/16 deferred ideas (A routing, B Scenario Builder), DC-016.

## Planned next session
- Sprint 01 Phase 1: structured logs, `/metrics`, OpenTelemetry traces, `/ingest` and `/eval` admin endpoints.
- Finish the real eval with `--resume` when the daily quota allows.

## Risks / issues (see [risk register](../07-risk-register.md))
| ID | Change | Action |
|---|---|---|
| R-12 | Added: provider daily quota stops real evals | Quota-aware, resumable runner; finish across days |
| R-06 | Not triggered | Finished real cases pass 18/18 |

## Decisions / changes (see [log](../14-decision-and-change-log.md))
- DC-015 guardrails; DC-016 temperature opt-in, plain-text answers, resumable quota-aware evals, masked ids, q-018 widening with evidence, this-run vs carried-over costs, deferred ideas A and B.

## Metrics
| Metric | Value |
|---|---|
| Eval overall score | Real `gpt-6-luna`, prompt `agent-v1`: 18/18 finished cases pass; 9 of 27 not run (INCOMPLETE). Fake harness run: 15/27 (not a quality number) |
| Tests passing | 137 / 137 (Postgres up) |
| Spend to date (OpenAI / GCP) | $0.0051 / $0 (real eval 0748; 0739 and 0811 made no successful model call) |
| Hours spent (build / learning) | |
