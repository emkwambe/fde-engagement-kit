"""OpenTelemetry tracing setup.

Exporter is chosen by environment variable, so the same image works on a laptop, in CI and on Cloud Run:
  OTEL_TRACES_EXPORTER=console (default)  one compact JSON line per finished span on stdout
  OTEL_TRACES_EXPORTER=otlp               send to OTEL_EXPORTER_OTLP_ENDPOINT (e.g. a collector or Jaeger)
  OTEL_TRACES_EXPORTER=none               tracing API works, nothing is exported (tests)
A TracerProvider can be installed only once per process, so setup_tracing() is idempotent.
"""

from __future__ import annotations

import json
import os
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor, SpanExporter

SERVICE_NAME = "fde-api"
_provider: TracerProvider | None = None


def compact(span: ReadableSpan) -> str:
    """One line per span: enough to read a trace in a terminal (the SDK's default is ~30 lines per span)."""
    ctx = span.get_span_context()
    parent = span.parent
    duration_ms = round(((span.end_time or 0) - (span.start_time or 0)) / 1e6, 1)
    record: dict[str, Any] = {
        "span": span.name, "trace_id": format(ctx.trace_id, "032x") if ctx else None,
        "span_id": format(ctx.span_id, "016x") if ctx else None,
        "parent_id": format(parent.span_id, "016x") if parent else None,
        "ms": duration_ms, "status": span.status.status_code.name,
        "attrs": dict(span.attributes or {}),
    }
    return json.dumps(record, default=str) + os.linesep


def _exporter() -> SpanExporter | None:
    choice = os.environ.get("OTEL_TRACES_EXPORTER", "console").lower()
    if choice == "none":
        return None
    if choice == "otlp":
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        return OTLPSpanExporter()  # reads OTEL_EXPORTER_OTLP_ENDPOINT itself
    return ConsoleSpanExporter(formatter=compact)


def setup_tracing(extra_exporter: SpanExporter | None = None) -> TracerProvider:
    """Install the process-wide TracerProvider once. extra_exporter lets tests capture spans in memory."""
    global _provider
    if _provider is None:
        _provider = TracerProvider(resource=Resource.create({"service.name": SERVICE_NAME}))
        exporter = _exporter()
        if exporter is not None:
            # Simple (synchronous) processor: a demo service with a few spans per request; no batching delay to explain.
            _provider.add_span_processor(SimpleSpanProcessor(exporter))
        trace.set_tracer_provider(_provider)
    if extra_exporter is not None:
        _provider.add_span_processor(SimpleSpanProcessor(extra_exporter))
    return _provider


def tracer() -> trace.Tracer:
    return trace.get_tracer("fde-engagement-kit")
