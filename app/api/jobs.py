import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal


JobStatus = Literal["queued", "processing", "completed", "failed"]


@dataclass
class IngestJob:
    job_id: str
    status: JobStatus
    files: list[str]
    files_processed: int = 0
    files_failed: int = 0
    failed_files: list[dict] = field(default_factory=list)
    chunks_created: int = 0
    nodes_created: int = 0
    edges_created: int = 0
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


@dataclass
class SyncJob:
    job_id: str
    status: JobStatus
    scope: str
    path: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class JobRegistry:
    def __init__(self):
        self._jobs: dict[str, IngestJob] = {}
        self._sync_jobs: dict[str, SyncJob] = {}
        self._queue: asyncio.Queue[str] = asyncio.Queue()

    def submit(self, files: list[str]) -> IngestJob:
        job = IngestJob(job_id=str(uuid.uuid4()), status="queued", files=files)
        self._jobs[job.job_id] = job
        self._queue.put_nowait(job.job_id)
        return job

    def get(self, job_id: str) -> IngestJob | None:
        return self._jobs.get(job_id)

    def submit_sync(self, scope: str, path: str | None = None) -> SyncJob:
        job = SyncJob(job_id=str(uuid.uuid4()), status="queued", scope=scope, path=path)
        self._sync_jobs[job.job_id] = job
        return job

    def get_sync(self, job_id: str) -> SyncJob | None:
        return self._sync_jobs.get(job_id)

    def update_sync(self, job_id: str, **kwargs) -> None:
        job = self._sync_jobs[job_id]
        for key, value in kwargs.items():
            setattr(job, key, value)

    def update(self, job_id: str, **kwargs) -> None:
        job = self._jobs[job_id]
        for key, value in kwargs.items():
            setattr(job, key, value)

    async def next_job_id(self) -> str:
        return await self._queue.get()

    def task_done(self) -> None:
        self._queue.task_done()


job_registry = JobRegistry()


def utc_now() -> datetime:
    return datetime.now(UTC)
