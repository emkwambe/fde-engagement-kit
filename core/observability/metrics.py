"""Prometheus metrics, served at GET /metrics in the text format Prometheus scrapes.

Counters only go up; Prometheus computes rates from them ("requests per second over 5 minutes").
Histograms count observations into buckets, so p95 latency can be computed later without storing every request.
Labels are kept LOW-cardinality on purpose: route templates ("/approvals/{thread_id}/approve"), never raw paths or
thread ids, otherwise every conversation would create a new time series.
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram

HTTP_REQUESTS = Counter("fde_http_requests_total", "HTTP requests handled", ["method", "route", "status"])
HTTP_SECONDS = Histogram("fde_http_request_duration_seconds", "HTTP request duration", ["route"],
                         buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 4, 8, 16, 32, 64))
MODEL_CALLS = Counter("fde_model_calls_total", "Chat model calls made by the agent", ["model"])
MODEL_TOKENS = Counter("fde_model_tokens_total", "Tokens reported by the model provider", ["model", "direction"])
TOOL_CALLS = Counter("fde_tool_calls_total", "Agent tool calls", ["tool", "outcome"])
APPROVALS = Counter("fde_approvals_total", "Writes that needed a human, by outcome", ["outcome"])
GUARDRAIL_BLOCKS = Counter("fde_guardrail_blocks_total", "Guardrail interventions", ["kind"])
