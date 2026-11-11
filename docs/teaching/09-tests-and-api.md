# 09 - Proving it works

Component: `tests/` (pytest), fake models, `core/api/main.py` (FastAPI: `/health`, `/chat`, `/docs`)

## ELI10

Before a plane takes off, the pilot runs a **checklist**: flaps, fuel, lights. They don't trust their memory, they check every time. **Tests** are our checklist: small programs that use the real code and shout if something is wrong. We have 39 of them.

Two tricks make the checklist fast and free:

- **Stand-ins (fakes).** Instead of paying a real AI for every check, tests use a pretend AI that always behaves the same way. Same input, same output, every time.
- **Acceptance tests first.** For Day 1, the tests were written *before* the code. They were the job description: "make these pass".

The **API** is the front door of the project. Other programs knock (`POST /chat`) and get an answer. `/health` is the doorbell light that says whether everything inside is working, and `/docs` is a self-made instruction manual you can click through in the browser.

## Practicums

```text
$ practicum start

[INTENT]  "Is everything working right now?"
[CONTEXT] Database up, all Day 1 code in place.
[ACTION]  uv run pytest -q
[RESULT]  39 passed
          Setup checks (18) + Day 1 acceptance tests (21). Run before every commit.
```

```text
$ practicum start   (break it on purpose)

[INTENT]  "What happens to the tests if the database is down?"
[CONTEXT] Postgres stopped.
[ACTION]  .\tasks.ps1 down; uv run pytest tests/test_etl_db.py -q -rs
          .\tasks.ps1 up   (undo)
[RESULT]  SKIPPED ... Postgres not reachable at postgresql://fde:fde@localhost:5432/fde
          (OperationalError). Run: .\tasks.ps1 up
          2 skipped
          Database tests SKIP with instructions instead of failing with a scary stack trace.
```

```text
$ practicum start   (break it on purpose)

[INTENT]  "What does the API say when the database is down?"
[CONTEXT] API running, Postgres stopped.
[ACTION]  .\tasks.ps1 down; Invoke-RestMethod http://localhost:8000/health
          .\tasks.ps1 up   (undo)
[RESULT]  status: degraded   database: False
          The front door stays open and reports the problem honestly, which is exactly
          what a load balancer or Cloud Run health check needs to see.
```

```text
$ practicum start

[INTENT]  "I opened the API in my browser and got 404. Is it broken?"
[CONTEXT] Browser at http://localhost:8000/
[ACTION]  Look at the API window's log, then open http://localhost:8000/docs
[RESULT]  "GET / HTTP/1.1" 404 Not Found
          "GET /favicon.ico HTTP/1.1" 404 Not Found
          Nothing lives at "/", so 404 is correct. /docs shows the interactive manual,
          generated automatically from the code, where "Try it out" calls /chat.
```

```text
$ practicum start

[INTENT]  "How much did today's testing cost?"
[CONTEXT] FAKE_LLM=1 the whole day.
[ACTION]  Invoke-RestMethod http://localhost:8000/health | Select-Object llm_provider
[RESULT]  llm_provider: fake
          $0 spent. Fakes make tests fast, free and repeatable. Real-model quality is
          measured separately with evals (Day 3), on purpose and within budget.
```

## Teach-back check

<details><summary>1. Why use a fake AI in tests?</summary>

Tests must be fast, free and repeatable. A real model costs money, needs a key and may answer differently each time. Quality of the real model is measured by evals, which are a separate tool.
</details>

<details><summary>2. Tests vs evals: what's the difference?</summary>

Tests check the code is correct (pass/fail, deterministic). Evals check the AI's answers are good enough (a score against a golden set, using the real model).
</details>

<details><summary>3. Why does /health report "degraded" instead of failing?</summary>

So monitoring can tell "the app is up but its database is down" apart from "the app is gone", and act accordingly.
</details>

## Interview line

"Everything is covered by deterministic tests using fake models, with acceptance tests written before the code, and the API exposes an honest health check, so CI is free and fast and real-model quality is measured separately with evals."
