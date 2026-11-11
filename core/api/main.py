"""HTTP API (D-09).  Run locally:  uv run uvicorn core.api.main:app --port 8000   (or .\\tasks.ps1 api)

Endpoints
  GET  /health                          status, engagement, model provider, database, checkpointer, embeddings_match
  POST /chat                            the agent: answer, or a write paused for approval   (Day 2)
  POST /ask                             documents only: cited RAG answer                     (Day 1)
  GET  /approvals                       writes waiting for a human decision
  POST /approvals/{thread_id}/approve   resume the paused thread and run the write
  POST /approvals/{thread_id}/reject    resume the paused thread without running it
  GET  /threads/{thread_id}/audit       everything recorded for one conversation
  GET  /metrics                         Prometheus metrics (requests, latency, model calls, tokens, tools, approvals)
  POST /ingest                          ADMIN: run ingestion for the configured engagement   (Bearer ADMIN_TOKEN)
  POST /eval                            ADMIN: run the golden set, FAKE mode only           (Bearer ADMIN_TOKEN)
  GET  /                                a small chat page with Approve / Reject buttons (FR-14)

Every request gets an OpenTelemetry span, a Prometheus observation and one JSON log line (core/observability).
The response header X-Trace-Id is the same id stored in agent.audit_log.trace_id.

Conversation state is checkpointed in Postgres (shared by every API process). If the database is
unreachable at startup the API still starts, with in-memory checkpoints and no audit trail, and
/health reports "degraded".
"""

from __future__ import annotations

import hmac
import logging
import os
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any, Literal

import psycopg
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from opentelemetry.trace import SpanKind, Status, StatusCode
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field

from core.agent.checkpoint import CHECKPOINT_SCHEMA
from core.agent.graph import agent_model, agent_tools, build_agent
from core.agent.service import AgentService
from core.config import load_engagement
from core.db.connection import connect, database_url
from core.ingest.documents import embedding_signature, stored_signatures
from core.llm.factory import get_chat_model, get_embeddings
from core.observability import current_trace_id, request_scope, setup_tracing, tracer
from core.observability import metrics as m
from core.observability.logging import setup_logging

UI_PAGE = Path(__file__).resolve().parents[2] / "ui" / "index.html"
state: dict[str, Any] = {}


def _postgres_checkpointer() -> tuple[BaseCheckpointSaver, Any]:
    """A connection POOL (the API serves requests in parallel threads; one connection is not thread-safe)."""
    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool

    pool = ConnectionPool(database_url(), min_size=1, max_size=5, open=True, timeout=5,
                          kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row,
                                  "options": f"-c search_path={CHECKPOINT_SCHEMA}"})
    try:
        saver = PostgresSaver(pool)  # type: ignore[arg-type]
        saver.setup()
    except Exception:
        pool.close()
        raise
    return saver, pool


@contextmanager
def _db() -> Iterator[psycopg.Connection]:
    with connect(vector=False) as conn:
        yield conn


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    cfg = load_engagement(os.environ.get("ENGAGEMENT", "demo-logistics"))
    embeddings = get_embeddings(cfg.embeddings)
    pool = None
    try:
        checkpointer, pool = _postgres_checkpointer()
        kind, db = "postgres", _db
    except Exception:
        checkpointer, kind, db = InMemorySaver(), "memory (database unreachable)", None
    tools = agent_tools(cfg, embeddings, sql_schema_text=None if db else "(database unreachable)")
    agent = build_agent(cfg, tools, agent_model(cfg), checkpointer=checkpointer)
    state.update(cfg=cfg, chat=get_chat_model(cfg.llm), embeddings=embeddings, checkpointer=kind,
                 service=AgentService(cfg, agent, db))
    yield
    state.clear()
    if pool is not None:
        pool.close()


app = FastAPI(title="FDE Engagement Kit", version="0.3.0", lifespan=lifespan)
setup_tracing()
request_log = setup_logging()
QUIET_ROUTES = {"/health", "/metrics"}  # probes and scrapers call these every few seconds: count them, log at DEBUG


