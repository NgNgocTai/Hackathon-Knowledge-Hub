import asyncio
import hashlib
import time
from pathlib import Path

from app.embedding.chunker import Chunker
from app.embedding.indexer import ChunkIndexer
from app.graph.extractor import EntityExtractor
from app.graph.indexer import GraphIndexer
from app.parser.registry import ParserRegistry
from app.storage.exceptions import GraphStoreError, VectorStoreError
from app.storage.interfaces import GraphStore, VectorStore
from app.sync.models import SyncEventType, SyncReport, SyncResult


class SyncEvictionService:
    def __init__(
        self,
        parser: ParserRegistry,
        chunk_indexer: ChunkIndexer,
        graph_indexer: GraphIndexer,
        vector_store: VectorStore,
        graph_store: GraphStore,
    ):
        self.parser = parser
        self.chunker = Chunker()
        self.extractor = EntityExtractor()
        self.chunk_indexer = chunk_indexer
        self.graph_indexer = graph_indexer
        self.vector_store = vector_store
        self.graph_store = graph_store

    async def sync_file(self, file_path: str, event_type: SyncEventType) -> SyncResult:
        backup_nodes, backup_edges = self.graph_store.fetch_nodes_by_file(file_path)

        try:
            nodes_deleted, _edges_deleted = self.graph_store.delete_by_file(file_path)
        except GraphStoreError as exc:
            return SyncResult(file_path, event_type, success=False, error=str(exc))

        try:
            chunks_deleted = self.vector_store.delete_by_file(file_path)
        except VectorStoreError as exc:
            self.graph_store.restore(backup_nodes, backup_edges)
            return SyncResult(
                file_path,
                event_type,
                success=False,
                nodes_deleted=nodes_deleted,
                error=str(exc),
            )

        if event_type == "deleted" or not Path(file_path).exists():
            return SyncResult(
                file_path,
                "deleted",
                success=True,
                nodes_deleted=nodes_deleted,
                chunks_deleted=chunks_deleted,
            )

        try:
            nodes_created, chunks_created = await self._reingest(file_path)
        except Exception as exc:
            return SyncResult(
                file_path,
                event_type,
                success=False,
                nodes_deleted=nodes_deleted,
                chunks_deleted=chunks_deleted,
                error=str(exc),
            )

        return SyncResult(
            file_path,
            event_type,
            success=True,
            nodes_deleted=nodes_deleted,
            chunks_deleted=chunks_deleted,
            nodes_created=nodes_created,
            chunks_created=chunks_created,
        )

    async def sync_all(self, source_paths: list[str], dry_run: bool = False) -> SyncReport:
        started = time.perf_counter()
        results: list[SyncResult] = []
        files = self._scan_files(source_paths)
        for file_path in files:
            if dry_run:
                results.append(SyncResult(file_path, "modified", success=True))
                continue
            results.append(await self.sync_file(file_path, "modified"))

        return SyncReport(
            files_synced=sum(1 for result in results if result.success),
            files_failed=sum(1 for result in results if not result.success),
            results=results,
            duration_seconds=time.perf_counter() - started,
        )

    def compute_source_hash(self, file_path: str) -> str:
        return self._source_hash(file_path)

    async def _reingest(self, file_path: str) -> tuple[int, int]:
        source_hash = self._source_hash(file_path)
        parser = self.parser.get_parser(file_path)
        ir = parser.parse(file_path, source_hash)
        chunks = self.chunker.chunk(ir, version="dev")
        indexed_chunks = await asyncio.to_thread(self.chunk_indexer.index, chunks)
        nodes, edges = self.extractor.extract(ir)
        await asyncio.to_thread(self.graph_indexer.index, nodes, edges)
        chunk_mapping = {chunk.entity_name: chunk.chunk_id for chunk in indexed_chunks}
        await asyncio.to_thread(self.graph_indexer.link_chunk_ids, chunk_mapping)
        return len(nodes), len(indexed_chunks)

    def _scan_files(self, source_paths: list[str]) -> list[str]:
        files: list[str] = []
        for source_path in source_paths:
            path = Path(source_path)
            if path.is_file():
                files.append(str(path))
            elif path.is_dir():
                for pattern in ("*.py", "*.md", "*.pdf"):
                    files.extend(str(candidate) for candidate in path.rglob(pattern) if candidate.is_file())
        return list(dict.fromkeys(files))

    def _source_hash(self, file_path: str) -> str:
        return "sha256:" + hashlib.sha256(Path(file_path).read_bytes()).hexdigest()
