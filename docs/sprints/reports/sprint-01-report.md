# Sprint 01 report: Day 3 close-out to Day 5

Brief: [docs/sprints/sprint-01-day3-to-day5.md](../sprint-01-day3-to-day5.md). Executor: Claude Code, working autonomously.
This report is updated after every phase. Each claim points to its evidence: a commit, a test, a file, or a command with its real output.

## 0. Orientation (written before any code changed)

**The project in five lines.** The FDE Engagement Kit is a reusable, config-driven kit for enterprise GenAI agents:
RAG over policy documents, a read-only SQL tool, tools generated from an OpenAPI spec, and human approval before any write.
A worked engagement (`engagements/demo-logistics`, fictional Northwind Logistics) runs on it.
The kit promises that a new customer is a new `engagements/<name>/` folder with zero changes in `core/` (NFR-02).
It is a portfolio and learning project, so documentation and teaching notes are deliverables, not extras.

**State at sprint start (verified).** `master` = `15d1c51`, last code commit `cadb61d` (Day 3 part 1, guardrails).
Uncommitted Day 3 part 2 work is in the tree as described in the brief (11 modified files, `core/evals/`, two test files,
six real eval report files). Baseline, run before any change:

```text
> uv run pytest -q      ->  136 passed in 35.63s   (exit 0)
> uv run ruff check .   ->  All checks passed!
> uv run mypy core      ->  Success: no issues found in 40 source files
```

All Phase 0.1 items are already present: `_turn()` uses `last.text`, `answer_question()` uses `reply.text`,
`ask_agent.py --history` prints `m.text`, `scoring.normalize()` maps curly quotes, q-018 has the alternatives and a `notes`,
`load_previous()` accepts legacy reports by file name, and each has a test in `tests/day03/test_model_params.py`.
The latest real report is `2026-11-11-0811-gpt-6-luna-cadb61d` (INCOMPLETE, 18/18 finished cases pass, 9 not run).

**What in the brief I think is wrong or risky, and how I will handle it.**

1. *Resume source.* The brief says `--resume` the 0748 report; the sponsor's later instruction says 0811. I use 0811,
   which already holds the same 18 results plus the q-018 re-run request.
2. *Quota arithmetic.* The 9 remaining cases need roughly 25-30 model requests. The account allows 50 per day, and the
   0811 run hit the limit at 08:11 today. The real eval will most likely end INCOMPLETE again. I will try it once near the
   end of the sprint (one run, no retries) and otherwise hand the exact resume command over under NEEDS HUMAN.
   A real eval of engagement #2 (about 80 requests) cannot fit today either: NEEDS HUMAN.
3. *The agent's system prompt is logistics-specific and lives in `core/agent/graph.py`.* Making it generic (Phase 3a)
   changes what the model sees. A new `PROMPT_VERSION` would make `--resume` refuse every stored result and force a fresh
   27-case run (about 2 days of quota). Proposed handling: the engagement owns its prompt file and version label, and the
   logistics file is byte-identical to today's prompt, so `agent-v1` stays truthful. The runner records a hash of the
   prompt text so the claim can be checked.
4. *More kit gaps than the brief lists.* Besides ETL, seed, ops migration, grants and the fake model, `core/` also hard-codes
   logistics content in: `core/evals/scoring.py` (`WRITE_TOOLS = {"createTicket"}`), `core/guardrails/input.py`
   (refusal text mentions shipments and SLA credits), `core/agent/doc_tool.py` (tool description lists SLA and claims),
   and the system prompt (item 3). Each gets a DC row in Phase 3a.
5. *Memory.* `\Memory\Available MBytes` = 3,201 MB at the start, just above the 3 GB floor in the author's rules.
   Docker image builds and a kind cluster are heavy. I check memory before each heavy step and stop that step (NEEDS HUMAN)
   if it is under 3 GB.
6. *trivy is not installed locally* (`Get-Command trivy` finds nothing). Per the brief, the image scan runs in CI only.
7. *Things only the human can do* (cloud deploy, billing check, demo video, cold rebuild, enabling the deploy workflow,
   confirming the skills matrix) go to NEEDS HUMAN. SC-04 (deployed) cannot be met by the executor under rule 5.
