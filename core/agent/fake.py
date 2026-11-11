"""ScriptedAgentChat: a deterministic, offline stand-in for a tool-calling LLM (FAKE_LLM=1).

A real model decides which tool to call by reading the question and the tool descriptions.
This fake follows a fixed script instead, so tests and demos are free, fast and repeatable:

  question mentions ORD-xxxx      -> query_ops_db on sla_breaches for that order
  question mentions SHP-xxxx      -> getShipment
  "how many" question             -> query_ops_db count(*) on sla_breaches
  policy question / credit ticket -> search_documents
  "ticket" + an order row         -> createTicket with the credit from the SLA policy table
  asks to delete/change data      -> refuses, calls nothing

It only knows the demo engagement's credit table (sla-policy.md#credits). Real reasoning
quality is measured with OpenAI in the Day 3 evals, never with this fake.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

ORDER = re.compile(r"\bORD-\d+\b")
SHIPMENT = re.compile(r"\bSHP-\d+\b")
WRITE_REQUEST = re.compile(r"\b(delete|drop|remove|update|insert|truncate|modify)\b", re.IGNORECASE)
CREDIT_RULES = {"Standard": (2, 10), "Silver": (3, 15), "Gold": (5, 25), "Platinum": (7, 35)}  # % per day, cap
REFUSAL = "I can't do that: I only have read access to the data, and the one write I can make is a credit ticket."


def _loads(text: str) -> Any:
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return None


class ScriptedAgentChat(BaseChatModel):
    tool_names: list[str] = []

    @property
    def _llm_type(self) -> str:
        return "scripted-agent-fake"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> ScriptedAgentChat:  # type: ignore[override]
        return self.model_copy(update={"tool_names": [getattr(t, "name", str(t)) for t in tools]})

    # ------------------------------------------------------------------ one model call
    def _generate(self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None,
                  **kwargs: Any) -> ChatResult:
        start = max((i for i, m in enumerate(messages) if isinstance(m, HumanMessage)), default=0)
        question = str(messages[start].content) if messages else ""
        done = {m.name: str(m.content) for m in messages[start + 1:] if isinstance(m, ToolMessage) and m.name}
        call = self._next_call(question, done)
        if call:
            name, args = call
            message = AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call_{len(done) + 1}_{name}"}])
        else:
            message = AIMessage(content=self._final_answer(question, done))
        return ChatResult(generations=[ChatGeneration(message=message)])

    def _can(self, name: str, done: dict[str, str]) -> bool:
        return name in self.tool_names and name not in done

    def _next_call(self, question: str, done: dict[str, str]) -> tuple[str, dict[str, Any]] | None:
        q = question.lower()
        if WRITE_REQUEST.search(question):
            return None
        order = ORDER.search(question)
        shipment = SHIPMENT.search(question)
        if order and self._can("query_ops_db", done):
            return "query_ops_db", {"query": "SELECT order_id, customer_id, tier, days_late, value_usd "
                                             f"FROM sla_breaches WHERE order_id = '{order.group(0)}'"}
        if shipment and self._can("getShipment", done):
            return "getShipment", {"shipment_id": shipment.group(0)}
        if "how many" in q and not order and self._can("query_ops_db", done):
            return "query_ops_db", {"query": "SELECT count(*) AS late_orders FROM sla_breaches"}
        policy_words = ("policy", "credit", "sla", "allow", "claim", "escalat", "rule")
        if any(w in q for w in policy_words) and "how many" not in q and self._can("search_documents", done):
            return "search_documents", {"query": "SLA credit per day late by customer tier" if order else question}
        if order and "ticket" in q and self._can("createTicket", done):
            row = self._order_row(done)
            if row:
                return "createTicket", self._ticket_args(row)
        return None

    @staticmethod
    def _order_row(done: dict[str, str]) -> dict[str, Any] | None:
        data = _loads(done.get("query_ops_db", ""))
        if not isinstance(data, dict) or not data.get("rows") or "tier" not in data.get("columns", []):
            return None
        return dict(zip(data["columns"], data["rows"][0], strict=False))

    @staticmethod
    def _ticket_args(row: dict[str, Any]) -> dict[str, Any]:
        per_day, cap = CREDIT_RULES.get(row["tier"], (2, 10))
        percent = min(per_day * row["days_late"], cap)
        amount = round(row["value_usd"] * percent / 100, 2)
        return {"order_id": row["order_id"], "customer_id": row["customer_id"], "days_late": row["days_late"],
                "credit_percent": percent, "credit_amount_usd": amount,
                "reason": f"{row['tier']} SLA credit: {row['days_late']} days late x {per_day}% = {percent}% "
                          "[sla-policy.md#credits]",
                "priority": "P3"}

    # ------------------------------------------------------------------ final answer
    def _final_answer(self, question: str, done: dict[str, str]) -> str:
        if WRITE_REQUEST.search(question) and not done:
            return REFUSAL
        parts: list[str] = []
        row = self._order_row(done)
        order = ORDER.search(question)
        if row:
            parts.append(f"{row['order_id']} ({row['tier']}, customer {row['customer_id']}) was {row['days_late']} "
                         f"day(s) late on a ${row['value_usd']:,.2f} order.")
        elif order and "query_ops_db" in done:
            parts.append(f"I found no SLA breach for {order.group(0)}.")
        elif "query_ops_db" in done:
            data = _loads(done["query_ops_db"]) or {}
            if data.get("rows"):
                parts.append(f"Result: {data['columns'][0]} = {data['rows'][0][0]}.")
        shipment = _loads(done.get("getShipment", ""))
        if isinstance(shipment, dict) and "last_status" in shipment:
            parts.append(f"Shipment {shipment['shipment_id']}: {shipment['last_status']} "
                         f"(last scan {shipment.get('last_scan_at')}).")
        elif isinstance(shipment, dict) and "error" in shipment:
            parts.append(f"The ERP says: {shipment['error']}.")
        docs = _loads(done.get("search_documents", ""))
        if isinstance(docs, dict) and docs.get("results") and not row:
            first = docs["results"][0]
            parts.append(f"Based on the sources: {' '.join(first['text'].split())[:300]} [{first['ref']}]")
        if row and "createTicket" not in done and "ticket" in question.lower():
            parts.append("I could not prepare the ticket.")
        ticket = _loads(done.get("createTicket", ""))
        if isinstance(ticket, dict) and "ticket_id" in ticket:
            parts.append(f"Created ticket {ticket['ticket_id']} for a {ticket['credit_percent']:g}% credit "
                         f"(${ticket['credit_amount_usd']:,.2f}) [sla-policy.md#credits].")
        elif isinstance(ticket, dict) and "error" in ticket:
            parts.append(f"The ticket was NOT created: {ticket['error']}")
        return " ".join(parts) or "I couldn't find this in the provided documents."
