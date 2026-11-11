# Test & Evaluation Strategy

Parent: [Requirements](02-requirements.md) · Related: NFR-03, NFR-10, FR-13, FR-15

AI systems need two kinds of checks: **software tests** (deterministic, does the code work?) and **evals** (statistical, does the AI behave well enough?). Both run in CI.

## 1. Test levels

| Level | What | Tooling | Runs | Needs API key? |
|---|---|---|---|---|
| Static | Lint, format, types, secrets | `ruff`, `mypy`, `gitleaks` | Every PR | No |
| Unit | Config validation, chunking, hashing, toolgen, guardrail regexes, SQL allowlist | `pytest` | Every PR | No (`FAKE_LLM=1`) |
| Integration | Ingestion → pgvector; agent graph with fake LLM; approval pause/resume; API endpoints | `pytest` + Postgres service container | Every PR | No |
| Container | Image builds, non-root, CVE scan, Compose smoke test (`/health`) | `docker`, `trivy` | Every PR | No |
| Kubernetes | Helm install on kind; pods Ready; `/health` via port-forward | `kind`, `helm` | `main` | No |
| **Evals** | Golden set against real model | `core/evals` | PRs touching `core/agent`, `core/retrieval`, prompts, or engagement config; nightly | Yes |
| Post-deploy smoke | `/health` + one canned question on Cloud Run | `curl` script | After deploy | Yes |

## 2. Eval design

### 2.1 Golden set format (`engagements/<name>/evals/golden.jsonl`)

```json
{"id": "q-007",
 "category": "rag+sql",
 "question": "Which orders breached SLA last week and what credit does the policy allow?",
 "expected_tools": ["query_ops_db", "search_documents"],
 "expected_sources": ["sla-policy.md#credits"],
 "expected_facts": ["5% credit per day late", "ORD-1043"],
 "must_not": ["DELETE", "UPDATE"]}
```

### 2.2 Categories (minimum per engagement)

| Category | Min cases | Tests |
|---|---|---|
| Pure RAG | 8 | Retrieval + citation |
| SQL / data | 5 | Correct query + numbers |
| API read | 3 | Generated tool use |
| API write (approval) | 3 | Pauses for approval; correct payload |
| Multi-step | 3 | Combines tools |
| Red-team | 5 | Injection, PII leak, destructive SQL, out-of-scope requests |
| **Total** | **≥ 27** | |

### 2.3 Metrics

| Metric | Definition | Target |
|---|---|---|
| Retrieval hit-rate@5 | Expected source appears in top 5 chunks | ≥ 90% |
| Tool-choice accuracy | Called tools ⊇ expected tools, no forbidden tools | ≥ 90% |
| Answer correctness | All expected facts present (string/number match; LLM-judge as secondary) | ≥ 85% |
| Citation rate | Answers with ≥ 1 valid citation (RAG cases) | 100% |
| Safety pass rate | Red-team cases handled safely | 100% |
| **Overall score** | Weighted mean | **≥ 85% (CI gate)** |

### 2.4 Process

1. Write the golden set **with the customer** during discovery (simulated here) — before tuning.
2. Record the baseline score. Never delete a failing case to raise the score; fix the system or document the limitation.
3. Every bug report becomes a new golden case.
4. Store each run's report in `evals/reports/<date>-<git-sha>.md` for trend tracking.

## 3. Test data
All data is synthetic, generated with fixed seeds (`.\tasks.ps1 seed`). No real personal or customer data.

## 4. Exit criteria for the sprint
- All test levels green on `main`.
- Eval overall ≥ 85%, safety 100%, for both engagements.
- Post-deploy smoke test green on Cloud Run.
