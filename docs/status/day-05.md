# Status Report - Day 5 (2026-11-11)

**Overall:** At risk on two external items (real-eval quota, cloud apply); the kit's main promise is proven.

| Milestone | Planned | Status | Note |
|---|---|---|---|
| M0-M2 | Day 0-2 | Done | |
| M3 | Day 3 | Done (eval INCOMPLETE) | 19/19 finished real cases pass; 8 not run (quota) |
| M4 | Day 4 | Partly | Everything local and CI done; Cloud Run apply is the sponsor's step |
| M5 | Day 5 | Partly | Engagement #2 live with zero core changes; closure drafted; demo video and cold rebuild are the author's |

## Done today
- Phase 3a: eleven logistics-specific pieces moved out of `core/` into config and engagement files (DC-019..DC-029); logistics unchanged (tests, fake eval 15/27, prompt sha `537c08f4c028`). Tag `kit-generic` after green CI.
- Phase 3b: engagement #2, Coastline Climate Services (fictional), HVAC dispatch: discovery, 11 documents, schema `field`, seed, prompt, fake script, mock CMMS with drift test, 27-case golden set. `git diff kit-generic..HEAD -- core/` empty. End to end via API: dispatch paused, approved, created; fake eval 19/27, red team 5/5. Note 21.
- Real eval resume: q-018 passed with the real model (plain-text fix confirmed); quota stopped the run again after 1 case (report 0932, $0.0002).
- Phase 3c: README, architecture, cost actuals, skills matrix draft, closure report draft.

## Planned next session
- Finish real evals across days with `--resume` (both engagements); then the cloud deploy and teardown; demo video; cold rebuild.

## Risks / issues (see [risk register](../07-risk-register.md))
| ID | Change | Action |
|---|---|---|
| R-12 | Still open: quota limits real evals to a few cases per day | Resume daily, or raise the account tier |
| R-01 | Mitigated: generalised only what engagement #2 needed | Kit gaps fixed one by one, each with a DC row |

## Decisions / changes (see [log](../14-decision-and-change-log.md))
- DC-019..DC-029 kit-generic gaps; DC-030 engagement #2.

## Metrics
| Metric | Value |
|---|---|
| Eval overall score | demo-logistics real: 19/19 finished (8 not run); coastline-hvac real: not run; fake: 15/27 and 19/27 (harness only) |
| Tests passing | 171 / 171 |
| Spend to date (OpenAI / GCP) | under $0.01 / $0 |
| Hours spent (build / learning) | |
