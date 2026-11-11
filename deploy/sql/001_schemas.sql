-- Schemas separate concerns and permissions (docs/06-data-model.md).
CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS kb;     -- knowledge base: documents, chunks, embeddings
CREATE SCHEMA IF NOT EXISTS ops;    -- customer operational data loaded by ETL
CREATE SCHEMA IF NOT EXISTS agent;  -- checkpoints, approvals, audit log
CREATE SCHEMA IF NOT EXISTS etl;    -- ingestion run history

CREATE TABLE IF NOT EXISTS public.schema_migrations (
  filename   text PRIMARY KEY,
  applied_at timestamptz NOT NULL DEFAULT now()
);
