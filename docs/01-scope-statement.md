# Scope Statement

Parent: [Project Charter](00-project-charter.md)

## 1. Product description

A Python monorepo containing:

1. **Core** — generic, customer-agnostic components.
2. **Engagements** — one folder per customer situation, driven by `engagement.yaml`.
3. **Deploy** — Docker, Helm, Terraform, GitHub Actions.
4. **Docs & playbook** — project management, technical documentation, and the repeatable FDE method.

## 2. Deliverables

| ID | Deliverable | Description | Acceptance criteria |
|---|---|---|---|
| D-01 | Config loader | Loads and validates `engagement.yaml` (Pydantic) with env-var secret interpolation | Invalid config fails fast with a clear error; unit-tested |
| D-02 | Connectors | File (local/GCS), SQL (Postgres), REST (OpenAPI) | Each connector has a unit test and is selectable by config |
| D-03 | Ingestion pipeline (ETL) | Extract → clean → chunk → embed → load to pgvector; tabular CSV → Postgres tables | Idempotent re-run; row/chunk counts logged |
| D-04 | Retrieval | Semantic + keyword (hybrid) search with metadata filters, returns citations | Retrieval hit-rate measured by evals |
| D-05 | Tool generator | Turns OpenAPI operations and SQL schema into LangChain tools | Tools generated for demo ERP spec without hand-written code |
| D-06 | Agent | LangGraph graph: plan → tool calls → human approval for writes → cited answer | Write operations pause until approved; state persisted |
| D-07 | Guardrails | PII redaction, read-only SQL enforcement, prompt-injection filter on retrieved text | Covered by tests and red-team eval cases |
| D-08 | Eval harness | Golden-set runner: retrieval hit-rate, tool-choice accuracy, answer correctness | Produces `report.md`; CI fails below threshold |
| D-09 | API service | FastAPI: `/chat`, `/ingest`, `/eval`, `/health`, `/metrics` | OpenAPI docs served; health check used by k8s and Cloud Run |
| D-10 | Mock enterprise system | Small FastAPI "legacy ERP / ticketing" service with an OpenAPI spec | Runs in Compose and k8s |
| D-11 | Minimal UI | Streamlit chat UI with approval buttons and citation display | Demo flow works end to end |
| D-12 | Containers | Dockerfiles (multi-stage, non-root) + `docker-compose.yml` | `.\tasks.ps1 demo` works on a clean clone |
| D-13 | Kubernetes | Helm chart, tested on kind | `helm install` → all pods Ready |
| D-14 | CI/CD | GitHub Actions: lint, type-check, test, eval gate, build, push, deploy | Green pipeline on `main` |
| D-15 | IaC | Terraform: Cloud Run, Cloud SQL (Postgres + pgvector), Artifact Registry, Secret Manager, service account | `terraform plan` clean; `apply` produces URL; `destroy` works |
| D-16 | Observability | Structured logs, OpenTelemetry traces (LangSmith optional), Prometheus metrics endpoint | One full trace of a tool-calling run captured |
| D-17 | Engagement #1 | `demo-logistics` (Northwind Logistics) | Golden set ≥ 27 cases, score ≥ 85% |
| D-18 | Engagement #2 | Second scenario (e.g., clinic operations or HR policy desk) | Runs with zero core changes |
| D-19 | Documentation | All files in `docs/` | Reviewed against index; runbook followed successfully |
| D-20 | Playbook & templates | Discovery, data access, pilot loop, handoff | Used to produce engagement #2 |
| D-21 | Demo video | ≤ 5 minutes | Uploaded and linked in README |
| D-22 | Closure report | Results vs. success criteria, lessons learned | Completed Day 5 |

## 3. In scope

- Python 3.12, FastAPI, LangChain, LangGraph, OpenAI (default) with provider switch (Anthropic, Azure OpenAI, Bedrock, Vertex via config).
- PostgreSQL 16 + pgvector as primary store; FAISS/Chroma as local alternatives behind an interface.
- Docker, Docker Compose, kind, Helm, GitHub Actions, Terraform, GCP Cloud Run + Cloud SQL.
- Synthetic data generation with fixed seeds.

## 4. Out of scope (explicit exclusions)

| Exclusion | Reason | Backlog? |
|---|---|---|
| AWS and Azure Terraform modules | Time box; GCP proves the pattern | Yes — v1.1 |
| SSO / OAuth, multi-tenant isolation | Not needed to show the core skills | Yes |
| Production SLA, HA database, autoscaling tuning | Demo scale | No |
| Fine-tuning models | Not in job requirements | No |
| Java implementation | Python satisfies "Python or Java" | No |
| SharePoint / Salesforce connectors | Need accounts; file export covers the pattern | Yes |
| Real customer or personal data | Privacy and legal risk | Never |

## 5. Constraints and assumptions

See [Charter §10–11](00-project-charter.md#10-assumptions).

## 6. Change control

Any addition to scope during the sprint must:

1. Be logged in [14-decision-and-change-log.md](14-decision-and-change-log.md).
2. Replace something of equal effort, or move to the backlog.
3. Pass the priority rule: *does it teach more?*

## 7. Definition of Done

A deliverable is **done** when:

- [ ] Code merged to `main` through a PR with green CI.
- [ ] Unit tests exist for non-trivial logic; agent-affecting changes run the eval gate.
- [ ] Relevant doc updated (architecture, runbook, or ADR).
- [ ] Journal entry explains how it works in the author's own words.
- [ ] No secrets in the repo (`gitleaks` passes).
