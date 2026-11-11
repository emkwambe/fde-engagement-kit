# Sprint 01 brief: finish Day 3, deliver Day 4 and Day 5

**For:** Claude Code, working autonomously in this repository on the author's Windows machine.
**From:** the project sponsor/author, with the plan reviewed by Claude (claude.ai).
**Read first:** `CLAUDE.md` (standing rules - they override anything here), then this brief, then
`docs/04-wbs-and-schedule.md`, `docs/02-requirements.md`, `docs/09-test-and-eval-strategy.md`,
`docs/14-decision-and-change-log.md`, `docs/teaching/README.md`.

## 0. How to work

- Work through the phases **in order**. Each phase ends with its Definition of Done (DoD) checklist,
  a commit (or a few small ones), a push, and an update to the sprint report (section 8).
- **Do not ask the human questions mid-sprint.** When you are blocked (missing credentials, provider quota,
  a decision that is genuinely the sponsor's), write it under **NEEDS HUMAN** in the report with the exact
  PowerShell commands or the decision options, then continue with the next item you can do.
- **Verify before you claim.** Every "done" in the report links to evidence: a command and its real output,
  a test name, a commit SHA, a file path. No claim without evidence.
- **When the plan is wrong, say so.** If an item in this brief is impossible, unwise, or already done, do not
  force it: record the deviation (DC row) and the reason, and do the closest sensible thing.
- Prefer the smallest change that meets the DoD. The project values working, tested, documented software
  over breadth.
- Keep the author's learning objective in mind: code must be readable and explained (docstrings that say
  *why*), and every new component gets its teaching note.

## 1. Where the project stands (start of sprint)

Committed and pushed (master): Day 0-2 complete, Day 3 part 1 (guardrails, note 14, DC-015) at `cadb61d`.
Local but **not yet committed** (Day 3 part 2, evals), expected in the working tree:

- `core/evals/{golden,scoring,run}.py`, 27-case `engagements/demo-logistics/evals/golden.jsonl`,
  `tests/day03/test_evals.py`, `tests/day03/test_model_params.py`, `core/ingest/documents.py`
  (embedding signature), `core/api/main.py` (`embeddings_match` in /health), `.gitignore` (real eval reports
  committed, fake ones ignored), `temperature` made opt-in (`core/config/schema.py`, `core/llm/factory.py`,
  both `engagement.yaml` files), plain-text answers (`AIMessage.text` in `core/agent/graph.py`,
  `core/rag/answer.py`, `scripts/ask_agent.py`), quote-normalised scoring, quota-aware runner with
  `--resume/--rerun`, masked account ids.
- Real-model eval reports in `engagements/demo-logistics/evals/reports/`:
  `2026-11-11-0739-gpt-6-luna-cadb61d.*` (every call failed: HTTP 400 `temperature` unsupported) and
  `2026-11-11-0748-gpt-6-luna-cadb61d.*` (18 cases ran: RAG 8/8, SQL 5/5, api_read 2/3, q-004 paused with
  the exact credit; then HTTP 429 daily quota of 50 requests; cost $0.0051; p95 15 s/case).
- Findings from those runs, already fixed in code (verify they are present - see Phase 0):
  (a) `gpt-6-luna` rejects `temperature`; (b) the model returns content as a list of blocks and the agent
  showed users `str(list)`; (c) q-018's answer ("wasn't found") was correct but failed an exact-wording
  check; (d) provider errors contained the OpenAI org id.

Expected test count at the start: **136 passed** (with Postgres up). Lint clean.

## 2. Phase 0 - Baseline and Day 3 part 2 close-out

1. Verify the working tree. Confirm each item in section 1 exists. If the plain-text answer fix, quote
   normalisation, q-018 alternatives or legacy `--resume` support are missing (the author may not have pasted
   the last block), implement them to this spec: `_turn()` uses `last.text`; `answer_question()` uses
   `reply.text`; `scripts/ask_agent.py --history` prints `m.text`; `core/evals/scoring.normalize()` maps
   curly quotes to straight ones before fact matching; q-018 `expected_facts` =
   `["not found|wasn't found|was not found|couldn't find|could not find|doesn't exist|does not exist|no shipment"]`
   with a `notes` explaining why; `load_previous()` accepts reports without `summary.model` when the file
   name contains `-<model>-`. Tests for each exist in `tests/day03/test_model_params.py`.
