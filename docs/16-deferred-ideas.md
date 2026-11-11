# Deferred Ideas

Parent: [Scope section 6 (change control)](01-scope-statement.md#6-change-control) · Rule: CLAUDE.md rule 10

New ideas that come up during a sprint go here as proposals, **never into code**. An idea is approved only by the
sponsor, at its decision gate, and then gets a DC row and a place in a sprint brief. Until then it is deferred.

## Template (copy for each idea)

```markdown
## <Letter>. <Name>                                   Status: deferred, not approved (DC-0xx)

### Problem and evidence
What is wrong or missing today, with file references and numbers.

### Real use cases
Who needs it, in which industry, how often.

### Workplace dynamics
Actors and roles; triggers; rules; hand-offs; edge cases: absence, conflict, abuse, timeouts.

### Success measures
Numbers that would show it works.

### Risks and kill criteria
What could go wrong; when we stop.

### Size
Effort, dependencies, which kit parts are reused.

### Decision gate
What must be true before the sponsor approves it.
```

## Index

| Idea | Status | Recorded in |
|---|---|---|
| A. Role-based approval routing | Deferred, not approved | DC-016 |
| B. Scenario Builder agent | Deferred, not approved | DC-016 |

---

## A. Role-based approval routing                   Status: deferred, not approved (DC-016)

### Problem and evidence

Today **any** person who can reach the API can approve **any** paused write, whatever its size.

- `POST /approvals/{thread_id}/approve` takes a free-text `by` field (`core/api/main.py`, `Decision` model). Nothing checks
  who that person is or what they may approve. The audit log records the name, but cannot prove it.
- The customer's own process says otherwise. `engagements/demo-logistics/data/docs/claims-process.md#steps` step 5:
  "A team lead approves tickets above $1,000." `escalation-matrix.md#levels`: team lead for credits above $1,000,
  operations manager for repeated failures for one customer in 30 days, VP of Operations for Platinum accounts and legal threats.
- Two golden cases already produce writes above that line: q-019 (`credit_amount_usd` 1322.31) and q-020 (1407.52).
  In a real deployment a customer-service agent could approve both. That is a policy breach the kit makes easy.
- The kit's promise is config over code, so the rules belong in `engagement.yaml`, not in an `if amount > 1000` in `core/`.

### Real use cases

| Who | Industry | How often |
|---|---|---|
| Customer-service leads approving credits | Logistics, retail, telecom (credits, refunds) | Daily; tens to hundreds per day at mid-size companies |
| Dispatch supervisors approving after-hours call-outs | Field service (HVAC, utilities) | Several per night shift |
| Finance approving vendor payments or write-offs | Any company with an ERP | Weekly batches plus urgent one-offs |
| Clinical managers approving schedule overrides | Healthcare operations | Daily |

### Workplace dynamics

- **Actors and roles.** Requester (the user who asked the agent), the agent (prepares the payload), approvers with roles
  (agent, team lead, ops manager, VP), an auditor (reads the trail), a system admin (maintains the role table).
- **Triggers.** A paused write. Routing reads the payload: amount, customer tier, tool name, and history
  ("second credit for this customer in 30 days").
- **Rules (config).** An ordered list in `engagement.yaml`, for example
  `{tool: createTicket, when: "credit_amount_usd > 1000", role: team_lead}`, first match wins, a default role last.
- **Separation of duties.** The requester can never approve their own request, even if their role allows it.
- **Hand-offs.** The approval appears only in the queues of people who hold the role; a lead can re-assign to a peer.
- **Edge cases.**
  - *Absence:* the only team lead is on leave. Delegation: a named stand-in for a date range, recorded in the audit log.
  - *Timeout:* nobody decides within N business hours (claims-process.md#turnaround says tickets must be opened within
    2 business days). Escalate one level up and notify; never auto-approve.
  - *Conflict:* two approvers click at once. Already solved: the atomic claim (`AgentService._claim`) lets one win, the other gets 409.
  - *Amount changes:* if the agent re-plans and the payload changes after a partial review, the approval is invalidated
    and routing runs again (approve the exact arguments, never "the ticket").
  - *Abuse:* someone splits a $3,000 credit into three $999 tickets to stay under the line. Rule on the sum per order or
    customer within a window; flag repeats to the ops manager.

### Success measures

- 100% of writes above a threshold are approved by a holder of the required role (audit query, zero exceptions).
- 0 self-approvals in the audit log.
- Median time-to-decision does not grow by more than 20% against today's single queue.
- Every timeout escalates within 1 hour of its deadline (test with a fake clock).
- New red-team golden cases (self-approval, split tickets) pass at 100%.

### Risks and kill criteria

- Real identity is needed: without SSO the `by` field is still a claim. Risk: building role logic on unproven identity.
  Kill or postpone if SSO/OIDC is not in scope for the same phase (charter section 5 puts SSO out of scope).
- Rule language grows into a programming language. Kill criterion: if the rules cannot be expressed as simple comparisons
  on payload fields, stop and use the customer's existing workflow tool instead (ServiceNow, Jira).
- Approvers learn to rubber-stamp. Measure decision time; very short times on large amounts are a signal.

### Size

About 2-3 days: config schema for roles and rules (0.5 d), routing on pause plus queue filtering (1 d), delegation and
timeout escalation with a scheduler (1 d), tests, golden cases and a teaching note (0.5 d).
Depends on: an identity provider (or a signed header from a gateway). Reuses: `agent.approvals`, the atomic claim,
the audit log, the console's approval buttons, and the golden-set approval check.

### Decision gate

Approve only when: (1) the sponsor decides authentication is in scope, (2) one real customer process (like
claims-process.md) has been mapped into rules and reviewed by the person who owns that process, and (3) the
deployed basics of this sprint (CI, container, Cloud Run) are done.

---

## B. Scenario Builder agent                         Status: deferred, not approved (DC-016)

### Problem and evidence

Every new engagement needs a consistent set of synthetic material before anything can be demonstrated: policy documents,
tables with deliberate mess, a mock API with an OpenAPI contract, and a golden set whose expected facts match the data.

- For engagement #1 this took most of Day 1 and Day 2 (`core/ingest/seed.py` before Sprint 01, 20 documents in
  `engagements/demo-logistics/data/docs/`, `services/mock-erp/`). Engagement #2 in this sprint repeats the same work.
