"""Call one generated tool by hand, exactly as the agent will.

Usage:
  uv run python scripts/try_tools.py getShipment '{"shipment_id": "SHP-2207"}'
  uv run python scripts/try_tools.py query_ops_db '{"query": "SELECT count(*) FROM orders"}'
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import ValidationError  # noqa: E402

from core.config import load_engagement  # noqa: E402
from core.toolgen.registry import build_tools, requires_approval  # noqa: E402


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        return
    name, raw_args = sys.argv[1], sys.argv[2]
    tools = {t.name: t for t in build_tools(load_engagement(os.environ.get("ENGAGEMENT", "demo-logistics")))}
    if name not in tools:
        print(f"Unknown tool '{name}'. Available: {', '.join(tools)}")
        return
    tool = tools[name]
    if requires_approval(tool):
        print(f"NOTE: {name} requires human approval when the agent uses it (Day 2 part 3).")
    try:
        print(tool.invoke(json.loads(raw_args)))
    except ValidationError as exc:
        print(f"Rejected before calling the system ({exc.error_count()} problem(s)):")
        for err in exc.errors():
            print(f"  {'.'.join(str(p) for p in err['loc'])}: {err['msg']}")


if __name__ == "__main__":
    main()
