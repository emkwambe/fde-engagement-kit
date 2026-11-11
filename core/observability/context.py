"""Per-request bookkeeping that every layer can reach without passing it through every function.

A ContextVar holds one RequestStats object per request. Worker threads (FastAPI's thread pool, LangGraph's tool
executor) start with a COPY of the context, so they see the same object and can add to it. The object is mutable on
purpose: re-assigning the ContextVar inside a thread would not be visible to the request, mutating the object is.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from threading import Lock

from opentelemetry import trace


@dataclass
class RequestStats:
    model_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    tool_calls: list[str] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def add_model_call(self, tokens_in: int, tokens_out: int) -> None:
        with self._lock:
            self.model_calls += 1
            self.tokens_in += tokens_in
            self.tokens_out += tokens_out

    def add_tool_call(self, name: str) -> None:
        with self._lock:
            self.tool_calls.append(name)


_STATS: ContextVar[RequestStats | None] = ContextVar("fde_request_stats", default=None)


def current_stats() -> RequestStats | None:
    return _STATS.get()


@contextmanager
def request_scope() -> Iterator[RequestStats]:
    stats = RequestStats()
    token = _STATS.set(stats)
    try:
        yield stats
    finally:
        _STATS.reset(token)


def current_trace_id() -> str:
    """The active OpenTelemetry trace id as 32 hex characters, or a fresh random id when no span is active.
    AgentService stores this in agent.audit_log.trace_id, so audit rows and traces share one id."""
    ctx = trace.get_current_span().get_span_context()
    return format(ctx.trace_id, "032x") if ctx.is_valid else uuid.uuid4().hex
