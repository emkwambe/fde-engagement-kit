# Requirements Specification

Parent: [Scope Statement](01-scope-statement.md)

Priority uses MoSCoW: **M**ust, **S**hould, **C**ould, **W**on't (this sprint).

## 1. Functional requirements

| ID | Requirement | Priority | Deliverable | Verified by |
|---|---|---|---|---|
| FR-01 | The system shall load a customer engagement from `engagements/<name>/engagement.yaml` and validate it against a schema. | M | D-01 | Unit test |
| FR-02 | The system shall ingest documents (PDF, DOCX, MD, HTML, TXT) from local paths or GCS, chunk them, embed them, and store vectors with source metadata. | M | D-02, D-03 | Integration test |
| FR-03 | The system shall load tabular data (CSV/JSON exports) into Postgres tables through a repeatable ETL job. | M | D-03 | Integration test |
| FR-04 | Re-running ingestion on unchanged sources shall not create duplicates (content-hash idempotency). | M | D-03 | Unit test |
| FR-05 | The system shall answer natural-language questions using retrieved context and return citations (document, section, chunk id). | M | D-04, D-06 | Eval: citation present |
| FR-06 | The system shall support hybrid retrieval (vector similarity + full-text) with metadata filters. | S | D-04 | Eval: hit-rate |
| FR-07 | The system shall auto-generate callable tools from an OpenAPI 3 spec listed in config. | M | D-05 | Unit test on demo spec |
| FR-08 | The system shall provide a read-only SQL tool over configured tables, with schema introspection for the LLM. | M | D-05, D-07 | Unit + red-team test |
| FR-09 | The agent shall pause before any tool call whose HTTP method is listed under `require_approval`, and resume only after explicit approval. | M | D-06 | Integration test |
| FR-10 | The agent shall persist conversation/graph state so an approval can resume a paused run. | M | D-06 | Integration test |
| FR-11 | The LLM and embedding providers shall be selectable by config without code changes. | M | D-01, D-06 | Run with 2 providers (or fake + OpenAI) |
| FR-12 | The system shall expose `/chat`, `/ingest`, `/eval`, `/health`, `/metrics` HTTP endpoints. | M | D-09 | API tests |
| FR-13 | The eval harness shall score retrieval hit-rate, tool-choice accuracy and answer correctness against a golden set and write a Markdown report. | M | D-08 | CI artifact |
| FR-14 | A chat UI shall show answers, citations, and approve/reject buttons for pending actions. | S | D-11 | Manual demo script |
| FR-15 | A `FAKE_LLM` mode shall let tests and CI run deterministically without API keys. | M | D-06, D-14 | CI |
| FR-16 | The vector store backend shall be swappable (pgvector default; FAISS/Chroma local). | C | D-04 | Unit test |
| FR-17 | Multi-cloud Terraform (AWS, Azure). | W | — | Backlog |

## 2. Non-functional requirements

| ID | Category | Requirement | Target | Verified by |
|---|---|---|---|---|
| NFR-01 | Reproducibility | Fresh clone to working local demo with one command | ≤ 15 min, `.\tasks.ps1 demo` | Timed run |
| NFR-02 | Reusability | New engagement requires no core code change | 0 lines changed in `core/` | Git diff |
| NFR-03 | Quality | Golden-set eval score | ≥ 85% | CI gate |
| NFR-04 | Latency | p95 `/chat` latency for a 1–2 tool turn (cloud) | ≤ 8 s | Metrics |
| NFR-05 | Security | No secrets in code; secrets via env/Secret Manager | `gitleaks` clean | CI |
| NFR-06 | Security | DB credentials used by the agent are read-only | Role grants SELECT only | Test |
| NFR-07 | Privacy | PII (emails, phones, SSN-like patterns) redacted before logging and before sending tool outputs to the LLM where configured | Red-team cases pass | Eval |
| NFR-08 | Observability | Every request traceable end to end (request → LLM calls → tools) | 1 trace id per request | Trace screenshot |
| NFR-09 | Cost | Spend within charter budget | ≤ USD 55 | Billing |
| NFR-10 | Maintainability | Lint + type-check + tests in CI | `ruff`, `mypy`, `pytest` green | CI |
| NFR-11 | Portability | Runs on Docker Compose, kind, and Cloud Run from the same image | Same image digest | CI logs |
| NFR-12 | Container hygiene | Non-root user, multi-stage build, pinned base image | Image scan has no critical CVEs | `trivy` in CI |

## 3. Traceability: job requirements → project evidence

Source: "Forward Deployed Engineer – AI / Generative AI" (Value Technology, Dice ID 91163786).

| Job requirement | Requirement IDs | Evidence in repo |
|---|---|---|
| Python, software engineering | NFR-10 | `core/`, tests, CI |
| REST APIs, backend services | FR-12 | `core/api/`, OpenAPI docs |
| Enterprise integrations, external APIs | FR-07, FR-08 | `core/toolgen/`, mock ERP |
| Generative AI, LLMs, prompt engineering | FR-05, FR-11 | `core/agent/prompts/` |
| RAG, embeddings, semantic search | FR-02, FR-05, FR-06 | `core/ingest/`, `core/retrieval/` |
| Vector databases (Pinecone, Weaviate, Chroma, FAISS) | FR-16 | pgvector + FAISS/Chroma adapters |
| AI agents, tool calling, agentic workflows | FR-07, FR-09, FR-10 | `core/agent/graph.py` |
| LangChain / LangGraph | FR-07, FR-09 | Agent + tool generation |
| OpenAI / Azure OpenAI / Anthropic APIs | FR-11 | Provider switch |
| AWS / Azure / GCP | FR-17 (backlog), D-15 | Terraform GCP; provider config |
| Docker, Kubernetes | NFR-11, NFR-12 | `deploy/docker`, `deploy/helm` |
| CI/CD, infrastructure as code | NFR-05, NFR-10 | `.github/workflows`, `deploy/terraform` |
| SQL, PostgreSQL, ETL, data pipelines | FR-03, FR-04, FR-08 | `core/ingest/etl.py` |
| Deploying, monitoring, evaluating, securing AI | FR-13, NFR-03, NFR-07, NFR-08 | `core/evals`, `core/guardrails`, tracing |
| Customer communication, consulting | — | `playbook/`, engagement discovery docs |
| Translate business requirements into solutions | — | `engagements/*/discovery.md` → config → evals |
| Documentation of designs and deployment | — | `docs/` |
