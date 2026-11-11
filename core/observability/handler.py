"""A LangChain callback that turns agent events into spans, metrics and per-request counts.

LangChain (and LangGraph, which is built on it) calls a callback handler at the start and end of every "run":
the whole graph, each graph node, each chat-model call and each tool call. Each run has a run_id and a parent_run_id,
which is exactly the tree a trace needs. We open a span on start, close it on end, and link it to the nearest
ancestor that has a span:

  HTTP POST /chat            (middleware, core/api/main.py)
  +-- agent.run              (the LangGraph graph)
      +-- agent.step agent   (graph node)  +-- llm.call
      +-- agent.step tools   (graph node)  +-- tool query_ops_db
      +-- agent.step agent                 +-- llm.call
Internal helper runs (routing functions, channel writes) get no span; their children attach to the nearest spanned
ancestor. Attributes hold names, counts and sizes only: never prompt text, tool arguments or results (PII-safe).
"""

from __future__ import annotations

from threading import Lock
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode

from core.observability import metrics
from core.observability.context import current_stats
from core.observability.tracing import tracer

NODE_SPANS = {"agent", "tools", "approval"}


class ObservabilityCallback(BaseCallbackHandler):
    """One shared instance; state is keyed by run_id, so concurrent requests don't mix."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._spans: dict[UUID, Span] = {}
        self._parents: dict[UUID, UUID | None] = {}
        self._models: dict[UUID, str] = {}
        self._tools: dict[UUID, str] = {}

    # ------------------------------------------------------------------ span bookkeeping
    def _start(self, name: str, run_id: UUID, parent_run_id: UUID | None, attrs: dict[str, Any] | None = None) -> None:
        with self._lock:
            self._parents[run_id] = parent_run_id
            ancestor = parent_run_id
            while ancestor is not None and ancestor not in self._spans:
                ancestor = self._parents.get(ancestor)
            parent_span = self._spans.get(ancestor) if ancestor is not None else None
        ctx = trace.set_span_in_context(parent_span) if parent_span is not None else None  # None = current context
        span = tracer().start_span(name, context=ctx, attributes=attrs or {})
        with self._lock:
            self._spans[run_id] = span

    def _remember(self, run_id: UUID, parent_run_id: UUID | None) -> None:
        with self._lock:
            self._parents[run_id] = parent_run_id

    def _end(self, run_id: UUID, error: BaseException | None = None, attrs: dict[str, Any] | None = None) -> None:
        with self._lock:
            span = self._spans.pop(run_id, None)
            self._parents.pop(run_id, None)
        if span is None:
            return
        for key, value in (attrs or {}).items():
            span.set_attribute(key, value)
        if error is not None:
            if type(error).__name__ == "GraphInterrupt":  # a pause for human approval, not a failure
                span.set_attribute("agent.interrupted", True)
            else:
                span.set_status(Status(StatusCode.ERROR, type(error).__name__))
        span.end()

    # ------------------------------------------------------------------ graph and nodes
    def on_chain_start(self, serialized: dict[str, Any] | None, inputs: Any, *, run_id: UUID,
                       parent_run_id: UUID | None = None, metadata: dict[str, Any] | None = None,
                       **kwargs: Any) -> None:
        name = kwargs.get("name") or ""
        node = (metadata or {}).get("langgraph_node")
        if parent_run_id is None:
            self._start("agent.run", run_id, None)
        elif node in NODE_SPANS and name == node:
            self._start(f"agent.step {node}", run_id, parent_run_id, {"agent.node": node})
        else:
            self._remember(run_id, parent_run_id)

    def on_chain_end(self, outputs: Any, *, run_id: UUID, **kwargs: Any) -> None:
        self._end(run_id)

    def on_chain_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        self._end(run_id, error)

    # ------------------------------------------------------------------ model calls
    def on_chat_model_start(self, serialized: dict[str, Any] | None, messages: Any, *, run_id: UUID,
                            parent_run_id: UUID | None = None, metadata: dict[str, Any] | None = None,
                            **kwargs: Any) -> None:
        params = kwargs.get("invocation_params") or {}
        model = str((metadata or {}).get("ls_model_name") or params.get("model") or params.get("model_name")
                    or params.get("_type") or "unknown")  # _type = the fake's _llm_type, e.g. scripted-agent-fake
        with self._lock:
            self._models[run_id] = model
        self._start("llm.call", run_id, parent_run_id, {"llm.model": model})

    def on_llm_end(self, response: Any, *, run_id: UUID, **kwargs: Any) -> None:
        with self._lock:
            model = self._models.pop(run_id, "unknown")
        tokens_in = tokens_out = 0
        try:
            usage = getattr(response.generations[0][0].message, "usage_metadata", None) or {}
            tokens_in, tokens_out = int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0))
        except (AttributeError, IndexError, TypeError):
            pass
        metrics.MODEL_CALLS.labels(model).inc()
        metrics.MODEL_TOKENS.labels(model, "in").inc(tokens_in)
        metrics.MODEL_TOKENS.labels(model, "out").inc(tokens_out)
        stats = current_stats()
        if stats is not None:
            stats.add_model_call(tokens_in, tokens_out)
        self._end(run_id, attrs={"llm.tokens_in": tokens_in, "llm.tokens_out": tokens_out})

    def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        with self._lock:
            model = self._models.pop(run_id, "unknown")
        metrics.MODEL_CALLS.labels(model).inc()
        self._end(run_id, error)

    # ------------------------------------------------------------------ tool calls
    def on_tool_start(self, serialized: dict[str, Any] | None, input_str: str, *, run_id: UUID,
                      parent_run_id: UUID | None = None, **kwargs: Any) -> None:
        name = str(kwargs.get("name") or (serialized or {}).get("name") or "unknown")
        with self._lock:
            self._tools[run_id] = name
        self._start(f"tool {name}", run_id, parent_run_id, {"tool.name": name})

    def on_tool_end(self, output: Any, *, run_id: UUID, **kwargs: Any) -> None:
        with self._lock:
            name = self._tools.pop(run_id, "unknown")
        content = str(getattr(output, "content", output))
        outcome = "error" if content.lstrip().startswith('{"error"') else "ok"
        metrics.TOOL_CALLS.labels(name, outcome).inc()
        stats = current_stats()
        if stats is not None:
            stats.add_tool_call(name)
        self._end(run_id, attrs={"tool.outcome": outcome, "tool.result_chars": len(content)})

    def on_tool_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        with self._lock:
            name = self._tools.pop(run_id, "unknown")
        metrics.TOOL_CALLS.labels(name, "exception").inc()
        stats = current_stats()
        if stats is not None:
            stats.add_tool_call(name)
        self._end(run_id, error)


CALLBACK = ObservabilityCallback()
