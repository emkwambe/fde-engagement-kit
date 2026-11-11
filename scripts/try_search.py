"""Compare vector vs hybrid retrieval for a question.

Usage:  uv run python scripts/try_search.py "Regional Express Charlotte"
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import load_engagement  # noqa: E402
from core.db.connection import connect  # noqa: E402
from core.llm.factory import get_embeddings  # noqa: E402
from core.retrieval.search import search  # noqa: E402


def main() -> None:
    question = " ".join(sys.argv[1:]) or "What credit does a Gold customer get per day late?"
    cfg = load_engagement(os.environ.get("ENGAGEMENT", "demo-logistics"))
    vector = get_embeddings(cfg.embeddings).embed_query(question)
    print(f"Question: {question}\n")
    with connect() as conn:
        for hybrid in (False, True):
            print("HYBRID (vector + full text, RRF)" if hybrid else "VECTOR ONLY")
            results = search(conn, engagement=cfg.engagement.name, query_text=question,
                             query_vector=vector, top_k=cfg.retrieval.top_k, hybrid=hybrid)
            for i, r in enumerate(results, 1):
                print(f"  {i}. {r.document_id:<30} {r.section[:28]:<28} score={r.score:.3f} sim={r.similarity:.3f}")
            print()


if __name__ == "__main__":
    main()