- Consistency is the hard part. Golden facts depend on seeded numbers: q-004 expects `credit_amount_usd` 723.0, which only
  holds because `ORD-1043` is pinned to $4,820.00 and exactly 3 days late in the seed. A generator that drifts silently
  breaks the evals.
- Discovery notes (`engagements/<name>/discovery.md`) already describe the customer's process in prose. Turning that into
  data, documents and cases is mostly mechanical, and mechanical work is where people make consistency mistakes.

### Real use cases

| Who | Industry | How often |
|---|---|---|
| FDEs preparing a pilot before real data access is approved | Any; especially regulated (health, finance) where access takes weeks | Every new engagement |
| Pre-sales engineers building a tailored demo | Software vendors | Weekly |
| Trainers building practice environments | Any | Per course |

### Workplace dynamics

- **Actors and roles.** The FDE (writes the discovery notes, runs the builder), the customer's subject-matter expert
  (SME, reviews), the builder agent (drafts), the eval owner (accepts the golden set).
- **Trigger.** A discovery doc reaches "reviewed" status.
- **Rules.** The builder only writes into the engagement folder; it never touches `core/`. Everything it produces is a
  draft until the SME approves it. This is the kit's own approval gate, reused: generation pauses for a human.
- **Hand-offs.** FDE to builder (discovery doc), builder to SME (documents and golden cases as a review list),
  SME to FDE (corrections), FDE to eval owner (frozen golden set).
- **Edge cases.**
  - *Absence:* SME unavailable. The golden set stays in draft and cannot gate a release. No silent approval.
  - *Conflict:* SME disagrees with a generated policy rule. The SME's wording wins; the generator regenerates dependent cases.
  - *Abuse:* someone generates golden cases that the current agent already passes, to inflate the score. Mitigation: the
    eval owner signs off on cases before the first real run, and case hashes make later edits visible.
  - *Timeout:* review not done before the pilot date. The pilot runs with the reviewed subset only, and says so.

### Success measures

- Time from reviewed discovery doc to first fake eval run: under 2 hours (Sprint 01's engagement #2 timing is the baseline,
  see teaching note 21).
- 100% of golden expected facts are derivable from the generated data (a consistency check that runs the SQL behind each fact).
- SME correction rate below 20% of generated documents after two engagements.

### Risks and kill criteria

- Generated documents can look plausible and be wrong about the domain. Kill criterion: if SMEs reject more than 40% of
  drafts in two engagements, stop and go back to templates.
- Tests generated by the same model that is tested reward its own blind spots. The eval owner's review is mandatory.
- Cost: generation uses the real model. Budget per scenario must be capped like evals.

### Size

About 3-4 days: a schema for a "scenario spec" (0.5 d), generators for tables and documents with seeded anchors (1.5 d),
a golden-case drafter with the consistency check (1 d), SME review flow using the approval queue (0.5 d), a note (0.5 d).
Depends on: the generic table specs and engagement-owned seed scripts from Sprint 01 Phase 3a. Reuses: the approval
interrupt, the golden-set schema and loader, the ETL, the mock-API pattern.

### Decision gate

Approve only when: (1) two engagements exist (this sprint), so the common shape is known from evidence, not guessed,
(2) the sponsor agrees on a per-scenario budget, and (3) a real SME (or a stand-in with domain knowledge) is available to
review at least one generated scenario.
