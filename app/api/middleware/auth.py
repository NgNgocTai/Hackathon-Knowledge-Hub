from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings


EXCLUDED_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        settings = get_settings()
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key not in settings.api_keys:
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})

        return await call_next(request)
