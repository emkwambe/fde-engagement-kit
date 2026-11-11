# 17 - Shipping containers

Component: `deploy/docker/api.Dockerfile`, `deploy/docker/mock-erp.Dockerfile`, `.dockerignore`, `docker-compose.yml`, `.\tasks.ps1 demo | images | stack-down`, `/health` `version`

<!-- Color key: NOTE (blue) = INTENT/Why, IMPORTANT (purple) = CONTEXT/When-Where, TIP (green) = ACTION/How, WARNING (yellow) = RESULT/What, CAUTION (red) = RESULT of a break-it practicum -->

## At a glance

| What | When | How | Why |
|---|---|---|---|
| Two images (API + console, mock ERP) and a Compose file that starts the whole stack: Postgres, a seed job, a migrate+ingest job, the mock ERP and the API | A clean clone must run with one command (NFR-01); the same image goes to Compose, kind and Cloud Run (NFR-11) | Multi-stage builds (uv builds the venv, the runtime stage copies only the venv and source), digest-pinned base, OS security updates, non-root uid 10001, healthchecks, the git commit baked in as `BUILD_SHA` | "Works on my machine" is not a delivery. A container fixes the Python version, the packages and the start command, and `/health` says exactly which commit is running |

## ELI10

A container is a lunchbox packed in the kitchen. Everything the meal needs is inside: the food (our code), the cutlery
(Python and the packages), and a note saying how to eat it (the start command). Whoever opens the box, at school, at a
friend's house, on a trip, gets the same meal.

Multi-stage means we cook in one kitchen (with all the pots and pans: uv, compilers, caches) and pack only the finished
meal into the box. The box is smaller, and there are fewer things inside that could go bad (fewer packages for a
scanner to flag). The sticker on the lid (`BUILD_SHA`) says which day it was cooked, so nobody eats yesterday's lunch
thinking it is today's: that is the "stale server" problem from Day 3, solved.

Where the analogy stops: lunchboxes are sealed. A container starts from the same packed box every time, but it can still
talk to the outside world (the database, the mock ERP, OpenAI), and those parts are not inside the box.

## Practicums

Color key: blue = **INTENT (Why?)**, purple = **CONTEXT (When / where?)**, green = **ACTION (How?)**, yellow = **RESULT (What?)**.

> [!IMPORTANT]
> These results come from GitHub Actions run 43035141379 (job `containers`, commit `37a85e0`), not from the author's
> laptop: when the images were first built, the laptop had 2.2-2.9 GB of free memory, under the project's 3 GB floor
> for heavy local runs. The CI runner is a clean machine, which is exactly the "fresh clone" NFR-01 asks about. Locally
> you run the same steps with `.\tasks.ps1 demo`.

### Practicum 1

> [!NOTE]
> **INTENT - Why?** "Are the images safe enough to ship: small, non-root, and free of known critical holes?"

> [!IMPORTANT]
> **CONTEXT - When / where?** CI builds both images, checks the user they run as, and scans them with trivy (fails on any CRITICAL vulnerability that already has a fix). The first run failed; this is the second.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> $log = gh run view --job 130572443115 --log
> $log | Select-String 'runs as 10001' | ForEach-Object { ($_.Line -split "`t")[-1] -replace '^\S+Z ', '' }
> $log | Select-String 'fde-(api|mock-erp):local \(debian' | ForEach-Object { ($_.Line -split "`t")[-1] -replace '^\S+Z ', '' } | Select-Object -Unique
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> fde-api:local runs as 10001:10001
> fde-mock-erp:local runs as 10001:10001
> | fde-api:local (debian 12.15)        | debian | 0 | - |
> | fde-mock-erp:local (debian 12.15)   | debian | 0 | - |
> Image sizes in the same log: fde-api:local 395MB, fde-mock-erp:local 203MB.
> The FIRST run (job 130570428801) failed on the same scan:
> | fde-api:local (debian 12.13)        | debian | 7 | - |      Total: 7 (CRITICAL: 7)
> 7 CRITICAL CVEs, all in Debian packages of the base image (libssl3, gnutls, perl), all with fixes published.
> Pinning the base by digest makes builds repeatable, but it also freezes old packages. The fix is one line in
> the runtime stage: apt-get update && apt-get -y upgrade. Debian went from 12.13 to 12.15 and the count to 0.
> ```

### Practicum 2

> [!NOTE]
> **INTENT - Why?** "Does a clean checkout come up as a working stack with one command, and which code is it running?"

> [!IMPORTANT]
> **CONTEXT - When / where?** `docker compose up -d --wait api` starts everything the api depends on, in order: Postgres (healthy), the seed job (writes CSV exports into a shared volume, then exits), the migrate job (schemas, read-only role, ETL, documents, then exits), the mock ERP (healthy), then the API (healthy).

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> $log = gh run view --job 130572443115 --log
> $log | Select-String 'Container fde-kit-\w+-1  (Exited|Healthy)$|"status":"ok"' | ForEach-Object { ($_.Line -split "`t")[-1] -replace '^\S+Z ', '' } | Select-Object -Last 6
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
>  Container fde-kit-seed-1  Exited
>  Container fde-kit-postgres-1  Healthy
>  Container fde-kit-migrate-1  Exited
>  Container fde-kit-api-1  Healthy
> {"status":"ok","engagement":"demo-logistics","llm_provider":"fake","database":true,"checkpointer":"postgres",
>  "embeddings_match":true,"version":{"app":"0.3.0","build_sha":"37a85e0"}}
> The jobs EXIT (that is success for a job); the services become HEALTHY. /health says status ok, the vectors match
> the model, and version.build_sha is the commit CI built. The next step in the log asked /chat a tool-calling
> question and got: "ORD-1043 (Gold, customer C-007) was 3 day(s) late on a $4,820.00 order."
> ```

## Teach-back check

<details><summary>1. Why two stages in the API Dockerfile?</summary>

The build stage needs uv, the download cache and build tools to create the virtual environment. The runtime stage only needs the finished `.venv` and our source. Copying just those makes the image smaller and leaves fewer packages that could contain vulnerabilities.
</details>

<details><summary>2. The base image is pinned by digest. Why did the scan still fail, and why is apt-get upgrade the right fix?</summary>

A digest freezes the image exactly, including its OS packages, so security fixes published later are not in it. Upgrading the OS packages in the runtime stage pulls those fixes while keeping the Python base the same. The alternative, bumping the digest, also works but needs a new pin every time Debian ships a fix.
</details>

<details><summary>3. Why does the mock ERP get its shipment export at build time, while the API gets its CSVs from a seed job?</summary>

On Cloud Run there is no shared disk between services, so the ERP cannot read a file another container wrote. Baking the export into its image (generated by the same seed code and seed number) works the same on Compose, kind and Cloud Run. The API's data goes into Postgres, which every target has.
</details>

<details><summary>4. What does BUILD_SHA solve?</summary>

On Day 3 a server started from old code kept answering on port 8000 and nobody could tell. Now the commit is baked into the image at build time and shown in /health, so "which code is this server running?" has a one-line answer.
</details>

## Interview line

"Both services ship as multi-stage, digest-pinned, non-root images with OS security updates applied; a clean checkout comes up with one `docker compose up`, and `/health` reports the exact commit, which CI checks against the commit it built."
