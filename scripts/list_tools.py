"""List every tool the agent gets for an engagement, generated from engagement.yaml.

Usage:  uv run python scripts/list_tools.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import load_engagement  # noqa: E402
from core.toolgen.registry import build_tools, requires_approval  # noqa: E402


def main() -> None:
    cfg = load_engagement(os.environ.get("ENGAGEMENT", "demo-logistics"))
    tools = build_tools(cfg)
    print(f"{len(tools)} tools for {cfg.engagement.name}\n")
    print(f"{'tool':<15} {'source':<8} {'call':<30} {'approval':<9} arguments")
    for t in tools:
        meta = t.metadata or {}
        args = ", ".join(t.args)
        call = f"{meta.get('method')} {meta.get('path')}"
        print(f"{t.name:<15} {meta.get('source'):<8} {call:<30} {'YES' if requires_approval(t) else 'no':<9} {args}")


if __name__ == "__main__":
    main()
