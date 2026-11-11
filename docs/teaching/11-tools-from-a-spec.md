# 11 - Tools from a spec

Component: `core/toolgen/openapi.py`, `core/toolgen/sql.py`, `core/toolgen/registry.py`, `scripts/list_tools.py`, `scripts/try_tools.py`, `tests/day02/test_toolgen.py`

<!-- Color key: NOTE (blue) = INTENT/Why, IMPORTANT (purple) = CONTEXT/When-Where, TIP (green) = ACTION/How, WARNING (yellow) = RESULT/What, CAUTION (red) = RESULT of a break-it practicum -->

## At a glance

| What | When | How | Why |
|---|---|---|---|
| Agent tools generated from each system's OpenAPI spec, plus a guarded read-only SQL tool | Onboarding a new system, or giving the agent abilities | Read the spec, copy names, arguments and rules into tools; flag writes for approval; validate and limit SQL | Reuse through config, rules carried over automatically, writes always need a human |

## ELI10

Imagine a new helper joins a shop. Nobody has time to train them on every machine, but each machine comes with a **printed instruction card**: what it does, which buttons exist, and the rules ("never set the oven above 250"). The helper reads the cards and instantly knows how to use every machine, safely.

Our **tool generator** is that helper. It reads the ERP's instruction card (`openapi.yaml`) and turns every operation into a **tool** the AI agent can use:

- The tool's **name** comes from the card (`getShipment`, `createTicket`, ...).
- The tool's **buttons** (arguments) and their **rules** (pattern, minimum, maximum, allowed values) are copied from the card, so a wrong request is stopped before it ever reaches the ERP.
- Anything that **changes** something (a POST, like `createTicket`) gets a sticker: **"ask a human first"**.

There's also one hand-made tool, `query_ops_db`, which lets the agent ask the database questions in SQL. It may only **read**: one SELECT at a time, a row limit, and a read-only database account.

Where the analogy stops: a human helper might notice a card is wrong; the generator trusts the card completely, which is why note 10's drift test keeps the card truthful.

## Practicums

Color key: blue = **INTENT (Why?)**, purple = **CONTEXT (When / where?)**, green = **ACTION (How?)**, yellow = **RESULT (What?)**.

### Practicum 1

> [!NOTE]
> **INTENT - Why?** "Which tools does the agent get, and which ones need approval?"

> [!IMPORTANT]
> **CONTEXT - When / where?** engagement.yaml lists the ERP spec and the SQL tool. Nothing is hand-coded per customer.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> uv run python scripts/list_tools.py
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> 5 tools for demo-logistics
> tool            source   call                           approval  arguments
> query_ops_db    sql      SELECT ops                     no        query
> getShipment     openapi  GET /shipments/{shipment_id}   no        shipment_id
> listShipments   openapi  GET /shipments                 no        order_id, status_contains, limit
> createTicket    openapi  POST /tickets                  YES       order_id, customer_id, days_late, ...
> getTicket       openapi  GET /tickets/{ticket_id}       no        ticket_id
> Four tools came straight from the ERP's spec. Only the POST is flagged for approval,
> because engagement.yaml says require_approval: [POST, PUT, PATCH, DELETE].
> ```

### Practicum 2

> [!NOTE]
> **INTENT - Why?** "Use a generated tool exactly as the agent will: where is SHP-2207?"

> [!IMPORTANT]
> **CONTEXT - When / where?** Mock ERP running (.\tasks.ps1 erp in a second window). Token and URL come from .env.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> uv run python scripts/try_tools.py getShipment '{"shipment_id": "SHP-2207"}'
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> {"shipment_id":"SHP-2207","order_id":"ORD-1207","carrier":"XPO",...,
>  "last_status":"Arrived at hub - Charlotte, NC"}
> The tool built the URL /shipments/SHP-2207, added the bearer token and an
> X-Client: fde-agent header, and returned the ERP's answer as text for the model.
> ```

### Practicum 3

> [!NOTE]
> **INTENT - Why?** "Is ORD-1043 late? Ask the database, not the documents."

> [!IMPORTANT]
> **CONTEXT - When / where?** Note 07 showed document search can't find order IDs. Order data lives in ops tables.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> uv run python scripts/try_tools.py query_ops_db '{"query": "SELECT order_id, tier, days_late, value_usd FROM sla_breaches WHERE order_id = ''ORD-1043''"}'
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> {"columns": ["order_id", "tier", "days_late", "value_usd"],
>  "rows": [["ORD-1043", "Gold", 3, 4820.0]], "row_count": 1, "truncated": false}
> Gold, 3 days late, $4,820. Combined with sla-policy.md#credits (5% per day),
> the agent can compute the credit: 15% = $723.00.
> (In PowerShell, a ' inside a '...' string is written twice: ''ORD-1043''.)
> ```

### Practicum 4

> [!NOTE]
> **INTENT - Why?** "How many orders breached their SLA?"

> [!IMPORTANT]
> **CONTEXT - When / where?** The tool description lists every table and column, so the model knows sla_breaches exists.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> uv run python scripts/try_tools.py query_ops_db '{"query": "SELECT count(*) AS late_orders FROM sla_breaches"}'
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> {"columns": ["late_orders"], "rows": [[96]], "row_count": 1, "truncated": false}
> 96 of 500 orders were late. Every query is wrapped with a row limit and runs as the
> read-only agent_ro account, so the agent can explore data without risk.
> ```

## Teach-back check

<details><summary>1. Why generate tools from the OpenAPI spec instead of writing them by hand?</summary>

A new customer system becomes agent tools by adding its spec to engagement.yaml, with no new code. The tools also inherit the system's own rules (pattern, minimum, maximum, enum), so they can never disagree with what the system accepts.
</details>

<details><summary>2. Why are the Authorization and X-Client headers not tool arguments?</summary>

Credentials and identity are set by our code from configuration, never chosen by the model. The model can't leak, change or forge them.
</details>

<details><summary>3. Name the three safety layers of the SQL tool.</summary>

(1) A validator allows only one SELECT/WITH statement with no write keywords. (2) Every query is wrapped with a row limit. (3) It connects as agent_ro, a read-only account with a 5-second timeout that can only see the ops schema.
</details>

<details><summary>4. Why do tools return errors as data instead of crashing?</summary>

So the agent can read the problem ("Shipment SHP-0000 not found", status 404) and recover, for example by asking the user for the correct ID, instead of the whole conversation failing.
</details>

## Interview line

"The agent's tools are generated from each system's OpenAPI contract plus a guarded read-only SQL tool, so onboarding a new system is configuration, validation rules carry over automatically, and every write is flagged for human approval."