@app.middleware("http")
async def observe(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """One span, one metrics observation and one JSON log line per request (D-16, NFR-08).
    request_scope() gives the endpoint (and the agent's worker threads) a counter object for model and tool calls."""
    start = time.perf_counter()
    status = 500
    with request_scope() as stats, tracer().start_as_current_span(f"HTTP {request.method}", kind=SpanKind.SERVER) as span:
        trace_id = current_trace_id()
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Trace-Id"] = trace_id
            return response
        finally:
            seconds = time.perf_counter() - start
            route = getattr(request.scope.get("route"), "path", "unmatched")  # the template, never the raw path
            span.update_name(f"{request.method} {route}")
            span.set_attributes({"http.method": request.method, "http.route": route, "http.status_code": status,
                                 "agent.model_calls": stats.model_calls, "agent.tool_calls": len(stats.tool_calls)})
            if status >= 500:
                span.set_status(Status(StatusCode.ERROR))
            m.HTTP_REQUESTS.labels(request.method, route, str(status)).inc()
            m.HTTP_SECONDS.labels(route).observe(seconds)
            fields = {"trace_id": trace_id, "method": request.method, "route": route, "status": status,
                      "duration_ms": round(seconds * 1000, 1), "model_calls": stats.model_calls,
                      "tokens_in": stats.tokens_in, "tokens_out": stats.tokens_out, "tool_calls": stats.tool_calls}
            if "thread_id" in request.path_params:
                fields["thread_id"] = request.path_params["thread_id"]
            request_log.log(logging.DEBUG if route in QUIET_ROUTES else logging.INFO, "request", extra={"fields": fields})


# ----------------------------------------------------------------------------- request / response models
class ChatRequest(BaseModel):
    thread_id: str = Field(..., min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.:-]+$")
    message: str = Field(..., min_length=1, max_length=4000)
    user: str = Field("anonymous", max_length=100)


class Step(BaseModel):
    call: str | None = None
    args: dict[str, Any] | None = None
    result: str | None = None
    content: str | None = None


class PendingCall(BaseModel):
    id: str
    name: str
    args: dict[str, Any]


class TurnResponse(BaseModel):
    thread_id: str
    status: Literal["done", "needs_approval"]
    answer: str
    pending: list[PendingCall]
    steps: list[Step]


class Decision(BaseModel):
    by: str = Field(..., min_length=1, max_length=100, description="Who decided (name or email)")
    reason: str = Field("", max_length=500)


class RejectDecision(Decision):
    reason: str = Field(..., min_length=3, max_length=500, description="Why - shown to the agent and audited")


class CitationOut(BaseModel):
    ref: str
    document_id: str
    section: str
    chunk_id: str


class AskResponse(BaseModel):
    answer: str
    citations: list[CitationOut]
    confidence: float


class IngestRequest(BaseModel):
    tables: bool = True
    documents: bool = True


class EvalRequest(BaseModel):
    cases: list[str] = Field(default_factory=list, description="Case ids to run; empty = the whole golden set")


def require_admin(authorization: str | None = Header(None)) -> None:
    """Admin endpoints change data (/ingest) or burn CPU (/eval). Fail closed: no ADMIN_TOKEN set = disabled.
    compare_digest takes the same time for every wrong token, so the token cannot be guessed byte by byte."""
    token = os.environ.get("ADMIN_TOKEN", "")
    if not token:
        raise HTTPException(status_code=503, detail="Admin endpoints are disabled: set ADMIN_TOKEN on the server.")
    if not hmac.compare_digest(authorization or "", f"Bearer {token}"):
        raise HTTPException(status_code=401, detail="Missing or invalid admin bearer token",
                            headers={"WWW-Authenticate": "Bearer"})


# ----------------------------------------------------------------------------- endpoints
def _service() -> AgentService:
    service: AgentService = state["service"]
    return service


@app.get("/health")
def health() -> dict[str, Any]:
    cfg = state["cfg"]
    db_ok, vectors_ok = True, False
    try:
        with connect(vector=False) as conn:
            # Day 3: the stored document vectors must come from the same embedding model as the queries,
            # otherwise search silently returns nonsense (e.g. after switching FAKE_LLM).
            vectors_ok = stored_signatures(conn, cfg.engagement.name) == {embedding_signature(cfg)}
    except Exception:
        db_ok = False
    ok = db_ok and vectors_ok and state["checkpointer"] == "postgres"
    return {"status": "ok" if ok else "degraded", "engagement": cfg.engagement.name,
            "llm_provider": cfg.llm.provider, "database": db_ok, "checkpointer": state["checkpointer"],
            "embeddings_match": vectors_ok}


@app.post("/chat", response_model=TurnResponse)
def chat(req: ChatRequest) -> dict[str, Any]:
    try:
        return _service().chat(req.thread_id, req.message, user=req.user).to_dict()
    except ValueError as exc:  # thread is waiting for an approval decision
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/approvals")
def approvals() -> list[dict[str, Any]]:
    return _service().pending()


@app.post("/approvals/{thread_id}/approve", response_model=TurnResponse)
def approve(thread_id: str, body: Decision) -> dict[str, Any]:
    try:
        return _service().decide(thread_id, approved=True, by=body.by, reason=body.reason).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/approvals/{thread_id}/reject", response_model=TurnResponse)
def reject(thread_id: str, body: RejectDecision) -> dict[str, Any]:
    try:
        return _service().decide(thread_id, approved=False, by=body.by, reason=body.reason).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/threads/{thread_id}/audit")
def audit(thread_id: str) -> list[dict[str, Any]]:
    return _service().audit(thread_id)


@app.post("/ask", response_model=AskResponse)
def ask_documents(req: ChatRequest) -> dict[str, Any]:
    """Day 1 behaviour, kept: answer from the documents only, with citations. No tools, no state."""
    from core.rag.answer import answer_question

    with connect() as conn:
        result = answer_question(req.message, cfg=state["cfg"], conn=conn,
                                 chat=state["chat"], embeddings=state["embeddings"])
    return result.to_dict()


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/ingest", dependencies=[Depends(require_admin)])
def ingest(body: IngestRequest | None = None) -> dict[str, Any]:
    """Re-run ingestion for the engagement this server is configured for (idempotent: unchanged files are skipped)."""
    from core.ingest.run import run_ingestion

    body = body or IngestRequest()
    try:
        return run_ingestion(state["cfg"], tables=body.tables, docs=body.documents)
    except (FileNotFoundError, NotImplementedError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/eval", dependencies=[Depends(require_admin)])
def run_eval(body: EvalRequest | None = None) -> dict[str, Any]:
    """Run the golden set in this process, FAKE mode only: it checks the harness and wiring of a live server.
    Real-model evals cost money and quota and can take minutes, so they stay a CLI / CI job (core.evals.run)."""
    from core.config import resolve_path
    from core.evals.golden import load_golden
    from core.evals.run import PreflightError, build_service, preflight, run_cases, summarize

    cfg = state["cfg"]
    if cfg.llm.provider != "fake":
        raise HTTPException(status_code=409, detail="Real-model evals run from the CLI or CI, not the API: "
                                                    "uv run python -m core.evals.run")
    wanted = set((body or EvalRequest()).cases)
    cases = [c for c in load_golden(resolve_path(cfg.evals.golden_set)) if not wanted or c.id in wanted]
    try:
        preflight(cfg)
    except PreflightError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    runs = run_cases(build_service(cfg), cases)
    return {"summary": summarize(runs, cfg),
            "cases": [{"id": r.score.case.id, "passed": r.score.passed, "reasons": r.score.reasons} for r in runs]}


@app.get("/", include_in_schema=False)
def ui() -> FileResponse:
    return FileResponse(UI_PAGE)
