# Data Model

Parent: [Architecture](05-architecture.md) · Related: FR-02–04, FR-08, FR-10

One Postgres 16 database with pgvector, split into schemas so concerns stay separate and permissions stay simple.

| Schema | Purpose | Agent access |
|---|---|---|
| `kb` | Documents, chunks, embeddings (knowledge base) | Via retrieval tool only |
| `ops` | Customer operational tables loaded by ETL (engagement-specific) | `SELECT` only, through `agent_ro` role |
| `agent` | LangGraph checkpoints, approvals, audit log | Service role only |
| `etl` | Ingestion runs and source hashes | Service role only |

## 1. Knowledge base (`kb`)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE kb.documents (
  id            text PRIMARY KEY,           -- stable id, e.g. path or URL
  engagement    text NOT NULL,
  title         text,
  source_uri    text NOT NULL,
  content_hash  text NOT NULL,
  metadata      jsonb DEFAULT '{}',
  ingested_at   timestamptz DEFAULT now()
);

CREATE TABLE kb.chunks (
  id            text PRIMARY KEY,           -- doc_id + ordinal
  document_id   text REFERENCES kb.documents(id) ON DELETE CASCADE,
  engagement    text NOT NULL,
  section       text,
  ordinal       int,
  text          text NOT NULL,
  tsv           tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
  embedding     vector(1536),               -- must match embedding model dimension
  content_hash  text NOT NULL,
  metadata      jsonb DEFAULT '{}'
);

CREATE INDEX ON kb.chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON kb.chunks USING gin (tsv);
CREATE INDEX ON kb.chunks (engagement);
```

## 2. Operational data (`ops`) — engagement #1 example (Northwind Logistics)

```sql
CREATE TABLE ops.customers (customer_id text PRIMARY KEY, name text, tier text, region text);
CREATE TABLE ops.orders (
  order_id text PRIMARY KEY, customer_id text REFERENCES ops.customers,
  created_at timestamptz, promised_at timestamptz, delivered_at timestamptz,
  status text, value_usd numeric(12,2)
);
CREATE TABLE ops.shipments (
  shipment_id text PRIMARY KEY, order_id text REFERENCES ops.orders,
  carrier text, origin text, destination text, last_scan_at timestamptz, last_status text
);
CREATE VIEW ops.sla_breaches AS
  SELECT o.*, (delivered_at - promised_at) AS delay
  FROM ops.orders o WHERE delivered_at > promised_at;
```

## 3. Read-only role

```sql
CREATE ROLE agent_ro LOGIN PASSWORD :'agent_ro_password';
GRANT USAGE ON SCHEMA ops TO agent_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA ops TO agent_ro;
ALTER ROLE agent_ro SET default_transaction_read_only = on;
ALTER ROLE agent_ro SET statement_timeout = '5s';
```

## 4. Agent & ETL tables (summary)

| Table | Key columns |
|---|---|
| `agent.checkpoints` | Managed by LangGraph Postgres checkpointer |
| `agent.approvals` | `id, thread_id, tool, payload jsonb, status, decided_by, decided_at` |
| `agent.audit_log` | `id, thread_id, trace_id, event, detail jsonb, at` |
| `etl.runs` | `id, engagement, source, started_at, finished_at, rows_in, rows_loaded, chunks_upserted, status` |
