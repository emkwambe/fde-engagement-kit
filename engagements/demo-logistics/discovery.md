# Discovery — Northwind Logistics (fictional)

| Field | Value |
|---|---|
| Customer | Northwind Logistics (fictional regional 3PL) |
| Champion | "Dana Ruiz", Operations Lead (simulated) |
| FDE | E. Mkwambe |
| Interview dates | 2026-11-09 (simulated) |
| Status | Agreed |

## 1. Problem statement
Northwind's customer-service team of 12 handles about 400 inquiries a week about late or missing shipments. To answer one, an agent checks the shipment in the legacy ERP, looks up the order in the reporting database, and then searches a shared drive of ~20 policy PDFs to find which SLA credit applies. It takes 10–20 minutes per inquiry, answers are inconsistent, and credits are often applied incorrectly, which costs money and customer trust.

## 2. Current workflow (as-is)
1. Customer emails about a late order.
2. Agent looks up the shipment status in the ERP web UI.
3. Agent asks an analyst (or runs a saved report) for order/SLA details.
4. Agent searches the policy drive for the customer's tier and credit rules.
5. Agent opens a ticket in the ERP to request the credit.

Time per task: 10–20 min · Volume: ~400/week · Pain: three systems, slow analyst queue, policy ambiguity.

## 3. Target workflow (to-be)
1. "Where is order ORD-1043 and is it late?"
2. "Which Gold-tier orders breached SLA last week?"
3. "What credit does our policy allow for a 3-day delay for a Gold customer?"
4. "Open a credit ticket for ORD-1043 for the amount the policy allows." → assistant prepares the ticket, agent approves.

## 4. Success metrics
| Metric | Baseline | Pilot target | How measured |
|---|---|---|---|
| Time to resolve a late-order inquiry | 10–20 min | < 3 min | timed sample of 20 inquiries |
| Golden-set eval score | n/a | ≥ 85% | eval harness |
| Correct credit amount | ~80% (est.) | ≥ 95% | golden set credit cases |
| Unsafe actions without approval | n/a | 0 | red-team cases + audit log |

## 5. Systems inventory
| System | Type | Access method | Owner | Sensitivity | Needed for |
|---|---|---|---|---|---|
| Policy drive | Docs | Export to bucket | Ops | Internal | SLA/credit rules |
| Reporting DB | Postgres | Read-only role | Data team | Internal + customer names | Orders, SLA breaches |
| Legacy ERP | REST API (OpenAPI) | Service token | IT | Internal | Shipment status, tickets |

## 6. Actions the assistant may take
| Action | System | R/W | Approval? | Who approves |
|---|---|---|---|---|
| Get shipment status | ERP | Read | No | — |
| Query orders/SLA | DB | Read | No | — |
| Create credit ticket | ERP | Write | **Yes** | Service agent |

## 7. Constraints
- Cloud: GCP, us-east1. LLM: OpenAI approved for pilot.
- No customer PII sent to logs; emails/phones redacted.
- Pilot in 1 week.

## 8. Out of scope for the pilot
Emailing customers directly; changing orders; carrier integrations.

## 9. Risks and open questions
| Item | Owner | Due |
|---|---|---|
| Policy PDFs conflict for legacy contracts | Ops | Pilot week 1 |
| ERP API rate limits unknown | IT | Day 2 |

## 10. Sign-off
| Name | Role | Date |
|---|---|---|
| Dana Ruiz (simulated) | Operations Lead | 2026-11-09 |
| E. Mkwambe | FDE | 2026-11-09 |
