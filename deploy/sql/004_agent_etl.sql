CREATE TABLE IF NOT EXISTS agent.approvals (
  id          bigserial PRIMARY KEY,
  thread_id   text NOT NULL,
  tool        text NOT NULL,
  payload     jsonb NOT NULL,
  status      text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
  decided_by  text,
  decided_at  timestamptz,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent.audit_log (
  id         bigserial PRIMARY KEY,
  thread_id  text,
  trace_id   text,
  event      text NOT NULL,
  detail     jsonb NOT NULL DEFAULT '{}',
  at         timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS etl.runs (
  id               bigserial PRIMARY KEY,
  engagement       text NOT NULL,
  source           text NOT NULL,
  started_at       timestamptz NOT NULL DEFAULT now(),
  finished_at      timestamptz,
  rows_in          int,
  rows_loaded      int,
  rows_rejected    int,
  chunks_upserted  int,
  status           text NOT NULL DEFAULT 'running',
  detail           jsonb NOT NULL DEFAULT '{}'
);
