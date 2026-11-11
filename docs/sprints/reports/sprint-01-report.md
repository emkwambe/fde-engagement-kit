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
| 0 Day 3 close-out | Done (real eval INCOMPLETE, see NEEDS HUMAN) | see section 3 | 137 passed | `docs/teaching/15-measuring-quality.md`, `docs/16-deferred-ideas.md`, DC-016 |
| 1 Observability + endpoints | Not started | | | |
| 2 Day 4 platform | Not started | | | |
| 3a Kit generic | Not started | | | |
| 3b Engagement #2 | Not started | | | |
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

(Phase 3.)

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

## 10. Risks and open questions

- R-12 provider quota (new). A higher OpenAI tier would let one eval finish in one day; sponsor decision.
