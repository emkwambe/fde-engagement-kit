# 18 - The robot reviewer

Component: `.github/workflows/ci.yml` (jobs `test`, `secrets`, `containers`), `.github/workflows/eval-real.yml`, `.github/workflows/deploy.yml`

<!-- Color key: NOTE (blue) = INTENT/Why, IMPORTANT (purple) = CONTEXT/When-Where, TIP (green) = ACTION/How, WARNING (yellow) = RESULT/What, CAUTION (red) = RESULT of a break-it practicum -->

## At a glance

| What | When | How | Why |
|---|---|---|---|
| Three workflows. `ci`: lint, types, tests with Postgres, the fake eval, a secrets scan, image build, CVE scan, Compose smoke test and Helm on kind. `eval-real`: the real-model eval, by hand. `deploy`: build, push and roll out to Cloud Run, disabled until enabled | `ci` on every push to master and every pull request; `eval-real` and `deploy` only when a person clicks Run | GitHub Actions on clean Ubuntu runners; a Postgres + pgvector service container; Docker, trivy, gitleaks and kind inside the job; Workload Identity Federation for GCP (no stored key) | A change is only trusted when a machine that is not the author's laptop builds and tests it from scratch, every time, the same way |

## ELI10

Imagine a school where every homework page goes through a robot before the teacher sees it. The robot checks the
spelling (ruff), checks that the sums add up (mypy, pytest), makes sure nobody wrote a password on the page (gitleaks),
packs the homework into a lunchbox and checks the box for mould (docker build, trivy), then actually opens the box in
two different rooms (Compose and Kubernetes) to see that it still works. If any check fails, the page goes back.

Two robots have special rules. The "real exam" robot (eval-real) costs money each time, so it only runs when a person
presses the button. The "send it to the shop" robot (deploy) has no key to the shop at all until the owner hands one
over by setting a few variables.

Where the analogy stops: the robot does not understand the homework. It runs the checks it was given. The quality of
CI is the quality of the tests and evals behind it.

## Practicums

Color key: blue = **INTENT (Why?)**, purple = **CONTEXT (When / where?)**, green = **ACTION (How?)**, yellow = **RESULT (What?)**.

### Practicum 1

> [!NOTE]
> **INTENT - Why?** "Did my change pass every check on a clean machine?"

> [!IMPORTANT]
> **CONTEXT - When / where?** Pull request #1 (`day4-platform`), opened as a draft so CI could run before anything reached master. Two runs: the first failed (trivy, note 17), the second passed.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> gh run view 43035141379 --json jobs,conclusion --jq '.conclusion, (.jobs[] | .name + " " + .conclusion)'
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> success
> secrets success
> test success
> containers success
> The first run, 43034563850, ended "failure": secrets success, test success, containers failure (trivy found 7
> CRITICAL CVEs). Fixed in commit 37a85e0; the second run, 43035141379, is green. The PR made the failure cheap:
> it happened on a branch, before master.
> ```

### Practicum 2

> [!NOTE]
> **INTENT - Why?** "What exactly did the test job prove?"

> [!IMPORTANT]
> **CONTEXT - When / where?** Job `test` of run 43035141379: a fresh runner, a Postgres + pgvector service container, `uv sync --frozen` (exactly uv.lock), then ruff, mypy, pytest and the fake eval.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> gh run view --job 130571870388 --log | Select-String 'passed in|All checks passed|Success: no issues|\[etl\] |\[docs\]|Overall \d+/|Gate not enforced' | ForEach-Object { ($_.Line -split "`t")[-1] -replace '^\S+Z ', '' }
> gh run view --job 130571869678 --log | Select-String 'commits scanned|no leaks found' | ForEach-Object { ($_.Line -split "`t")[-1] -replace '^\S+Z ', '' }
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> All checks passed!
> Success: no issues found in 46 source files
> 147 passed in 13.40s
> [etl] customers  in=41   loaded=40   duplicates=0   rejected=1
> [etl] orders     in=506  loaded=500  duplicates=5   rejected=1
> [etl] shipments  in=500  loaded=500  duplicates=0   rejected=0
> [docs] seen=20 skipped=20 chunks_upserted=0
> Overall 15/27 = 56% (threshold 85%) | safety 1.0 | cost this run n/a
> Gate not enforced (fake model): this run checks the harness, not answer quality.
> 21 commits scanned.
> no leaks found
> The same 147 tests as on the laptop, on a machine that has never seen this repo. The fake eval ran all 27 cases
> end to end (data, documents, tools, mock ERP). gitleaks read the WHOLE history: a key deleted later is still leaked.
> ```

## Teach-back check

<details><summary>1. Why is the real-model eval not part of every CI run?</summary>

It costs money and uses the provider's daily quota (50 requests here; one full run needs about 75-90). Running it on every push would burn the quota in one afternoon and still be incomplete. So CI runs the free fake eval as a harness check, and the real eval is a manual workflow (or a scheduled one with a bigger quota).
</details>

<details><summary>2. How does deploy.yml get into GCP without a stored key?</summary>

GitHub mints a short-lived OIDC token for the run. GCP's Workload Identity Federation trusts tokens from GitHub, but Terraform limits it to this one repository (attribute_condition), and exchanges the token for short-lived credentials of the deploy service account. Nothing long-lived is stored anywhere (threat T-08).
</details>

<details><summary>3. Why are workflow inputs passed through env variables in eval-real.yml?</summary>

Writing `${{ inputs.cases }}` straight into a shell script means a crafted input becomes shell code (script injection). Passing it as an environment variable makes it data; the script also checks each case id against `q-NNN`.
</details>

<details><summary>4. Why open a draft pull request for Day 4 instead of pushing to master?</summary>

The teaching notes quote CI output, so CI had to run before the notes could be written, and a failing infrastructure change should fail on a branch, not on master. It also shows the normal team workflow: PR, CI, review, merge.
</details>

## Interview line

"Every push runs lint, types, 147 tests against a real pgvector, a fake end-to-end eval, a full-history secrets scan, image build with a CVE gate, a Compose smoke test and a Helm install on kind; the real-model eval and the Cloud Run deploy are manual workflows, the deploy using Workload Identity Federation instead of keys."
