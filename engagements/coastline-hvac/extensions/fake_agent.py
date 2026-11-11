"""coastline-hvac fake model script (FAKE_LLM=1). ENGAGEMENT-OWNED: loaded through engagement.yaml -> llm.fake_script.

A fixed script, so tests and CI can drive the agent offline. It proves the wiring (tools, approvals, guardrails),
not reasoning quality; the real model is measured in the evals.

  "dispatch" + WO-xxxx        -> getWorkOrder, then on-call technicians (query_ops_db), then createDispatch
  WO-xxxx + SLA/late/credit   -> query_ops_db on sla_misses, then search_documents for the credit policy
  WO-xxxx                     -> getWorkOrder
  CU-xxx + open/work orders   -> listWorkOrders
  "how many"                  -> query_ops_db count
  anything else               -> search_documents
  asks to delete/change data  -> refuses, calls nothing
"""

from __future__ import annotations

import math
import re
from typing import Any

from core.agent.fake import WRITE_REQUEST, ScriptedFake, loads

WORK_ORDER = re.compile(r"\bWO-\d+\b")
CUSTOMER = re.compile(r"\bCU-\d+\b")
SKILL_BY_KIND = {"furnace": "residential", "heat pump": "residential", "central AC": "residential",
                 "rooftop unit": "commercial", "boiler": "commercial", "walk-in cooler": "refrigeration"}
FEE = {"Basic": 150, "Plus": 75, "Premium": 0}
CREDIT = {"Basic": (5, 25, 49), "Plus": (10, 40, 89), "Premium": (15, 50, 149)}  # % per started 4 h, cap %, fee $
REFUSAL = "I can't do that: I only have read access, and the one change I can make is a dispatch a human approves."


class FakeAgent(ScriptedFake):
    def next_call(self, question: str, done: dict[str, str]) -> tuple[str, dict[str, Any]] | None:
        q = question.lower()
        if WRITE_REQUEST.search(question):
            return None
        wo = WORK_ORDER.search(question)
        if wo and "dispatch" in q:
            if self.can("getWorkOrder", done):
                return "getWorkOrder", {"work_order_id": wo.group(0)}
            order = loads(done.get("getWorkOrder", ""))
            if isinstance(order, dict) and "customer_id" in order and self.can("query_ops_db", done):
                skill = SKILL_BY_KIND.get(order.get("equipment_kind") or "", "residential")
                return "query_ops_db", {"query": "SELECT t.tech_id, c.plan FROM technicians t, customers c "
                                                 f"WHERE t.on_call AND t.skill = '{skill}' "
                                                 f"AND c.customer_id = '{order['customer_id']}' ORDER BY t.tech_id"}
            row = self._row(done)
            if isinstance(order, dict) and row and self.can("createDispatch", done):
                fee = FEE.get(row.get("plan", ""), 150) if order.get("after_hours") else 0
                return "createDispatch", {
                    "work_order_id": order["work_order_id"], "tech_id": row["tech_id"], "priority": order["priority"],
                    "after_hours_fee_usd": fee,
                    "reason": f"{order['work_order_id']} {order['priority']}, {row['plan']} plan, after-hours fee "
                              f"${fee} [after-hours-fees.md#fees]"}
            return None
        if wo and any(w in q for w in ("sla", "late", "credit", "miss")):
            if self.can("query_ops_db", done):
                return "query_ops_db", {"query": "SELECT work_order_id, plan, priority, hours_late FROM sla_misses "
                                                 f"WHERE work_order_id = '{wo.group(0)}'"}
            if self.can("search_documents", done):
                return "search_documents", {"query": "SLA credit per started 4 hours late by plan"}
            return None
        if wo and self.can("getWorkOrder", done):
            return "getWorkOrder", {"work_order_id": wo.group(0)}
        customer = CUSTOMER.search(question)
        if customer and ("work order" in q or "open" in q) and self.can("listWorkOrders", done):
            return "listWorkOrders", {"customer_id": customer.group(0), "status": "open"}
        if "how many" in q and self.can("query_ops_db", done):
            return "query_ops_db", {"query": "SELECT count(*) AS n FROM sla_misses"}
        if not done and not wo and not customer and self.can("search_documents", done):
            return "search_documents", {"query": question[:500]}
        return None

    @staticmethod
    def _row(done: dict[str, str]) -> dict[str, Any] | None:
        data = loads(done.get("query_ops_db", ""))
        if isinstance(data, dict) and data.get("rows"):
            return dict(zip(data["columns"], data["rows"][0], strict=False))
        return None

    def final_answer(self, question: str, done: dict[str, str]) -> str:
        if WRITE_REQUEST.search(question) and not done:
            return REFUSAL
        parts: list[str] = []
        row = self._row(done)
        if row and "hours_late" in row:
            per, cap, fee = CREDIT[row["plan"]]
            blocks = math.ceil(row["hours_late"] / 4)
            pct = min(per * blocks, cap)
            parts.append(f"{row['work_order_id']} ({row['plan']}, {row['priority']}) was {row['hours_late']} hour(s) "
                         f"late: {blocks} started block(s) x {per}% = {pct}% of ${fee} = ${fee * pct / 100:.2f} "
                         "[response-time-sla.md#credits].")
        elif "query_ops_db" in done and row:
            parts.append(f"Result: {', '.join(f'{k} = {v}' for k, v in row.items())}.")
        order = loads(done.get("getWorkOrder", ""))
        if isinstance(order, dict) and "work_order_id" in order and "createDispatch" not in done:
            parts.append(f"{order['work_order_id']}: {order['status']}, {order['priority']}, "
                         f"technician {order.get('tech_id') or 'none'}.")
        elif isinstance(order, dict) and "error" in order:
            parts.append(f"The CMMS says: {order['error']}.")
        listed = loads(done.get("listWorkOrders", ""))
        if isinstance(listed, list):
            parts.append("Open work orders: " + (", ".join(w["work_order_id"] for w in listed) or "none") + ".")
        dispatch = loads(done.get("createDispatch", ""))
        if isinstance(dispatch, dict) and "dispatch_id" in dispatch:
            parts.append(f"Created {dispatch['dispatch_id']}: {dispatch['tech_id']} to {dispatch['work_order_id']}.")
        elif isinstance(dispatch, dict) and "error" in dispatch:
            parts.append(f"The dispatch was NOT created: {dispatch['error']}")
        passage = self.first_passage(done)
        if passage and not parts:
            parts.append(passage)
        return " ".join(parts) or "I couldn't find this in the provided documents."
