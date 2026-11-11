"""Print the agent's graph as Mermaid text (paste it into https://mermaid.live or a GitHub .md file).

Usage:  uv run python scripts/show_graph.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent.graph import agent_model, agent_tools, build_agent  # noqa: E402
from core.config import load_engagement  # noqa: E402
from core.llm.factory import get_embeddings  # noqa: E402


def main() -> None:
    cfg = load_engagement(os.environ.get("ENGAGEMENT", "demo-logistics"))
    tools = agent_tools(cfg, get_embeddings(cfg.embeddings), sql_schema_text="(not needed to draw the graph)")
    agent = build_agent(cfg, tools, agent_model(cfg))
    print(agent.get_graph().draw_mermaid())
    print(f"tools ({len(tools)}): {', '.join(t.name for t in tools)}")


if __name__ == "__main__":
    main()
