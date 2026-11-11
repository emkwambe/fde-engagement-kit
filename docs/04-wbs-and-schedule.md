# Work Breakdown Structure & Schedule

Parent: [Project Charter](00-project-charter.md) · Milestones M0–M5

## 1. WBS

```
1.0 FDE Engagement Kit
├── 1.1 Initiation & planning
│   ├── 1.1.1 Charter, scope, requirements
│   ├── 1.1.2 Skills matrix baseline (Before column)
│   ├── 1.1.3 Risk register, RACI, comms plan
│   └── 1.1.4 Environment & accounts (OpenAI, GCP, GitHub)
├── 1.2 Core platform
│   ├── 1.2.1 Repo scaffold, config loader (D-01)
│   ├── 1.2.2 Connectors: files, SQL, REST (D-02)
│   ├── 1.2.3 ETL + ingestion + embeddings (D-03)
│   ├── 1.2.4 Retrieval (hybrid, citations) (D-04)
│   ├── 1.2.5 Tool generator: OpenAPI + SQL (D-05)
│   ├── 1.2.6 LangGraph agent + approvals + checkpoints (D-06)
│   ├── 1.2.7 Guardrails (D-07)
│   ├── 1.2.8 Eval harness (D-08)
│   ├── 1.2.9 FastAPI service (D-09)
│   └── 1.2.10 Streamlit UI (D-11)
├── 1.3 Engagements
│   ├── 1.3.1 Mock ERP service + OpenAPI spec (D-10)
│   ├── 1.3.2 Engagement #1 demo-logistics: data, config, golden set (D-17)
│   └── 1.3.3 Engagement #2 (D-18)
├── 1.4 Platform & delivery
│   ├── 1.4.1 Dockerfiles + Compose (D-12)
│   ├── 1.4.2 Helm chart on kind (D-13)
│   ├── 1.4.3 GitHub Actions CI/CD (D-14)
│   ├── 1.4.4 Terraform GCP (D-15)
│   └── 1.4.5 Observability (D-16)
└── 1.5 Documentation & closure
    ├── 1.5.1 Architecture, ADRs, security, test strategy, runbook
    ├── 1.5.2 Playbook & templates (D-20)
    ├── 1.5.3 Demo video (D-21)
    └── 1.5.4 Closure report, skills matrix After column (D-22)
```

## 2. Schedule (1-week sprint)

Each session ≈ 6–8 focused hours. Learning time is budgeted explicitly (📖) because skill development is the primary objective.

### Day 0 — Prep (≈ 2 h) → **M0**

| Block | Task | WBS |
|---|---|---|
| 0:00–0:45 | Read charter/scope; fill skills matrix *Before* column | 1.1.1–1.1.2 |
| 0:45–1:30 | Install/verify: Python 3.12, uv, Docker, kind, kubectl, Helm, Terraform, gcloud; create GCP project + budget alert; OpenAI key with usage limit | 1.1.4 |
| 1:30–2:00 | Write `engagements/demo-logistics/discovery.md` using the playbook (simulated customer interview) | 1.3.2 |

### Day 1 — Data & RAG foundation → **M1: first cited answer**

| Block | Task | WBS | Skills |
|---|---|---|---|
| 📖 0:00–1:00 | pgvector, embeddings, chunking concepts | — | S-05, S-06 |
| 1:00–2:00 | Scaffold repo, `pyproject.toml`, config loader + schema, Compose with Postgres+pgvector | 1.2.1 | S-01 |
| 2:00–3:30 | Synthetic data generator (seeded): orders, shipments, SLAs CSV; ~20 policy docs | 1.3.2 | S-03 |
| 3:30–5:00 | ETL job (CSV → Postgres) and document ingestion (chunk → embed → pgvector, content hash) | 1.2.2–1.2.3 | S-03, S-04, S-05 |
| 5:00–6:30 | Retriever with citations + minimal `/chat` RAG endpoint | 1.2.4, 1.2.9 | S-06, S-07 |
| 6:30–7:00 | Journal; ADR-002 (vector store) | 1.5.1 | S-23 |

### Day 2 — Agent & integrations → **M2: agent acts**

