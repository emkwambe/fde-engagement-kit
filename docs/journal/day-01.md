# Learning Journal - Day 1 (2026-11-10)

> Draft written with Claude from the session record. Rewrite each explanation in your own words before committing the final version - that rewrite is the learning step.

## Skills worked on
S-01, S-03, S-04, S-05, S-06, S-07, S-08 (see [skills matrix](../03-skills-matrix.md))

## How the work was split
- Setup code (config, migrations, seed data, ETL, API shell) was written by Claude (DC-006).
- RAG core (chunking, ingestion, search, answer) was also provided by Claude as complete files at my request (DC-007).
  My job for these four files: read them until I can explain every line, then cold-rebuild one on Day 5.

## What I built / ran
- Local stack on Windows: Docker Postgres + pgvector, `tasks.ps1` task runner, uv environment.
- Messy synthetic data loaded by ETL: 40 customers, 500 orders, 500 shipments; 2 bad rows rejected with reasons, 5 duplicates removed.
- 20 policy documents -> 70 chunks -> pgvector; re-ingest skips all 20 (idempotent).
- Vector + hybrid (RRF) search; `/chat` returns cited answers and says "I don't know" below the similarity threshold.
- 39 tests green; milestone M1 reached.

## Explain it in 5 sentences (as if to an interviewer)

**Chunking**
1. I split markdown by heading first, so every chunk belongs to exactly one section and citations can point to it.
2. Inside a section I pack whole paragraphs greedily until the next one would exceed the token budget.
3. When a chunk closes, the next one starts with the last ~100 tokens of it, so facts on a boundary appear whole somewhere.
4. A paragraph that is too big on its own is split by words into pieces of chunk_size minus overlap, leaving room for the overlap.
5. I would tune 800/100 with evals: measure retrieval hit-rate at several sizes and keep the best.

**Ingestion**
1. Each document is hashed; if the stored hash matches, it is skipped, so re-ingesting 5,000 docs with 3 changes only re-embeds 3.
2. A changed document is deleted and re-inserted; ON DELETE CASCADE removes its old chunks, so no stale chunks remain.
3. All chunks of a document are embedded in one batch call to save cost and avoid rate limits.
4. Rows are keyed by (engagement, id) so two customers can both have a file called sla-policy.md.
5. The function never commits; the caller owns the transaction, so a failure leaves the database unchanged.

**Search**
1. Vector search orders chunks by cosine distance with pgvector's `<=>` operator, backed by an HNSW index.
2. Full-text search uses Postgres tsvector and websearch_to_tsquery, which match exact tokens like names and codes.
3. Hybrid mode fuses the two rankings with Reciprocal Rank Fusion: score = sum of 1/(60 + rank).
4. RRF uses only rank positions, so cosine scores and text-rank scores never need to be normalized.
5. Example: "Regional Express Charlotte" - vector search ranked the Actions section first, hybrid correctly ranked the Summary section (the only one mentioning Charlotte) first.

**Cited answer**
1. The question is embedded, top-k chunks are retrieved, and the best cosine similarity is checked against min_score (0.3).
2. Below the threshold the API answers "I couldn't find this" without calling the LLM - cheaper and avoids hallucinating.
3. Otherwise the system message holds the rules and the human message holds the question, then CONTEXT with each chunk labelled by its citation ref.
4. The prompt tells the model the context is data, not instructions - the first defence against the injection planted in carrier-notes-q3.md.
5. The response returns the answer, deduplicated citations in rank order, and a confidence score.

## What confused me, and how I resolved it
- Pasted code into the test file by mistake -> restored the test file from the original zip; lesson: check the target path before replacing a file.
- Browser download didn't land in Downloads -> switched to PowerShell here-strings that write files directly.
- A design bug in the setup code (kb rows keyed by file name only) would let one engagement overwrite another -> fixed with a new migration (005), not by editing an applied one.
- "LF will be replaced by CRLF" warnings are harmless line-ending conversion from .gitattributes.

## One thing I'd do differently
- Read the tests before touching any code - they are the real specification.

## Open questions -> backlog
- How do real OpenAI embeddings change the scores and the right min_score? (run with FAKE_LLM=0)
- Should hybrid search weight vector and full-text rankings differently?

## Confidence today (1-5) per skill
| Skill | Level |
|---|---|
| S-05 Embeddings & chunking | |
| S-06 Vector DBs & semantic search | |
| S-07 RAG | |
| S-08 Prompt engineering | |
