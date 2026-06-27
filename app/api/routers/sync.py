import asyncio

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_sync_service
from app.api.jobs import job_registry, utc_now
from app.api.schemas.sync import SyncRequest, SyncResponse, SyncStatusResponse
from app.sync.syncer import SyncEvictionService

router = APIRouter(tags=["sync"])


@router.post("/sync", response_model=SyncResponse, status_code=202)
async def sync(request: SyncRequest, sync_service: SyncEvictionService = Depends(get_sync_service)) -> SyncResponse:
    if request.scope == "file" and not request.path:
        raise HTTPException(status_code=400, detail="path is required when scope=file")
    job = job_registry.submit_sync(request.scope, request.path)
    asyncio.create_task(_process_sync_job(job.job_id, request, sync_service))
    return SyncResponse(
        job_id=job.job_id,
        status=job.status,
        message="Sync job queued.",
    )


@router.get("/sync/{job_id}", response_model=SyncStatusResponse)
def sync_status(job_id: str) -> SyncStatusResponse:
    job = job_registry.get_sync(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return SyncStatusResponse(
        job_id=job.job_id,
        status=job.status,
        scope=job.scope,
        path=job.path,
        error=job.error,
    )


async def _process_sync_job(job_id: str, request: SyncRequest, sync_service: SyncEvictionService) -> None:
    job_registry.update_sync(job_id, status="processing", started_at=utc_now())
    try:
        if request.scope == "file" and request.path:
            await sync_service.sync_file(request.path, "modified")
        else:
            await sync_service.sync_all([request.path or "."], dry_run=request.dry_run)
        job_registry.update_sync(job_id, status="completed", finished_at=utc_now())
    except Exception as exc:
        job_registry.update_sync(job_id, status="failed", error=str(exc), finished_at=utc_now())
