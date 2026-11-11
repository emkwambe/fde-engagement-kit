"""Scripted fake models: deterministic, offline stand-ins for a tool-calling LLM (FAKE_LLM=1).

A real model decides which tool to call by reading the question and the tool descriptions. A scripted fake follows a
fixed script instead, so tests, CI and demos are free, fast and repeatable. Real reasoning quality is measured with the
real model in the evals, never with a fake.

  ScriptedFake      the machinery every script shares: find the latest question, collect the tool results so far,
                    ask the script for the next tool call or the final answer.
  GenericFakeChat   the kit's default script, for ANY engagement: refuse requests to change data, otherwise search the
                    documents once and answer from the best passage.
An engagement can bring its own script (engagement.yaml -> llm.fake_script: a file in its extensions/ folder with a
class FakeAgent(ScriptedFake)), e.g. demo-logistics scripts SQL lookups and credit tickets (Sprint 01, kit-generic).
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

WRITE_REQUEST = re.compile(r"\b(delete|drop|remove|update|insert|truncate|modify)\b", re.IGNORECASE)
REFUSAL = "I can't do that: I only have read access to the data, and every change needs a human's approval."
NO_ANSWER = "I couldn't find this in the provided documents."


def loads(text: str) -> Any:
    """json.loads that returns None instead of raising (tool results are usually, not always, JSON)."""
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return None


class ScriptedFake(BaseChatModel):
    """Base class: subclasses implement next_call() and final_answer()."""

    tool_names: list[str] = []

    @property
    def _llm_type(self) -> str:
        return "scripted-agent-fake"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> ScriptedFake:  # type: ignore[override]
        return self.model_copy(update={"tool_names": [getattr(t, "name", str(t)) for t in tools]})

    def can(self, name: str, done: dict[str, str]) -> bool:
        """The tool exists for this engagement and has not been called yet in this turn."""
        return name in self.tool_names and name not in done

    # ------------------------------------------------------------------ one model call
    def _generate(self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None,
                  **kwargs: Any) -> ChatResult:
        start = max((i for i, m in enumerate(messages) if isinstance(m, HumanMessage)), default=0)
        question = str(messages[start].content) if messages else ""
        done = {m.name: str(m.content) for m in messages[start + 1:] if isinstance(m, ToolMessage) and m.name}
        call = self.next_call(question, done)
        if call:
            name, args = call
            message = AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call_{len(done) + 1}_{name}"}])
        else:
            message = AIMessage(content=self.final_answer(question, done))
        return ChatResult(generations=[ChatGeneration(message=message)])

    # ------------------------------------------------------------------ the script
    def next_call(self, question: str, done: dict[str, str]) -> tuple[str, dict[str, Any]] | None:
        raise NotImplementedError

    def final_answer(self, question: str, done: dict[str, str]) -> str:
        raise NotImplementedError

    # ------------------------------------------------------------------ helpers for scripts
    @staticmethod
    def first_passage(done: dict[str, str]) -> str | None:
        docs = loads(done.get("search_documents", ""))
        if isinstance(docs, dict) and docs.get("results"):
            first = docs["results"][0]
            return f"Based on the sources: {' '.join(first['text'].split())[:300]} [{first['ref']}]"
        return None


class GenericFakeChat(ScriptedFake):
    """Default fake for any engagement: one document search, then an extractive answer with its citation."""

    def next_call(self, question: str, done: dict[str, str]) -> tuple[str, dict[str, Any]] | None:
        if WRITE_REQUEST.search(question):
            return None
        if self.can("search_documents", done):
            return "search_documents", {"query": question[:500]}
        return None

    def final_answer(self, question: str, done: dict[str, str]) -> str:
        if WRITE_REQUEST.search(question) and not done:
            return REFUSAL
        return self.first_passage(done) or NO_ANSWER
