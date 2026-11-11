# Project Charter — FDE Engagement Kit

| Field | Value |
|---|---|
| Project name | FDE Engagement Kit |
| Repository | `fde-engagement-kit` |
| Version | 1.0 (baseline) |
| Date | 2026-11-09 |
| Sponsor / Project manager / Lead engineer | E. Mkwambe |
| Duration | 1-week sprint (5 working sessions + 1 prep session) |
| Status | Approved — ready for Day 0 |

---

## 1. Purpose

Build a **reusable, config-driven toolkit** for delivering enterprise Generative-AI solutions the way a Forward Deployed Engineer (FDE) does: discover a customer's problem, connect to their documents, databases and APIs, ship an evaluated AI agent, deploy it to the cloud, and hand it over with documentation.

The kit separates a **generic core** (connectors, RAG, agent, guardrails, evals, deployment) from **customer-specific engagements** (one folder each: config, API specs, eval set, discovery notes). A new real-world situation is handled by creating a new engagement folder, not by rewriting code.

## 2. Business case

| Problem | Response |
|---|---|
| Job postings for FDE / AI engineer roles demand a long list of concrete skills (LangGraph, RAG, vector DBs, tool calling, Docker, Kubernetes, CI/CD, cloud, SQL, ETL). | Build and document each skill in one coherent, working system. |
| Tutorials and toy demos don't show delivery judgment. | Run the project with real project-management artifacts and an engagement playbook. |
| One-off demos can't be reused for paid work. | Config-driven design: the same core serves any feasible customer scenario. |

## 3. Objectives

### 3.1 Internal objective — skill development (PRIMARY)

> Gain hands-on, explainable competence in every skill listed in [03-skills-matrix.md](03-skills-matrix.md), reaching the target level for each, and be able to rebuild any component from memory and defend every design decision in an interview.

Measured by: skills-matrix self-assessment (before/after), daily learning journal, and the ability to complete a "cold rebuild" exercise (see §7).

### 3.2 External objective — capability showcase (SECONDARY)

> Demonstrate that the author can select and correctly use the **relevant and proper** infrastructure and tools to deliver a feasible customer need end-to-end: discovery → design → build → evaluate → deploy → hand off.

Measured by: a public repository with two working engagements on one core, a live cloud deployment, passing CI with an eval gate, complete documentation, and a ≤5-minute demo video.

**Priority rule:** when time is short, choose the option that teaches more over the option that looks better. Polish never displaces learning.

## 4. Success criteria

| ID | Criterion | Target | Evidence |
|---|---|---|---|
| SC-01 | Skills reach target level | ≥ 90% of skills at target in self-assessment | `03-skills-matrix.md` (after column) |
| SC-02 | Reusability proven | 2 engagements run on the same core with zero core code changes for the second | Git diff of engagement #2 |
| SC-03 | Quality gate | Agent eval score ≥ 85% on golden set; CI blocks merges below threshold | CI run + `evals/report.md` |
| SC-04 | Deployed | Public HTTPS endpoint on GCP Cloud Run provisioned by Terraform | `terraform apply` output, URL |
| SC-05 | Reproducible locally | Fresh clone → working demo with `.\tasks.ps1 demo` in ≤ 15 min | Timed test on a clean machine / Codespace |
| SC-06 | Documented | All docs in the index complete; runbook validated by following it | `docs/` + closure report |
| SC-07 | Budget | Cloud + API spend ≤ budget cap (see §8) | Billing report |

## 5. Scope summary

Full detail in [01-scope-statement.md](01-scope-statement.md).

**In scope:** generic core (connectors for files/SQL/REST, ingestion & embeddings, pgvector, LangGraph agent with tool calling and human approval, OpenAPI tool generation, guardrails, eval harness, FastAPI service), Docker/Compose, Helm on kind, GitHub Actions CI/CD, Terraform for GCP Cloud Run, two engagements, full documentation and playbook.

**Out of scope:** production SLAs, SSO/multi-tenant auth, AWS/Azure Terraform modules (backlog), fine-tuning, real customer data.

## 6. Milestones

| ID | Milestone | Session | Exit criterion |
|---|---|---|---|
| M0 | Charter approved, environment ready | Day 0 | Accounts, tools, keys verified |
| M1 | First cited answer | Day 1 | `/chat` answers a policy question with citations from pgvector |
| M2 | Agent acts | Day 2 | Agent uses SQL + generated API tools; write action waits for approval |
| M3 | Quality baseline | Day 3 | Eval harness runs in CI; guardrails and tracing on |
| M4 | Deployed | Day 4 | CI/CD pipeline deploys to Cloud Run via Terraform; Helm runs on kind |
| M5 | Reusable & delivered | Day 5 | Second engagement live; demo video; closure report |

Detail: [04-wbs-and-schedule.md](04-wbs-and-schedule.md).

## 7. Learning approach (supports the primary objective)

1. **Read → build → explain.** For each skill: read the official docs, build the component, then write a 5-sentence explanation in the daily journal.
2. **No unexplained code.** Any generated or copied code is annotated or rewritten until every line can be explained.
3. **Decision records.** Every significant choice gets an ADR, including rejected alternatives.
4. **Cold rebuild (Day 5).** Without notes, rebuild one component (e.g., the RAG retriever or the LangGraph approval node) in ≤ 45 min.
5. **Mock interview.** Answer the questions in [03-skills-matrix.md §4](03-skills-matrix.md) aloud and record gaps.

## 8. Budget

| Item | Cap |
|---|---|
| OpenAI API (chat + embeddings, dev + evals) | USD 20 |
| GCP (Cloud Run, Cloud SQL, Artifact Registry, Secret Manager) | USD 25 (set a GCP budget alert at 50/90/100%) |
| Contingency | USD 10 |
| **Total** | **USD 55** |

Detail and cost controls: [12-cost-estimate.md](12-cost-estimate.md).

## 9. Stakeholders

| Stakeholder | Role | Interest |
|---|---|---|
| E. Mkwambe | Sponsor, PM, engineer | Skill growth, portfolio, reusable asset |
| Hiring managers / interviewers | Primary external audience | Evidence of skills and delivery judgment |
| Recruiters (e.g., Dice listings) | Secondary audience | Keyword match, clear README |
| "Northwind Logistics" (fictional) | Simulated customer for engagement #1 | A working ops copilot |
| "Second engagement customer" (fictional) | Simulated customer for engagement #2 | Proves reuse |

RACI and communication plan: [08-raci-and-communication.md](08-raci-and-communication.md).

## 10. Assumptions

- Python 3.12, Docker, kubectl, kind, Helm, Terraform, gcloud CLI available.
- An OpenAI API key and a GCP project with billing are available.
- All data used is synthetic or public; no real customer data enters the project.
- About 6–8 focused hours per working session.

## 11. Constraints

- Fixed 1-week time box; scope flexes, time does not.
- Budget cap in §8.
- Default LLM provider is OpenAI; provider must remain switchable by config.
- Primary cloud is GCP Cloud Run.

## 12. High-level risks

Top risks: scope creep into framework-building, cloud setup time, API cost overrun, shallow learning from copying code. Full register: [07-risk-register.md](07-risk-register.md).

## 13. Approval

| Role | Name | Decision | Date |
|---|---|---|---|
| Sponsor | E. Mkwambe | Approved | 2026-11-09 |
