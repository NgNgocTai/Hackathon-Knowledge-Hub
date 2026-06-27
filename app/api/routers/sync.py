import uuid

from fastapi import APIRouter, HTTPException

from app.api.schemas.sync import SyncRequest, SyncResponse

router = APIRouter(tags=["sync"])


@router.post("/sync", response_model=SyncResponse, status_code=202)
def sync(request: SyncRequest) -> SyncResponse:
    if request.scope == "file" and not request.path:
        raise HTTPException(status_code=400, detail="path is required when scope=file")
    return SyncResponse(
        job_id=str(uuid.uuid4()),
        status="accepted",
        message="Sync job queued. Full sync implementation is provided by the sync module.",
    )
