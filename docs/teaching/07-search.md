# 07 - Finding the right page

Component: `core/retrieval/search.py` (vector, full-text, hybrid with RRF), `scripts/try_search.py`

<!-- Color key: NOTE (blue) = INTENT/Why, IMPORTANT (purple) = CONTEXT/When-Where, TIP (green) = ACTION/How, WARNING (yellow) = RESULT/What, CAUTION (red) = RESULT of a break-it practicum -->

## At a glance

| What | When | How | Why |
|---|---|---|---|
| Finding the most relevant chunks: vector, full-text and hybrid | Every question the system answers | pgvector cosine distance plus Postgres full-text, fused with Reciprocal Rank Fusion | Meaning and exact words both matter; fusion needs no score normalization |

## ELI10

You lost your dog in the park and ask two friends to help.

- **Friend 1 (vector search)** is great at *ideas*: you say "a fluffy brown animal" and they point at a teddy-bear-shaped bush and a golden retriever. They understand meaning, but they might miss exact details.
- **Friend 2 (full-text search)** is great at *exact words*: you say "the dog's tag says REX" and they only look for tags reading REX. Precise, but no imagination.

**Hybrid search** asks both friends for their top list, then gives points by position: 1st place earns the most, 2nd a bit less, and so on. Anything near the top of **both** lists wins. That point system is called **Reciprocal Rank Fusion (RRF)**: score = 1/(60 + position), added up across both lists. It only uses positions, so we never have to compare Friend 1's "confidence" with Friend 2's: they speak different languages.

## Practicums

Color key: blue = **INTENT (Why?)**, purple = **CONTEXT (When / where?)**, green = **ACTION (How?)**, yellow = **RESULT (What?)**.

### Practicum 1

> [!NOTE]
> **INTENT - Why?** "Which section mentions Regional Express delays in Charlotte?"

> [!IMPORTANT]
> **CONTEXT - When / where?** 70 chunks ingested; carrier-notes-q3.md has a Summary section (mentions Charlotte) and an Actions section (mentions Regional Express only).

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> uv run python scripts/try_search.py "Regional Express Charlotte"
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> VECTOR ONLY: 1. carrier-notes-q3.md  Actions  score=0.365
>              2. carrier-notes-q3.md  Summary  score=0.311
> HYBRID:      1. carrier-notes-q3.md  Summary  score=0.033
>              2. carrier-notes-q3.md  Actions  score=0.016
> Summary is the only section with ALL three words, so full-text ranks it 1st.
> Being high on both lists nearly doubles its RRF score (0.033), and hybrid
> puts the correct section first.
> ```

### Practicum 2

> [!NOTE]
> **INTENT - Why?** "What credit does a Gold customer get per day late?"

> [!IMPORTANT]
> **CONTEXT - When / where?** 70 chunks ingested from the 20 policy documents.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> uv run python scripts/try_search.py "What credit does a Gold customer get per day late?"
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> VECTOR ONLY: 1. sla-policy.md  Credits  score=0.463 sim=0.463
>              2. legacy-contracts.md  Legacy Credit Terms  score=0.379
> HYBRID:      1. sla-policy.md  Credits  score=0.016 sim=0.463
> Both agree on #1. Note legacy-contracts.md at #2: it has DIFFERENT Gold
> terms (4%/day). A good answer should mention the conflict.
> ```

## Teach-back check

<details><summary>1. Give an example where vector search alone fails.</summary>

Exact identifiers and names: order IDs, product codes, "Charlotte". Embeddings blur exact tokens; full-text matches them precisely.
</details>

<details><summary>2. Why RRF instead of adding the two scores together?</summary>

Cosine similarity (0 to 1) and text rank (unbounded) aren't on the same scale. RRF only uses positions, so no normalization is needed.
</details>

<details><summary>3. In hybrid mode, why does each result still carry a `similarity`?</summary>

The RRF score says where a chunk ranked, not how relevant it is. The answer step needs real similarity to decide "I don't know".
</details>

## Interview line

"I use hybrid retrieval, pgvector cosine plus Postgres full-text fused with Reciprocal Rank Fusion, because embeddings miss exact identifiers and keyword search misses meaning."