8. *Latency.* NFR-04 targets p95 <= 8 s per `/chat` turn on the cloud; the real runs show about 15-16 s p95 per eval case
   on a local machine with `gpt-6-luna`. I report it as a risk, not something to fix this sprint.
9. *Shared read-only role.* Two engagements in one local database will share the `agent_ro` role. If grants follow the
   configured schema, the role can read both schemas. Acceptable for a demo (each real customer has its own database),
   but I will record it as a known limitation.
10. *Missing Day 2 status and journal.* Only `docs/status/day-01.md` and `docs/journal/day-01.md` exist. The brief asks for
    Days 3-5; I will write those and list the Day 2 gap under Risks rather than back-fill it.

## 1. Summary

**After Phase 0.** Day 3 part 2 (evals) is verified and committed with teaching note 15, docs/16 (deferred ideas A and B)
and DC-016. A runner bug found at the start of the sprint is fixed with a test: resumed reports no longer claim the cost
and latency of the results they reused. The real eval of demo-logistics is still INCOMPLETE (18/18 finished cases pass,
9 not run because of the 50-requests-per-day quota); one resume attempt is planned near the end of the sprint.

## 2. Phase table

| Phase | Status | Commits | Tests | Evidence |
|---|---|---|---|---|
| 0 Day 3 close-out | Done (real eval INCOMPLETE, see NEEDS HUMAN) | `27222c7` | 137 passed | `docs/teaching/15-measuring-quality.md`, `docs/16-deferred-ideas.md`, DC-016 |
| 1 Observability + endpoints | Done | `46fbc0b` | 146 passed | `docs/teaching/16-observability.md`, `tests/day03/test_observability.py`, DC-017 |
| 2 Day 4 platform | Done locally + in CI; cloud deploy is NEEDS HUMAN | PR #1: `af3f620`, `57a3f59`, `f19e899` (CI tested `37a85e0` = GitHub's merge of the PR) | 147 passed (laptop and CI) | CI run 43035141379 (green), notes 17-20, DC-018 |
| 3a Kit generic | Done | `9097578` (tag `kit-generic`) | 164 passed; master CI 43037679612 green | DC-019..DC-029, `tests/day05/test_kit_generic.py` |
| 3b Engagement #2 | Done (real eval: NEEDS HUMAN) | see 3b checklist | 171 passed | note 21, DC-030, `tests/day05/test_coastline_hvac.py` |
| 3c Docs and closure | Not started | | | |

## 3. Definition of Done checklists

### Phase 0

- [x] Working tree verified; every item of brief section 1 present (see Orientation). No item had to be re-implemented.
- [x] Tests green, lint clean (output below, from the commit gate).
- [ ] Real eval complete. **Not yet**: latest real report `2026-11-11-0811-gpt-6-luna-cadb61d` is INCOMPLETE (9 not run).
      Resume command under NEEDS HUMAN item 1; one attempt planned at the end of this sprint.
- [x] Every failing real case has a written root cause: see section 4 (q-018 is the only finished case that ever failed).
- [x] Note 15 (`docs/teaching/15-measuring-quality.md`), docs/16, DC-016, `docs/status/day-03.md`, `docs/journal/day-03.md`,
      series table, risk R-12.
- [x] Extra item (sponsor): runner separates "this run" from "carried over"; test
      `tests/day03/test_model_params.py::test_resumed_results_do_not_count_as_this_runs_cost_or_latency`.
      The 0811 report files are unchanged (historical record); explained in note 15 practicum 4 and Findings F-01.

### Phase 1

- [x] Structured JSON request log (trace id, route, status, duration, model calls, tokens, tool names; no prompt text):
      `core/observability/logging.py`, middleware `observe` in `core/api/main.py`; test
      `test_a_tool_calling_chat_is_one_trace_that_matches_the_audit_log` asserts the line has no question text.
- [x] `/metrics` (prometheus-client) with requests/latency by route, model calls and tokens, tool calls by tool,
      approvals by outcome, guardrail blocks. Scraped with `Invoke-WebRequest` (note 16 practicum 2), non-zero:
      `fde_http_requests_total{method="POST",route="/chat",status="200"} 3.0`, `fde_tool_calls_total{outcome="ok",tool="query_ops_db"} 2.0`,
      `fde_approvals_total{outcome="requested"} 1.0`, `fde_guardrail_blocks_total{kind="input_injection"} 1.0`.
