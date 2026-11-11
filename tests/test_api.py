import pytest
from fastapi.testclient import TestClient

from core.api.main import app


def test_health_and_validation():
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["engagement"] == "demo-logistics"
        assert client.post("/ask", json={"thread_id": "t", "message": ""}).status_code == 422


@pytest.mark.db
@pytest.mark.day01
def test_ask_returns_cited_answer(conn, demo_cfg):
    """Day 1 behaviour: POST /ask answers from the documents only, with citations (/chat is the agent now)."""
    from core.ingest.documents import ingest_documents
    from core.llm.factory import get_embeddings

    ingest_documents(conn, demo_cfg, get_embeddings(demo_cfg.embeddings))
    conn.commit()
    with TestClient(app) as client:
        r = client.post("/ask", json={"thread_id": "t1", "message": "What credit does a Gold customer get per day late?"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert any(c["ref"] == "sla-policy.md#credits" for c in body["citations"])