2. Run the suite and lint. Fix anything red before moving on.
3. **Finish the real eval** (respecting the budget and quota rules in CLAUDE.md):
   `$env:FAKE_LLM='0'`; re-ingest docs; `uv run python -m core.evals.run --resume <0748 report .json> --rerun q-018`;
   restore fake vectors; `Remove-Item Env:FAKE_LLM`. If the quota stops it again, keep the INCOMPLETE report,
   put the resume command under NEEDS HUMAN, and continue with the other phases; come back to it at the end.
4. **Analyse failures honestly.** For every failing case: root cause (agent, prompt, tool description,
   retrieval, golden case, or model limit), with evidence from the report JSON. Fix the system where the
   system is wrong (e.g. tool descriptions, system prompt - bump `PROMPT_VERSION` when the prompt changes),
   then re-run only the affected cases with `--resume ... --rerun`. Respect the budget.
5. Write `docs/teaching/15-measuring-quality.md` (evals): golden set design, the six checks, fake vs real,
   the gate, and the real story of the three runs (400 temperature -> fix; 429 quota -> resumable runner;
   content-block answers found through q-018). RESULT blocks use the real report numbers.
6. Write `docs/16-deferred-ideas.md` with full idea briefs (template below) for:
   **A. Role-based approval routing** (amount/role thresholds from `claims-process.md` and
   `escalation-matrix.md`, separation of duties, escalation on timeout, delegation, re-approval when the amount
   changes) and **B. Scenario Builder agent** (generate consistent synthetic docs/data/mock API/golden sets from
   discovery notes, with SME review as an approval gate). Both are **deferred, not approved** for this phase.
   Template per idea: Problem & evidence (with file references) / Real use cases (who, which industry, how
   often) / Workplace dynamics (actors, roles, triggers, rules, hand-offs, edge cases: absence, conflict,
   abuse, timeouts) / Success measures (numbers) / Risks & kill criteria / Size (effort, dependencies, kit
   parts reused) / Decision gate (what must be true to approve).
7. Decision log: DC-016 (temperature opt-in; plain-text answers; quota-aware resumable evals; masked ids;
   q-018 widening with evidence; deferred ideas A and B recorded, not approved). Update
   `docs/teaching/README.md` series table, `docs/status/day-03.md` and `docs/journal/day-03.md` (templates:
   `docs/13-status-report-template.md` and `docs/journal/TEMPLATE.md`; Day 1 files show the expected depth).

**DoD Phase 0:** tests green; lint clean; real eval report complete (or INCOMPLETE with the resume command
under NEEDS HUMAN); every failing real case has a written root cause; note 15, docs/16, DC-016, status and
journal committed and pushed as "Day 3 part 2: ...".

## 3. Phase 1 - Day 3 remainder: observability and the missing endpoints

The WBS puts observability (D-16, NFR-08) on Day 3, and FR-12 lists `/ingest`, `/eval`, `/metrics`, which do
not exist yet. The Streamlit UI (D-11) was replaced by the one-file HTML console at `/` (DC-014) - record
that deviation formally if it is not already in the log.

1. Structured JSON logging for the API (one line per request: trace id, route, status, duration, model
   calls, tool calls; never prompt text when `log_prompts: false`; PII-safe).
2. `/metrics` in Prometheus format: request count/latency by route, model calls and tokens, tool calls by
   tool, approvals by outcome, guardrail blocks. Use a small, well-known library (`prometheus-client`).
3. Tracing: OpenTelemetry spans for request -> agent step -> model call -> tool call, exported to the console
   by default (OTLP endpoint optional by env var). The trace id must match the audit log's `trace_id`.
4. `POST /ingest` (runs ingestion for the configured engagement; protect with a bearer token from env;
   returns the stats) and `POST /eval` (runs the eval in the API process **only in fake mode**, returns the
   summary; real-model evals stay a CLI/CI job because of cost and quota). Both are admin endpoints; document
   that in the security doc.
5. Fix the favicon 404 (tiny inline SVG favicon in `ui/index.html`).
6. Tests for all of the above; teaching note `16-observability.md`.

**DoD Phase 1:** one real trace of a tool-calling `/chat` run captured (console export pasted into the
note), `/metrics` scraped with `Invoke-WebRequest` showing non-zero counters, tests + lint green, note 16,
DC row, commit + push.

## 4. Phase 2 - Day 4: containers, Kubernetes, CI/CD, infrastructure as code

1. **Docker (D-12, NFR-11, NFR-12):** multi-stage, non-root, pinned base images for the API (which also
   serves the console) and the mock ERP, in `deploy/docker/`. `/health` reports the build version
   (`BUILD_SHA` env, set at build time) - this closes the "which code is the server running?" gap found on
   Day 3. Extend `docker-compose.yml` so `docker compose up` runs postgres + mock ERP + API with healthchecks.
   `.\tasks.ps1 demo` must work on a clean clone (NFR-01: under 15 minutes). Image scan with `trivy` if
   available locally (no critical CVEs); if trivy is not installed, run it in CI only and say so.
