-- {{EMBEDDING_DIM}} is replaced by migrate.py with embeddings.dimensions from engagement.yaml.
CREATE TABLE IF NOT EXISTS kb.documents (
  id            text PRIMARY KEY,
  engagement    text NOT NULL,
  title         text,
  source_uri    text NOT NULL,
  content_hash  text NOT NULL,
  metadata      jsonb NOT NULL DEFAULT '{}',
  ingested_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS kb.chunks (
  id            text PRIMARY KEY,
  document_id   text NOT NULL REFERENCES kb.documents(id) ON DELETE CASCADE,
  engagement    text NOT NULL,
  section       text,
  ordinal       int  NOT NULL,
  text          text NOT NULL,
  tsv           tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
  embedding     vector({{EMBEDDING_DIM}}) NOT NULL,
  content_hash  text NOT NULL,
  metadata      jsonb NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw ON kb.chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_tsv_gin        ON kb.chunks USING gin (tsv);
CREATE INDEX IF NOT EXISTS chunks_engagement     ON kb.chunks (engagement);
