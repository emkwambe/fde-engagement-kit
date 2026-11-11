# Decision & Change Log

Small decisions go here. Significant architecture decisions get an [ADR](adr/). Scope changes follow [Scope section 6](01-scope-statement.md#6-change-control).

| ID | Date | Type (Decision / Change request) | Description | Reason | Impact (scope / time / cost) | Approved by | Status |
|---|---|---|---|---|---|---|---|
| DC-001 | 2026-11-09 | Decision | Hybrid approach: one-off demo built inside reusable kit structure | Balance shippable demo with reuse | Baseline | Sponsor | Accepted |
| DC-002 | 2026-11-09 | Decision | Docs as Markdown in repo | Reviewers see docs next to code | None | Sponsor | Accepted |
| DC-003 | 2026-11-09 | Decision | 1-week sprint; skill development is primary objective | Depth of learning | Baseline | Sponsor | Accepted |
| DC-004 | 2026-11-09 | Decision | GCP Cloud Run primary; OpenAI default LLM | Fastest deploy; most common LLM in postings | See ADR-003, ADR-005 | Sponsor | Accepted |
| DC-005 | 2026-11-10 | Decision | PowerShell 7 is the standard shell; `tasks.ps1` replaces make; runbook commands in PowerShell | Author works in PowerShell on Windows | Docs + task runner | Sponsor | Accepted |
| DC-006 | 2026-11-10 | Decision | Day 1 split: Claude writes setup code (Compose, config, seed data, ETL, DB migrations, API shell); author writes RAG core (chunking, embeddings, document ingestion, retrieval, answer) against specs and acceptance tests | Learning time goes to the skills interviewers probe | Schedule unchanged | Sponsor | Accepted |
| DC-007 | 2026-11-10 | Change request | RAG core (chunking, ingestion, search, answer) provided as complete files by Claude instead of written by author | Author's preference; keeps schedule | Learning risk R-02 raised; mitigated by journal explanations + Day 5 cold rebuild | Sponsor | Accepted |
| DC-008 | 2026-11-10 | Decision | Knowledge-base tables keyed by (engagement, id) via new migration 005; applied migrations are never edited | Two engagements with the same file name overwrote each other | Re-ingest required (derived data) | Sponsor | Accepted |
| DC-009 | 2026-11-10 | Decision | Every component gets a teaching note (ELI10 inside ICAR practicums: Intent, Context, Action, Result) in docs/teaching/. The AUTHOR writes notes 00-07 and every new note; Claude provides template, hints and rubric reviews. Notes 08-09 are labelled worked examples written by Claude. From Day 2 a component is done only when its note is written and reviewed | Teaching is the deepest test of understanding; notes written by someone else would not build the author's skill; mitigates R-02 | ~30-45 min per component | Sponsor | Accepted |
