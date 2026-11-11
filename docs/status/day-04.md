# Status Report - Day 4 (2026-11-11)

**Overall:** At risk for M4 as defined (a live Cloud Run URL needs the human's `terraform apply`); everything the executor may do is done.

| Milestone | Planned | Status | Note |
|---|---|---|---|
| M0 | Day 0 | Done | |
| M1 | Day 1 | Done | |
| M2 | Day 2 | Done | |
| M3 | Day 3 | Done (eval INCOMPLETE) | Evals, guardrails, observability; real eval waits for quota |
| M4 | Day 4 | Partly | Images, Compose, Helm on kind and CI green (run 43035141379); Terraform validated, not applied (NEEDS HUMAN) |
| M5 | Day 5 | In progress | |

## Done today
- Multi-stage, non-root, digest-pinned images for the API and the mock ERP; `/health` shows the build commit.
- Compose stack: postgres, seed job, migrate+ingest job, mock ERP, API, all with healthchecks (`.\tasks.ps1 demo`).
- Helm chart `deploy/helm/fde-kit`: installed on kind in CI, all 3 pods Ready, `/health` ok through port-forward.
- CI (`ci.yml`): ruff, mypy, 147 tests with pgvector, fake eval, gitleaks (21 commits, no leaks), image build, trivy, Compose and kind smoke tests. `eval-real.yml` and `deploy.yml` (disabled) added.
- Terraform for GCP: `fmt -check` and `validate` pass; deploy and teardown sequence in the runbook.
- Finding: trivy blocked the first build (7 CRITICAL CVEs in the pinned Debian base); fixed with OS upgrades in the image.
- Teaching notes 17-20, DC-018.

## Planned next session
- Day 5: make the kit generic where it is not (Phase 3a), engagement #2 with zero `core/` changes (3b), closure (3c).

## Risks / issues (see [risk register](../07-risk-register.md))
| ID | Change | Action |
|---|---|---|
| R-10 | Triggered: laptop free memory 2.2-2.9 GB, under the 3 GB floor | Docker builds, Compose and kind verified in GitHub Actions instead |
| R-03 | Unchanged | Cloud deploy is a human step; runbook section 4 is ready |

## Decisions / changes (see [log](../14-decision-and-change-log.md))
- DC-018: Day 4 platform decisions and the two deviations (CI instead of local runs; draft PR before notes).

## Metrics
| Metric | Value |
|---|---|
| Eval overall score | Unchanged: real 18/18 finished cases pass, 9 not run (quota) |
| Tests passing | 147 / 147 (laptop and CI) |
| Spend to date (OpenAI / GCP) | $0.0051 / $0 |
| Hours spent (build / learning) | |
