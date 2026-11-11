# 13 - Asking permission

Component: `core/agent/service.py`, `core/api/main.py`, `ui/index.html`, `scripts/ask_agent.py`, `tasks.ps1` (`api` task), `tests/day02/test_approvals_api.py`

<!-- Color key: NOTE (blue) = INTENT/Why, IMPORTANT (purple) = CONTEXT/When-Where, TIP (green) = ACTION/How, WARNING (yellow) = RESULT/What, CAUTION (red) = RESULT of a break-it practicum -->

## At a glance

| What | When | How | Why |
|---|---|---|---|
| The agent behind an HTTP API: chat, a queue of writes waiting for approval, approve/reject endpoints, an audit trail, and a small web console | Whenever people (or other systems) use the agent, not just a developer at a terminal | AgentService runs every turn and records it in agent.approvals and agent.audit_log; decisions are claimed with one atomic UPDATE; FastAPI exposes it all | Enterprise customers need to know who approved what, when and why, and a double click must never create two tickets |

## ELI10

Note 12 built a game with a referee who freezes the board when a red card is played. This note adds the **office around the game**:

- A **front desk** (the API). Anyone can walk up and ask a question (`POST /chat`).
- An **in-tray** (`GET /approvals`). Every frozen red card lands there, with its exact details, until a manager deals with it.
- A **rubber stamp** with two sides: APPROVED and REJECTED (`/approve`, `/reject`). Rejecting requires a written reason.
- A **logbook** (the audit log). The receptionist writes down every step: who asked, which tools were used, who stamped what, and when. Private conversations aren't copied into the logbook word for word. It records only "a 67-letter message arrived" plus a fingerprint (a hash).
- Only **one stamp per paper**. If two managers grab the same paper at the same moment, the first one wins and the second is told "already decided".

Where the analogy stops: a real in-tray can't be in two offices at once. Ours can, because it lives in Postgres, so several copies of the API (Cloud Run replicas) share the same tray and logbook.

## Practicums

Color key: blue = **INTENT (Why?)**, purple = **CONTEXT (When / where?)**, green = **ACTION (How?)**, yellow = **RESULT (What?)**.

Before you start: Postgres up (`.\tasks.ps1 up`), mock ERP running (`.\tasks.ps1 erp`), and `FAKE_LLM=1`. Start the API in a third window with `.\tasks.ps1 api`. It opens the agent console in your browser.

### Practicum 1

> [!NOTE]
> **INTENT - Why?** "Is the API up, and where does it keep conversation state?"

> [!IMPORTANT]
> **CONTEXT - When / where?** The API window shows "Uvicorn running on http://127.0.0.1:8000".

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> Invoke-RestMethod http://localhost:8000/health
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> status       : ok
> engagement   : demo-logistics
> llm_provider : fake
> database     : True
> checkpointer : postgres
> "postgres" means paused conversations survive an API restart. If the database is down at
> startup, the API still starts, with checkpointer "memory (database unreachable)" and
> status "degraded": it works, but nothing is saved or audited, and /health says so.
> ```

### Practicum 2

> [!NOTE]
> **INTENT - Why?** "Ask for a write over HTTP. What does a client get back?"

> [!IMPORTANT]
> **CONTEXT - When / where?** The same request as note 12, now through POST /chat. The client chooses the thread id.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> $body = @{ thread_id = 'api-demo'; message = 'Open a credit ticket for ORD-1043 for the amount the policy allows.'; user = 'HP' } | ConvertTo-Json
> $turn = Invoke-RestMethod http://localhost:8000/chat -Method Post -ContentType 'application/json' -Body $body
> $turn.status
> $turn.pending.args
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> needs_approval
> order_id          : ORD-1043
> customer_id       : C-007
> days_late         : 3
> credit_percent    : 15
> credit_amount_usd : 723
> reason            : Gold SLA credit: 3 days late x 5% = 15% [sla-policy.md#credits]
> priority          : P3
> The HTTP request finished at once. It didn't wait for a human. The answer says
> "needs_approval" and shows exactly what would be sent to the ERP, so a UI can display it.
> ```

### Practicum 3

> [!NOTE]
> **INTENT - Why?** "What is waiting for a decision right now, across all conversations?"

