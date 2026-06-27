from app.api.main import create_app
from app.api.schemas.health import DependencyHealth
from fastapi.testclient import TestClient


def test_health_does_not_require_api_key(monkeypatch):
    monkeypatch.setattr(
        "app.api.routers.health._check_qdrant",
        lambda _url: DependencyHealth(status="error", type="qdrant"),
    )
    monkeypatch.setattr(
        "app.api.routers.health._check_neo4j",
        lambda _uri, _user, _password: DependencyHealth(status="error", type="neo4j"),
    )

    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200


def test_protected_endpoint_requires_api_key():
    response = TestClient(create_app()).post("/sync", json={"scope": "all"})

    assert response.status_code == 401