2. **Kubernetes (D-13):** Helm chart in `deploy/helm/fde-kit` (API, mock ERP, Postgres for kind only;
   ConfigMap from engagement config, Secret for tokens, readiness/liveness probes on `/health`). Test on kind
   with `.\tasks.ps1 kind-up`, `helm install`, all pods Ready, `/health` via port-forward. If kind/helm are not
   installed, install nothing system-wide without saying so: put the install commands under NEEDS HUMAN and
   validate the chart with `helm lint`/`helm template` if available.
3. **CI/CD (D-14, NFR-05, NFR-10):** `.github/workflows/ci.yml`: ruff, mypy, pytest with a Postgres+pgvector
   service container (FAKE_LLM=1), gitleaks, docker build, trivy scan, and the **fake** eval as a harness
   check. A separate `eval-real.yml` workflow, manual trigger only (`workflow_dispatch`), using the
   `OPENAI_API_KEY` repository secret, that runs the real eval and uploads the report as an artifact. A
   `deploy.yml` that builds, pushes to Artifact Registry and deploys to Cloud Run via Workload Identity
   Federation - present but **disabled until the human enables it** (manual trigger, documented secrets).
   Push and confirm the CI run is green with `gh run list` / `gh run view` (if `gh` is authenticated; else
   NEEDS HUMAN).
4. **Terraform (D-15):** `deploy/terraform/gcp`: Artifact Registry, Cloud SQL Postgres 16 with pgvector
   (smallest tier from `docs/12-cost-estimate.md`), Secret Manager secrets, a service account with least
   privilege, Cloud Run services (API + mock ERP), budget-friendly settings (min instances 0). Remote state
   documented. `terraform fmt -check` and `terraform validate` must pass. **Do not apply** (CLAUDE.md rule 5):
   write the full PowerShell deployment and teardown sequence into `docs/11-deployment-runbook.md` and under
   NEEDS HUMAN, including the cost estimate per hour and the `destroy` step.
5. Teaching notes: `17-containers.md`, `18-ci-cd.md`, `19-kubernetes.md`, `20-infrastructure-as-code.md`
   (RESULTs from real local runs: docker build/up, helm on kind, CI run, terraform validate). Status and
   journal for Day 4. DC rows / ADR-003 update as needed.

**DoD Phase 2:** `docker compose up` brings up a working stack from a clean clone (`/health` ok, version
shown); chart installs on kind with all pods Ready (or validated + NEEDS HUMAN); CI green on GitHub (or
NEEDS HUMAN with the reason); `terraform validate` clean and the human-run deploy/destroy sequence written;
notes 17-20 committed; every commit green and pushed.

## 5. Phase 3 - Day 5: prove the kit's promise with a second engagement

### 3a. Make the kit generic where it is not (allowed core changes, before engagement #2)

Known kit gaps (verify; there may be more): the tabular ETL is logistics-specific (`LOGISTICS_TABLES` in
`core/ingest/etl.py`), the seed generator is logistics-specific (`core/ingest/seed.py`), the ops tables come
from a logistics migration, the read-only role's grants may only cover schema `ops`, and the scripted fake
model (`core/agent/fake.py`) only knows the logistics script. Make these **config-driven and generic**
(e.g. table specs - columns, types, keys, cleaning rules - declared in `engagement.yaml` or an engagement
`tables.yaml`; per-engagement schema; grants for the configured schema; engagement-owned data scripts in the
engagement folder). Logistics must keep passing every test and its golden set. Each gap = one DC row. Tag the
commit that finishes 3a (`git tag kit-generic`).

### 3b. Engagement #2 with zero core changes (D-18, NFR-02)

- Domain: **Field service for an HVAC maintenance company** (fictional "Coastline Climate Services"):
  service contracts with response-time SLAs by plan (Basic / Plus / Premium), work orders, technicians,
  parts warranty rules, a mock **CMMS** (work-order system) API with `getWorkOrder`, `listWorkOrders`,
  `createDispatch` (a write: needs approval), and policy docs (response-time SLA and credits, warranty,
  emergency vs routine, after-hours fees, escalation, data privacy, plus one planted prompt-injection line
  for the red team). The mock CMMS lives under `services/mock-cmms/` with a generated OpenAPI contract and a
  drift test, like the mock ERP.
- Follow the playbook (`playbook/`, `engagements/_template/`): discovery doc first, then config, data, docs,
  golden set (>= 27 cases with the same category minimums), then evals.
