# 10 - The legacy system

Component: `services/mock-erp/app.py`, `services/mock-erp/openapi.yaml`, `.\tasks.ps1 erp`, `.\tasks.ps1 erp-spec`, `tests/day02/test_mock_erp.py`

<!-- Color key: NOTE (blue) = INTENT/Why, IMPORTANT (purple) = CONTEXT/When-Where, TIP (green) = ACTION/How, WARNING (yellow) = RESULT/What, CAUTION (red) = RESULT of a break-it practicum -->

## At a glance

| What | When | How | Why |
|---|---|---|---|
| A stand-in for the customer's legacy system: a protected REST API | Whenever data or actions live in another system | Bearer-token auth, schema validation, an OpenAPI contract generated from code and a drift test | Integrate through the contract, never around it, so rules and access stay with the system owner |

## ELI10

Think of a **bank**. You never walk into the vault to take money. You go to the **teller window**, show your **card**, and ask using the bank's own forms. The teller checks your card, checks the form is filled in correctly, and only then does what you asked.

Our mock ERP is Northwind's old "legacy" business system, and it works like that bank:

- The **API** is the teller window: the only way in. Nobody (including our AI agent) touches its database.
- The **bearer token** is your card: no card, no service (`401 Unauthorized`).
- The **OpenAPI spec** (`openapi.yaml`) is the printed list of forms the bank accepts: every endpoint, every field, every rule. Our agent will read this list to learn what it is allowed to ask for.
- The **validation rules** are the teller checking the form: a credit above 35% is refused (`422`) before anything happens.

Where the analogy stops: a real teller can use judgment; the ERP only follows its written rules, which is exactly why those rules must be strict.

## Practicums

Color key: blue = **INTENT (Why?)**, purple = **CONTEXT (When / where?)**, green = **ACTION (How?)**, yellow = **RESULT (What?)**.

### Practicum 1

> [!NOTE]
> **INTENT - Why?** "Is the legacy system up?"

> [!IMPORTANT]
> **CONTEXT - When / where?** Mock ERP started with .\tasks.ps1 erp in a second window (port 8100).

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> Invoke-RestMethod http://localhost:8100/health | Format-List
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> status           : ok
> shipments_loaded : 500
> tickets          : 0
> /health is the only endpoint that needs no token: monitoring tools must be able
> to check "is it alive?" without holding business credentials.
> ```

### Practicum 2

> [!NOTE]
> **INTENT - Why?** "Is shipment SHP-2207 stuck?"

> [!IMPORTANT]
> **CONTEXT - When / where?** Customer asks about a late delivery. Token dev-token from .env.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> $auth = @{ Authorization = 'Bearer dev-token' }
> Invoke-RestMethod http://localhost:8100/shipments/SHP-2207 -Headers $auth | Format-List
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> shipment_id  : SHP-2207
> order_id     : ORD-1207
> carrier      : XPO
> origin       : Knoxville, TN
> destination  : Charlotte, NC
> last_scan_at : 11/7/2026 11:00:00 AM
> last_status  : Arrived at hub - Charlotte, NC
> Not stuck: it reached the destination city's hub, so delivery is the next step.
> ERP log: "GET /shipments/SHP-2207 HTTP/1.1" 200 OK
> ```

### Practicum 3

> [!NOTE]
> **INTENT - Why?** "Which shipments are delayed by weather?"

> [!IMPORTANT]
> **CONTEXT - When / where?** The list endpoint filters by text in the carrier's last status.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> $auth = @{ Authorization = 'Bearer dev-token' }
> Invoke-RestMethod "http://localhost:8100/shipments?status_contains=weather&limit=3" -Headers $auth | Select-Object shipment_id, order_id, carrier, last_status
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> SHP-2012  ORD-1012  UPS Freight       Delayed - weather
> SHP-2013  ORD-1013  FedEx Ground      Delayed - weather
> SHP-2025  ORD-1025  Regional Express  Delayed - weather
> 11 in total (limit=100). These may be force majeure cases: no SLA credit owed
> (weather-and-force-majeure.md). The agent will combine this API with that document.
> ```

### Practicum 4

> [!NOTE]
> **INTENT - Why?** "Open a correct credit ticket for ORD-1043."

> [!IMPORTANT]
> **CONTEXT - When / where?** Gold, 3 days late, \$4,820 order: 5% x 3 = 15% = \$723.00 (sla-policy.md#credits).

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> $auth = @{ Authorization = 'Bearer dev-token'; 'X-Client' = 'powershell' }
> $t = @{ order_id='ORD-1043'; customer_id='C-007'; days_late=3; credit_percent=15; credit_amount_usd=723; reason='Gold SLA credit, 3 days late'; priority='P2' } | ConvertTo-Json
> Invoke-RestMethod http://localhost:8100/tickets -Method Post -Headers $auth -ContentType 'application/json' -Body $t | Format-List
> Remove-Item services\mock-erp\data -Recurse -Force   # undo: delete test tickets
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> ticket_id         : TCK-0001
> status            : open
> credit_percent    : 15
> credit_amount_usd : 723
> created_by        : powershell
> The X-Client header records WHO created it (later: the agent, after approval).
> Tickets are saved to services\mock-erp\data\tickets.json, so they survive restarts.
> ```

## Teach-back check

<details><summary>1. Why does the agent use the ERP's API instead of reading its database?</summary>

That's how real enterprises expose systems: the API enforces auth, validation and business rules, and the owner can change the database without breaking us. Reading the database directly would skip every safety rule.
</details>

<details><summary>2. Why is openapi.yaml generated from the code instead of written by hand?</summary>

A hand-written contract drifts from reality. Generating it from the code, plus a test that compares them, guarantees the agent's "list of forms" is always true.
</details>

<details><summary>3. What stops the agent from creating a ticket with nonsense values?</summary>

The ERP's own validation (for example, credit_percent at most 35, order IDs like ORD-1234) returns 422 before anything is saved. On Day 2 a human approval step is added in front of every write as a second layer.
</details>

## Interview line

"I integrate with customer systems only through their API contract: token auth, schema validation and an OpenAPI spec generated from code with a drift test, so the agent's tools always match what the system really accepts."
