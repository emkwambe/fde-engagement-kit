"""HTTP API (D-09).  Run locally:  uv run uvicorn core.api.main:app --port 8000   (or .\\tasks.ps1 api)

Endpoints
  GET  /health                          status, engagement, model provider, database, checkpointer
  POST /chat                            the agent: answer, or a write paused for approval   (Day 2)
  POST /ask                             documents only: cited RAG answer                     (Day 1)
  GET  /approvals                       writes waiting for a human decision
  POST /approvals/{thread_id}/approve   resume the paused thread and run the write
  POST /approvals/{thread_id}/reject    resume the paused thread without running it
  GET  /threads/{thread_id}/audit       everything recorded for one conversation
  GET  /                                a small chat page with Approve / Reject buttons (FR-14)

Conversation state is checkpointed in Postgres (shared by every API process). If the database is
unreachable at startup the API still starts, with in-memory checkpoints and no audit trail, and
/health reports "degraded".
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any, Literal

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel, Field

from core.agent.checkpoint import CHECKPOINT_SCHEMA
from core.agent.graph import agent_model, agent_tools, build_agent
from core.agent.service import AgentService
from core.config import load_engagement
from core.db.connection import connect, database_url
from core.llm.factory import get_chat_model, get_embeddings

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


app = FastAPI(title="FDE Engagement Kit", version="0.2.0", lifespan=lifespan)


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


# ----------------------------------------------------------------------------- endpoints
def _service() -> AgentService:
    service: AgentService = state["service"]
    return service


@app.get("/health")
def health() -> dict[str, Any]:
    db_ok = True
    try:
        with connect(vector=False) as conn:
            conn.execute("SELECT 1")
    except Exception:
        db_ok = False
    ok = db_ok and state["checkpointer"] == "postgres"
    return {"status": "ok" if ok else "degraded", "engagement": state["cfg"].engagement.name,
            "llm_provider": state["cfg"].llm.provider, "database": db_ok, "checkpointer": state["checkpointer"]}


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


@app.get("/", include_in_schema=False)
def ui() -> FileResponse:
    return FileResponse(UI_PAGE)