- [x] OpenTelemetry spans request -> agent.run -> agent.step -> llm.call / tool, console exporter by default, OTLP by env.
      Trace id = `agent.audit_log.trace_id` = `X-Trace-Id`: one real trace of a tool-calling `/chat` (fake model, real graph,
      tools and DB) pasted in note 16 practicum 1, trace `d254bd3fdfeb986567093f5bf36409ce`, 4 audit rows with the same id.
- [x] `POST /ingest` and `POST /eval` (bearer `ADMIN_TOKEN`, fail closed; `/eval` fake only, 409 otherwise); documented in
      `docs/10-security-and-compliance.md` sections 4-5. Tests: `test_admin_endpoints_fail_closed_without_a_token`,
      `test_admin_endpoints_reject_a_wrong_token`, `test_eval_endpoint_refuses_real_model_runs`, `test_eval_endpoint_runs_fake_cases`,
      `test_ingest_endpoint_returns_the_load_counts`.
- [x] Favicon: inline SVG in `ui/index.html`.
- [x] Note 16, DC-017 (includes the formal D-11 Streamlit -> HTML console deviation), tests + lint green (gate output in the commit).

### Phase 2

- [x] Docker (D-12, NFR-11, NFR-12): `deploy/docker/api.Dockerfile`, `deploy/docker/mock-erp.Dockerfile`: multi-stage,
      non-root (`fde-api:local runs as 10001:10001`), base pinned by digest, OS updates. `/health` -> `"version":{"app":"0.3.0","build_sha":"37a85e0"}`
      (test `test_health_reports_which_build_is_running`). trivy: first run 7 CRITICAL (job 130570428801), after the fix 0 (job 130572443115).
      trivy is not installed locally, so the scan runs in CI only (as the brief allows).
- [x] `docker compose up` from a clean clone -> working stack: CI job `containers`, step "Compose smoke test": seed Exited,
      migrate Exited, postgres/mock-erp/api Healthy, `/health` status ok with the CI commit, `/chat` tool-calling answer.
      **Not run on the laptop** (free memory 2,253-2,874 MB < 3 GB floor); the CI runner is the clean machine. Timing: the whole
      containers job, including image builds from scratch, took about 3 minutes (14:06:41 -> 14:09:34), well inside NFR-01's 15 minutes.
- [x] Helm on kind: CI step "Helm install on kind": `STATUS: deployed`, `fde-api`, `fde-mock-erp`, `fde-postgres-0` all `1/1 Running`,
      `kind health ok {'app': '0.3.0', 'build_sha': '37a85e0'}`. Locally: `helm lint` 0 failed, `helm template` 8 objects (note 19).
- [x] CI green on GitHub: run 43035141379 <https://github.com/emkwambe/fde-engagement-kit/actions/runs/43035141379>
      (test, secrets, containers all success). `eval-real.yml` (manual) and `deploy.yml` (manual, disabled) present.
- [x] Terraform (D-15): `terraform fmt -check` exit 0, `terraform validate` "Success! The configuration is valid." Not applied.
      Deploy and teardown sequence with cost per hour ($0.0373/h) in `docs/11-deployment-runbook.md` sections 4 and 7 and NEEDS HUMAN item 3.
- [x] Notes 17-20, Day 4 status and journal, DC-018.

### Phase 3a

- [x] Gaps fixed generically, logistics unchanged (tests, fake eval 15/27, prompt sha `537c08f4c028`); one DC row per gap
      (DC-019..DC-029); table in section 5.
- [x] Tag `kit-generic` on `9097578` after master CI run 43037679612 was green (tag never moved).

### Phase 3b

- [x] Domain as briefed: HVAC field service, plans Basic/Plus/Premium with response-time SLAs and credits, work orders,
      technicians, parts warranty, mock CMMS with `getWorkOrder`, `listWorkOrders`, `createDispatch` (write, approval),
      policy docs incl. response-time SLA and credits, warranty, emergency vs routine, after-hours fees, escalation,
      data privacy, and one planted injection line (`vendor-notes-q3.md#appendix`). Generated OpenAPI contract + drift test
      (`test_cmms_contract_matches_the_committed_spec`).
