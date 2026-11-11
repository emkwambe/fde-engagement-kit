# 00 - How this project is run

Component: charter, scope, WBS, risk register, decision log (`docs/00` to `docs/15`)

<!-- Color key: NOTE (blue) = INTENT/Why, IMPORTANT (purple) = CONTEXT/When-Where, TIP (green) = ACTION/How, WARNING (yellow) = RESULT/What, CAUTION (red) = RESULT of a break-it practicum -->

## At a glance

| What | When | How | Why |
|---|---|---|---|
| Charter, scope, risk register and decision log for the project | Before building (charter, scope) and every day (risks, decisions) | Measurable success criteria, an explicit out-of-scope list, logged decisions with reasons | So everyone agrees what "done" means and every choice can be explained later |

## ELI10

Imagine building a treehouse with friends. Before anyone picks up a hammer, you agree on three things: **why** you're building it (a place to read), **what's in and what's out** (a roof yes, a swimming pool no), and **how you'll know it's finished** (four walls, a roof, a ladder). Then you keep a notebook: every time you change the plan ("let's use rope instead of a ladder"), you write down what changed and why.

That's all project documents are. The **charter** is the "why" and "how we know we're done". The **scope** is "what's in and out". The **risk register** is "what could go wrong and what we'll do about it". The **decision log** is the notebook. Customers trust an engineer who keeps that notebook, because when something goes wrong months later, the notebook explains why things are the way they are.

## Practicums

Color key: blue = **INTENT (Why?)**, purple = **CONTEXT (When / where?)**, green = **ACTION (How?)**, yellow = **RESULT (What?)**, red = **RESULT of a break-it practicum**.

### Practicum 1

> [!NOTE]
> **INTENT - Why?** "How will we know this project succeeded?"

> [!IMPORTANT]
> **CONTEXT - When / where?** Day 0. Nothing is built yet; the charter is the agreed plan.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> Select-String -Path docs\00-project-charter.md -Pattern '\| SC-0'
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> 7 success criteria, SC-01 to SC-07: skills at target, reuse proven,
> eval score >= 85%, deployed on Cloud Run, `.\tasks.ps1 demo` works in
> <= 15 min, docs complete, budget within the cap.
> Every one is measurable: "done" is a checklist, not a feeling.
> ```

### Practicum 2

> [!NOTE]
> **INTENT - Why?** "Can we also add AWS and Azure Terraform this week?"

> [!IMPORTANT]
> **CONTEXT - When / where?** Day 3. A reviewer suggests more clouds. Time box is fixed at one week.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> Select-String -Path docs\01-scope-statement.md -Pattern 'AWS and Azure'
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> "AWS and Azure Terraform modules | Time box; GCP proves the pattern | Yes - v1.1"
> It's explicitly OUT of scope and parked in the backlog. Scope change control
> says: log it, swap it for equal effort, or defer it. Answer: "Great idea, v1.1."
> ```

### Practicum 3

> [!NOTE]
> **INTENT - Why?** "Why are the knowledge-base tables keyed by engagement AND id?"

> [!IMPORTANT]
> **CONTEXT - When / where?** Day 1. A design bug was found mid-sprint: two customers with a file called sla-policy.md would overwrite each other.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> Select-String -Path docs\14-decision-and-change-log.md -Pattern 'DC-008'
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> "DC-008 | Decision | Knowledge-base tables keyed by (engagement, id) via new
> migration 005; applied migrations are never edited | Two engagements with the
> same file name overwrote each other ..."
> Six months from now, nobody has to guess. The notebook answers.
> ```

### Practicum 4 (break it on purpose: a thought experiment)

> [!NOTE]
> **INTENT - Why?** "What happens without a risk register?"

> [!IMPORTANT]
> **CONTEXT - When / where?** Day 1. The RAG code was provided rather than hand-written, which threatens the main goal (learning).

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> Select-String -Path docs\status\day-01.md -Pattern 'R-02'
> ```

> [!CAUTION]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> "R-02 | Raised: RAG core code was provided, not hand-written | Journal
> explanations in own words; Day 5 cold rebuild of chunking or search"
> Because the risk was written down WITH a response, it becomes an action
> (teach-back notes, cold rebuild) instead of a silent problem found on Day 5.
> ```

## Teach-back check

<details><summary>1. What's the difference between the charter and the scope statement?</summary>

The charter says **why** and **how we know we're done** (objectives, success criteria, budget). The scope statement says **exactly what gets built and what doesn't** (deliverables, exclusions, change control).
</details>

<details><summary>2. Why log small decisions, not just big ones?</summary>

Small decisions are the ones nobody remembers. Months later, "why is it like this?" is answered in seconds instead of hours, and you look trustworthy to the customer.
</details>

<details><summary>3. What makes a success criterion good?</summary>

It's measurable and checkable by someone else: "eval score >= 85% in CI", not "the AI works well".
</details>

## Interview line

"I run every engagement with a short charter, an explicit out-of-scope list and a decision log, so the customer and I always agree on what 'done' means and why each choice was made."
