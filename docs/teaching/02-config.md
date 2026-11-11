# 02 - Settings in one file

Component: `engagements/<name>/engagement.yaml`, `core/config/schema.py`, `core/config/loader.py`

<!-- Color key: NOTE (blue) = INTENT/Why, IMPORTANT (purple) = CONTEXT/When-Where, TIP (green) = ACTION/How, WARNING (yellow) = RESULT/What, CAUTION (red) = RESULT of a break-it practicum -->

## At a glance

| What | When | How | Why |
|---|---|---|---|
| One validated settings file per customer: engagement.yaml | Onboarding a new customer, or switching models and providers | Pydantic schema forbids unknown keys; ${ENV} placeholders filled from .env; FAKE_LLM=1 switches to free fakes | New customer = new config, not new code; typos fail fast; secrets stay out of Git |

## ELI10

Think of a video game's **settings screen**: difficulty, volume, language. You change the settings, not the game itself. Our project works the same way. Everything that's different from one customer to the next (which AI model, where the documents are, how big the chunks are, which database) lives in one settings file: `engagement.yaml`. The code reads the file and behaves accordingly.

Two safety features:

- **A strict checker.** If you misspell a setting, the checker refuses to start and tells you exactly which line is wrong, instead of silently ignoring it.
- **No secrets in the file.** Passwords and keys are written as `${DATABASE_URL}`, a placeholder that's filled from your private `.env` file at start-up. The settings file can be shared; the secrets never are.

There's also a **practice mode**: `FAKE_LLM=1` swaps the real AI for a free, offline stand-in, so everything can be tested without an API key or cost.

## Practicums

Color key: blue = **INTENT (Why?)**, purple = **CONTEXT (When / where?)**, green = **ACTION (How?)**, yellow = **RESULT (What?)**, red = **RESULT of a break-it practicum**.

### Practicum 1

> [!NOTE]
> **INTENT - Why?** "What settings is the project actually running with?"

> [!IMPORTANT]
> **CONTEXT - When / where?** Day 1, .env has FAKE_LLM=1.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> uv run python -c "from core.config import load_engagement as l; c=l('demo-logistics'); print(c.llm.provider, c.embeddings.provider, c.retrieval.top_k, c.retrieval.chunk_size, c.retrieval.chunk_overlap, c.retrieval.min_score)"
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> fake fake 5 800 100 0.3
> The YAML says provider: openai, but FAKE_LLM=1 switched both models to
> "fake" at load time, without editing the file.
> ```

### Practicum 2 (break it on purpose)

> [!NOTE]
> **INTENT - Why?** "What if someone misspells a setting?"

> [!IMPORTANT]
> **CONTEXT - When / where?** A copy of engagement.yaml with top_k mistyped as top_kk.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> uv run pytest tests/test_config.py::test_unknown_key_is_rejected -v
> ```

> [!CAUTION]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> PASSED. Underneath, the loader raised:
> "1 validation error for EngagementConfig / retrieval.top_kk ..."
> Without the strict checker, top_kk would be ignored and top_k would
> silently stay 5: a bug that's very hard to notice.
> ```

### Practicum 3 (break it on purpose)

> [!NOTE]
> **INTENT - Why?** "What if the overlap is as big as the chunk?"

> [!IMPORTANT]
> **CONTEXT - When / where?** A copy of the config with chunk_size 200 and chunk_overlap 200.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> uv run pytest tests/test_config.py::test_overlap_must_be_smaller_than_size -v
> ```

> [!CAUTION]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> PASSED. The loader raised:
> "Value error, retrieval.chunk_overlap must be smaller than retrieval.chunk_size"
> Rules that involve TWO settings are checked too, not just single values.
> ```

### Practicum 4 (break it on purpose)

> [!NOTE]
> **INTENT - Why?** "What if the database address is missing?"

> [!IMPORTANT]
> **CONTEXT - When / where?** DATABASE_URL not set (for example, .env was never created).

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> $env:DATABASE_URL = ''; uv run python -c "from core.config import load_engagement; load_engagement('demo-logistics')"
> # undo: open a new PowerShell window, or run .\tasks.ps1 help to reload .env
> ```

> [!CAUTION]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> "engagement.yaml: environment variable(s) not set: DATABASE_URL.
>  Add them to .env (see .env.example)."
> A clear message that says what to do, instead of a confusing crash later.
> ```

## Teach-back check

<details><summary>1. Why keep customer settings in YAML instead of in the code?</summary>

So a new customer means a new settings file, not new code (ADR-004). The same tested code serves every engagement.
</details>

<details><summary>2. Why "forbid unknown keys"?</summary>

A typo should fail loudly at start-up. Silently ignoring it leaves the system running with a default you didn't choose.
</details>

<details><summary>3. Where do secrets live, and why not in engagement.yaml?</summary>

In `.env` locally and Secret Manager in the cloud. engagement.yaml is committed to Git; anything committed should be treated as public.
</details>

## Interview line

"All customer-specific behavior is a validated config file with environment-variable secrets, so onboarding a new customer is configuration, and typos fail fast instead of silently."