- [x] Playbook order: `discovery.md` first, then docs, data, config, golden set, evals (timings in note 21).
- [x] Golden set 27 cases, same category minimums (`test_golden_set_meets_the_test_strategy_minimums` for coastline-hvac).
- [x] End to end: ingest (30/8/48/120 rows, 11 docs, 35 chunks), chat, approval (paused `createDispatch` with T-07 / $75,
      DSP-0001 only after approval), fake eval 19/27 via `/eval` (red team 5/5). Test `test_a_dispatch_pauses_for_approval_and_runs_only_after_it`.
- [x] Zero `core/` changes since `kit-generic` (section 5).
- [ ] Real eval of engagement #2: **not run** (quota; NEEDS HUMAN item 4).
- [x] Note 21 with real timings and the zero-diff proof.

## 4. Evals

### demo-logistics

| Run (report) | Model | Prompt | Cases ran / passed | Overall | Safety | Gate | Cost (this run) | p95 | Note |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-11-0739-gpt-6-luna-cadb61d | openai/gpt-6-luna | agent-v1 | 27 / 2 | 7% | 40% | FAIL | $0.0000 | 0.25 s | every call HTTP 400 `temperature` |
| 2026-11-11-0748-gpt-6-luna-cadb61d | openai/gpt-6-luna | agent-v1 | 27 / 18 | 67% | 40% | FAIL | $0.0051 | 15.18 s | 429 daily quota after 18 cases; crashes counted as failures (old runner) |
| 2026-11-11-0811-gpt-6-luna-cadb61d | openai/gpt-6-luna | agent-v1 | 18 / 18 (9 not run) | 100% of finished | 100% of finished | INCOMPLETE | **$0 actual** (report says $0.0045: F-01) | n/a (report says 16.55 s: F-01) | first call hit the quota; 18 results reused |
| fake harness (not committed, `*-fake-*`) | fake | agent-v1 | 27 / 15 | 56% | 100% | not enforced | n/a | 0.1 s | checks the harness only |

### Failing real cases and root causes

| Case | Report | Root cause | Category of cause | Fix or limitation |
|---|---|---|---|---|
| all 25 non-blocked cases | 0739 | `gpt-6-luna` rejects the `temperature` parameter (HTTP 400) | Model/provider limit + our config default | `llm.temperature` opt-in (DC-016); test `test_temperature_is_not_sent_unless_configured` |
| q-018 | 0748 | Answer was correct ("wasn't found") but (a) shown as `str(list)` of content blocks and (b) the check required the exact words "not found" | Agent bug (a) + golden case too narrow (b) | (a) `AIMessage.text` in `_turn()`/`answer_question()`; (b) alternatives with evidence in `notes`. Re-run pending (quota) |
| q-019..q-027 (8 cases) | 0748 | HTTP 429 daily quota; scored as CRASH by the runner of that time | Provider quota (not an agent failure) | Quota-aware runner (NOT RUN + resume). Not yet re-run |

## 5. Kit-genericity proof

### Gaps fixed in Phase 3a (before the `kit-generic` tag)

| Gap | Was | Now | DC |
|---|---|---|---|
| G1 tabular ETL | `LOGISTICS_TABLES`, `clean_tier` in `core/ingest/etl.py` | table specs + column types in `sources.tables[].tables` | DC-019 |
| G1b ETL foreign keys | one FK per table, no optional links | every reference checked, empty allowed | DC-020 |
| G2 seed generator | `generate_logistics` in `core/ingest/seed.py` | engagement `extensions/seed.py`, named by `seed_script` | DC-021 |
| G3 ops tables | logistics migration 003 only | engagement `schema_sql` in its own schema (003 kept, append-only) | DC-022 |
| G4 read-only grants | `ops` only | `ops` + configured `tools.sql.schema` | DC-023 |
| G5 fake model | logistics script in `core/agent/fake.py` | `ScriptedFake` + `GenericFakeChat`; engagement `fake_script` | DC-024 |
| G6 system prompt | logistics text in `core/agent/graph.py` | `llm.system_prompt` + `prompt_version`; logistics byte-identical (sha `537c08f4c028`) | DC-025 |
| G7 scoring | `WRITE_TOOLS = {"createTicket"}` | any paused requires-approval call | DC-026 |
| G8 refusal text | mentioned shipments and SLA credits | `guardrails.blocked_answer` | DC-027 |
| G9 doc tool description | listed SLA, claims | `retrieval.tool_description` | DC-028 |
| G10 console examples | logistics questions in `ui/index.html` | `engagement.examples` via `GET /engagement` | DC-029 |

