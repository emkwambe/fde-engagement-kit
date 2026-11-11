# 03 - The database

Component: PostgreSQL 16 + pgvector, `deploy/sql/*.sql`, `core/db/migrate.py`, role `agent_ro`

<!-- Color key: NOTE (blue) = INTENT/Why, IMPORTANT (purple) = CONTEXT/When-Where, TIP (green) = ACTION/How, WARNING (yellow) = RESULT/What, CAUTION (red) = RESULT of a break-it practicum -->

## At a glance

| What | When | How | Why |
|---|---|---|---|
| Postgres + pgvector split into ops, kb, agent and etl schemas | Storing business data, document vectors, agent state and load history | Numbered append-only migrations; a read-only least-privilege role for the agent | Reproducible schema everywhere, and safety enforced by the database, not the prompt |

## ELI10

A database is a **library with very organized shelves**. We split our library into four rooms (called **schemas**):

| Room | What's in it |
|---|---|
| `ops` | The customer's business records: customers, orders, shipments |
| `kb` | The knowledge base: policy documents cut into pages, plus their "number fingerprints" (embeddings) |
| `agent` | The AI's notebook: approvals and an audit log |
| `etl` | The loading log: every time data was loaded, how much, and what was rejected |

**Migrations** are numbered building instructions (`001_...sql`, `002_...sql`). The database remembers which ones it has already followed, so running `migrate` twice is safe. Rule: never rewrite instructions that were already followed; add a new numbered one instead.

The AI gets a special **library card** (`agent_ro`) that only lets it *read* the `ops` room, and can't even open the other rooms. Even if the AI is tricked into trying to delete something, the card won't allow it.

## Practicums

Color key: blue = **INTENT (Why?)**, purple = **CONTEXT (When / where?)**, green = **ACTION (How?)**, yellow = **RESULT (What?)**.

### Practicum 1

> [!NOTE]
> **INTENT - Why?** "Which building instructions has this database followed?"

> [!IMPORTANT]
> **CONTEXT - When / where?** After Day 1, including the mid-sprint fix.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> docker compose exec postgres psql -U fde -d fde -tAc "SELECT filename FROM public.schema_migrations ORDER BY 1"
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> 001_schemas.sql
> 002_kb.sql
> 003_ops_logistics.sql
> 004_agent_etl.sql
> 005_kb_engagement_keys.sql
> 005 FIXED a design bug without editing 002. Anyone's database, old or new,
> ends up in the same state by replaying the list in order.
> ```

### Practicum 2

> [!NOTE]
> **INTENT - Why?** "What can the agent's own database account read?"

> [!IMPORTANT]
> **CONTEXT - When / where?** Role agent_ro: SELECT on the ops schema only, read-only transactions, 5 s timeout. Day 2's SQL tool connects with it.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> docker compose exec postgres psql -U agent_ro -d fde -tAc "SELECT count(*) FROM ops.orders"
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> 500
> It can read the 500 orders. It can't write, and it can't open the kb, agent
> or etl rooms (phase 2 shows those refusals).
> ```

## Teach-back check

<details><summary>1. Why did we add migration 005 instead of fixing 002?</summary>

Databases that already ran 002 would never see the fix: migrations run once. A new numbered migration reaches every database, old and new.
</details>

<details><summary>2. Why is the read-only rule enforced by a database role and not by the prompt?</summary>

Prompts can be ignored or manipulated (prompt injection). A database permission can't be talked out of.
</details>

<details><summary>3. What does pgvector add to Postgres?</summary>

A `vector` column type, distance operators like `<=>` (cosine distance) and fast indexes (HNSW), so similarity search runs inside the same database as everything else.
</details>

## Interview line

"The agent connects with a read-only, least-privilege database role, and schema changes ship as append-only numbered migrations, so safety and reproducibility are enforced by the platform, not by convention."
