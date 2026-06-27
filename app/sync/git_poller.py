import asyncio
from collections.abc import Callable
from datetime import UTC, datetime

from app.sync.models import SyncEventType


class GitPoller:
    def __init__(self, repo_path: str, interval_sec: int = 60):
        self.repo_path = repo_path
        self.interval_sec = interval_sec
        self._last_check = datetime.now(UTC)
        self._running = False

    async def start_polling(self, callback: Callable[[str, SyncEventType], None]) -> None:
        from git import Repo

        self._running = True
        repo = Repo(self.repo_path)
        while self._running:
            since = self._last_check
            self._last_check = datetime.now(UTC)
            for commit in repo.iter_commits(since=since.isoformat()):
                for file_path in commit.stats.files:
                    callback(file_path, "modified")
            await asyncio.sleep(self.interval_sec)

    def stop(self) -> None:
        self._running = False
