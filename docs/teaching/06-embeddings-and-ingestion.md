# 06 - Turning words into numbers

Component: embeddings (`core/llm/factory.py`), `core/ingest/documents.py` (`ingest_documents`)

<!-- Color key: NOTE (blue) = INTENT/Why, IMPORTANT (purple) = CONTEXT/When-Where, TIP (green) = ACTION/How, WARNING (yellow) = RESULT/What, CAUTION (red) = RESULT of a break-it practicum -->

## At a glance

| What | When | How | Why |
|---|---|---|---|
| Turning chunks into vectors and storing them in pgvector | On first load and whenever documents change | Hash each document, skip unchanged ones, batch-embed, replace old chunks completely | Cheap re-runs, no stale chunks, validated vector sizes |

## ELI10

Computers can't compare meanings, but they're great at comparing numbers. An **embedding** turns a piece of text into a list of numbers: a **map coordinate** for its meaning. Texts about similar things land close together on the map; unrelated texts land far apart. Our map has 1,536 directions instead of 2, but the idea is the same as "close on the map = similar".

**Ingestion** is filing every index card from note 05 onto the map:

1. Read each document and take its **fingerprint** (a hash). If the fingerprint hasn't changed since last time, skip it: no work, no cost.
2. If it changed, cut it into cards, turn **all** its cards into coordinates in one trip (a batch), throw away the old cards, and store the new ones.

Practice mode uses a pretend map (`HashingFakeEmbeddings`) that only notices shared words. The real OpenAI map understands meaning, including synonyms.

## Practicums

Color key: blue = **INTENT (Why?)**, purple = **CONTEXT (When / where?)**, green = **ACTION (How?)**, yellow = **RESULT (What?)**.

### Practicum 1

> [!NOTE]
> **INTENT - Why?** "Show me that similar sentences get similar numbers."

> [!IMPORTANT]
> **CONTEXT - When / where?** Practice-mode embeddings (word-hash based), 1,536 numbers per text.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> uv run python -c "from core.llm.factory import HashingFakeEmbeddings as H; import numpy as np; e=H(1536); a,b,c,d=(np.array(e.embed_query(t)) for t in ['Gold customer late delivery credit','credit for a late Gold delivery','weather force majeure storm','the shipment was delayed']); print(len(a), round(float(a@b),3), round(float(a@c),3), round(float(a@d),3))"
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> 1536 0.73 0.0 0.0
> Same words, reordered: 0.73 (close). Unrelated: 0.0 (far).
> "the shipment was delayed" means the same as "late delivery" but scores 0.0:
> the practice map only sees shared WORDS. A real embedding model would score
> it high. That's why final quality is measured with real models (Day 3).
> ```

### Practicum 2

> [!NOTE]
> **INTENT - Why?** "Run ingestion twice. What does the second run cost?"

> [!IMPORTANT]
> **CONTEXT - When / where?** 20 documents, knowledge base empty before the first run.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> .\tasks.ps1 ingest; .\tasks.ps1 ingest
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> [docs] seen=20 skipped=0  chunks_upserted=70
> [docs] seen=20 skipped=20 chunks_upserted=0
> Second run: zero embedding calls, zero cost. With 5,000 documents and 3
> changed, only those 3 would be re-embedded.
> ```

### Practicum 3

> [!NOTE]
> **INTENT - Why?** "A customer updates one policy. What happens?"

> [!IMPORTANT]
> **CONTEXT - When / where?** Add a section to claims-process.md, re-ingest, then undo.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> Add-Content engagements\demo-logistics\data\docs\claims-process.md "`n## Escalation`nEscalate unresolved claims after 5 business days."
> .\tasks.ps1 ingest
> git checkout -- engagements\demo-logistics\data\docs\claims-process.md   # undo
> .\tasks.ps1 ingest
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> [docs] seen=20 skipped=19 chunks_upserted=5   (changed file: 4 old sections + 1 new)
> [docs] seen=20 skipped=19 chunks_upserted=4   (after undo: back to 4)
> Only the changed document is re-embedded, and its old cards are replaced,
> never left behind as stale duplicates.
> ```

### Practicum 4

> [!NOTE]
> **INTENT - Why?** "How big is each map coordinate, and how many are stored?"

> [!IMPORTANT]
> **CONTEXT - When / where?** Embedding model dimension is set in engagement.yaml (1536).

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> docker compose exec postgres psql -U fde -d fde -tAc "SELECT vector_dims(embedding), count(*) FROM kb.chunks WHERE engagement='demo-logistics' GROUP BY 1"
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> 1536|70
> 70 chunks, 1,536 numbers each. Switching to a model with a different size
> means re-ingesting everything: the ingestion code checks this and stops with
> an "Embedding size mismatch" error instead of storing broken data.
> ```

## Teach-back check

<details><summary>1. What is an embedding, in one sentence?</summary>

A list of numbers that places a text on a "meaning map", so texts with similar meaning are close together.
</details>

<details><summary>2. Why hash the whole document before doing anything else?</summary>

To skip unchanged documents. Embedding costs money and time; the hash makes re-runs nearly free (idempotent).
</details>

<details><summary>3. Why delete-then-insert a changed document instead of updating chunks one by one?</summary>

The new version may have fewer or different chunks. Deleting the document cascades to ALL its old chunks, so no stale chunk survives to give wrong answers.
</details>

## Interview line

"Ingestion is hash-gated and batched: unchanged documents cost nothing, changed ones are fully replaced so no stale chunks remain, and embedding dimensions are validated before anything is stored."
