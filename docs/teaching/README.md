# Teaching Notes

> The best way to know something deeply is to teach it.

Detailed project documentation written as **lesson notes**. Every component gets one note that explains it in plain words (ELI10) and then proves it with hands-on **ICAR practicums** you can run yourself. Notes are written in build order, starting from Day 0, and a new note ships in the same commit as each new component.

These notes are part of the project documentation (DC-010). They don't change the project objectives: skill development is still the primary objective (see the [charter](../00-project-charter.md)), and the notes are the main study material for it.

## How every note is organized

1. **At a glance:** What / When / How / Why in one table row.
2. **ELI10:** what it is, explained to a curious 10-year-old with an everyday analogy, plus where the analogy stops being true.
3. **Practicums:** hands-on exercises in ICAR format, color-coded (below), showing the component working.
4. **Teach-back check:** questions with hidden answers. Answer out loud before opening.
5. **Interview line:** one sentence you could say in an interview.

**Phase 2 (later):** "break it on purpose" practicums are added to every note once the whole project works (DC-011). Notes 00-02 already contain a few.

## Color key: ICAR and the W questions

Each practicum is a sequence of colored boxes (GitHub alert blocks):

| ICAR part | W question | Box | Color |
|---|---|---|---|
| **INTENT** | **Why?** What do we want to know or do? | `[!NOTE]` | Blue |
| **CONTEXT** | **When / where?** What is running, what just happened? | `[!IMPORTANT]` | Purple |
| **ACTION** | **How?** The exact PowerShell command | `[!TIP]` | Green |
| **RESULT** | **What?** What happened, and what it means | `[!WARNING]` | Yellow |
| **RESULT** of a break-it practicum (phase 2) | **What went wrong, and why is that good or bad?** | `[!CAUTION]` | Red |

> [!NOTE]
> **INTENT - Why?** Example: "Is shipment SHP-2207 stuck?"

> [!IMPORTANT]
> **CONTEXT - When / where?** Example: Mock ERP running on port 8100, token in `.env`.

> [!TIP]
> **ACTION - How?** Example: `Invoke-RestMethod http://localhost:8100/shipments/SHP-2207 -Headers $auth`

> [!WARNING]
> **RESULT - What?** Example: `last_status : Arrived at hub - Charlotte, NC`: not stuck, delivery is next.

Colors show on GitHub. In VS Code's Markdown preview (Ctrl+Shift+V) the boxes still show their labels (INTENT, CONTEXT, ACTION, RESULT) even where colors aren't supported.

## Rules every note follows

- Every RESULT is real output from this project, never invented. Long lines are shortened with `...`, and symbols like dashes or >= are written in plain ASCII. If your output differs, find out why: that's a lesson too.
- Every ACTION is PowerShell, run from `C:\Users\HP\Projects\fde-engagement-kit`.
- Commands that change something show how to undo them (`# undo`).

## The series

| # | Teaching note | Covers | Day |
|---|---|---|---|
| 00 | [How this project is run](00-project-governance.md) | Charter, scope, WBS, risks, decision log: why a real project needs paperwork | 0 |
| 01 | [The workbench](01-workbench.md) | PowerShell, `tasks.ps1`, uv, Docker, Git: the tools around the code | 0 |
| 02 | [Settings in one file](02-config.md) | `engagement.yaml`, the config loader, `${ENV}` secrets, fake mode | 1 |
| 03 | [The database](03-database.md) | Postgres, schemas, migrations, the read-only role, why we never edit an applied migration | 1 |
| 04 | [Messy data in, clean data out](04-etl.md) | Seed generator and ETL: cleaning, rejecting, de-duplicating, idempotency | 1 |
| 05 | [Cutting books into pages](05-chunking.md) | Chunking: sections, token budgets, overlap | 1 |
| 06 | [Turning words into numbers](06-embeddings-and-ingestion.md) | Embeddings and ingestion: vectors, hashing, batching | 1 |
| 07 | [Finding the right page](07-search.md) | Vector search, full-text search, hybrid with RRF | 1 |
| 08 | [Answering with receipts](08-cited-answers.md) | RAG prompt, citations, the "I don't know" gate, prompt injection | 1 |
| 09 | [Proving it works](09-tests-and-api.md) | Tests, fakes, acceptance tests, the API | 1 |
| 10 | [The legacy system](10-mock-erp.md) | Mock ERP: REST API, OpenAPI contract, bearer auth, drift test | 2 |
| 11 | [Tools from a spec](11-tools-from-a-spec.md) | Tool generator, read-only SQL tool, approval flags | 2 |
| 12 | [The agent graph](12-agent-graph.md) | LangGraph: agent loop, routing, approval interrupt, Postgres checkpoints | 2 |
| 13 | Asking permission | Approval API, audit trail, `/chat` upgrade | 2 (next) |

## How to use these notes

- **To learn:** read the ELI10, run every practicum yourself and compare your output, then do the teach-back check without looking.
- **To teach:** walk someone through the practicums live. If you can't answer their "why?", go back to the code.
- **For interviews:** the interview line plus one practicum story per component make strong answers.

## Quality bar (checked before a note is committed)

| # | Criterion | Pass when |
|---|---|---|
| 1 | Accurate analogy | The ELI10 analogy matches how the component really works, including its limits |
| 2 | Real results | Every RESULT was actually produced by running the ACTION in this project |
| 3 | Break it on purpose (phase 2) | At least one practicum shows a failure AND explains why the system reacts that way |
| 4 | Explains "why" | Each result says what it means, not just what it printed |
| 5 | Teach-back | Questions can be answered from the note alone; answers are correct |
| 6 | Plain words | A newcomer can follow it without other documents |
| 7 | Interview-ready | The interview line is one sentence, specific, and true for this project |
