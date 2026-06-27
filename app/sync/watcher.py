from collections.abc import Callable

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from app.sync.models import SyncEventType


class _ChangeHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable[[str, SyncEventType], None]):
        self.callback = callback

    def on_created(self, event):
        if not event.is_directory:
            self.callback(event.src_path, "created")

    def on_modified(self, event):
        if not event.is_directory:
            self.callback(event.src_path, "modified")

    def on_deleted(self, event):
        if not event.is_directory:
            self.callback(event.src_path, "deleted")


class FileWatcher:
    def __init__(self):
        self._observer: Observer | None = None

    def start(self, watch_paths: list[str], callback: Callable[[str, SyncEventType], None]) -> None:
        self._observer = Observer()
        handler = _ChangeHandler(callback)
        for path in watch_paths:
            self._observer.schedule(handler, path, recursive=True)
        self._observer.start()
        self._observer.join()

    def stop(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
