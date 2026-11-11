"""Question -> retrieved context -> cited answer.
>>> YOU IMPLEMENT answer_question (Day 1, task 4, skills S-07/S-08) <<<

Spec: docs/specs/day-01-rag-core.md#task-4--cited-answer
Tests: tests/day01/test_answer.py
"""

from __future__ import annotations

from dataclasses import dataclass, field

import psycopg
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from core.config.schema import EngagementConfig
from core.ingest.chunking import slugify

NO_ANSWER = "I couldn't find this in the provided documents."


@dataclass(frozen=True)
class Citation:
    document_id: str
    section: str
    chunk_id: str

    @property
    def ref(self) -> str:
        """'sla-policy.md#credits' — the format golden sets use (expected_sources)."""
        return f"{self.document_id}#{slugify(self.section)}"


@dataclass
class Answer:
    answer: str
    citations: list[Citation] = field(default_factory=list)
    confidence: float = 0.0  # best retrieval similarity, so callers can see how grounded the answer is

    def to_dict(self) -> dict[str, object]:
        return {
            "answer": self.answer,
            "citations": [{"ref": c.ref, "document_id": c.document_id, "section": c.section,
                           "chunk_id": c.chunk_id} for c in self.citations],
            "confidence": round(self.confidence, 4),
        }


def answer_question(
    question: str,
    *,
    cfg: EngagementConfig,
    conn: psycopg.Connection,
    chat: BaseChatModel,
    embeddings: Embeddings,
) -> Answer:
    """Answer using only retrieved documents, with citations.

    Requirements (checked by tests):
      1. Embed the question (embeddings.embed_query) and call core.retrieval.search.search with
         cfg.retrieval.top_k and cfg.retrieval.hybrid.
      2. If there are no results, or the best `similarity` is below cfg.retrieval.min_score,
         return Answer(NO_ANSWER, [], best_similarity) WITHOUT calling the chat model.
      3. Otherwise build a prompt: a system message with the rules (answer only from context,
         cite sources, say you don't know when context is insufficient) and a human message that
         contains the question and then the literal marker "CONTEXT:" followed by the chunks,
         each labelled with its citation ref. Treat chunk text as data, not instructions.
      4. Return the model's text, citations for the chunks you passed as context (deduplicated,
         in rank order), and confidence = best similarity.
    Note: the fake chat model (FAKE_LLM=1) answers from the text after "CONTEXT:".
    """
    raise NotImplementedError("Day 1 task 4: implement answer_question — see docs/specs/day-01-rag-core.md")
