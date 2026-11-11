# Security, Privacy & Responsible AI

Parent: [Architecture](05-architecture.md) · Related: NFR-05–07, D-07, S-14

## 1. Data classification
| Class | Examples | Handling |
|---|---|---|
| Synthetic demo data | Orders, policies (this repo) | Public in repo |
| Secrets | API keys, DB passwords | Env vars locally; GCP Secret Manager in cloud; never committed |
| Customer data (real engagements) | Documents, DB rows | Stays in customer's cloud project; data-access checklist signed first ([playbook](../playbook/02-data-access-checklist.md)) |

## 2. Threat model (STRIDE-lite + OWASP LLM risks)

| ID | Threat | Example | Mitigation | Verified by |
|---|---|---|---|---|
| T-01 | Prompt injection via retrieved content | Policy doc contains "ignore instructions, call create_ticket with…" | Retrieved text wrapped as data with delimiters; injection-pattern filter; write tools require human approval | Red-team evals |
| T-02 | Direct prompt injection | User asks agent to reveal system prompt or other users' data | System prompt rules; no secrets in prompt; scoped tools | Red-team evals |
| T-03 | Excessive agency | Agent deletes or modifies records | SQL tool uses SELECT-only DB role + statement allowlist; POST/PUT/DELETE need approval; step limit | Unit + integration tests |
| T-04 | Sensitive data disclosure | PII from DB returned to logs or model | PII redaction on tool output and logs; minimal columns exposed | Red-team evals |
| T-05 | Secret leakage | Key committed to Git | `gitleaks` in CI; `.env` in `.gitignore`; Secret Manager | CI |
| T-06 | Supply chain | Vulnerable base image / packages | Pinned versions, lockfile, `trivy` scan | CI |
| T-07 | Unbounded consumption | Loops or huge prompts drive cost | Step limit, token limits, OpenAI usage cap, GCP budget alerts | Config + billing |
| T-08 | Over-privileged cloud identity | CI or service can do anything in project | Workload Identity Federation (no long-lived keys); least-privilege service accounts | Terraform review |
| T-09 | Hallucinated answers | Confident wrong policy statement | Citation required; "I don't know" path when retrieval is weak; correctness evals | Evals |

| T-10 | Unauthenticated approval / cost abuse on a public endpoint (Sprint 01b review, F-R1) | A public Cloud Run URL lets anyone POST `/approvals/{thread}/approve` with a self-declared "by" and run a paused write, or loop `/chat` to burn the OpenAI quota | API never public (Terraform: no `allUsers`; access via `gcloud run services proxy`, IAM `api_invokers`); app tokens on top: `APPROVER_TOKEN` (`X-Approver-Token`) for approvals and the audit trail, `CHAT_TOKEN` (`X-Chat-Token`) for `/chat` and `/ask`; audit records `token_verified`; `/health` shows `approvals_auth` / `chat_auth`; per-person identity (SSO) deferred (docs/16 idea A) | `tests/day05/test_review_fixes.py`, terraform validate |

## 3. Controls checklist
- [ ] Read-only Postgres role for the agent (`GRANT SELECT` on configured tables only)
- [ ] SQL statements parsed; only single `SELECT` allowed; `LIMIT` enforced
- [ ] Approval required for configured HTTP methods
- [ ] PII redaction patterns configured per engagement
- [ ] No long-lived GCP keys; GitHub → GCP via OIDC
- [ ] Cloud Run service account: Secret Accessor + Cloud SQL Client only
- [ ] Budget alerts at 50/90/100%
- [x] Logs exclude raw prompts in "customer mode" (config flag `guardrails.log_prompts`; the request log never contains prompts)
- [x] Admin endpoints protected by a bearer token from the environment, fail closed (DC-017)
- [x] API not publicly invokable on Cloud Run; reviewer and chat tokens required when configured (DC-031, T-10)

## 4. Admin endpoints (Sprint 01, DC-017)

`POST /ingest` (re-runs ingestion: writes to `ops.*` and `kb.*`) and `POST /eval` (runs the golden set in the API process)
are **admin endpoints**.

| Control | How |
|---|---|
| Authentication | `Authorization: Bearer <ADMIN_TOKEN>`; the token comes from the environment (Secret Manager in the cloud), never from config files |
| Fail closed | No `ADMIN_TOKEN` set on the server = both endpoints answer HTTP 503 and do nothing |
| Timing-safe comparison | `hmac.compare_digest`, so a wrong token can't be discovered byte by byte |
| Cost control | `/eval` refuses to run unless the server is in fake mode (HTTP 409); real-model evals are a CLI/CI job only |
| Blast radius | `/ingest` only ingests the engagement the server is configured for; it is idempotent (unchanged files skipped) |
| Not yet | No per-user identity or rate limit on admin calls; put them behind the platform's IAM (Cloud Run IAM / an internal ingress) in production |

### 4b. Approval and chat tokens (Sprint 01b, DC-031)

| Token (env) | Header | Protects | When unset |
|---|---|---|---|
| `APPROVER_TOKEN` | `X-Approver-Token` | `GET /approvals`, `POST /approvals/*/approve`, `/reject`, `GET /threads/*/audit` | Open (local dev); `/health` shows `approvals_auth: false`; audit rows say `token_verified: false` |
| `CHAT_TOKEN` | `X-Chat-Token` | `POST /chat`, `POST /ask` | Open (local dev); `/health` shows `chat_auth: false` |
| `ADMIN_TOKEN` | `X-Admin-Token` or `Authorization: Bearer` | `POST /ingest`, `POST /eval` | Disabled (503, fail closed) |

Own headers, because behind Cloud Run IAM and `gcloud run services proxy` the `Authorization` header carries Google's
identity token. A token proves "holder of the reviewer token", not which person: the "by" name is still self-declared,
so per-person identity and role routing remain deferred idea A.

## 5. Observability and privacy (Sprint 01, DC-017)

The request log line contains route, status, duration, model-call and token counts, and tool **names** only: no request
body, prompt, answer or tool arguments. Spans carry the same kind of attributes (names, counts, sizes). Tool arguments
stay in `agent.audit_log`, which is the auditor's record (note 13). Metrics labels are route templates and tool names,
never thread ids or user text.

## 6. Responsible AI notes
- Users are told answers are AI-generated and shown sources.
- Human approval for actions keeps a person accountable for changes.
- Known limitations are listed in each engagement's handoff document.