Logistics after 3a: all tests pass (same assertions; imports moved to `tests/helpers.py`), fake eval 15/27 before and after,
prompt sha unchanged. New tests: `tests/day05/test_kit_generic.py` (19 with the ETL tests).

### Zero-diff proof for engagement #2

Before the 3b commit (working tree vs tag), captured in note 21 practicum 1:

```text
> git diff --stat kit-generic -- core/
(lines: 0)
```

After the 3b commit: see the Phase 3b checklist (the same command over `kit-generic..HEAD`).

## 6. Decisions and deviations

- DC-016 (Phase 0): see the decision log.
- Deviation: resumed from the 0811 report instead of 0748 (sponsor instruction; 0811 contains the same 18 results).
- Deviation: the real-eval resume was not attempted in Phase 0 because the quota had run out 20 minutes earlier;
  it is attempted once at the end of the sprint instead (no retry loop).

## 7. Findings

- **F-01 Resumed report claimed spend it did not have.** The 0811 report says "cost: $0.0045 ... p95 16.55 s", but that run
  made no successful model call; the numbers were the sum of the 18 reused results. Origin: `summarize()` added tokens and
  seconds of every finished result. Caught by: the sponsor, reading the report. Fix: headline = this run only;
  "carried over" block for reused results. The files stay as history.
- **F-02 Fake mode showed "$0.0000" instead of "n/a".** In fake mode the model name is still `gpt-6-luna` (from `LLM_MODEL`),
  so the price table matched. Origin: `summarize()`; caught by the executor while capturing note 15 output. Fixed.
- **F-04 A real-looking provider org id was in an uncommitted test.** `test_account_ids_are_masked` used the literal id from
  the provider's 429 message as its example input. Origin: the Day 3 part 2 test was written from the real error text.
  Caught by: the executor's pre-commit grep for `org-` ids. Fix: replaced with a made-up id of the same shape (the test
  checks the same pattern). It never reached git (`gitleaks git .` -> "no leaks found").
- **F-05 A stale API process held port 8000.** An API started at 06:56 (before this sprint, PID 15616) still answered on
  port 8000 with pre-sprint code: its `/health` had no `embeddings_match` field. My new server failed to bind
  (`[winerror 10048] only one usage of each socket address`). Caught by: reading the `/health` output. Handling: captured
  note 16 on port 8001; did not stop the human's process (NEEDS HUMAN item 2). Phase 2 adds the build version to `/health`.
- **F-06 FastAPI 0.162 emits its own spans** (`POST /chat` root, `fastapi.endpoint`, ...) once a tracer provider exists.
  Not planned, harmless: our spans nest inside. Documented in note 16.
- **F-07 trivy blocked the first image build.** 7 CRITICAL CVEs (libssl3, gnutls, perl) in the digest-pinned Debian 12.13 base,
  all with fixes published. Origin: pinning by digest freezes OS packages. Caught by: the CI trivy gate (as designed).
  Fix: `apt-get upgrade` in the runtime stage; 0 CRITICAL on Debian 12.15.
- **F-08 Laptop memory under the 3 GB floor.** 2,253 MB free after Phase 1 (Chrome and the Docker WSL VM). Image builds, Compose and
  kind moved to CI (R-10's mitigation). Not a code problem, but the brief assumed local runs.
- **F-09 Shell heredocs with quotes failed twice** in the executor's own tooling (bash "unexpected EOF"). No repo impact;
  edits switched to script files.
- **F-10 Wrong commit named in notes 17-19 (corrected).** I first wrote that CI built "commit 37a85e0". For a pull_request
  event GitHub tests a merge commit of the PR into master, so 37a85e0 is that merge commit; the branch head was 57a3f59.
  Origin: assuming GITHUB_SHA = branch head. Caught by: the executor, comparing `git log` after the merge with the notes.
  Fixed in the notes and this report before the tag.
- **F-03 Logistics content in `core/`** beyond the brief's list (scoring `WRITE_TOOLS`, refusal text, doc tool description,
  system prompt). Handled in Phase 3a.

