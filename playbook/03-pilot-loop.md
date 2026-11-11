# Pilot Loop

Run weekly (or every few days) during a pilot.

```
Collect → Triage → Add to golden set → Fix → Re-eval → Release → Report
```

1. **Collect** — user feedback (thumbs up/down + comment), failed traces, support requests.
2. **Triage** each failure into one bucket:
   | Bucket | Typical fix |
   |---|---|
   | Retrieval miss (right doc not found) | Chunking, metadata filters, hybrid weights, missing source |
   | Generation error (doc found, answer wrong) | Prompt, model tier, answer format |
   | Tool error (wrong tool / bad arguments) | Tool descriptions, OpenAPI summaries, examples |
   | Data issue (source wrong or stale) | Customer data owner; ETL fix |
   | Out of scope | Document; decline gracefully |
3. **Add** each real failure as a golden case (anonymized).
4. **Fix** the smallest thing that resolves the bucket.
5. **Re-eval** — the full golden set must not regress.
6. **Release** through CI/CD.
7. **Report** to the champion:

| Week | Eval score | Safety pass | Weekly users | Top issue | Action |
|---|---|---|---|---|---|
| 1 | | | | | |
