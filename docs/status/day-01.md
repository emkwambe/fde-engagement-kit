# Status Report - Day 1 (2026-11-10)

**Overall:** On track

| Milestone | Planned | Status | Note |
|---|---|---|---|
| M0 | Day 0 | Done | Tools installed, repo on GitHub, baseline committed |
| M1 | Day 1 | Done | `/chat` returns cited answers; no-answer gate works |
| M2 | Day 2 | Not started | Agent + SQL tool + generated API tools |
| M3 | Day 3 | Not started | |
| M4 | Day 4 | Not started | |
| M5 | Day 5 | Not started | |

## Done today
- Local stack running on Windows (Docker Postgres + pgvector, PowerShell task runner).
- ETL: 40 customers, 500 orders, 500 shipments loaded; 2 rows rejected with reasons; 5 duplicates removed.
- RAG core: chunking, idempotent ingestion (20 docs -> 70 chunks), vector + hybrid search, cited answers.
- Migration 005: knowledge-base rows keyed by (engagement, id).
- 39 tests passing; lint and type checks clean.

## Planned next session (Day 2)
- Mock ERP service with an OpenAPI spec (shipments, tickets).
- Tool generation from OpenAPI; read-only SQL tool.
- LangGraph agent with approval step before write actions.

## Risks / issues (see [risk register](../07-risk-register.md))
| ID | Change | Action |
|---|---|---|
| R-02 | Raised: RAG core code was provided, not hand-written | Journal explanations in own words; Day 5 cold rebuild of chunking or search |
| R-11 | Mitigated | Messy synthetic data handled by ETL with counted rejections |

## Decisions / changes (see [log](../14-decision-and-change-log.md))
- DC-005 PowerShell standard; DC-006 work split; DC-007 complete files for RAG core; DC-008 kb keyed by engagement.

## Metrics
| Metric | Value |
|---|---|
| Eval overall score | n/a (evals arrive Day 3) |
| Tests passing | 39 / 39 |
| Spend to date (OpenAI / GCP) | $0 / $0 (fake models, local only) |
| Hours spent (build / learning) | |
