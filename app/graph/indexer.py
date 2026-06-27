from app.graph.models import GraphEdge, GraphNode
from app.storage.interfaces import GraphStore


class GraphIndexer:
    def __init__(self, store: GraphStore):
        self.store = store

    def index(self, nodes: list[GraphNode], edges: list[GraphEdge]) -> None:
        self.store.merge_nodes(nodes)
        self.store.merge_edges(edges)

    def link_chunk_ids(self, chunk_mapping: dict[str, str]) -> None:
        self.store.link_chunk_ids(chunk_mapping)

    def delete_by_file(self, file_path: str) -> tuple[int, int]:
        return self.store.delete_by_file(file_path)
