from typing import Literal

from pydantic import BaseModel


class SyncRequest(BaseModel):
    scope: Literal["all", "file"]
    path: str | None = None
    dry_run: bool = False


class SyncResponse(BaseModel):
    job_id: str
    status: str
    message: str
