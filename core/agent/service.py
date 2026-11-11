"""AgentService: the one place where a conversation turn is run AND recorded (Day 2, part 4, FR-09/FR-11).

The API and the CLI both go through this class, so every pause, decision and tool call leaves the
same audit trail no matter where it came from:

  agent.approvals  - one row per write that needed a human: pending -> approved | rejected, who, when
  agent.audit_log  - one row per event: user_message, tool_call, tool_result, approval_requested,
                     approval_decided, answer. All rows of one request share a trace_id.

Privacy (guardrails.log_prompts): when false, user messages and answers are stored as length + SHA-256
hash only, so the audit log proves WHAT happened without keeping customer text. Tool arguments are
always stored, because they are the actions an auditor needs to see.

Double-click safety: decide() first CLAIMS the pending approval with a single UPDATE ... WHERE
status = 'pending'. Only one request can win; the second gets "nothing waiting" (HTTP 409).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

import psycopg
from langgraph.graph.state import CompiledStateGraph

from core.agent.graph import AgentTurn, ask, decide
from core.config.schema import EngagementConfig
from core.guardrails import BLOCKED_ANSWER, check_input
from core.guardrails.pii import redact

DbFactory = Callable[[], AbstractContextManager[psycopg.Connection]]
MAX_DETAIL = 2000  # characters of a tool result kept in the audit log


class AgentService:
    def __init__(self, cfg: EngagementConfig, agent: CompiledStateGraph, db: DbFactory | None) -> None:
        self.cfg, self.agent, self.db = cfg, agent, db

    # ------------------------------------------------------------------ public API
    def chat(self, thread_id: str, message: str, user: str = "anonymous") -> AgentTurn:
        trace = uuid.uuid4().hex
        blocked = check_input(message, self.cfg.guardrails)
        if blocked:  # direct prompt injection: refuse without calling the model or any tool (T-02)
            turn = AgentTurn(thread_id, "done", answer=BLOCKED_ANSWER)
            first = {"event": "guardrail_blocked", "detail": {"user": user, "matched": blocked, **self._text(message)}}
            self._record(turn, trace, first=first)
            return turn
        turn = ask(self.agent, self.cfg, thread_id, message)
        self._record(turn, trace, first={"event": "user_message", "detail": {"user": user, **self._text(message)}})
        return turn

    def decide(self, thread_id: str, *, approved: bool, by: str, reason: str = "") -> AgentTurn:
        trace = uuid.uuid4().hex
        claimed = self._claim(thread_id, approved, by)
        try:
            turn = decide(self.agent, self.cfg, thread_id, approved=approved, by=by, reason=reason)
        except Exception:
            self._unclaim(claimed)  # the graph could not resume: put the approval back to pending
            raise
        decision = {"event": "approval_decided",
                    "detail": {"approved": approved, "by": by, "reason": reason, "approval_ids": claimed}}
        self._record(turn, trace, first=decision)
        return turn

    def pending(self) -> list[dict[str, Any]]:
        if self.db is None:
            return []
        sql = """SELECT id, thread_id, tool, payload, created_at FROM agent.approvals
                 WHERE status = 'pending' ORDER BY created_at"""
        with self.db() as conn:
            rows = conn.execute(sql).fetchall()
        return [{"id": r[0], "thread_id": r[1], "tool": r[2], "args": r[3], "created_at": r[4].isoformat()}
                for r in rows]

    def audit(self, thread_id: str) -> list[dict[str, Any]]:
        if self.db is None:
            return []
        sql = "SELECT id, trace_id, event, detail, at FROM agent.audit_log WHERE thread_id = %s ORDER BY id"
        with self.db() as conn:
            rows = conn.execute(sql, (thread_id,)).fetchall()
        return [{"id": r[0], "trace_id": r[1], "event": r[2], "detail": r[3], "at": r[4].isoformat()} for r in rows]

    # ------------------------------------------------------------------ recording
    def _text(self, text: str) -> dict[str, Any]:
        if self.cfg.guardrails.log_prompts:
            return {"text": redact(text, self.cfg.guardrails.pii_redaction)[0]}  # even full logs never keep PII
        return {"chars": len(text), "sha256": hashlib.sha256(text.encode()).hexdigest()[:16]}

    def _record(self, turn: AgentTurn, trace: str, first: dict[str, Any]) -> None:
        if self.db is None:
            return
        events = [first]
        for s in turn.steps:
            if "call" in s:
                events.append({"event": "tool_call", "detail": {"tool": s["call"], "args": s["args"]}})
            else:
                events.append({"event": "tool_result", "detail": {"tool": s["result"], "content": s["content"][:MAX_DETAIL]}})
        if turn.status == "needs_approval":
            events += [{"event": "approval_requested", "detail": {"tool": p["name"], "args": p["args"]}}
                       for p in turn.pending]
        else:
            events.append({"event": "answer", "detail": self._text(turn.answer)})
        with self.db() as conn:
            for p in turn.pending:
                conn.execute("INSERT INTO agent.approvals (thread_id, tool, payload) VALUES (%s, %s, %s)",
                             (turn.thread_id, p["name"], json.dumps(p["args"])))
            with conn.cursor() as cur:
                cur.executemany("INSERT INTO agent.audit_log (thread_id, trace_id, event, detail) VALUES (%s, %s, %s, %s)",
                                [(turn.thread_id, trace, e["event"], json.dumps(e["detail"], default=str)) for e in events])

    def _claim(self, thread_id: str, approved: bool, by: str) -> list[int]:
        if self.db is None:
            return []
        sql = """UPDATE agent.approvals SET status = %s, decided_by = %s, decided_at = now()
                 WHERE thread_id = %s AND status = 'pending' RETURNING id"""
        with self.db() as conn:
            ids = [r[0] for r in conn.execute(sql, ("approved" if approved else "rejected", by, thread_id)).fetchall()]
        if not ids:  # nothing pending, or another request already decided it (double click)
            raise ValueError(f"Thread {thread_id} has nothing waiting for approval.")
        return ids

    def _unclaim(self, ids: list[int]) -> None:
        if self.db is None or not ids:
            return
        with self.db() as conn:
            conn.execute("UPDATE agent.approvals SET status = 'pending', decided_by = NULL, decided_at = NULL "
                         "WHERE id = ANY(%s)", (ids,))
