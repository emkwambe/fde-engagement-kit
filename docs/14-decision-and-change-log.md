# Decision & Change Log

Small decisions go here. Significant architecture decisions get an [ADR](adr/). Scope changes follow [Scope §6](01-scope-statement.md#6-change-control).

| ID | Date | Type (Decision / Change request) | Description | Reason | Impact (scope / time / cost) | Approved by | Status |
|---|---|---|---|---|---|---|---|
| DC-001 | 2026-11-09 | Decision | Hybrid approach: one-off demo built inside reusable kit structure | Balance shippable demo with reuse | Baseline | Sponsor | Accepted |
| DC-002 | 2026-11-09 | Decision | Docs as Markdown in repo | Reviewers see docs next to code | None | Sponsor | Accepted |
| DC-003 | 2026-11-09 | Decision | 1-week sprint; skill development is primary objective | Depth of learning | Baseline | Sponsor | Accepted |
| DC-004 | 2026-11-09 | Decision | GCP Cloud Run primary; OpenAI default LLM | Fastest deploy; most common LLM in postings | See ADR-003, ADR-005 | Sponsor | Accepted |
| DC-005 | 2026-11-10 | Decision | PowerShell 7 is the standard shell; `tasks.ps1` replaces make; runbook commands in PowerShell | Author works in PowerShell on Windows | Docs + task runner | Sponsor | Accepted |
| DC-006 | 2026-11-10 | Decision | Day 1 split: Claude writes setup code (Compose, config, seed data, ETL, DB migrations, API shell); author writes RAG core (chunking, embeddings, document ingestion, retrieval, answer) against specs and acceptance tests | Learning time goes to the skills interviewers probe | Schedule unchanged | Sponsor | Accepted |
