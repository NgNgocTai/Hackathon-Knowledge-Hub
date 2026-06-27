from dataclasses import dataclass, field
from typing import Literal


SyncEventType = Literal["created", "modified", "deleted"]


@dataclass
class SyncResult:
    file_path: str
    event_type: SyncEventType
    success: bool
    nodes_deleted: int = 0
    chunks_deleted: int = 0
    nodes_created: int = 0
    chunks_created: int = 0
    error: str | None = None


@dataclass
class SyncReport:
    files_synced: int
    files_failed: int
    results: list[SyncResult] = field(default_factory=list)
    duration_seconds: float = 0.0
