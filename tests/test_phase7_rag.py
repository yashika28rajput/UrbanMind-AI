from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_knowledge_graph_seeded_relationships() -> None:
    response = client.post(
        "/api/v1/knowledge-graph/query",
        json={"entity": "PM2.5", "entity_type": "Pollutant"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["count"] >= 1
    assert any(item["relationship"] == "ASSOCIATED_WITH" and item["target"] == "Respiratory Risk" for item in data["results"])


def test_rag_query_returns_grounded_sources() -> None:
    response = client.post(
        "/api/v1/rag/query",
        json={
            "query": "How can green infrastructure reduce PM2.5 risk in Delhi?",
            "city": "Delhi",
            "top_k": 5,
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert data["grounded"] is True
    assert len(data["sources"]) >= 1


def test_rag_search_requires_non_empty_query() -> None:
    response = client.post("/api/v1/rag/search", json={"query": "", "top_k": 5})
    assert response.status_code == 400
