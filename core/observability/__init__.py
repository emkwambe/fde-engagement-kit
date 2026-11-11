"""Observability (Day 3 remainder, D-16, NFR-08): know what every request did, how long it took, and what it cost.

Three signals, one id:
  logs     one JSON line per HTTP request (logging.py): route, status, duration, model and tool calls. No prompt text.
  metrics  Prometheus counters and histograms at GET /metrics (metrics.py): rates, latency, tokens, tool use.
  traces   OpenTelemetry spans (tracing.py): request -> agent step -> model call / tool call, with parent links.
The trace id of the request span is the same id that AgentService writes into agent.audit_log.trace_id, so a log line,
a trace and an audit row of one request can be joined.

handler.ObservabilityCallback is a LangChain callback attached to every agent run (core/agent/graph.run_config).
LangChain calls it when a model or tool starts and ends; it feeds all three signals.
"""

from core.observability.context import RequestStats, current_stats, current_trace_id, request_scope
from core.observability.tracing import setup_tracing, tracer

__all__ = ["RequestStats", "current_stats", "current_trace_id", "request_scope", "setup_tracing", "tracer"]
