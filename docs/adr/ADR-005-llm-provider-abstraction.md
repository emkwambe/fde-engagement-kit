# ADR-005: OpenAI as default LLM, behind a provider abstraction

- **Status:** Accepted
- **Date:** 2026-11-09
- **Related:** FR-11, FR-15, S-12

## Context
Customers mandate different providers (Azure OpenAI in Microsoft shops, Bedrock on AWS, Vertex on GCP, Anthropic directly). Tests and CI must run without paid keys.

## Decision
- Default: OpenAI chat model and OpenAI embeddings, model names set in `engagement.yaml` (verify current model names and prices at build time).
- All model creation goes through one factory (LangChain `init_chat_model` / embeddings factory) keyed by `provider` + `model`.
- `FAKE_LLM=1` swaps in deterministic fake chat and embedding models for unit tests and CI.

## Consequences
- ✅ Switching provider is a config change; demonstrated at least once (fake ↔ OpenAI, and one other provider if a key is available).
- ⚠️ Embedding dimension changes when switching embedding models → re-ingest required; config validation warns about this.
- ⚠️ Tool-calling behavior differs between models → golden-set evals must be re-run after a switch.
