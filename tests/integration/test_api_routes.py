from fastapi.testclient import TestClient

from app.api.dependencies import get_retriever
from app.api.main import create_app
from app.retrieval.models import RetrievalResult


class FakeRetriever:
    def __init__(self, results=None):
        self.results = results if results is not None else []

    def query(self, query_text, top_k=5, options=None):
        return self.results[:top_k]


def _client_with_retriever(fake_retriever):
    app = create_app()
    app.dependency_overrides[get_retriever] = lambda: fake_retriever
    return TestClient(app)


def test_query_requires_api_key():
    client = _client_with_retriever(FakeRetriever())

    response = client.post("/query", json={"query": "hello", "top_k": 5})

    assert response.status_code == 401


def test_query_returns_results_with_api_key():
    client = _client_with_retriever(
        FakeRetriever(
            [
                RetrievalResult(
                    chunk_id="chunk-1",
                    content="def ingest(): pass",
                    relevance_score=0.9,
                    vector_score=0.9,
                    graph_score=0.0,
                    metadata={
                        "source_file": "app/api/routers/ingest.py",
                        "entity_name": "ingest",
                        "chunk_type": "code_function",
                    },
                    graph_context=[],
                )
            ]
        )
    )

    response = client.post(
        "/query",
        headers={"X-API-Key": "dev-secret-key"},
        json={"query": "How does ingest work?", "top_k": 5},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_results"] == 1
    assert body["results"][0]["chunk_id"] == "chunk-1"


def test_query_returns_no_results_status():
    client = _client_with_retriever(FakeRetriever())

    response = client.post(
        "/query",
        headers={"X-API-Key": "dev-secret-key"},
        json={"query": "unknown", "top_k": 5},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "no_results"
    assert body["results"] == []
