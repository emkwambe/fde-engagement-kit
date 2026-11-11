"""HTTP API (D-09).  Run locally:  uv run uvicorn core.api.main:app --reload --port 8000

Day 1 endpoints: GET /health, POST /chat (RAG only). Day 2 swaps /chat to the LangGraph agent.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from core.config import load_engagement
from core.db.connection import connect
from core.llm.factory import get_chat_model, get_embeddings

state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    cfg = load_engagement(os.environ.get("ENGAGEMENT", "demo-logistics"))
    state.update(cfg=cfg, chat=get_chat_model(cfg.llm), embeddings=get_embeddings(cfg.embeddings))
    yield
    state.clear()


app = FastAPI(title="FDE Engagement Kit", version="0.1.0", lifespan=lifespan)


class ChatRequest(BaseModel):
    thread_id: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=4000)


class CitationOut(BaseModel):
    ref: str
    document_id: str
    section: str
    chunk_id: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[CitationOut]
    confidence: float


@app.get("/health")
def health() -> dict[str, Any]:
    db_ok = True
    try:
        with connect(vector=False) as conn:
            conn.execute("SELECT 1")
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "engagement": state["cfg"].engagement.name,
            "llm_provider": state["cfg"].llm.provider, "database": db_ok}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> dict[str, Any]:
    from core.rag.answer import answer_question

    try:
        with connect() as conn:
            result = answer_question(req.message, cfg=state["cfg"], conn=conn,
                                     chat=state["chat"], embeddings=state["embeddings"])
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    return result.to_dict()
