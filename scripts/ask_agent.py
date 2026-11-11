"""Talk to the agent from PowerShell. Conversations are saved in Postgres, so a paused thread
can be approved or rejected later, from a new window, even after a restart. Every turn is recorded
in agent.audit_log and every pause in agent.approvals (same AgentService as the API).

Usage:
  uv run python scripts/ask_agent.py "Where is shipment SHP-2207?"
  uv run python scripts/ask_agent.py "Open a credit ticket for ORD-1043 for the amount the policy allows." --thread t1
  uv run python scripts/ask_agent.py --thread t1 --approve
  uv run python scripts/ask_agent.py --thread t1 --reject "Customer already got a goodwill credit"
  uv run python scripts/ask_agent.py --thread t1 --history
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent.checkpoint import postgres_checkpointer  # noqa: E402
from core.agent.graph import AgentTurn, agent_model, agent_tools, build_agent, run_config  # noqa: E402
from core.agent.service import AgentService  # noqa: E402
from core.config import load_engagement  # noqa: E402
from core.db.connection import connect  # noqa: E402
from core.llm.factory import get_embeddings  # noqa: E402


def short(text: str, width: int = 150) -> str:
    text = " ".join(text.split())
    return text if len(text) <= width else text[: width - 3] + "..."


def show(turn: AgentTurn) -> None:
    print(f"thread: {turn.thread_id}")
    for s in turn.steps:
        if "call" in s:
            print(f"  -> {s['call']} {short(json.dumps(s['args']))}")
        else:
            print(f"  <- {s['result']}: {short(s['content'])}")
    if turn.status == "needs_approval":
        for p in turn.pending:
            print(f"\nPAUSED - {p['name']} needs human approval. Arguments:")
            print(json.dumps(p["args"], indent=2))
        print(f'\nApprove:  uv run python scripts/ask_agent.py --thread {turn.thread_id} --approve')
        print(f'Reject:   uv run python scripts/ask_agent.py --thread {turn.thread_id} --reject "reason"')
    else:
        print(f"\nANSWER:\n{turn.answer}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the FDE agent a question.")
    parser.add_argument("message", nargs="?", help="your question or request")
    parser.add_argument("--thread", default=None, help="conversation id (new one if omitted)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--approve", action="store_true", help="approve the paused tool call")
    group.add_argument("--reject", metavar="REASON", help="reject the paused tool call")
    group.add_argument("--history", action="store_true", help="print the saved conversation")
    args = parser.parse_args()

    cfg = load_engagement(os.environ.get("ENGAGEMENT", "demo-logistics"))
    thread = args.thread or f"cli-{uuid.uuid4().hex[:8]}"
    tools = agent_tools(cfg, get_embeddings(cfg.embeddings))
    with postgres_checkpointer() as saver:
        agent = build_agent(cfg, tools, agent_model(cfg), checkpointer=saver)
        service = AgentService(cfg, agent, db=lambda: connect(vector=False))
        user = os.environ.get("USERNAME") or os.environ.get("USER") or "cli"
        if args.history:
            for m in agent.get_state(run_config(cfg, thread)).values.get("messages", []):
                calls = getattr(m, "tool_calls", None)
                print(f"[{m.type}] {short(m.text or json.dumps(calls), 200)}")
            return
        try:
            if args.approve or args.reject is not None:
                turn = service.decide(thread, approved=args.approve, by=user, reason=args.reject or "")
            elif args.message:
                turn = service.chat(thread, args.message, user=user)
            else:
                parser.print_help()
                return
        except ValueError as exc:  # e.g. approving a thread that is not paused
            print(f"Cannot do that: {exc}")
            return
        show(turn)


if __name__ == "__main__":
    main()
