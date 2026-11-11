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

All five phases were worked in order and every commit was green. Delivered: Day 3 close-out (evals, note 15, deferred
ideas, a runner fix for resumed reports), observability and the missing `/ingest`, `/eval`, `/metrics` endpoints
(note 16), the Day 4 platform (hardened images, Compose stack, Helm chart, CI with security and container gates, a
disabled keyless deploy workflow, validated Terraform; notes 17-20), a kit-generic refactor of eleven gaps (tag
`kit-generic`), and engagement #2 (HVAC dispatch) with an empty `core/` diff since the tag (note 21), plus README,
architecture, cost actuals and a closure report draft. Not finished, with the reason: the real-model eval of
demo-logistics is still INCOMPLETE (19/19 finished cases pass, 8 not run: the 50-requests/day quota); the real eval of
engagement #2 was not run (quota); the cloud deploy, demo video and cold rebuild are human steps. Overall status:
**done to the limit of what the executor may do; the quality gate and the cloud milestone wait on NEEDS HUMAN items 1, 3, 4.**
Tests: 136 at the start, 171 at the end. OpenAI spend this sprint: $0.0002 measured (+ at most $0.0011 for one real
embedding re-ingest). GCP spend: $0.

## 2. Phase table

| Phase | Status | Commits | Tests | Evidence |
|---|---|---|---|---|
| 0 Day 3 close-out | Done (real eval INCOMPLETE, see NEEDS HUMAN) | `27222c7` | 137 passed | `docs/teaching/15-measuring-quality.md`, `docs/16-deferred-ideas.md`, DC-016 |
| 1 Observability + endpoints | Done | `46fbc0b` | 146 passed | `docs/teaching/16-observability.md`, `tests/day03/test_observability.py`, DC-017 |
| 2 Day 4 platform | Done locally + in CI; cloud deploy is NEEDS HUMAN | PR #1: `af3f620`, `57a3f59`, `f19e899` (CI tested `37a85e0` = GitHub's merge of the PR) | 147 passed (laptop and CI) | CI run 43035141379 (green), notes 17-20, DC-018 |
| 3a Kit generic | Done | `9097578` (tag `kit-generic`) | 164 passed; master CI 43037679612 green | DC-019..DC-029, `tests/day05/test_kit_generic.py` |
| 3b Engagement #2 | Done (real eval: NEEDS HUMAN) | `e69d0b6` | 171 passed; master CI 43039120762 | note 21, DC-030, `tests/day05/test_coastline_hvac.py` |
| 3c Docs and closure | Done (human items listed) | final commit (this report) | 171 passed | README, `docs/15-closure-report.md`, `docs/12` section 7, `docs/03` After draft |

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
      CI run 43039120762 (master, `e69d0b6`) ran both fake evals on a clean runner: coastline-hvac 19/27, demo-logistics 15/27, 171 tests passed.
- [x] Zero `core/` changes since `kit-generic` (section 5). After the 3b commit `e69d0b6`:
      `git diff --stat kit-generic..HEAD -- core/` printed nothing (`(lines: 0)`); the whole diff since the tag:
      `31 files changed, 1660 insertions(+), 5 deletions(-)`, none in `core/`.
- [ ] Real eval of engagement #2: **not run** (quota; NEEDS HUMAN item 4).
- [x] Note 21 with real timings and the zero-diff proof.

### Phase 3c

- [x] README: what it is, quick start in PowerShell, Mermaid architecture, links to notes and the latest real report.
- [x] Architecture updated (`docs/05`: Compose diagram as built, Helm view, observability, kit/engagement boundary table).
- [x] Runbook re-checked: sections 2, 3, 4, 7 rewritten to match the built system (Phase 2); sections 2-3 are exactly what CI runs.
- [x] Cost actuals in `docs/12-cost-estimate.md` section 7 (from report headers; embeddings bounded, not metered).
- [x] Skills matrix After column drafted as "evidence N (draft)", clearly not a judgement of the author's skill.
- [x] `docs/15-closure-report.md`: objectives vs results, FR/NFR coverage table (met / partly / not met), failures and
      lessons, deferred ideas, next steps.
- [ ] Demo video, cold rebuild, cloud deploy/destroy and billing check, enabling the deploy workflow, confirming the
      skills matrix: NEEDS HUMAN items 3, 5-8.

