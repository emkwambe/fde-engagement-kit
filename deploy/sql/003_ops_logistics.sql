-- Operational tables for the demo-logistics engagement (loaded by core/ingest/etl.py).
CREATE TABLE IF NOT EXISTS ops.customers (
  customer_id text PRIMARY KEY,
  name        text NOT NULL,
  tier        text NOT NULL CHECK (tier IN ('Standard','Silver','Gold','Platinum')),
  region      text,
  email       text,
  phone       text
);

CREATE TABLE IF NOT EXISTS ops.orders (
  order_id     text PRIMARY KEY,
  customer_id  text NOT NULL REFERENCES ops.customers(customer_id),
  created_at   timestamptz NOT NULL,
  promised_at  timestamptz NOT NULL,
  delivered_at timestamptz,
  status       text NOT NULL,
  value_usd    numeric(12,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS ops.shipments (
  shipment_id  text PRIMARY KEY,
  order_id     text NOT NULL REFERENCES ops.orders(order_id),
  carrier      text NOT NULL,
  origin       text,
  destination  text,
  last_scan_at timestamptz,
  last_status  text
);

CREATE OR REPLACE VIEW ops.sla_breaches AS
SELECT o.order_id, o.customer_id, c.tier, o.promised_at, o.delivered_at, o.value_usd,
       CEIL(EXTRACT(EPOCH FROM (o.delivered_at - o.promised_at)) / 86400)::int AS days_late
FROM ops.orders o JOIN ops.customers c USING (customer_id)
WHERE o.delivered_at > o.promised_at;
