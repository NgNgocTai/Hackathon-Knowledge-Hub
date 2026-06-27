from fastapi import FastAPI

from app.api.routers import health
from app.config import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="Knowledge Hub",
        description="Long-term memory and context provider for AI agents in SDLC.",
        version="0.1.0",
    )
    app.include_router(health.router)
    return app


app = create_app()
