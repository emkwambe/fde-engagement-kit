# Risk Register

Scoring: Probability (P) and Impact (I) on 1–5. **Score = P × I**. Review at the end of every session.

| ID | Risk | Category | P | I | Score | Response | Mitigation / contingency | Trigger | Status |
|---|---|---|---|---|---|---|---|---|---|
| R-01 | Building a framework instead of a working system (over-generalizing) | Scope | 4 | 5 | 20 | Avoid | ADR-004 rule: generalize only what engagement #1 or #2 needs; M1 must ship on Day 1 | No cited answer by end of Day 1 | Open |
| R-02 | Copying code without understanding it — learning goal missed | Learning | 4 | 5 | 20 | Avoid | "No unexplained code" rule; daily journal; cold rebuild on Day 5 | Journal entry can't explain a component | Open |
| R-03 | GCP setup (IAM, Cloud SQL networking, WIF) takes much longer than planned | Technical | 4 | 4 | 16 | Mitigate | Follow runbook; deploy manually with `gcloud run deploy` first, then codify in Terraform | Day 4 deploy not working by hour 5 | Open |
| R-04 | LangGraph API changes / version confusion with tutorials | Technical | 3 | 3 | 9 | Mitigate | Pin versions; use official docs for the pinned version only | Import errors / deprecated APIs | Open |
| R-05 | API or cloud cost exceeds budget | Cost | 2 | 3 | 6 | Mitigate | Usage limits, budget alerts, mini model for dev, destroy after demo | 50% budget alert | Open |
| R-06 | Eval scores stay low; time sink tuning prompts | Quality | 3 | 4 | 12 | Mitigate | Diagnose retrieval vs. generation separately; accept and document limitations after 1 h time box | Score < 70% at end of Day 3 | Open |
| R-07 | Schedule slip (life, fatigue) | Schedule | 3 | 3 | 9 | Accept | Cut lines in [WBS §3](04-wbs-and-schedule.md#3-minimum-viable-cut-lines); buffer day allowed | Two milestones late | Open |
| R-08 | Secret accidentally committed | Security | 2 | 5 | 10 | Avoid | `.gitignore`, pre-commit `gitleaks`, CI scan; rotate key immediately if leaked | gitleaks alert | Open |
| R-09 | Demo looks like a tutorial to reviewers | Reputation | 3 | 4 | 12 | Mitigate | Lead README with the customer problem, decisions, evals, and reuse proof — not the tech list | Feedback from 1–2 peers | Open |
| R-10 | Local machine resources too small for kind + Postgres + Compose | Technical | 2 | 3 | 6 | Mitigate | Run kind in GitHub Actions or a Codespace | OOM / very slow | Open |
| R-11 | Synthetic data too clean — unrealistic | Quality | 3 | 2 | 6 | Mitigate | Inject messy data on purpose: duplicates, nulls, inconsistent dates, scanned-looking PDF | — | Open |
| R-12 | Provider quota (50 chat requests/day) stops real evals part-way; a full 27-case run needs about 75-90 requests | Technical | 5 | 3 | 15 | Mitigate | Quota-aware runner: NOT RUN + INCOMPLETE + `--resume` across days (DC-016); never retry on 429; ask for a higher tier before a release gate | Report status INCOMPLETE | Open |

| R-13 | Public API on Cloud Run: anyone approves writes or burns model quota (review finding F-R1) | Security | 4 | 5 | 20 | Avoid | API not public (IAM invokers + proxy); APPROVER_TOKEN and CHAT_TOKEN; audit `token_verified` (DC-031, T-10) | `approvals_auth: false` in a deployed `/health` | Mitigated |

## Risk review log
| Date | Session | Changes |
|---|---|---|
| 2026-11-09 | Day 0 | Baseline created |
| 2026-11-11 | Day 3 | R-12 added (provider daily quota). R-06 trigger not hit: finished real cases 18/18 pass |
| 2026-11-11 | Sprint 01b | R-13 added and mitigated (review finding F-R1) |
