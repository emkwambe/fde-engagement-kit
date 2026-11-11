# Discovery - Coastline Climate Services (fictional)

Simulated engagement #2 (D-18). All people, data and documents are invented. The name is fictional: real HVAC companies
with similar names exist (web search 2026-11-11), so it is always written with "(fictional)".

| Field | Value |
|---|---|
| Customer | Coastline Climate Services (fictional): residential and light-commercial HVAC maintenance, 3 coastal cities |
| Champion (name, role) | "Dana Ruiz" (fictional), Dispatch Operations Manager |
| FDE | E. Mkwambe (simulated interview written by Claude) |
| Interview dates | 2026-11-11 (simulated) |
| Status | Agreed (simulated sign-off) |

## 1. Problem statement
"Our dispatchers answer the same three questions all day: is this customer's call covered and how fast must we get
there, did we miss the response time and what credit do we owe, and who can go right now. The answers are spread over a
contracts binder, the reporting database and the CMMS screen. A dispatcher spends 10-15 minutes per escalated call, we
get about 120 such calls a week, and credits are calculated by hand, often wrongly."

## 2. Current workflow (as-is)
1. Customer calls; dispatcher finds the service plan (Basic / Plus / Premium) in the reporting DB.
2. Dispatcher looks up the response-time SLA and fee rules in the PDF binder.
3. Dispatcher opens the work order in the CMMS, checks status and technician.
4. For a missed SLA, dispatcher computes the credit by hand and emails billing.
5. For an emergency, dispatcher phones the on-call technician and creates a dispatch in the CMMS.

Time per task today: 10-15 min · Volume per week: about 120 escalated calls · Pain points: wrong credits, slow
after-hours dispatch, policy questions to the manager.

## 3. Target workflow (to-be)
1. "What response time does a Premium customer get for an emergency?"
2. "Did work order WO-5017 miss its SLA, and what credit do we owe?"
3. "What is the status of WO-5003?"
4. "Dispatch the on-call technician to WO-5040 with the right after-hours fee." (a write: a human approves first)
5. "Which open emergency work orders does customer CU-004 have?"

## 4. Success metrics (agreed with champion)
| Metric | Baseline | Pilot target | How measured |
|---|---|---|---|
| Time to answer an SLA or credit question | 10-15 min | < 2 min | user timing sample |
| Answer correctness on golden set | n/a | >= 85% | eval harness (real model) |
| Red-team cases handled safely | n/a | 100% | eval harness |
| Dispatches created without a human approval | n/a | 0 | audit log |

## 5. Systems inventory
| System | Type | Access method | Owner | Sensitivity | Needed for |
|---|---|---|---|---|---|
| Policy binder (SLA, warranty, fees, escalation, privacy) | docs | Markdown export | Operations | Internal | Policy answers with citations |
| Reporting database (customers, technicians, equipment, work orders) | DB | Read-only SQL (schema `field`) | IT | Contains customer PII (email, phone) | Plans, SLA misses, counts |
| CMMS (work-order system) | API | REST + OpenAPI, bearer token | Field Ops vendor | Internal | Live work-order status, dispatch |

## 6. Actions the assistant may take
| Action | System | Read / Write | Approval required? | Who approves |
|---|---|---|---|---|
| Look up a work order / list work orders | CMMS | Read | No | - |
| Query the reporting database | DB | Read (SELECT only, read-only role) | No | - |
| Create a dispatch (assign a technician) | CMMS | Write (POST) | **Yes** | Dispatcher on shift |

## 7. Constraints
- Data residency: US only. Provider: OpenAI is acceptable for the pilot (switchable by config).
- Customer emails and phone numbers must never reach the model or logs (redact email, phone).
- The CMMS rejects after-hours fees above $150 and dispatches to technicians who are not on call outside hours.

## 8. Out of scope for the pilot
- Scheduling optimisation, parts ordering, invoicing, customer-facing chat.
- Role-based approval routing (see docs/16 idea A).

## 9. Risks and open questions
| Item | Owner | Due |
|---|---|---|
| Vendor notes in the binder contain text aimed at "AI assistants" (found by scan_docs): ask Ops to remove it | Operations | Before go-live |
| Credit rules for contracts signed before 2025 differ (legacy terms) | Contracts | Pilot week 2 |

## 10. Sign-off
| Name | Role | Date |
|---|---|---|
| "Dana Ruiz" (fictional) | Dispatch Operations Manager | 2026-11-11 (simulated) |
