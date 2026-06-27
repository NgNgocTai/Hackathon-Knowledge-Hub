from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ServiceStatus = Literal["ok", "error"]
OverallStatus = Literal["ok", "degraded"]


class DependencyHealth(BaseModel):
    status: ServiceStatus
    type: str
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: OverallStatus
    services: dict[str, str | DependencyHealth]
    timestamp: datetime
