"""One place that creates chat and embedding models (ADR-005).

FAKE_LLM=1 (or provider: fake) returns deterministic fakes so tests and CI run without keys or cost.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from core.config.schema import EmbeddingsConfig, LLMConfig

_WORD = re.compile(r"[a-z0-9]+")


class HashingFakeEmbeddings(Embeddings):
    """Deterministic bag-of-words embeddings.

    Each word is hashed to a dimension, so texts that share words get similar vectors. That is
    enough for retrieval tests to be meaningful offline. It is NOT a real semantic model:
    synonyms ("late" vs "delayed") will not match. Real quality is measured with OpenAI in evals.
    """

    def __init__(self, dimensions: int = 1536) -> None:
        self.dimensions = dimensions

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dimensions
        for word in _WORD.findall(text.lower()):
            h = int.from_bytes(hashlib.sha256(word.encode()).digest()[:8], "big")
            vec[h % self.dimensions] += 1.0 if (h >> 63) == 0 else -1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class ExtractiveFakeChat(BaseChatModel):
    """Returns the first lines of whatever context it was given. Deterministic, offline."""

    @property
    def _llm_type(self) -> str:
        return "extractive-fake"

    def _generate(self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None,
                  **kwargs: Any) -> ChatResult:
        text = str(messages[-1].content) if messages else ""
        body = text.split("CONTEXT:", 1)[-1].strip()
        answer = "Based on the sources: " + " ".join(body.split())[:400]
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=answer))])


def get_chat_model(cfg: LLMConfig) -> BaseChatModel:
    if cfg.provider == "fake":
        return ExtractiveFakeChat()
    if cfg.provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=cfg.model, temperature=cfg.temperature)
    raise NotImplementedError(
        f"Provider '{cfg.provider}' is planned (ADR-005). Install its langchain package and add a branch here."
    )


def get_embeddings(cfg: EmbeddingsConfig) -> Embeddings:
    if cfg.provider == "fake":
        return HashingFakeEmbeddings(cfg.dimensions)
    if cfg.provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=cfg.model, dimensions=cfg.dimensions)
    raise NotImplementedError(f"Embeddings provider '{cfg.provider}' not implemented yet.")