- **Zero changes in `core/`** after the `kit-generic` tag: prove it in the report with
  `git diff --stat kit-generic..HEAD -- core/` (must be empty). If you find another gap, stop engagement #2,
  go back to 3a, fix it generically, move the tag, and record it - that is a finding, not a failure.
- Fake eval runs for both engagements. Real eval for engagement #2 only if the budget and quota allow
  (CLAUDE.md rule 6); otherwise NEEDS HUMAN with the exact commands.
- Teaching note `21-second-engagement.md`: how a new customer is onboarded with the kit, with the real
  timings (how long each playbook step took) and the zero-diff proof.

### 3c. Delivery and closure

- Docs pass: README (what it is, 5-minute quick start in PowerShell, architecture diagram, links to the
  teaching notes and the latest real eval report), architecture diagrams updated (Mermaid), runbook steps
  re-checked, cost actuals filled into `docs/12-cost-estimate.md` from real numbers, skills matrix "After"
  column (`docs/03-skills-matrix.md`) drafted for the author to confirm.
- `docs/15-closure-report.md`: objectives vs results (with evidence), requirement coverage table
  (FR/NFR -> evidence -> met / partly / not met), what failed and what was learned (temperature 400, content
  blocks, quota, stale server, JSON-line guardrail bug, embedding-signature bug), deferred ideas (link
  docs/16), next steps. Honest: "partly met" is fine when true.
- Items only the human can do go under NEEDS HUMAN: the demo video, the cold-rebuild exercise, cloud
  deploy/destroy and billing check, enabling the deploy workflow, confirming the skills matrix.

**DoD Phase 3:** `kit-generic` tag exists; engagement #2 runs end to end (ingest, chat, approval, fake eval)
with an empty `core/` diff since the tag; both golden sets >= 27 cases; note 21; README, closure report,
cost actuals and requirement coverage table committed; everything green and pushed.

## 6. Guardrails summary (from CLAUDE.md, repeated because they matter)

No billable cloud actions. OpenAI <= $1.00 per sprint, no retry loops on 429. Never weaken tests or golden
cases. Never expose secrets or account ids. Append-only migrations. No destructive git/docker commands.
Every commit green; small commits; push after each part. PowerShell for every human-facing command.
New ideas go to docs/16, not into code.

## 7. Global Definition of Done (the sprint is finished when)

- [ ] All phases' DoD met, or each unmet item is listed under NEEDS HUMAN / "partly met" with the reason.
- [ ] `uv run pytest -q` green; `.\tasks.ps1 lint` clean; CI green on `master` (or NEEDS HUMAN).
- [ ] Real eval for demo-logistics: complete report committed, gate result stated honestly, every failure
      has a root cause; the cost of every real run recorded.
- [ ] Engagement #2 delivered with a provably empty `core/` diff since `kit-generic`.
- [ ] Teaching notes 15-21 exist, follow the template, and every RESULT is real captured output.
- [ ] Decision log, status reports and journals are up to date for Days 3-5.
- [ ] The sprint report (section 8) is complete and pushed.

## 8. The sprint report (this is what gets reviewed)

Keep `docs/sprints/reports/sprint-01-report.md` up to date after **every** phase (commit it with that phase).
Write it for a reviewer who will check your claims against the repository. Structure:

1. **Summary** - one paragraph: what was delivered, what was not, overall status.
2. **Phase table** - Phase | Status (done / partly / blocked) | Commits (SHAs) | Tests (count) | Evidence links.
3. **Definition of Done checklists** - every DoD item from sections 2-5 and 7, ticked or not, each with its
   evidence (file path, test name, command + real output excerpt, CI run URL).
4. **Evals** - table per engagement and per run: model, prompt version, cases ran / passed, overall, safety,
   gate, cost, p95 latency, report file. Then every failing case: id, root cause, fix or limitation.
5. **Kit-genericity proof** - the `git diff --stat kit-generic..HEAD -- core/` output (must be empty) and the
   list of gaps fixed in 3a with their DC numbers.
6. **Decisions and deviations** - DC numbers added, one line each, and every place this brief was not
   followed exactly, with the reason.
7. **Findings** - bugs found, surprises, things the plan got wrong. Failures are welcome here.
8. **Cost and quota** - OpenAI spend per run and total (must be <= $1.00); requests used; any other spend
   (should be $0 - no cloud resources were created).
9. **NEEDS HUMAN** - numbered list. Each item: why it needs the human, the exact PowerShell commands or the
   decision options, the expected result, and what to send back.
10. **Risks and open questions** for the sponsor.

Do not mark the sprint finished until the report is complete and pushed.