> [!IMPORTANT]
> **CONTEXT - When / where?** AgentService wrote a row to agent.approvals when the graph paused.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> Invoke-RestMethod http://localhost:8000/approvals | Format-Table id, thread_id, tool, created_at
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> id thread_id tool         created_at
> -- --------- ----         ----------
> 22 api-demo  createTicket 11/11/2026 06:19:36
> This is the approver's in-tray. (Your id is different: it is a database counter.)
> ```

### Practicum 4

> [!NOTE]
> **INTENT - Why?** "Approve it, then click Approve a second time. Do we get two tickets?"

> [!IMPORTANT]
> **CONTEXT - When / where?** decide() first claims the approval with UPDATE ... WHERE status = 'pending'. Only one request can change that row.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> $decision = @{ by = 'HP' } | ConvertTo-Json
> $done = Invoke-RestMethod http://localhost:8000/approvals/api-demo/approve -Method Post -ContentType 'application/json' -Body $decision
> $done.status
> $done.answer
> Invoke-RestMethod http://localhost:8000/approvals/api-demo/approve -Method Post -ContentType 'application/json' -Body $decision
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> done
> ORD-1043 (Gold, customer C-007) was 3 day(s) late on a $4,820.00 order. Created ticket TCK-0002
> for a 15% credit ($723.00) [sla-policy.md#credits].
> Invoke-RestMethod: ...
>      |  {   "detail": "Thread api-demo has nothing waiting for approval." }
> The second click got HTTP 409 Conflict and nothing ran: one approval, one ticket.
> (Your ticket number depends on how many tickets you created before.)
> ```

### Practicum 5

> [!NOTE]
> **INTENT - Why?** "Can an auditor reconstruct what happened, without us storing private text?"

> [!IMPORTANT]
> **CONTEXT - When / where?** engagement.yaml has guardrails.log_prompts: false.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> $audit = Invoke-RestMethod http://localhost:8000/threads/api-demo/audit
> $audit | ForEach-Object { $_ } | Select-Object @{n='trace';e={$_.trace_id.Substring(0,8)}}, event | Format-Table
> $audit[0].detail
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> trace    event
> -----    -----
> 94580a9a user_message
> 94580a9a tool_call
> 94580a9a tool_result
> 94580a9a tool_call
> 94580a9a tool_result
> 94580a9a tool_call
> 94580a9a approval_requested
> 4ae1eb79 approval_decided
> 4ae1eb79 tool_result
> 4ae1eb79 answer
>
> user chars sha256
> ---- ----- ------
> HP      67 218dec0e5d4ab0a3
> Two trace ids = two HTTP requests (the chat, then the approval), linked by the thread id.
> The user's message is stored as its length + a hash, not the text. Tool calls and arguments
> ARE stored: they are the actions an auditor must be able to see.
> ```

### Practicum 6

> [!NOTE]
> **INTENT - Why?** "What does a non-technical user see?"

> [!IMPORTANT]
> **CONTEXT - When / where?** The browser tab opened by `.\tasks.ps1 api` (or go to http://localhost:8000).

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> Start-Process http://localhost:8000
> # In the page: type your name, click the example "Open a credit ticket for ORD-1043 ...", click Send,
> # read the yellow "Waiting for your approval" card, then click Approve.
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> WAITING FOR YOUR APPROVAL
> createTicket wants to run with: { "order_id": "ORD-1043", ... "credit_amount_usd": 723, ... }
> [Reason (required to reject)]  [Approve]  [Reject]
> AGENT
> ORD-1043 (Gold, customer C-007) was 3 day(s) late on a $4,820.00 order. Created ticket TCK-0003 ...
> The page is one HTML file calling the same endpoints as practicums 2-4. Reject only works
> after a reason of 3+ characters is typed, and the API enforces the same rule (HTTP 422).
> ```

## Teach-back check

<details><summary>1. Why does the API return "needs_approval" immediately instead of waiting for the human?</summary>

An approval can take minutes or days. An HTTP request can't stay open that long, and the server may restart in between. The graph's state is saved by the Postgres checkpointer, so the approval is a separate, later request that resumes it.
</details>

<details><summary>2. How do we guarantee one approval creates exactly one ticket?</summary>

decide() first runs UPDATE agent.approvals SET status = ... WHERE thread_id = ... AND status = 'pending' RETURNING id. The database lets only one request change that row. A second request gets no rows back, so it's refused with 409 before the graph is touched. If resuming the graph fails, the claim is put back to pending.
</details>

<details><summary>3. What goes into the audit log, and what deliberately does not?</summary>

In: who asked, every tool call with its arguments, tool results (truncated), the approval request, who decided and why, and a trace id per request. Not in (with log_prompts: false): the text of user messages and answers. Only their length and a SHA-256 fingerprint are kept, because they may contain customer personal data.
</details>

<details><summary>4. Why do the API and the CLI both go through AgentService?</summary>

So the rules (record the pause, claim the decision, audit every step) live in one place. A second door that skipped them would be an unaudited way to approve writes.
</details>

## Interview line

"Writes pause into an approvals queue exposed over the API; a decision is claimed atomically in Postgres so a double click can't create two tickets, and every request leaves an audit trail with trace ids that records actions but not customer text."
