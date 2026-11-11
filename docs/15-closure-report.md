# Project Closure Report

Status: **Draft for sponsor sign-off** (2026-11-11, end of Sprint 01). Written by the executor (Claude Code) from the
repository and the sprint report; items only the sponsor can judge are marked as such.
Evidence for every line: [sprint 01 report](sprints/reports/sprint-01-report.md).

## 1. Summary

The kit was built and proven on two fictional customers in two industries: Northwind Logistics (late shipments and SLA
credits) and Coastline Climate Services (HVAC dispatch). Both run on the same `core/`; the second needed zero core
changes after a refactor that moved eleven customer-specific pieces into configuration and engagement-owned files
(`git diff --stat kit-generic..HEAD -- core/` is empty). The agent answers with citations, queries data read-only,
acts through generated API tools only after a human approves, is guarded against prompt injection and PII leaks, is
observable (logs, metrics, traces joined by one id), ships as hardened containers, installs on Kubernetes, and passes CI
on every push. Two things are not finished: the real-model quality gate (the eval is incomplete because the provider
account allows 50 requests a day; every finished case passes, 20/20) and the cloud deployment (prepared and validated;
applying it is the sponsor's step).

## 2. Results vs. success criteria

| ID | Criterion | Target | Actual | Met? |
|---|---|---|---|---|
| SC-01 | Skills at target | >= 90% | After column drafted for the author to confirm ([skills matrix](03-skills-matrix.md)) | Sponsor to judge |
| SC-02 | Reuse proven | 0 core changes for engagement #2 | 0 lines (`git diff kit-generic..e69d0b6 -- core/`, e69d0b6 = the engagement #2 commit); engagement #2 runs end to end. Core changed later only for the generic security fix of review finding F-R1 | **Met** |
| SC-03 | Eval score | >= 85%, CI gate | Real: 20/20 finished cases pass, 7 of 27 not run (quota; see [01b review](sprints/reports/sprint-01b-review.md)); CI runs the fake eval as a harness check, the real gate is a manual workflow | **Partly** (not measured on a complete run) |
| SC-04 | Deployed | Cloud Run URL via Terraform | Terraform validated, runbook and deploy workflow ready; not applied (rule 5) | **Not met** (NEEDS HUMAN) |
| SC-05 | Reproducible | `.\tasks.ps1 demo` <= 15 min | Same steps on a clean CI runner, image builds included: about 3 min (run 43035141379); not timed on a clean laptop | **Partly** |
| SC-06 | Documented | All docs complete; runbook validated | Docs and 22 teaching notes complete; runbook sections 2-3 validated in CI, section 4 not executed | **Partly** |
| SC-07 | Budget | <= USD 55 | OpenAI under $0.01 for the whole project (eval chat $0.0058 measured + embedding re-ingests at most $0.0011 each, not metered); GCP $0 | **Met** |

## 3. Skills outcome (primary objective)

- Skills that reached target, skills below target, the cold-rebuild result and the interview self-check are the author's
  own assessment and are not written here. The matrix has a drafted After column with the evidence each level rests on.
- Cold rebuild exercise: **not done** (NEEDS HUMAN).

## 4. Requirement coverage

| ID | Requirement (short) | Evidence | Status |
|---|---|---|---|
| FR-01 | Load and validate engagement config | `core/config`, `tests/test_config.py`, template validated | Met |
| FR-02 | Ingest PDF/DOCX/MD/HTML/TXT from local or GCS | MD, TXT, PDF from local (`core/ingest/documents.py`); DOCX, HTML and GCS raise NotImplementedError | Partly |
| FR-03 | Tabular ETL into Postgres | Config-driven table specs (DC-019); both engagements load with counted rejects | Met |
| FR-04 | Idempotent ingestion | Re-ingest: `seen=20 skipped=20` (note 16 practicum 3) | Met |
| FR-05 | Cited answers | `search_documents` refs, citation check 100% on finished real cases | Met |
| FR-06 | Hybrid retrieval with metadata filters | Hybrid RRF yes; only an engagement filter, no user-facing metadata filters | Partly |
| FR-07 | Tools from OpenAPI | Mock ERP and mock CMMS specs -> tools, no hand-written tool code | Met |
| FR-08 | Read-only SQL tool with schema introspection | `core/toolgen/sql.py`, `agent_ro` grants per schema (DC-023) | Met |
| FR-09 | Pause before writes | `createTicket` / `createDispatch` pause; tests in day02 and day05 | Met |
| FR-10 | Persist state across approval | Postgres checkpointer; approve resumes the thread | Met |
| FR-11 | Provider by config | OpenAI and fake implemented (the verification clause allows "fake + OpenAI"); others are stubs | Met (as verified) |
| FR-12 | /chat /ingest /eval /health /metrics | All exist (DC-014, DC-017); tests in `tests/day03/test_observability.py` | Met |
| FR-13 | Eval harness + Markdown report | `core/evals`, reports committed for real runs | Met |
| FR-14 | Chat UI with citations and approvals | One-file console at `/` (replaces Streamlit, DC-017) | Met |
| FR-15 | FAKE_LLM mode | Tests and CI run without keys | Met |
| FR-16 | Swappable vector store (Could) | Schema accepts faiss/chroma; only pgvector implemented | Not met |
| FR-17 | Multi-cloud Terraform (Won't) | Out of scope | n/a |
| NFR-01 | Clean clone to demo <= 15 min | CI clean runner about 3 min; laptop timing NEEDS HUMAN | Partly |
| NFR-02 | 0 core lines for a new engagement | Empty diff since `kit-generic` | Met |
| NFR-03 | Eval >= 85% | 20/20 finished; incomplete (7 not run) | Partly |
| NFR-04 | p95 /chat <= 8 s (cloud) | Not measured in the cloud; real eval cases locally: p95 15-17 s per case | Not met (unmeasured target environment; risk) |
| NFR-05 | No secrets in code | gitleaks over full history in CI: no leaks | Met |
| NFR-06 | Read-only DB credentials | `agent_ro`: SELECT, read-only transactions, test for INSERT refusal | Met |
| NFR-07 | PII redaction | Tool results and logs redacted (tests); real red-team PII case q-026 not yet run | Met by tests; eval pending |
| NFR-08 | Every request traceable | One trace per request, id in audit log and header (note 16) | Met |
| NFR-09 | Cost within budget | Under $0.01 | Met |
| NFR-10 | Lint, types, tests in CI | ruff, mypy, pytest in CI | Met |
| NFR-11 | Same image on Compose, kind, Cloud Run | Compose and kind use the same images in CI; Cloud Run not deployed | Partly |
| NFR-12 | Container hygiene | Non-root, multi-stage, digest-pinned, trivy 0 CRITICAL with fix | Met |

## 5. Deliverables status

| D | Deliverable | Status |
|---|---|---|
| D-01..D-07 | Config, connectors, ingestion, retrieval, toolgen, agent, guardrails | Done (D-02: local files only; GCS backlog) |
| D-08 | Eval harness | Done; real gate incomplete (quota) |
| D-09 | API service | Done (all five endpoints) |
| D-10 | Mock enterprise system | Done (mock ERP; plus mock CMMS for #2) |
| D-11 | Minimal UI | Done as an HTML console instead of Streamlit (DC-017) |
| D-12 | Containers | Done (verified in CI) |
| D-13 | Kubernetes | Done (Helm on kind in CI) |
| D-14 | CI/CD | Done; deploy workflow disabled until enabled |
| D-15 | IaC | Prepared and validated; apply/destroy is the sponsor's step |
| D-16 | Observability | Done (trace captured, note 16) |
| D-17 | Engagement #1 | Done; real eval incomplete |
| D-18 | Engagement #2 | Done; real eval not run (quota) |
| D-19 | Documentation | Done (this sprint: notes 15-21, docs/16, status and journals Days 3-5) |
| D-20 | Playbook | Used for engagement #2 (note 21) |
| D-21 | Demo video | Not done (NEEDS HUMAN) |
| D-22 | Closure report | This draft |

## 5b. Schedule and cost

| | Planned | Actual |
|---|---|---|
| Sessions | 6 | Days 0-5 (Day 3 close-out to Day 5 in one autonomous session, Sprint 01) |
| Hours | | The author records hours |
| Cost (USD) | 55 | Under 0.01 (OpenAI); 0 (GCP) |

## 6. What failed, and what was learned

| What happened | Root cause | What changed |
|---|---|---|
| First real eval: every call HTTP 400 | `gpt-6-luna` rejects `temperature`; we always sent it | Parameters are opt-in (DC-016) |
| Users saw `[{'type': 'text', ...}]` | Newer models return content as a list of blocks; code used `str(content)` | `message.text` everywhere; found through a failing golden case (q-018) |
| Real eval stopped after 18 cases | 50 requests/day quota | Quota-aware runner: NOT RUN, INCOMPLETE, `--resume` across days |
| Resumed report claimed $0.0045 it did not spend | Reused results counted as this run's | "This run" vs "carried over" (Sprint 01) |
| An old server answered on port 8000 | No way to see which code a server runs | `BUILD_SHA` in `/health` |
| Guardrail hid whole tool results (Day 3) | Line-based filter on one-line JSON | JSON-aware cleaning (DC-015) |
| Switching FAKE_LLM gave nonsense search scores | Vectors from another embedding model | Embedding signature stored and checked (`/health`, eval preflight) |
| First image build failed the CVE gate | Digest pin froze old Debian packages | OS upgrade in the runtime stage |
| Laptop memory under the 3 GB floor | Browser + Docker VM | Container proofs moved to CI |
| Sponsor review F-R1 (HIGH): the planned Cloud Run API was public, so anyone could approve writes or spend quota | Access was designed per endpoint (admin token) instead of per deployment; "by" is self-declared | API IAM-only with proxy access; reviewer and chat tokens; audit `token_verified` (DC-031, T-10, R-13) |
| Sponsor review F-R2 (MEDIUM): `.\tasks.ps1` shown as ".TAB asks.ps1" in tasks.ps1 and the report | Edit scripts passed through a heredoc that collapsed `\\` before Python read `\t` as TAB | Fixed; repo scanned; test fails on TAB+"asks.ps1" or control characters (DC-032) |
| Sponsor review F-R3 (LOW): two API tests failed instead of skipping with Postgres down | They opened the database through `/eval` without asking for the database fixture | Both depend on `migrated_db` now (DC-034) |
| Commit 4a7c808 titled "Real eval complete" for an INCOMPLETE report (F-R4) | A commit step meant only for exit code 0 was run anyway | Not rewritten (rule 7); corrected in DC-033; the commit step is now conditional on exit code 0 |
| Logistics content inside `core/` | Built for one customer first | Eleven gaps moved to config (DC-019..DC-029) |

| What went well | What didn't | What I'd do differently next engagement |
|---|---|---|
| Every real failure became a test; reports kept as history | Real evals are throttled by the account quota | Ask for a quota that fits a full run before the eval day |
| One trace id across logs, traces and audit | Latency target unmeasured in the cloud | Measure p95 on the target platform early |
| Second engagement in about 10 minutes of build time | Engagement #2's golden set not yet judged by a real model | Run a one-case real smoke test before every full run |

## 7. Backlog / next version

- Deferred, not approved: [A. role-based approval routing, B. Scenario Builder agent](16-deferred-ideas.md).
- GCS/S3 document sources, DOCX/HTML readers (FR-02); vector-store adapters (FR-16).
- `/health` returning 503 when degraded (trade-off in note 19); per-engagement database roles.
- AWS and Azure Terraform modules; GKE deployment of the Helm chart; LLM-as-judge as a secondary check.
- Phase 2 "break it on purpose" practicums (DC-011).

## 8. Sign-off

| Role | Name | Date |
|---|---|---|
| Sponsor | E. Mkwambe | (on acceptance) |
