"""search_documents: the Day 1 retrieval as a tool the agent can call (Day 2, part 3).

The agent decides WHEN to read policy; this tool decides HOW (same hybrid search and the same
min_score gate as /chat). It returns labelled passages; the model writes the answer and cites
the refs. Passages are data, not instructions (see SYSTEM_PROMPT in graph.py).
"""

from __future__ import annotations

import json

from langchain_core.embeddings import Embeddings
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from core.config.schema import EngagementConfig
from core.db.connection import connect
from core.rag.answer import Citation
from core.retrieval.search import search


class SearchArgs(BaseModel):
    query: str = Field(min_length=2, max_length=500,
                       description="What to look up in the policy documents, in plain words")


def search_documents_tool(cfg: EngagementConfig, embeddings: Embeddings, dsn: str | None = None) -> StructuredTool:
    def search_documents(query: str) -> str:
        with connect(dsn) as conn:
            results = search(conn, engagement=cfg.engagement.name, query_text=query,
                             query_vector=embeddings.embed_query(query),
                             top_k=cfg.retrieval.top_k, hybrid=cfg.retrieval.hybrid)
        best = max((r.similarity for r in results), default=0.0)
        if not results or best < cfg.retrieval.min_score:
            return json.dumps({"results": [], "note": "No relevant policy documents found. Say you don't know."})
        passages = [{"ref": Citation(r.document_id, r.section, r.chunk_id).ref, "title": r.title, "text": r.text}
                    for r in results]
        return json.dumps({"results": passages})

    return StructuredTool.from_function(
        func=search_documents, name="search_documents", args_schema=SearchArgs,
        description=cfg.retrieval.tool_description,  # per engagement: the model chooses tools by description
        metadata={"source": "rag", "method": "SEARCH", "path": "kb.chunks", "requires_approval": False},
    )