### Global Definition of Done (brief section 7)

- [x] Every phase's DoD met or listed as partly / NEEDS HUMAN with the reason (sections 3, 9).
- [x] `uv run pytest -q` green (171 passed), `.\tasks.ps1 lint` clean, CI green on master (runs 43037679612, 43039120762).
- [ ] Real eval for demo-logistics complete: **no** (INCOMPLETE, 8 not run); gate result stated honestly (not measurable
      yet); every failure has a root cause (section 4); the cost of every real run recorded (section 8).
- [x] Engagement #2 delivered with a provably empty `core/` diff since `kit-generic`.
- [x] Teaching notes 15-21 exist, follow the template, every RESULT is captured output (CI-sourced results say so).
- [x] Decision log (DC-016..DC-030), status reports and journals for Days 3-5.
- [x] This report complete and pushed.

## 4. Evals

### demo-logistics

| Run (report) | Model | Prompt | Cases ran / passed | Overall | Safety | Gate | Cost (this run) | p95 | Note |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-11-0739-gpt-6-luna-cadb61d | openai/gpt-6-luna | agent-v1 | 27 / 2 | 7% | 40% | FAIL | $0.0000 | 0.25 s | every call HTTP 400 `temperature` |
| 2026-11-11-0748-gpt-6-luna-cadb61d | openai/gpt-6-luna | agent-v1 | 27 / 18 | 67% | 40% | FAIL | $0.0051 | 15.18 s | 429 daily quota after 18 cases; crashes counted as failures (old runner) |
| 2026-11-11-0811-gpt-6-luna-cadb61d | openai/gpt-6-luna | agent-v1 | 18 / 18 (9 not run) | 100% of finished | 100% of finished | INCOMPLETE | **$0 actual** (report says $0.0045: F-01) | n/a (report says 16.55 s: F-01) | first call hit the quota; 18 results reused |
| **2026-11-11-0932-gpt-6-luna-e69d0b6** (Sprint 01) | openai/gpt-6-luna | agent-v1 (sha 537c08f4c028) | 19 / 19 (8 not run) | 100% of finished | 100% of finished (2/2) | INCOMPLETE | **$0.0002** this run (+ $0.0045 carried over) | 8.18 s (1 case) | q-018 re-run passes; 429 after 1 case |
| fake harness (not committed, `*-fake-*`) | fake | agent-v1 | 27 / 15 | 56% | 100% | not enforced | n/a | 0.1 s | checks the harness only; same before and after 3a |

### coastline-hvac

| Run | Model | Prompt | Cases ran / passed | Overall | Safety | Gate | Cost | Note |
|---|---|---|---|---|---|---|---|---|
| fake via CLI, 09:25 (not committed) | fake | hvac-agent-v1 | 27 / 18 | 67% | 100% | not enforced | n/a | q-016 CRASH = bug in the engagement's fake script (KeyError on a 404 body), fixed in its extensions file |
| fake via `POST /eval`, 09:27 | fake | hvac-agent-v1 | 27 / 19 | 70% | 100% | not enforced | n/a | after the fake-script fix |
| real | - | - | not run | - | - | - | - | quota: NEEDS HUMAN item 4 |

### Failing real cases and root causes

| Case | Report | Root cause | Category of cause | Fix or limitation |
|---|---|---|---|---|
| all 25 non-blocked cases | 0739 | `gpt-6-luna` rejects the `temperature` parameter (HTTP 400) | Model/provider limit + our config default | `llm.temperature` opt-in (DC-016); test `test_temperature_is_not_sent_unless_configured` |
| q-018 | 0748 | Answer was correct ("wasn't found") but (a) shown as `str(list)` of content blocks and (b) the check required the exact words "not found" | Agent bug (a) + golden case too narrow (b) | (a) `AIMessage.text` in `_turn()`/`answer_question()`; (b) alternatives with evidence in `notes`. **Verified in 0932: passes; stored answer is plain text: 'Shipment SHP-0000 wasn't found, so I can't confirm its status. ...'** |
| q-019..q-027 (8 cases) | 0748, 0811, 0932 | HTTP 429 daily quota (0748 scored them as CRASH; the new runner marks NOT RUN) | Provider quota (not an agent failure) | Not yet run with the real model: NEEDS HUMAN item 1. No root cause can be claimed for cases that never ran |

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
  it was attempted once later (09:31, report 0932: one case ran, then 429). No retry loop.
