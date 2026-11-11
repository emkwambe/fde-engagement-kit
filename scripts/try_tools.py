"""Call one agent tool by hand, exactly as the agent will (guardrails ON by default).

Usage:
  uv run python scripts/try_tools.py getShipment '{"shipment_id": "SHP-2207"}'
  uv run python scripts/try_tools.py query_ops_db '{"query": "SELECT count(*) FROM orders"}'
  uv run python scripts/try_tools.py search_documents '{"query": "carrier performance Q3"}'
  add --raw at the end to see the result WITHOUT guardrails (what the model would have seen before Day 3)
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import ValidationError  # noqa: E402

from core.agent.graph import agent_tools  # noqa: E402
from core.config import load_engagement  # noqa: E402
from core.config.schema import Guardrails  # noqa: E402
from core.llm.factory import get_embeddings  # noqa: E402
from core.toolgen.registry import requires_approval  # noqa: E402


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--raw"]
    raw = "--raw" in sys.argv
    if len(args) < 2:
        print(__doc__)
        return
    name, raw_args = args[0], args[1]
    cfg = load_engagement(os.environ.get("ENGAGEMENT", "demo-logistics"))
    if raw:
        cfg = cfg.model_copy(update={"guardrails": Guardrails(pii_redaction=[], injection_filter=False)})
        print("NOTE: guardrails OFF (--raw)")
    tools = {t.name: t for t in agent_tools(cfg, get_embeddings(cfg.embeddings))}
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