| Block | Task | WBS | Skills |
|---|---|---|---|
| 📖 0:00–1:00 | LangGraph: state, nodes, conditional edges, checkpointers, interrupts | — | S-10 |
| 1:00–2:00 | Mock ERP service (FastAPI) + OpenAPI spec: shipments, tickets | 1.3.1 | S-02 |
| 2:00–3:30 | Tool generator: OpenAPI → tools; SQL schema → read-only query tool | 1.2.5 | S-11, S-04 |
| 3:30–5:30 | LangGraph agent: router, tool node, approval interrupt for POST/PUT/DELETE, Postgres checkpointer | 1.2.6 | S-09, S-10 |
| 5:30–6:30 | Provider switch (OpenAI default, fake LLM for tests); prompt files with versions | 1.2.6 | S-08, S-12 |
| 6:30–7:00 | Journal; ADR-001 (LangGraph), ADR-005 (provider abstraction) | 1.5.1 | S-23 |

### Day 3 — Quality, safety, observability → **M3: quality baseline**

| Block | Task | WBS | Skills |
|---|---|---|---|
| 📖 0:00–0:45 | RAG/agent evaluation methods; OWASP Top 10 for LLM applications | — | S-13, S-14 |
| 0:45–2:00 | Golden set (≥ 27 cases incl. 5 red-team; see test strategy §2.2) for demo-logistics | 1.3.2 | S-13 |
| 2:00–3:30 | Eval harness + Markdown report + threshold exit code | 1.2.8 | S-13 |
| 3:30–5:00 | Guardrails: PII redaction, SQL allowlist/read-only role, injection filter on retrieved chunks | 1.2.7 | S-14 |
| 5:00–6:00 | OpenTelemetry traces + `/metrics`; structured logging | 1.4.5 | S-15 |
| 6:00–7:00 | Streamlit UI with approvals and citations; journal | 1.2.10 | — |

### Day 4 — Containers, Kubernetes, CI/CD, cloud → **M4: deployed**

| Block | Task | WBS | Skills |
|---|---|---|---|
| 📖 0:00–0:45 | Helm basics; Terraform state; Workload Identity Federation for GitHub → GCP | — | S-17, S-19 |
| 0:45–1:45 | Multi-stage, non-root Dockerfiles; image scan | 1.4.1 | S-16 |
| 1:45–3:00 | Helm chart; deploy full stack to kind; probes; ConfigMap/Secret | 1.4.2 | S-17 |
| 3:00–4:30 | GitHub Actions: lint → type-check → test → eval gate → build → push | 1.4.3 | S-18 |
| 4:30–6:30 | Terraform: Artifact Registry, Cloud SQL (pgvector), Secret Manager, Cloud Run, service account; deploy job | 1.4.4 | S-19, S-20 |
| 6:30–7:00 | Validate runbook steps; journal; ADR-003 | 1.5.1 | S-23 |

### Day 5 — Reuse, delivery, closure → **M5: reusable & delivered**

| Block | Task | WBS | Skills |
|---|---|---|---|
| 0:00–2:00 | Engagement #2 via the playbook: discovery → config → data → golden set → eval (no core changes) | 1.3.3 | S-22 |
| 2:00–2:45 | Cold rebuild exercise (one component, no notes) | — | all |
| 2:45–3:45 | Finish docs: architecture diagrams, runbook, cost actuals | 1.5.1 | S-23 |
| 3:45–4:45 | Record ≤ 5-min demo video | 1.5.3 | S-22 |
| 4:45–5:45 | Closure report; skills matrix *After*; interview self-check | 1.5.4 | S-24 |
| 5:45–6:00 | `terraform destroy` or scale to zero; confirm billing | 1.4.4 | S-20 |

## 3. Minimum viable cut lines

If a day overruns, cut in this order (cut **top** first):

1. Streamlit UI → use `/docs` Swagger page for the demo.
2. Hybrid search → vector-only.
3. Helm on kind → plain manifests.
4. GCS connector → local files only.
5. Engagement #2 shrinks to config + 10 golden cases.

**Never cut:** evals, guardrails, journal entries, the discovery doc, Terraform deploy.

## 4. Critical path

`Config loader → Ingestion → Retrieval → Agent → Evals → CI eval gate → Docker → Terraform deploy`

A slip on any of these moves M4. Everything else can float.
