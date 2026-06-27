from datetime import UTC, datetime

import httpx
from fastapi import APIRouter
from neo4j import GraphDatabase

from app.api.schemas.health import DependencyHealth, HealthResponse
from app.config import get_settings

router = APIRouter(tags=["health"])


def _check_qdrant(qdrant_url: str) -> DependencyHealth:
    try:
        response = httpx.get(f"{qdrant_url.rstrip('/')}/collections", timeout=2.0)
        response.raise_for_status()
    except Exception as exc:
        return DependencyHealth(status="error", type="qdrant", message=str(exc))

    data = response.json()
    collections = data.get("result", {}).get("collections", [])
    return DependencyHealth(
        status="ok",
        type="qdrant",
        details={"collections": len(collections)},
    )


def _check_neo4j(uri: str, user: str, password: str) -> DependencyHealth:
    try:
        with GraphDatabase.driver(uri, auth=(user, password)) as driver:
            driver.verify_connectivity()
    except Exception as exc:
        return DependencyHealth(status="error", type="neo4j", message=str(exc))

    return DependencyHealth(status="ok", type="neo4j")


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    vector_db = _check_qdrant(settings.qdrant_url)
    graph_db = _check_neo4j(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    status = "ok" if vector_db.status == "ok" and graph_db.status == "ok" else "degraded"

    return HealthResponse(
        status=status,
        services={
            "api": "ok",
            "vector_db": vector_db,
            "graph_db": graph_db,
        },
        timestamp=datetime.now(UTC),
    )
