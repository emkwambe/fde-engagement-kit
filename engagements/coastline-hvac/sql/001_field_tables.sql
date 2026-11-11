-- Coastline Climate Services (fictional): reporting tables in their own schema `field`.
-- Engagement-owned DDL (sources.tables[].schema_sql), applied once by core.db.migrate. Idempotent on purpose.
CREATE SCHEMA IF NOT EXISTS field;

CREATE TABLE IF NOT EXISTS field.customers (
  customer_id    text PRIMARY KEY,
  name           text NOT NULL,
  plan           text NOT NULL CHECK (plan IN ('Basic', 'Plus', 'Premium')),
  city           text,
  email          text,
  phone          text,
  contract_start date
);

CREATE TABLE IF NOT EXISTS field.technicians (
  tech_id  text PRIMARY KEY,
  name     text NOT NULL,
  skill    text NOT NULL CHECK (skill IN ('residential', 'commercial', 'refrigeration')),
  on_call  boolean NOT NULL DEFAULT false,
  epa_608  boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS field.equipment (
  equipment_id text PRIMARY KEY,
  customer_id  text NOT NULL REFERENCES field.customers(customer_id),
  kind         text NOT NULL,
  installed_on date
);

CREATE TABLE IF NOT EXISTS field.work_orders (
  work_order_id text PRIMARY KEY,
  customer_id   text NOT NULL REFERENCES field.customers(customer_id),
  equipment_id  text REFERENCES field.equipment(equipment_id),
  priority      text NOT NULL CHECK (priority IN ('emergency', 'routine')),
  opened_at     timestamptz NOT NULL,
  responded_at  timestamptz,
  status        text NOT NULL,
  tech_id       text REFERENCES field.technicians(tech_id),
  after_hours   boolean,
  summary       text
);

-- Work orders answered later than the plan's response time (response-time-sla.md#response-times).
-- hours_late is rounded UP to whole hours; credits are per STARTED 4 hours late (see #credits), computed by the agent.
CREATE OR REPLACE VIEW field.sla_misses AS
SELECT w.work_order_id, w.customer_id, c.plan, w.priority, w.opened_at, w.responded_at, s.sla_hours,
       CEIL(EXTRACT(EPOCH FROM (w.responded_at - w.opened_at)) / 3600 - s.sla_hours)::int AS hours_late
FROM field.work_orders w
JOIN field.customers c USING (customer_id)
JOIN (VALUES ('Basic', 'emergency', 24), ('Basic', 'routine', 72), ('Plus', 'emergency', 8),
             ('Plus', 'routine', 48), ('Premium', 'emergency', 4), ('Premium', 'routine', 24))
     AS s(plan, priority, sla_hours) ON s.plan = c.plan AND s.priority = w.priority
WHERE w.responded_at > w.opened_at + make_interval(hours => s.sla_hours);
