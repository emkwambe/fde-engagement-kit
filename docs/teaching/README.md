# Teaching Notes

> The best way to know something deeply is to teach it.

Every component of this project gets a teaching note: an ELI10 explanation proved with hands-on **ICAR practicums**. **The author writes the notes**, because writing the explanation, choosing the practicums and running them is the learning. Claude builds and tests components, provides hints, and reviews each draft against the rubric below.

Rule from Day 2 on: a component is not "done" until its teaching note is written and reviewed.

## The method: ELI10 inside ICAR

Each note has the same shape (copy [TEMPLATE.md](TEMPLATE.md)):

1. **ELI10:** what it is, in plain words, with an everyday analogy.
2. **Practicums:** 3 to 5 hands-on exercises in ICAR format. You choose the intent, run the action, record the real result.
3. **Break it on purpose:** at least one practicum makes the component fail.
4. **Teach-back check:** 3 questions with hidden answers.
5. **Interview line:** one sentence you could say in an interview.

Short form if you prefer: **what** it is, **when** you need it, **how** it works, **why** it's built this way. The practicums are still required.

### ICAR format

```text
$ practicum start

[INTENT]  The question or task, in quotes, as someone would ask it
[CONTEXT] The situation: what is running, what data exists, what just happened
[ACTION]  The exact PowerShell command you ran, from the project folder
[RESULT]  What actually happened (your real output) and what it means
```

## Rubric (used for every review)

| # | Criterion | Pass when |
|---|---|---|
| 1 | Accurate analogy | The ELI10 analogy matches how the component really works, including its limits |
| 2 | Real results | Every `[RESULT]` is output you actually got, not copied or imagined |
| 3 | Break it on purpose | At least one practicum shows a failure AND explains why the system reacts that way |
| 4 | Explains "why" | Each result ends with what it means, not just what it printed |
| 5 | Teach-back | Questions can be answered from the note alone; answers are correct |
| 6 | Own words | Reads like you explaining it, not like documentation |
| 7 | Interview-ready | The interview line is one sentence, specific, and true for this project |

## The series

| # | Teaching note | Covers | Status |
|---|---|---|---|
| 00 | How this project is run | Charter, scope, WBS, risks, decision log: why a real project needs paperwork | To write |
| 01 | The workbench | PowerShell, `tasks.ps1`, uv, Docker, Git: the tools around the code | To write |
| 02 | Settings in one file | `engagement.yaml`, the config loader, `${ENV}` secrets, fake mode | To write |
| 03 | The database | Postgres, schemas, migrations, the read-only role, why we never edit an applied migration | To write |
| 04 | Messy data in, clean data out | Seed generator and ETL: cleaning, rejecting, de-duplicating, idempotency | To write |
| 05 | Cutting books into pages | Chunking: sections, token budgets, overlap | To write (suggested first) |
| 06 | Turning words into numbers | Embeddings and ingestion: vectors, hashing, batching | To write |
| 07 | Finding the right page | Vector search, full-text search, hybrid with RRF | To write |
| 08 | [Answering with receipts](08-cited-answers.md) | RAG prompt, citations, the "I don't know" gate, prompt injection | Worked example (written by Claude) |
| 09 | [Proving it works](09-tests-and-api.md) | Tests, fakes, acceptance tests, the API | Worked example (written by Claude) |
| 10 | The legacy system | Mock ERP: REST API, OpenAPI contract, auth | Day 2 |
| 11 | Tools from a spec | Tool generator, read-only SQL tool, approval flags | Day 2 |
| 12 | The agent graph | LangGraph: plan, tools, state, checkpoints | Day 2 |
| 13 | Asking permission | Human-in-the-loop approval, `/chat` upgrade | Day 2 |

Name your files like the worked examples: `00-project-governance.md`, `01-workbench.md`, `02-config.md`, `03-database.md`, `04-etl.md`, `05-chunking.md`, `06-embeddings-and-ingestion.md`, `07-search.md`.

## Where to look (hints, not answers)

| # | Read these | A starter intent (pick your own too) | A break-it idea |
|---|---|---|---|
| 00 | `docs/00`, `docs/01`, `docs/07`, `docs/14` | "How do we know this project is done?" | What if a scope change isn't logged? |
| 01 | `tasks.ps1`, `pyproject.toml`, `uv.lock`, `docker-compose.yml`, `.gitattributes` | "Is this computer ready?" | Stop Docker Desktop, then run `.\tasks.ps1 up` |
| 02 | `engagements/demo-logistics/engagement.yaml`, `core/config/` | "Which settings is the project really using?" | Misspell a key in a copy of the YAML |
| 03 | `deploy/sql/`, `core/db/migrate.py` | "What can the agent's account do?" | Try a DELETE as `agent_ro` |
| 04 | `core/ingest/seed.py`, `core/ingest/etl.py`, `etl.runs` table | "Why are there 500 orders, not 506?" | Run ingest twice; count rows |
| 05 | `core/ingest/chunking.py`, `tests/day01/test_chunking.py` | "How is sla-policy.md cut up?" | Set overlap equal to chunk size |
| 06 | `core/ingest/documents.py`, `core/llm/factory.py` | "What does re-ingesting cost?" | Edit one document, re-ingest, undo with `git checkout` |
| 07 | `core/retrieval/search.py`, `scripts/try_search.py` | "Which section mentions Charlotte?" | Search for an order ID; read the scores |

## Review workflow

1. Copy the template: `Copy-Item docs\teaching\TEMPLATE.md docs\teaching\05-chunking.md`
2. Write it, running every action yourself.
3. Paste the whole file into the chat for review; Claude scores it against the rubric.
4. Fix, then commit: `git add docs/teaching; git commit -m "Teaching note 05: chunking"; git push`