## 8. Cost and quota

| Run | OpenAI cost | Model requests | Source |
|---|---|---|---|
| 0739 (before sprint) | $0.0000 | 25 calls, all rejected with HTTP 400 | report |
| 0748 (before sprint) | $0.0051 | not recorded by the runner; the 50/day quota was reached | report |
| 0811 (before sprint) | $0.0000 | 1 (HTTP 429) | report case list; header figure is F-01 |
| Sprint 01 so far | $0.0000 | 0 | no real run yet |

Other spend: $0 (no cloud resources created).

## 9. NEEDS HUMAN

1. **Finish the real eval of demo-logistics** (quota). Why: the account allows 50 chat requests per day and the 9 remaining
   cases need roughly 25-30. Commands (PowerShell, repo root, mock ERP running in another window via `.	asks.ps1 erp`):
   ```powershell
   $env:FAKE_LLM = '0'
   uv run python -m core.ingest.run --docs-only
   uv run python -m core.evals.run --resume engagements/demo-logistics/evals/reports/2026-11-11-0811-gpt-6-luna-cadb61d.json
   Remove-Item Env:FAKE_LLM
   uv run python -m core.ingest.run --docs-only    # restores fake vectors (FAKE_LLM=1 from .env)
   ```
   Expected: a new report; if the quota stops it again, resume from the NEWEST report it printed. Send back the report file name.
   (This item is updated at the end of the sprint with the newest report to resume from.)

2. **Stop the stale API on port 8000.** Why: it runs code from before Sprint 01 (F-05), so anything you try on port 8000
   shows old behaviour. It is your process, so I did not stop it.
   ```powershell
   Get-NetTCPConnection -LocalPort 8000 -State Listen | ForEach-Object { Get-Process -Id $_.OwningProcess } | Format-Table Id, ProcessName, StartTime
   Stop-Process -Id 15616      # only if the line above shows that PID; then restart with .	asks.ps1 api
   ```
   Expected: `/health` on port 8000 then shows `embeddings_match` (and, after Phase 2, `version`).

3. **Deploy to GCP (optional, billable) and tear down.** Why: CLAUDE.md rule 5, the executor never creates cloud resources.
   Cost while it exists: about $0.037 per hour ($0.90 per day), almost all Cloud SQL. Commands: `docs/11-deployment-runbook.md`
   section 4.1 (one-time: state bucket, `terraform init`), 4.2 (registry, images, `plan`, `apply`, ingest job, smoke test),
   4.3 (enable `deploy.yml` with `gh variable set ...`), section 7 (`terraform destroy`, then `gcloud sql instances list` must
   show 0 items, and a billing check). Expected: `api_url` output and `/health` status ok with your commit. Send back:
   the api_url, the `/health` JSON, and confirmation that destroy left no Cloud SQL instance.

4. **Real eval of engagement #2.** Why: needs about 75-90 model requests; the account allows 50 per day and they are
   used by demo-logistics. Run it after demo-logistics is complete, on a new day (two windows: `.\tasks.ps1 cmms`, and
   this one). Commands:
   ```powershell
   $env:FAKE_LLM = '0'
   uv run python -m core.ingest.run --engagement coastline-hvac --docs-only
   uv run python -m core.evals.run --engagement coastline-hvac
   # if it stops with INCOMPLETE, the next day:
   uv run python -m core.evals.run --engagement coastline-hvac --resume <the .json it printed>
   Remove-Item Env:FAKE_LLM
   uv run python -m core.ingest.run --engagement coastline-hvac --docs-only   # restore fake vectors
   ```
   Expected: a report in `engagements/coastline-hvac/evals/reports/`; cost about $0.005 on gpt-6-luna. Send back the report
   file names; failing cases get a root cause like section 4.

## 10. Risks and open questions

- R-12 provider quota (new). A higher OpenAI tier would let one eval finish in one day; sponsor decision.
