"""Task 4 — cited answer. Needs Postgres. Run: uv run pytest tests/day01/test_answer.py -v"""

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from core.llm.factory import ExtractiveFakeChat, HashingFakeEmbeddings
from core.rag.answer import NO_ANSWER, answer_question
from tests.day01.conftest import SpyChat

pytestmark = [pytest.mark.day01, pytest.mark.db]

Q = "What credit per day late does a Gold tier customer get?"


def test_answers_with_citations(conn, ingested):
    emb = HashingFakeEmbeddings(ingested.embeddings.dimensions)
    ans = answer_question(Q, cfg=ingested, conn=conn, chat=ExtractiveFakeChat(), embeddings=emb)
    assert ans.answer and ans.answer != NO_ANSWER
    assert "sla-policy.md#credits" in [c.ref for c in ans.citations]
    assert len({c.chunk_id for c in ans.citations}) == len(ans.citations), "duplicate citations"
    assert ans.confidence >= ingested.retrieval.min_score


def test_prompt_structure(conn, ingested):
    spy = SpyChat()
    spy.calls.clear()
    emb = HashingFakeEmbeddings(ingested.embeddings.dimensions)
    answer_question(Q, cfg=ingested, conn=conn, chat=spy, embeddings=emb)
    assert len(spy.calls) == 1, "call the chat model exactly once"
    messages = spy.calls[0]
    assert isinstance(messages[0], SystemMessage), "first message should hold the rules"
    human = messages[-1]
    assert isinstance(human, HumanMessage)
    assert Q in human.content
    assert "CONTEXT:" in human.content
    assert human.content.index(Q) < human.content.index("CONTEXT:"), "question first, then CONTEXT:"
    assert "sla-policy.md#credits" in human.content, "label each chunk with its citation ref"


def test_says_it_does_not_know_without_calling_the_model(conn, ingested):
    spy = SpyChat(fail_if_called=True)
    emb = HashingFakeEmbeddings(ingested.embeddings.dimensions)
    ans = answer_question("zqxv blorf wibble quux", cfg=ingested, conn=conn, chat=spy, embeddings=emb)
    assert ans.answer == NO_ANSWER
    assert ans.citations == []
