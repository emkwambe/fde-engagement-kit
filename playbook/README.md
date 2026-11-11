# FDE Engagement Playbook

The repeatable method for applying this kit to a **real** customer situation. The code is the reusable part; this playbook makes the *delivery* reusable.

```
Discover → Secure access → Configure → Baseline eval → Pilot loop → Hand off
  (01)          (02)         (kit)        (kit)          (03)          (04)
```

| Phase | Typical duration (real engagement) | Output |
|---|---|---|
| 1. Discover | 1–3 days | `engagements/<name>/discovery.md` signed off by customer champion |
| 2. Secure access | 1–5 days (often the longest wait) | Completed [data access checklist](02-data-access-checklist.md) |
| 3. Configure | 0.5–2 days | `engagement.yaml`, OpenAPI specs, ingestion run |
| 4. Baseline eval | 0.5–1 day | Golden set written **with** the customer; baseline report |
| 5. Pilot loop | 1–4 weeks | Weekly eval trend, fixes, user feedback → [pilot loop](03-pilot-loop.md) |
| 6. Hand off | 1–2 days | [Handoff package](04-handoff-template.md) |

## Starting a new engagement
```powershell
Copy-Item -Recurse engagements\_template engagements\<customer-slug>
# 1. fill discovery.md with the customer
# 2. complete the data access checklist
# 3. edit engagement.yaml, add specs/, data/ (or point at real sources)
# 4. write evals/golden.jsonl with the customer
.\tasks.ps1 ingest -Engagement <customer-slug>
.\tasks.ps1 eval   -Engagement <customer-slug>   # this is your baseline
```

## Feasibility check — is this kit the right fit?
Good fit when the customer problem is mostly:
- ✅ "Find answers in our documents" (RAG)
- ✅ "Answer questions about our data" (SQL)
- ✅ "Do routine actions in our systems" (APIs with approval)
- ✅ Any combination of the above

Needs extension work (`extensions/` folder or core change):
- ⚠️ Systems with no API and no export (screen-scraping, RPA)
- ⚠️ Real-time streaming data
- ⚠️ Strict on-prem/air-gapped deployment with no hosted LLM (needs a self-hosted model provider)

Not a fit: predictive ML/forecasting problems, model training, image/video analysis as the core need.
