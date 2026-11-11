"""Helpers for Day 1 acceptance tests."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from core.config import EngagementConfig
from core.config.schema import DocumentSource
from core.llm.factory import HashingFakeEmbeddings

TEST_ENGAGEMENT = "pytest-day01"
DEMO_DOCS = Path("engagements/demo-logistics/data/docs")


def make_cfg(base: EngagementConfig, docs_dir: Path, name: str = TEST_ENGAGEMENT) -> EngagementConfig:
    cfg = base.model_copy(deep=True)
    cfg.engagement.name = name
    cfg.sources.documents = [DocumentSource(type="local", path=str(docs_dir.resolve()), include=["*.md"])]
    return cfg


class CountingEmbeddings(Embeddings):
    def __init__(self, dims: int) -> None:
        self.inner = HashingFakeEmbeddings(dims)
        self.document_calls = 0
        self.texts_embedded = 0

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.document_calls += 1
        self.texts_embedded += len(texts)
        return self.inner.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self.inner.embed_query(text)


class SpyChat(BaseChatModel):
    """Records the messages it receives; answers with a fixed string."""

    calls: list[list[BaseMessage]] = []
    fail_if_called: bool = False

    @property
    def _llm_type(self) -> str:
        return "spy"

    def _generate(self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None,
                  **kwargs: Any) -> ChatResult:
        if self.fail_if_called:
            raise AssertionError("chat model must not be called here")
        self.calls.append(messages)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="Gold earns 5% per day."))])


def clear_engagement(conn, name: str) -> None:
    conn.execute("DELETE FROM kb.documents WHERE engagement = %s", (name,))
    conn.commit()


@pytest.fixture
def demo_docs_copy(tmp_path: Path) -> Path:
    dst = tmp_path / "docs"
    shutil.copytree(DEMO_DOCS, dst)
    return dst


@pytest.fixture
def ingested(conn, demo_cfg, demo_docs_copy):
    """Demo docs ingested under the test engagement; cleaned up afterwards."""
    from core.ingest.documents import ingest_documents

    cfg = make_cfg(demo_cfg, demo_docs_copy)
    clear_engagement(conn, cfg.engagement.name)
    ingest_documents(conn, cfg, HashingFakeEmbeddings(cfg.embeddings.dimensions))
    conn.commit()
    yield cfg
    clear_engagement(conn, cfg.engagement.name)
