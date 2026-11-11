# Sprint 01b - Sponsor review and real-eval progress (2026-11-11)

This is the sponsor's review of Sprint 01b (the fixes for review findings F-R1 and F-R2) and a record of the work done
by hand after it: the laptop smoke test, clean-up of a stale process, and two more real-eval resume runs.
The executor's own report is [sprint-01-report.md](sprint-01-report.md), section 11.

## 1. Verdict

**Accepted.** Both review findings are fixed and covered by tests. The kit's promise still holds. One small new test
issue (F-R3) and one commit-message mistake (F-R4) were found; both are recorded below. The real eval is still
INCOMPLETE because of the provider quota: 20 of 27 cases have run and all 20 pass.

## 2. What was checked, and how

Every check ran on commit `e1e0a78` (Sprint 01b) in a separate clone, not on the executor's machine.

| Claim in the 01b report | How it was checked | Result |
|---|---|---|
| F-R1: the API is no longer public on Cloud Run | Searched `deploy/terraform/gcp/main.tf` for `api_public` and `allUsers` | No `api_public`; access through `api_invokers` (one IAM member per listed caller). `allUsers` remains only on the mock ERP (documented, DC-031) |
| F-R1: approvals and chat need tokens | Read `core/api/main.py`; ran `tests/day05/test_review_fixes.py` | `APPROVER_TOKEN` (`X-Approver-Token`) and `CHAT_TOKEN` (`X-Chat-Token`); `/health` shows `approvals_auth` and `chat_auth`; 401 without the token |
| F-R2: no corrupted `.\tasks.ps1` | Searched every `.md` and `.ps1` for a TAB followed by `asks.ps1` | 0 found |
| Kit promise (NFR-02) | `git diff kit-generic..e69d0b6 -- core/` | 0 lines. After e69d0b6 only `core/agent/service.py` and `core/api/main.py` changed (60 lines added, 17 removed), both for the generic F-R1 fix |
| Every commit green | `uv run pytest -q`, `ruff check .`, `mypy core` | **179 passed** with Postgres running (matches the report); ruff and mypy clean (47 files) |
| It runs on the author's laptop | `.\tasks.ps1 demo`, then `/health`, `/chat`, `/metrics`, `.\tasks.ps1 stack-down` | Passed. First container run on the laptop. `build_sha` = `e1e0a78`, `embeddings_match` = True, `/chat` answered the SHP-2207 status, metrics counted the requests |

## 3. Findings

| ID | Severity | Finding | Action | Status |
|---|---|---|---|---|
| F-R3 | LOW | Two tests call `POST /eval`, which builds the agent service and so opens Postgres, but they did not ask for the database fixture. With Postgres stopped they **failed** (`psycopg.OperationalError`) instead of **skipping**. Found because the first review run had the database down: 2 failed, 135 passed, 42 skipped | Both tests now take the `migrated_db` fixture and carry `@pytest.mark.db` (DC-034). Checked both ways: database up 179 passed; database down 135 passed, 44 skipped, 0 failed | Fixed |
| F-R4 | LOW | Commit `4a7c808` is titled "Real eval complete (gpt-6-luna)", but the report it adds (1047) is INCOMPLETE (20 of 27). The title came from a command block meant only for a complete run, and the block was run anyway | Not amended: the commit is pushed, and history rewrites are forbidden (CLAUDE.md rule 7). Recorded here and in DC-033. The next commit block for the eval now commits only when the exit code is 0 | Documented |

### Observations (no change needed now)

| ID | Observation | Decision |
|---|---|---|
| O-1 | The mock ERP stays callable on Cloud Run without IAM, protected by its own 40-character bearer token (DC-031, part 3) | Accepted for the portfolio: it holds only fake data and plays a third-party system. **Before any real customer**, make it IAM-private like the API (needs the tool generator to send a Google ID token; already in the backlog) |
| O-2 | An old mock ERP process (PID 13008, started 06:09) was still listening on port 8100 during the smoke test | Stopped with `Stop-Process -Id 13008`; `Get-NetTCPConnection -LocalPort 8100 -State Listen` then printed nothing |
| O-3 | The provider's 50-requests-per-day limit refills gradually, not all at once at midnight. A resume 75 minutes after the quota ran out got one case through; a second resume two minutes later got none | Resume once a day, about 24 hours after the last full use. A retry soon after a quota stop runs no cases but still re-embeds the documents (at most $0.0011) |

## 4. Real eval of demo-logistics: progress

| Report | Commit | Cases run in this report | Result | Cost (this run) |
|---|---|---|---|---|
| 0932 | e69d0b6 | 1 (q-018) | 19 of 27 done, all pass; INCOMPLETE | $0.0002 |
| 1047 | e1e0a78 | 1 (q-019, approval-gated write) | 20 of 27 done, all pass; INCOMPLETE | $0.0005 (2,388 tokens in / 449 out) |
| 1049 | 4a7c808 | 0 (first call got HTTP 429) | 20 of 27 done, all pass; INCOMPLETE | $0.0000 |

Safety score 1.0 throughout. Still to run: q-020 (api_write), q-021 to q-023 (multi), q-025 to q-027 (red_team),
about 20 requests in total.

Resume command (PowerShell, repo root, mock ERP running in another window with `.\tasks.ps1 erp`):

```powershell
.\tasks.ps1 up
$resume = 'engagements/demo-logistics/evals/reports/2026-11-11-1049-gpt-6-luna-4a7c808.json'
try {
  $env:FAKE_LLM = '0'
  uv run python -m core.ingest.run --docs-only
  uv run python -m core.evals.run --resume $resume
  $code = $LASTEXITCODE
}
finally {
  Remove-Item Env:FAKE_LLM -ErrorAction SilentlyContinue
  uv run python -m core.ingest.run --docs-only
}
Write-Host "Eval exit code: $code  (0 = complete and passed, 3 = quota stop)"
```

## 5. Spend

| Item | Amount |
|---|---|
| Chat, eval reports 0739 to 1049 | $0.0058 (from report headers) |
| Embedding re-ingests for real runs (not metered) | at most $0.0011 each, five so far |
| GCP | $0 (nothing applied) |

Well under the $1.00 sprint budget (CLAUDE.md rule 6).

## 6. Next steps (sponsor / author)

1. Resume the real eval of demo-logistics once a day until it is complete, then commit the final report.
2. Run the real eval of coastline-hvac (needs its own day of quota).
3. Optional: deploy to GCP with Terraform, smoke test through `gcloud run services proxy`, then destroy
   (`docs/11-deployment-runbook.md` section 4).
4. Record the demo video, do the cold rebuild, confirm the skills matrix, sign the closure report.
