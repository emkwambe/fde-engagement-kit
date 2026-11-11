# ADR-002: Use PostgreSQL + pgvector as the default vector store

- **Status:** Accepted
- **Date:** 2026-11-09
- **Related:** FR-02, FR-06, FR-16, S-06

## Context
We need vector search plus keyword search, metadata filters, the customer's relational data, and agent checkpoints. Enterprise customers usually already run Postgres and prefer not to add a new vendor for a pilot.

## Options
1. **pgvector** — one database for vectors, full-text, relational data, checkpoints; available on Cloud SQL, RDS, Azure Postgres.
2. **Pinecone / Weaviate (managed)** — scale and features, but extra vendor, cost, and data-residency review.
3. **FAISS / Chroma** — great locally, not a shared multi-replica service by themselves.

## Decision
pgvector with an HNSW index (cosine distance) and a GIN full-text index for hybrid search. Vector-store access goes through an interface so FAISS/Chroma (local) and Pinecone (future) adapters can be added.

## Consequences
- ✅ One managed service in each cloud; simplest IaC.
- ✅ Hybrid search with SQL — easy to explain.
- ⚠️ At very large scale (tens of millions of vectors, high QPS) a dedicated vector DB may be better — revisit per engagement.
