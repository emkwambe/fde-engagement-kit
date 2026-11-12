# Cost Estimate & Controls

Parent: [Charter §8](00-project-charter.md#8-budget) · Related: NFR-09, T-07

**Prices checked on 2026-11-09** from the official OpenAI API and Google Cloud pricing pages (list prices, USD, no discounts). GCP prices shown are the published us-central1 (Iowa) rates; confirm the us-east1 rate in the GCP console before Day 4. Prices change; re-check before a real engagement.

## 1. Summary

| Category | Expected (sprint) | Worst case* | Budget cap |
|---|---|---|---|
| OpenAI API | $4.20 | $8.40 | $20 |
| Google Cloud | $9.20 | $27.50 | $25 |
| Free services | $0.00 | $0.00 | — |
| **Total** | **≈ $13.40** | **≈ $35.90** | **$55 (incl. $10 contingency)** |

\*Worst case = token usage doubles **and** Cloud SQL is left running for a full month instead of ~10 days. The single biggest cost risk is forgetting to delete Cloud SQL.

## 2. Unit prices used

| Service | Item | Unit price |
|---|---|---|
| OpenAI | `gpt-6-luna` (development model) | $0.10 / 1M input tokens · $0.50 / 1M output tokens |
| OpenAI | `gpt-6.1-terra` (target model: final evals, demo) | $1.00 / 1M input · $5.00 / 1M output |
| OpenAI | `text-embedding-3-small` | $0.02 / 1M tokens |
| Cloud SQL | `db-g1-small` (shared core, 1.7 GiB RAM) | $0.035 / hour |
| Cloud SQL | `db-f1-micro` (shared core, 0.6 GiB RAM), cheaper fallback | $0.0105 / hour |
| Cloud SQL | SSD storage | $0.000232877 / GiB-hour (≈ $0.17 / GiB-month) |
| Cloud Run | Request-based billing, monthly free tier | 180,000 vCPU-s · 360,000 GiB-s · 2M requests free |
| Cloud Run | Above free tier | $0.000024 / vCPU-s (active) |
| Artifact Registry | Storage | First 0.5 GiB free, then ≈ $0.10 / GiB-month |
| Secret Manager | Active secret versions | First 6 free, then ≈ $0.06 / version-month |
| Secret Manager | Access operations | First 10,000 / month free, then $0.03 / 10,000 |

## 3. Itemized: OpenAI API

| # | What it's for | Model | Volume assumption | Tokens | Cost |
|---|---|---|---|---|---|
| O-1 | **Ingestion:** turning policy docs into vectors (2 engagements × ~50 docs × ~5k tokens, re-ingested 3×) | text-embedding-3-small | 3 runs | 1.5M | $0.03 |
| O-2 | **Query embeddings:** embedding each question for search | text-embedding-3-small | ~3,000 questions × 50 tokens | 0.15M | < $0.01 |
| O-3 | **Development chat:** testing the agent while building (Days 1–4) | gpt-6-luna | ~300 turns × 6k in / 500 out | 1.8M in · 0.15M out | $0.26 |
| O-4 | **Routine evals:** golden-set runs on PRs | gpt-6-luna | 2 engagements × 27 cases × 8 runs × 8k in / 600 out | 3.46M in · 0.26M out | $0.48 |
| O-5 | **Final evals:** run on the target model before merge/release | gpt-6.1-terra | 2 engagements × 27 cases × 2 runs | 0.86M in · 0.07M out | $1.19 |
| O-6 | **Demo, smoke tests, video recording** | gpt-6.1-terra | ~100 turns × 6k in / 500 out | 0.6M in · 0.05M out | $0.85 |
| O-7 | **Buffer:** agent loops, retries, debugging | — | +50% of O-3…O-6 | — | $1.39 |
| | **OpenAI total** | | | | **≈ $4.20** |

## 4. Itemized: Google Cloud

Assumes the cloud stack runs ~10 days (Day 4 deploy → demos and interviews) and is then destroyed.

| # | Resource | What it's for | Config | Calculation | Cost |
|---|---|---|---|---|---|
| G-1 | **Cloud SQL instance** | Managed Postgres + pgvector (documents, vectors, orders, agent checkpoints) | db-g1-small, no HA | 240 h × $0.035 | $8.40 |
| G-2 | **Cloud SQL storage** | Database disk | 10 GiB SSD | 10 × 240 h × $0.000233 | $0.56 |
| G-3 | **Cloud SQL backups** | Automated backups | 1 GiB, 7-day retention | ≈ | $0.10 |
| G-4 | **Cloud Run: api** | FastAPI + agent service | 1 vCPU, 512 MiB, min instances 0 | ~2,000 requests × 5 s = 10k vCPU-s, inside free tier | $0.00 |
| G-5 | **Cloud Run: mock-erp** | Simulated enterprise API | 1 vCPU, 256 MiB, min 0 | Inside free tier | $0.00 |
| G-6 | **Cloud Run job: ingest** | Runs ingestion in the cloud | 1 vCPU, 1 GiB | A few minutes total, inside free tier | $0.00 |
| G-7 | **Artifact Registry** | Stores Docker images | ~1.5 GiB of image versions | 1 GiB over free tier × $0.10 | $0.10 |
| G-8 | **Secret Manager** | OpenAI key, DB password, ERP token | 3 secrets, ~5 versions | Inside free tier (6 versions, 10k accesses) | $0.00 |
| G-9 | **Cloud Storage** | Terraform state (and optional docs bucket) | < 100 MB | ≈ | $0.02 |
| G-10 | **Logging & monitoring** | Cloud Run logs, metrics | Demo volume | Inside free allotment | $0.00 |
| G-11 | **Network egress** | Responses to users, calls to OpenAI | < 1 GiB | ≈ | $0.02 |
| | **GCP total (10 days)** | | | | **≈ $9.20** |

If Cloud SQL runs a **full month**: G-1 becomes 730 h × $0.035 = $25.55 and G-2 becomes $1.70, so GCP ≈ $27.50.
Using **db-f1-micro** instead cuts G-1 to $2.52 (10 days) or $7.67 (month), but 0.6 GiB RAM is tight for pgvector + checkpoints. Try it only if the budget matters more than headroom.

## 5. Free services used ($0)

| Service | What it's for | Why it's free |
|---|---|---|
| GitHub repo + Actions | Code hosting, CI/CD | Free for public repositories |
| Docker, kind, Helm, Terraform CLI | Local containers, Kubernetes, IaC | Open source |
| Postgres + pgvector (local) | Local development database | Open source, runs in Docker |
| Jaeger / OpenTelemetry Collector | Local tracing | Open source |
| Streamlit | Demo UI | Open source; runs locally or in Cloud Run free tier |
| Cloud Run URL (`*.run.app`) | Public HTTPS endpoint | Included; no custom domain needed |

Optional extras not included above: a custom domain (~$12/year), LangSmith paid tiers, a screen-recording tool upgrade.

## 6. Cost controls

| Control | Where | Setting |
|---|---|---|
| OpenAI monthly usage limit | OpenAI dashboard → project limits | $20 |
| Separate OpenAI project key | OpenAI dashboard | One key for this repo only |
| Cheap model by default | `.env` → `LLM_MODEL=gpt-6-luna` | Switch to `gpt-6.1-terra` only for final evals and the demo |
| GCP budget + alerts | Billing → Budgets | $25, alerts at 50% / 90% / 100% |
| Cloud Run scale to zero | Terraform `min_instance_count = 0` | No idle compute cost |
| Cloud SQL teardown | `terraform destroy` after demos | Removes the largest cost item |
| Agent limits | `engagement.yaml` | `max_steps: 8`, max output tokens |
| Eval scope | CI path filters | Evals run only when agent, retrieval, prompts or config change |

## 7. Actuals (filled on Day 5, 2026-11-11, from the eval reports)

| Item | Expected | Actual | Variance | Note |
|---|---|---|---|---|
| O-1...O-7 OpenAI | $4.20 | under $0.01 | about -$4.19 | Chat (evals only): 0739 $0.0000 (all HTTP 400), 0748 $0.0051, 0811 $0.0000 (first call hit the quota), 0932 $0.0002, 1047 $0.0005, 1049 $0.0000 (first call hit the quota), 1540 $0.0028 (7 cases), 1550 $0.0001 (q-025 re-run), total $0.0087 from report headers. Embeddings (re-ingests for real runs, not metered by the runner): at most 70 chunks x 800 tokens x $0.02/1M = $0.0011 each, seven re-ingests |
| G-1...G-3 Cloud SQL | $9.06 | $0 | -$9.06 | Not deployed; Terraform validated only (CLAUDE.md rule 5) |
| G-4...G-11 Other GCP | $0.14 | $0 | -$0.14 | Not deployed |
| **Total** | **$13.40** | **under $0.01** | | Spend was limited by the 50-requests/day quota, not by budget |

Why so far under: development and CI use fake models (FAKE_LLM=1), the expensive target model (gpt-6.1-terra) was never
used, and the cloud stack was not applied. A full 27-case run on gpt-6-luna costs about $0.006-0.008 at the measured rate
(about 2,000 input tokens per case); the planned O-4 assumed 8,000.

## 8. Customer-facing cost model (reusable)

For a real engagement, estimate the monthly run cost as:

```
LLM        ≈ users × questions/user/day × 22 workdays × (input tokens × input price + output tokens × output price)
Embeddings ≈ corpus tokens × embedding price (one time) + monthly changed tokens × embedding price
Infra      ≈ database instance + storage + container runtime + registry + egress
```

Worked example: 25 users × 10 questions/day × 22 days = 5,500 questions/month, each ≈ 8k input and 600 output tokens on gpt-6.1-terra:
5,500 × (8,000 × $1/1M + 600 × $5/1M) = 5,500 × $0.011 = **≈ $60/month LLM**, plus about $27/month infrastructure (always-on db-g1-small) ≈ **$90/month**. Show the customer a low / expected / high range and the levers: model tier, prompt caching, retrieval depth, and database size.
