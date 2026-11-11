# 04 - Messy data in, clean data out

Component: `core/ingest/seed.py` (synthetic data), `core/ingest/etl.py` (Extract, Transform, Load)

<!-- Color key: NOTE (blue) = INTENT/Why, IMPORTANT (purple) = CONTEXT/When-Where, TIP (green) = ACTION/How, WARNING (yellow) = RESULT/What, CAUTION (red) = RESULT of a break-it practicum -->

## At a glance

| What | When | How | Why |
|---|---|---|---|
| Extract-Transform-Load from messy CSV exports into clean tables | Whenever customer data arrives as files or exports | Clean each field, reject bad rows with reasons, de-duplicate, upsert, log every run | Real data is messy; every row must be explainable; re-runs must be safe |

## ELI10

Imagine a friend dumps a box of trading cards on your desk. Some cards are duplicates, some have smudged dates, one is from a different game entirely. Before you put them in your album you **sort** them: fix what can be fixed, throw out what can't, and write down what you threw out and why.

That's **ETL**: **E**xtract (open the box), **T**ransform (clean and check each card), **L**oad (put them in the album).

Real company data is always messy, so our fake data is messy *on purpose*: tiers written as "GOLD" or "gold ", dates in two formats, prices like "\$1,234.50", 5 duplicate orders, one customer with a tier that doesn't exist ("Bronze"), and one order for a customer who doesn't exist. Running the loader twice must give the same album, never double the cards. That property is called **idempotent**.

## Practicums

Color key: blue = **INTENT (Why?)**, purple = **CONTEXT (When / where?)**, green = **ACTION (How?)**, yellow = **RESULT (What?)**.

### Practicum 1

> [!NOTE]
> **INTENT - Why?** "Load the customer's exports and tell me what happened."

> [!IMPORTANT]
> **CONTEXT - When / where?** Fresh seed: customers.csv (41 rows), orders.csv (506 rows), shipments.csv (500 rows).

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> .\tasks.ps1 seed; .\tasks.ps1 ingest
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> [etl] customers  in=41   loaded=40   duplicates=0   rejected=1
>         rejected: invalid tier 'Bronze'
> [etl] orders     in=506  loaded=500  duplicates=5   rejected=1
>         rejected: unknown customer_id 'C-404'
> [etl] shipments  in=500  loaded=500  duplicates=0   rejected=0
> Every row is accounted for: in = loaded + duplicates + rejected.
> ```

### Practicum 2

> [!NOTE]
> **INTENT - Why?** "Prove the loader is idempotent."

> [!IMPORTANT]
> **CONTEXT - When / where?** Data already loaded once.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> .\tasks.ps1 ingest   # run it a second time
> docker compose exec postgres psql -U fde -d fde -tAc "SELECT count(*) FROM ops.orders"
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> Same counts as the first run, and 500 orders, not 1000.
> Upsert ("insert, or update if the ID exists") makes re-runs safe.
> ```

### Practicum 3

> [!NOTE]
> **INTENT - Why?** "Where's the record of what the loader did?"

> [!IMPORTANT]
> **CONTEXT - When / where?** A customer asks "why is order ORD-9999 missing?" a week later.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> docker compose exec postgres psql -U fde -d fde -c "SELECT source, rows_in, rows_loaded, rows_rejected, detail->>'duplicates' AS dups FROM etl.runs ORDER BY id DESC LIMIT 3"
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> .../shipments.csv | 500 | 500 | 0 | 0
> .../orders.csv    | 506 | 500 | 1 | 5
> .../customers.csv |  41 |  40 | 1 | 0
> The run log (including the rejected rows and reasons) answers the question.
> ```

### Practicum 4

> [!NOTE]
> **INTENT - Why?** "Is ORD-1043 late, and by how much?"

> [!IMPORTANT]
> **CONTEXT - When / where?** The ops.sla_breaches view computes lateness from promised vs delivered time.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> docker compose exec postgres psql -U fde -d fde -c "SELECT order_id, tier, days_late, value_usd FROM ops.sla_breaches WHERE order_id='ORD-1043'"
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> ORD-1043 | Gold | 3 | 4820.00
> Clean data makes this a one-line question. Day 2's agent will ask it.
> ```

## Teach-back check

<details><summary>1. Why make the synthetic data messy on purpose?</summary>

Real exports always are. A loader tested only on clean data breaks on the first real customer file.
</details>

<details><summary>2. Why reject bad rows instead of dropping them silently?</summary>

Silent drops create "missing data" mysteries. Counted rejections with reasons let you explain every row to the customer.
</details>

<details><summary>3. What makes the loader idempotent?</summary>

Upserts keyed on the primary key, plus de-duplication before loading, so running it twice gives the same result.
</details>

## Interview line

"My ETL is idempotent and accountable: every input row is loaded, de-duplicated or rejected with a reason, and each run is logged, so data questions are answerable weeks later."