- DC-017 observability + admin endpoints; formal record that the HTML console replaces the Streamlit UI (D-11).
- DC-018 Day 4 platform. Deviations inside it: image builds, Compose and kind verified in CI, not on the laptop
  (memory under the 3 GB floor); trivy only in CI (not installed locally); Day 4 went through draft PR #1, so its first
  two commits carry no note (notes 17-20 are in the commit that completed the part, before the fast-forward to master).
- DC-019..DC-029: one row per kit gap (section 5). Deviation: no separate teaching note for 3a; it is taught in note 21.
- DC-030 engagement #2. Deviation: real eval of engagement #2 not run (quota).
- Deviation: Phase 3b content (discovery doc and policy documents) was written while CI for Phase 2 was running, before
  3a was finished; nothing of 3b was committed before the `kit-generic` tag, so the zero-diff proof is unaffected.
- Deviation: one Phase 2 commit (`57a3f59`, Dockerfile-only) was pushed without re-running the local gate; it changed no
  Python, and CI ran the full test suite on it (green).

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
- **F-11 (review F-R1, HIGH) The planned Cloud Run API was public.** See section 11.
- **F-12 (review F-R2, MEDIUM) Tab characters inside `.\tasks.ps1`.** Origin: the executor's edit scripts went through
  a Bash heredoc that collapsed `\\` to one backslash, so Python read `\t` as a TAB. The executor had seen the symptom
  twice (F-09, "unexpected EOF" and an assertion showing a tab) but did not check what had already been written. See section 11.
- **F-03 Logistics content in `core/`** beyond the brief's list (scoring `WRITE_TOOLS`, refusal text, doc tool description,
  system prompt). Handled in Phase 3a.

## 8. Cost and quota

| Run | OpenAI cost | Model requests | Source |
|---|---|---|---|
| 0739 (before sprint) | $0.0000 | 25 calls, all rejected with HTTP 400 | report |
| 0748 (before sprint) | $0.0051 | not recorded by the runner; the 50/day quota was reached | report |
| 0811 (before sprint) | $0.0000 | 1 (HTTP 429) | report case list; header figure is F-01 |
| 0932 (Sprint 01) | $0.0002 | 1 case ran (q-018: 1,717 tokens in / 53 out), then HTTP 429 | report header "This run" line |
| Real embedding re-ingest for 0932 (Sprint 01) | at most $0.0011 | 1 batch per document (20 documents, 70 chunks) | bound computed: 70 x 800 tokens x $0.02/1M |
| **Sprint 01 total** | **$0.0002 measured, at most $0.0013 with embeddings** | | well under the $1.00 sprint budget |

Other spend: $0 (no cloud resources created).

## 9. NEEDS HUMAN

1. **Finish the real eval of demo-logistics** (quota). Why: the account allows 50 chat requests per day and the 9 remaining
   cases need roughly 25-30. Commands (PowerShell, repo root, mock ERP running in another window via `.\tasks.ps1 erp`):
   ```powershell
   $env:FAKE_LLM = '0'
   uv run python -m core.ingest.run --docs-only
   uv run python -m core.evals.run --resume engagements/demo-logistics/evals/reports/2026-11-11-0932-gpt-6-luna-e69d0b6.json
   Remove-Item Env:FAKE_LLM
   uv run python -m core.ingest.run --docs-only    # restores fake vectors (FAKE_LLM=1 from .env)
   ```
   Expected: a new report; if the quota stops it again, resume from the NEWEST report it printed. Send back the report file name.
   Updated at the end of the sprint: resume from **0932** (it holds the 19 finished results; 0811 holds only 18).
   8 cases remain, about 25 requests, so plan for one day of quota.

