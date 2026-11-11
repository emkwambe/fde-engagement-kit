-- Knowledge-base rows are unique per engagement, not globally.
-- Two customers can both have a "sla-policy.md"; without this, ingesting one overwrites the other.
-- kb.* is derived data (rebuilt by ingestion), so it is safe to drop and recreate here.
DROP TABLE IF EXISTS kb.chunks;
DROP TABLE IF EXISTS kb.documents;

CREATE TABLE kb.documents (
  engagement    text NOT NULL,
  id            text NOT NULL,
  title         text,
  source_uri    text NOT NULL,
  content_hash  text NOT NULL,
  metadata      jsonb NOT NULL DEFAULT '{}',
  ingested_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (engagement, id)
);

CREATE TABLE kb.chunks (
  engagement    text NOT NULL,
  id            text NOT NULL,
  document_id   text NOT NULL,
  section       text,
  ordinal       int  NOT NULL,
  text          text NOT NULL,
  tsv           tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
  embedding     vector({{EMBEDDING_DIM}}) NOT NULL,
  content_hash  text NOT NULL,
  metadata      jsonb NOT NULL DEFAULT '{}',
  PRIMARY KEY (engagement, id),
  FOREIGN KEY (engagement, document_id) REFERENCES kb.documents (engagement, id) ON DELETE CASCADE
);

CREATE INDEX chunks_embedding_hnsw ON kb.chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX chunks_tsv_gin        ON kb.chunks USING gin (tsv);
