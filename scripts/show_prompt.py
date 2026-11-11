"""Print exactly what the model would receive for a question (system + human message).

Usage:  uv run python scripts/show_prompt.py "Gold credit"
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import load_engagement  # noqa: E402
from core.db.connection import connect  # noqa: E402
from core.llm.factory import get_embeddings  # noqa: E402
from core.rag.answer import build_messages  # noqa: E402
from core.retrieval.search import search  # noqa: E402


def main() -> None:
    question = " ".join(sys.argv[1:]) or "Gold credit"
    cfg = load_engagement(os.environ.get("ENGAGEMENT", "demo-logistics"))
    vector = get_embeddings(cfg.embeddings).embed_query(question)
    with connect() as conn:
        results = search(conn, engagement=cfg.engagement.name, query_text=question,
                         query_vector=vector, top_k=cfg.retrieval.top_k, hybrid=cfg.retrieval.hybrid)
    for message in build_messages(question, results, cfg.engagement.customer):
        print(f"===== {type(message).__name__} =====")
        print(message.content)
        print()


if __name__ == "__main__":
    main()
