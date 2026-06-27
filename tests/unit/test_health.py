from fastapi.testclient import TestClient

from app.api.main import create_app
from app.api.schemas.health import DependencyHealth


def test_health_response_shape(monkeypatch):
    monkeypatch.setattr(
        "app.api.routers.health._check_qdrant",
        lambda _url: DependencyHealth(status="ok", type="qdrant"),
    )
    monkeypatch.setattr(
        "app.api.routers.health._check_neo4j",
        lambda _uri, _user, _password: DependencyHealth(status="ok", type="neo4j"),
    )

    client = TestClient(create_app())
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["services"]["api"] == "ok"
    assert body["services"]["vector_db"]["status"] == "ok"
    assert body["services"]["graph_db"]["status"] == "ok"