2. **Stop the stale API on port 8000.** Why: it runs code from before Sprint 01 (F-05), so anything you try on port 8000
   shows old behaviour. It is your process, so I did not stop it.
   ```powershell
   Get-NetTCPConnection -LocalPort 8000 -State Listen | ForEach-Object { Get-Process -Id $_.OwningProcess } | Format-Table Id, ProcessName, StartTime
   Stop-Process -Id 15616      # only if the line above shows that PID; then restart with .\tasks.ps1 api
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

5. **Demo video (D-21, at most 5 minutes).** Why: needs the author's voice and screen. Suggested flow: `.\tasks.ps1 demo`,
   the console answering a policy question with citations, a credit ticket pausing for approval and being approved,
   `/metrics`, then engagement #2's dispatch. Send back the video link for the README.
6. **Cold rebuild exercise (charter section 7).** Why: it measures the author's skill, which the executor cannot do.
   Pick one component (for example `core/retrieval/search.py` or the approval node in `core/agent/graph.py`), rebuild it
   without notes in at most 45 minutes, run `uv run pytest -q tests/day01` (or `tests/day02/test_agent.py`). Send back
   the component, the time and what was hard.
7. **Confirm the skills matrix After column** (`docs/03-skills-matrix.md`). Why: the drafted values describe the
   repository's evidence, not your skill. Replace each "evidence N (draft)" with your own level; fill Before from memory if
   you can. Send back: done, and SC-01's percentage.
8. **Sign the closure report** (`docs/15-closure-report.md` section 8) after items 1, 3, 4 and record your hours in
   section 5b and in the status reports.

## 10. Risks and open questions

- R-12 provider quota (new). A higher OpenAI tier would let one eval finish in one day; sponsor decision.
- NFR-04 latency: real cases took 15-17 s at p95 per case locally (several model calls each). The 8 s cloud target is
  likely to fail with this model and design; options are a faster model, fewer steps, or a changed target. Sponsor decision.
- The quality gate has never been measured on a complete run. 19/19 finished cases is encouraging but the unrun cases
  include all three multi-step cases and two write cases with capped credits, the hardest ones.
- Engagement #2's prompt and golden set have never seen a real model; expect some failures and golden-case reviews.
- One shared `agent_ro` role can read every engagement's schema in a shared database (DC-023). Fine for a demo; a real
  deployment uses one database per customer.
- Engagement-owned Python (seed and fake scripts) runs inside the kit's process. Today it is our own code; with real
  customers it needs the same review as core code. Open question for the sponsor.
- Missing Day 2 status and journal (noted in Orientation); not back-filled.

## 11. Review findings (sprint 01b)

Two findings from the sponsor's code review of Sprint 01, both fixed. Gate before the commit: tests and lint green (output
in the commit section below); `terraform validate` clean; CI result at the end of this section.

### F-R1 (HIGH): public approvals and chat on Cloud Run

**Problem.** `deploy/terraform/gcp/main.tf` granted `allUsers` the `run.invoker` role on `fde-api`. Only `/ingest` and
`/eval` needed a token. Once deployed, anyone could `POST /approvals/{thread}/approve` (the "by" field is self-declared)
to run a paused write, or call `/chat` in a loop to spend the OpenAI quota. Blocked NEEDS HUMAN item 3.

**Fix (DC-031, threat T-10, risk R-13).**

1. Terraform: the `api_public` binding is gone. New variable `api_invokers` (IAM members); the deploy service account may
   invoke (its smoke test now goes through `gcloud run services proxy`). The mock ERP stays invokable without IAM, with
   the reason documented in `main.tf` and DC-031 (third-party role with its own random bearer token; IAM-private needs a
   toolgen feature, backlog). Runbook section 4.2 steps 5-6: proxy access, expected 403 on the bare URL, how to read the tokens.
2. App (generic, env-driven, `core/api/main.py`): `APPROVER_TOKEN` (`X-Approver-Token`) guards `GET /approvals`,
   approve, reject and `GET /threads/*/audit`; `CHAT_TOKEN` (`X-Chat-Token`) guards `/chat` and `/ask`; `ADMIN_TOKEN` is
   also accepted as `X-Admin-Token`. Own headers, because the IAM identity token occupies `Authorization` behind the proxy.
   Unset = local behaviour unchanged, and `/health` shows `"approvals_auth": false, "chat_auth": false`. Every
   `approval_decided` audit row records `token_verified`. Console: optional "Reviewer token" and "Chat token" fields,
   kept in page memory only. Terraform generates both tokens into Secret Manager; Helm values and Compose pass them through.
3. Tests (`tests/day05/test_review_fixes.py`): `test_without_the_reviewer_token_approval_routes_answer_401`,
   `test_with_the_reviewer_token_the_approval_runs_and_is_audited_as_verified` (401 first, the write stays paused, then 200
   with the token, audit `token_verified: true`), `test_local_mode_is_unchanged_and_audited_as_not_verified`,
   `test_without_the_chat_token_chat_answers_401`, `test_health_shows_which_access_tokens_are_on`,
   `test_admin_token_also_works_in_its_own_header`. All 171 earlier tests pass unchanged (local mode).
4. Docs: T-10 and section 4b in `docs/10-security-and-compliance.md`, R-13 in the risk register, DC-031, note 13
   practicum 7 (real output below), note 20 teach-back 3-4, closure report section 6.

**Evidence: live run** (API with `APPROVER_TOKEN=dev-reviewer-token`, port 8001):

```text
GET /health -> ... "approvals_auth":true,"chat_auth":false ...
no token -> 401  {"detail": "Missing or invalid reviewer token (X-Approver-Token)"}
with token -> done
approved by        token_verified
   False team-lead           True
```

```text
> terraform -chdir=deploy/terraform/gcp fmt -check -recursive   -> exit 0
> terraform -chdir=deploy/terraform/gcp validate                 -> Success! The configuration is valid.
> helm lint deploy/helm/fde-kit                                  -> 1 chart(s) linted, 0 chart(s) failed
> grep allUsers deploy/terraform/gcp/*.tf                        -> only the documented mock ERP binding (main.tf)
```

Residual risk: a token proves "holder of the reviewer token", not which person; per-person identity and role routing stay
deferred idea A.

### F-R2 (MEDIUM): `.\tasks.ps1` corrupted to ".TAB asks.ps1"

**Problem.** `tasks.ps1` lines 107 and 121 and this report (lines 309 and 325) contained a TAB character where `\t` was meant.

**Root cause.** The executor sent Python edit scripts through Bash heredocs. In this environment the heredoc text reached
Python with `\\` already collapsed to one backslash, so `".\\tasks.ps1"` in a Python string became `".\tasks.ps1"`, and
Python turned `\t` into a TAB. The same mechanism broke the first repair attempt (it replaced the TAB with a TAB), which
the new test caught at once. A regex sent the same way failed with "unbalanced parenthesis" for the same reason.

**Fix.** A script file that builds the backslash as `chr(92)`; 2 + 2 occurrences replaced, 0 tabs left in both files.
**Scan.** Every tracked .md, .ps1, .yml, .yaml, .tf and .py file was scanned for control characters and for
escape-like sequences (`\n`, `\t`, `\r`): 189 escape-like sequences found, all legitimate (Python string escapes,
`.\\tasks.ps1` in Python docstrings, one Python one-liner in note 05); no other control characters.
**Prevention.** `test_no_tab_where_a_backslash_t_was_meant` (TAB + "asks.ps1" in any tracked text file) and
`test_no_control_characters_in_tracked_text_files` (any control character other than tab, newline, CR; any tab in .md
or .ps1). Both failed on the corrupted files and pass after the fix. They run in CI with the rest of pytest. Working rule:
multi-line edits are written as script files, never through heredocs.

### Effect on the zero-diff proof

The F-R1 fix changes `core/api/main.py` and `core/agent/service.py` after the `kit-generic` tag. These are generic
security changes from the review, not changes needed by engagement #2, so the tag was not moved. The proof stays valid
for the range that added engagement #2: `git diff --stat kit-generic..e69d0b6 -- core/` prints nothing. Output after the
Sprint 01b commit is below.

```text
> git diff --stat kit-generic..e69d0b6 -- core/
(no output: 0 lines)
> git diff --stat kit-generic..HEAD -- core/      (after the Sprint 01b commit 065ccf1)
 core/agent/service.py |  8 ++++--
 core/api/main.py      | 69 ++++++++++++++++++++++++++++++++++++++++-----------
 2 files changed, 60 insertions(+), 17 deletions(-)
```

CI on the Sprint 01b commit `065ccf1`: run 43047112135, **success** (test, secrets, containers), 179 tests on the clean runner.
