from typing import Literal

from pydantic import BaseModel, Field


SourceType = Literal["file", "directory", "git_repo"]


class IngestSource(BaseModel):
    type: SourceType
    path: str
    include_patterns: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)
    branch: str | None = None
    include_git_log: bool = False


class IngestOptions(BaseModel):
    force_reindex: bool = False


class IngestRequest(BaseModel):
    sources: list[IngestSource] = Field(min_length=1)
    options: IngestOptions = Field(default_factory=IngestOptions)


class IngestResponse(BaseModel):
    job_id: str
    status: str
    estimated_files: int
    message: str


class FailedFile(BaseModel):
    path: str
    error: str


class IngestStatusResponse(BaseModel):
    job_id: str
    status: str
    files_processed: int
    files_failed: int
    failed_files: list[FailedFile]
    chunks_created: int
    nodes_created: int
    edges_created: int
    error: str | None = None
