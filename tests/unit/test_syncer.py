import pytest

from app.sync.syncer import SyncEvictionService
from app.storage.exceptions import VectorStoreError


class FakeParserRegistry:
    def get_parser(self, file_path):
        raise AssertionError("parser should not be called for deleted files")


class FakeChunkIndexer:
    pass


class FakeGraphIndexer:
    pass


class FakeGraphStore:
    def __init__(self):
        self.calls = []
        self.restored = False

    def fetch_nodes_by_file(self, file_path):
        self.calls.append("backup_graph")
        return ["node"], ["edge"]

    def delete_by_file(self, file_path):
        self.calls.append("delete_graph")
        return 1, 2

    def restore(self, nodes, edges):
        self.calls.append("restore_graph")
        self.restored = True


class FakeVectorStore:
    def __init__(self, fail_delete=False):
        self.fail_delete = fail_delete
        self.calls = []

    def delete_by_file(self, source_file):
        self.calls.append("delete_vector")
        if self.fail_delete:
            raise VectorStoreError("vector down")
        return 3


@pytest.mark.asyncio
async def test_sync_file_deletes_graph_before_vector():
    graph_store = FakeGraphStore()
    vector_store = FakeVectorStore()
    service = SyncEvictionService(
        FakeParserRegistry(),
        FakeChunkIndexer(),
        FakeGraphIndexer(),
        vector_store,
        graph_store,
    )

    result = await service.sync_file("app/deleted.py", "deleted")

    assert result.success is True
    assert graph_store.calls == ["backup_graph", "delete_graph"]
    assert vector_store.calls == ["delete_vector"]
    assert result.nodes_deleted == 1
    assert result.chunks_deleted == 3


@pytest.mark.asyncio
async def test_sync_file_restores_graph_when_vector_delete_fails():
    graph_store = FakeGraphStore()
    vector_store = FakeVectorStore(fail_delete=True)
    service = SyncEvictionService(
        FakeParserRegistry(),
        FakeChunkIndexer(),
        FakeGraphIndexer(),
        vector_store,
        graph_store,
    )

    result = await service.sync_file("app/broken.py", "deleted")

    assert result.success is False
    assert graph_store.restored is True
    assert graph_store.calls == ["backup_graph", "delete_graph", "restore_graph"]
