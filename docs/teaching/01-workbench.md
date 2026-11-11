# 01 - The workbench

Component: PowerShell 7, `tasks.ps1`, uv, Docker Compose, Git/GitHub

<!-- Color key: NOTE (blue) = INTENT/Why, IMPORTANT (purple) = CONTEXT/When-Where, TIP (green) = ACTION/How, WARNING (yellow) = RESULT/What, CAUTION (red) = RESULT of a break-it practicum -->

## At a glance

| What | When | How | Why |
|---|---|---|---|
| The tools around the code: PowerShell, tasks.ps1, uv, Docker, Git | Every session, before and after any code change | Named tasks run the same steps every time; locked dependencies; a containerized database; one commit per task | A fresh clone becomes a working project on any machine, with a readable history |

## ELI10

A carpenter doesn't build a table with bare hands. They have a **workbench** with tools hung in the same place every day, so they never waste time looking for the saw. Our workbench:

- **PowerShell** is the place where you type instructions to the computer.
- **`tasks.ps1`** is a list of named recipes: say `.\tasks.ps1 up` and it does every step of "start the database" for you, the same way every time.
- **uv** is the shopkeeper who fetches the exact Python parts the project needs (listed in `pyproject.toml`, locked in `uv.lock`) and keeps them in a private box (`.venv`) so they never mix with other projects.
- **Docker** is a lunchbox: it packs a whole program (Postgres) with everything it needs, so it runs the same on every computer.
- **Git** is a time machine with labels: every commit is a saved moment you can go back to. **GitHub** keeps a copy online.

## Practicums

Color key: blue = **INTENT (Why?)**, purple = **CONTEXT (When / where?)**, green = **ACTION (How?)**, yellow = **RESULT (What?)**, red = **RESULT of a break-it practicum**.

### Practicum 1

> [!NOTE]
> **INTENT - Why?** "Is this computer ready to build the project?"

> [!IMPORTANT]
> **CONTEXT - When / where?** Day 0. Fresh Windows machine with some tools installed.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> .\tasks.ps1 check-tools
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> OK for python, uv, docker compose, kubectl, gcloud, git, gh;
> MISS kind version / MISS helm version --short / MISS terraform version.
> Fix: winget install Kubernetes.kind, Helm.Helm, Hashicorp.Terraform,
> then open a NEW PowerShell window (PATH only reloads in new windows).
> Second run: all 10 OK.
> ```

### Practicum 2

> [!NOTE]
> **INTENT - Why?** "Start the database."

> [!IMPORTANT]
> **CONTEXT - When / where?** Docker Desktop is running; nothing started yet.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> .\tasks.ps1 up
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> Network fde-kit_default Created / Volume fde-kit_pgdata Created /
> Container fde-kit-postgres-1 Healthy (4.8s)
> The VOLUME is where the data lives. Stopping the container (.\tasks.ps1 down)
> keeps the data; only deleting the volume erases it.
> ```

### Practicum 3 (break it on purpose)

> [!NOTE]
> **INTENT - Why?** "Why did my test command end in a red error?"

> [!IMPORTANT]
> **CONTEXT - When / where?** Day 1, before any RAG code existed. Some tests were expected to fail.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> .\tasks.ps1 test
> ```

> [!CAUTION]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> "12 failed, 18 passed, 9 errors", then
> "Exception: ... Step failed: Run tests (exit 1)"
> tasks.ps1 checks every step's exit code and STOPS on failure. That's on
> purpose: in a chain like demo = up -> migrate -> seed -> ingest, a broken
> step must not let the next one run on bad data.
> ```

### Practicum 4

> [!NOTE]
> **INTENT - Why?** "What are all these 'LF will be replaced by CRLF' warnings?"

> [!IMPORTANT]
> **CONTEXT - When / where?** First git add on Windows.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> Get-Content .gitattributes
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> * text=auto / *.ps1 text eol=crlf / *.sh text eol=lf
> Windows ends lines with CRLF, Linux with LF. Git converts automatically so
> the repo stays consistent. The warning is information, not an error.
> ```

### Practicum 5

> [!NOTE]
> **INTENT - Why?** "Which saved moments does the project have?"

> [!IMPORTANT]
> **CONTEXT - When / where?** End of Day 1.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> git log --oneline
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> 855d9fe Day 1: journal draft, status report, decision log (M1 complete)
> c2a53a2 Day 1 task 4: cited answers with no-answer gate (M1)
> a745340 Day 1 task 3: vector + hybrid (RRF) search
> 0b2e787 Day 1 task 2: document ingestion; kb keyed by engagement
> 8f8b380 Day 1 task 1: chunking
> 5f37f89 Day 1 task 1: chunking (restore test file)
> 735e88d Day 0: docs, setup code, Day 1 specs and tests
> One commit per finished task = a readable story for reviewers.
> ```

## Teach-back check

<details><summary>1. Why use tasks.ps1 instead of typing the commands yourself?</summary>

Same steps, same order, every time, for every person. It removes "works on my machine" mistakes and documents how the project runs.
</details>

<details><summary>2. What's the difference between uv.lock and pyproject.toml?</summary>

`pyproject.toml` says what we need ("fastapi 0.115 or newer"). `uv.lock` records the exact versions that were installed, so everyone gets identical parts.
</details>

<details><summary>3. If you run `.\tasks.ps1 down`, is your data gone?</summary>

No. The container stops, but the data lives in the Docker volume `fde-kit_pgdata` and comes back with `.\tasks.ps1 up`.
</details>

## Interview line

"Everything runs through one task runner with locked dependencies and a containerized database, so a fresh clone becomes a working demo with a few commands on any machine."
