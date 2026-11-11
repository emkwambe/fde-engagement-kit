# CLAUDE.md - standing rules for this repository

This file is read by Claude Code at the start of every session. It holds the rules that never change.
The current work order lives in `docs/sprints/` (read the newest sprint brief before doing anything).

## What this project is

The **FDE Engagement Kit**: a reusable, config-driven kit for delivering enterprise GenAI agents
(RAG + read-only SQL + tools generated from OpenAPI + human approval for writes), plus a worked demo
engagement (`engagements/demo-logistics`, fictional Northwind Logistics). It is a portfolio project for
Forward Deployed Engineer roles. **The kit's promise:** a new customer = a new `engagements/<name>/` folder
(config, docs, data, golden set) with **zero changes in `core/`** (NFR-02).

Objectives (charter, unchanged): (1) internal and most important: develop the skills; (2) external: show
the ability to use the right infrastructure and tools to deliver. Documentation is a first-class deliverable.

## Stack and commands

- Python 3.12+, uv, FastAPI, Pydantic v2, psycopg 3, Postgres 16 + pgvector, LangChain core, LangGraph,
  OpenAI (default provider), pytest, ruff, mypy. Windows 11 + PowerShell 7 is the author's machine.
- Task runner: `.\tasks.ps1 <task>` (help, setup, up, down, migrate, seed, ingest, eval, demo, api, erp,
  erp-spec, test, lint, kind-up, kind-down, ingest-remote, check-tools).
- Tests: `uv run pytest -q` (always fake models; DB tests need `.\tasks.ps1 up`). Lint: `.\tasks.ps1 lint`.
- Fake vs real models: `FAKE_LLM=1` in `.env` (default). A real run needs `$env:FAKE_LLM='0'` **and** the
  documents re-ingested with the real embedding model; afterwards restore fake vectors
  (`uv run python -m core.ingest.run --docs-only` with FAKE_LLM=1). The eval preflight enforces this.

## Non-negotiable rules

1. **PowerShell for humans.** Every command written in docs, runbooks, teaching notes or reports is
   PowerShell 7 that works on Windows from the repo root. (You may use any shell to run things yourself.)
2. **Never weaken a test or a golden case to make it pass.** Fix the system, or document the limitation.
   Widening a golden fact is allowed only when the model's answer was verifiably correct; put the evidence
   in the case's `notes` and in the decision log.
3. **Secrets.** Never print, log, commit or paste the contents of `.env` or any key. Provider error text
   that contains account ids must be masked (`core/evals/run.py: mask_ids`). `gitleaks`-clean always.
4. **Migrations are append-only.** Never edit an applied file in `deploy/sql/`; add the next number.
5. **No billable cloud actions.** Never run `terraform apply`, `terraform destroy`, `gcloud ... create/deploy/
   delete`, or anything that creates or changes cloud resources or costs money beyond the OpenAI budget below.
   Prepare them, validate them (`terraform fmt -check`, `terraform validate`), and hand the exact
   PowerShell commands to the human under **NEEDS HUMAN** in the sprint report.
6. **OpenAI budget.** At most **USD 1.00** of OpenAI spend per sprint, all of it on evals. The account allows
   **50 requests per day** for the chat model: never loop or retry on 429; a daily-quota stop is normal
   (`INCOMPLETE`, then `--resume` later). Record every real run's cost from its report.
7. **Destructive commands are off limits:** `git push --force`, history rewrites, `git reset --hard` on pushed
   commits, `docker compose down -v`, deleting volumes/data the human created, deleting eval reports.
8. **Every commit is green:** `uv run pytest -q` passes and `.\tasks.ps1 lint` is clean (ruff + mypy).
   Small commits, one per finished part, message `Day N part M: <what>; teaching note NN (DC-0xx)`.
   Push after each finished part. Never commit `.env`, `.venv`, generated CSVs, or fake-model eval reports.
9. **Decisions are written down.** Every non-trivial decision or deviation gets a row in
   `docs/14-decision-and-change-log.md` (next free DC number); architecture-level ones also get an ADR.
10. **Scope control.** No features beyond the sprint brief. New ideas go to `docs/16-deferred-ideas.md` as
    proposals (template inside that file), never into code.
11. **Config over code.** Engagement-specific behaviour belongs in `engagements/<name>/` (YAML, docs, data,
    golden set, engagement-owned scripts). A change in `core/` must be generic (useful to every engagement).

## Teaching notes (docs/teaching/)

Every new component ships with a teaching note in the **same commit**, following `docs/teaching/TEMPLATE.md`
and the README rules: At a glance table (What/When/How/Why), ELI10 with "where the analogy stops",
ICAR practicums as GitHub alert boxes (NOTE = INTENT/Why, IMPORTANT = CONTEXT/When-Where,
TIP = ACTION/How with PowerShell, WARNING = RESULT/What), teach-back questions with hidden answers,
one interview line. **Every RESULT is real output you captured by running the ACTION** (shorten long lines
with `...`, plain ASCII). No "break it on purpose" practicums yet (phase 2, DC-011). Update the series table
in `docs/teaching/README.md`.

## Style of the docs

Plain words, short sentences, no marketing language. Explain *why*, not only *what*. Numbers come from real
runs. When something failed, say so and say what was learned - failures are part of the portfolio story.
