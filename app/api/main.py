from fastapi import FastAPI

from app.api.middleware.auth import APIKeyAuthMiddleware
from app.api.routers import health, ingest, query, sync
from app.config import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="Knowledge Hub",
        description="Long-term memory and context provider for AI agents in SDLC.",
        version="0.1.0",
    )
    app.add_middleware(APIKeyAuthMiddleware)
    app.include_router(health.router)
    app.include_router(ingest.router)
    app.include_router(query.router)
    app.include_router(sync.router)
    return app


app = create_app()
