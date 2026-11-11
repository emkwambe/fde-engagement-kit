# 05 - Cutting books into pages

Component: `core/ingest/chunking.py` (`split_markdown`, `count_tokens`)

<!-- Color key: NOTE (blue) = INTENT/Why, IMPORTANT (purple) = CONTEXT/When-Where, TIP (green) = ACTION/How, WARNING (yellow) = RESULT/What, CAUTION (red) = RESULT of a break-it practicum -->

## At a glance

| What | When | How | Why |
|---|---|---|---|
| Cutting documents into section-sized, token-limited chunks | Before embedding any document | Split by headings, pack paragraphs to a token budget, overlap consecutive chunks | Precise citations, no mixed topics, no fact cut in half |

## ELI10

Suppose your teacher says "find the rule about late homework" and hands you a 300-page book. You'd want it cut into **index cards**, each about one topic, with the chapter name written at the top. Then you only read the few cards that matter.

AI search works the same way. We cut each document into **chunks** (cards):

- **Never across a chapter.** A card never mixes two headings, so every card can say exactly where it came from (`sla-policy.md#credits`).
- **Not too big.** AI models measure text in **tokens** (word pieces, roughly 3/4 of a word each), and each card has a token budget (800).
- **A little overlap.** Each new card repeats the last few lines of the previous card, so a sentence that falls on the cut is never lost in half.

## Practicums

Color key: blue = **INTENT (Why?)**, purple = **CONTEXT (When / where?)**, green = **ACTION (How?)**, yellow = **RESULT (What?)**.

### Practicum 1

> [!NOTE]
> **INTENT - Why?** "How does the SLA policy get cut up?"

> [!IMPORTANT]
> **CONTEXT - When / where?** sla-policy.md has a title and 4 sections; budget 800 tokens, overlap 100.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> uv run python -c "from core.ingest.chunking import split_markdown, count_tokens; from pathlib import Path; [print(c.ordinal, repr(c.section), count_tokens(c.text)) for c in split_markdown(Path('engagements/demo-logistics/data/docs/sla-policy.md').read_text(encoding='utf-8'), 800, 100)]"
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> 0 'Service Level Agreement (SLA) Policy' 24
> 1 'Delivery Commitments' 104
> 2 'Credits' 77
> 3 'Exclusions' 48
> 4 'Claim Window' 38
> One card per section: each is far under 800 tokens, and headings are never mixed.
> ```

### Practicum 2

> [!NOTE]
> **INTENT - Why?** "Show me the overlap with my own eyes."

> [!IMPORTANT]
> **CONTEXT - When / where?** One long section, tiny budget (60 tokens, overlap 15) to force several cards.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> uv run python -c "from core.ingest.chunking import split_markdown; d='## Alpha\n\n' + ' '.join(f'The carrier scanned pallet {i} at the hub.' for i in range(30)); cs=split_markdown(d, 60, 15); print(len(cs), 'chunks'); print('END  :', ' '.join(cs[0].text.split()[-6:])); print('START:', ' '.join(cs[1].text.split()[:6]))"
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> 7 chunks
> END  : at the hub. The carrier scanned
> START: The carrier scanned pallet 3 at
> The words "The carrier scanned" end card 0 AND start card 1: that's the overlap.
> ```

### Practicum 3

> [!NOTE]
> **INTENT - Why?** "Are tokens the same as words?"

> [!IMPORTANT]
> **CONTEXT - When / where?** Budgets are counted in tokens because that's what models are billed and limited by.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> uv run python -c "from core.ingest.chunking import count_tokens; print(count_tokens('The carrier scanned the pallet.'))"
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> 7   (for 5 words)
> Punctuation and word pieces count too. Never size chunks by word count.
> ```

### Practicum 4

> [!NOTE]
> **INTENT - Why?** "How many cards does the whole knowledge base make?"

> [!IMPORTANT]
> **CONTEXT - When / where?** 20 policy documents.

> [!TIP]
> **ACTION - How?**
>
> ```powershell
> .\tasks.ps1 ingest   # on an empty knowledge base
> ```

> [!WARNING]
> **RESULT - What happened, and what does it mean?**
>
> ```text
> [docs] seen=20 skipped=0 chunks_upserted=70
> About 3.5 cards per document: small documents, one card per section.
> ```

## Teach-back check

<details><summary>1. Why never let a chunk cross a heading?</summary>

So every chunk belongs to one section and its citation points to a precise place. Mixed chunks also embed as a blurry "average" of two topics and match neither well.
</details>

<details><summary>2. Why is a long paragraph split into pieces of (chunk_size - overlap)?</summary>

Because the next card will start with up to `overlap` tokens copied from the previous one. Leaving that room means "overlap + piece" still fits the budget.
</details>

<details><summary>3. How would you choose 800/100 for a real customer?</summary>

Don't guess: run the evals (Day 3) at several sizes and keep the one with the best retrieval hit-rate.
</details>

## Interview line

"I chunk by document structure first, then pack paragraphs to a token budget with overlap, so every chunk is citable to one section and no fact is cut in half, and I tune the size with retrieval evals."
