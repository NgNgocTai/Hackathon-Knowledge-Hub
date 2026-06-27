from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.embedding.models import Chunk
from app.graph.models import GraphEdge, GraphNode


@dataclass
class SearchResult:
    chunk_id: str
    score: float
    payload: dict[str, Any] = field(default_factory=dict)
    vector: list[float] | None = None

    @property
    def chunk(self) -> Chunk:
        return Chunk.from_payload(self.chunk_id, self.payload, self.vector)


class VectorStore(ABC):
    @abstractmethod
    def upsert(self, chunks: list[Chunk]) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        query_vector: list[float],
        top_k: int,
        filters: dict | None = None,
        score_threshold: float = 0.5,
    ) -> list[SearchResult]:
        raise NotImplementedError

    @abstractmethod
    def delete_by_file(self, source_file: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def fetch(self, chunk_ids: list[str]) -> list[Chunk]:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> bool:
        raise NotImplementedError


class GraphStore(ABC):
    @abstractmethod
    def merge_nodes(self, nodes: list[GraphNode]) -> None:
        raise NotImplementedError

    @abstractmethod
    def merge_edges(self, edges: list[GraphEdge]) -> None:
        raise NotImplementedError

    @abstractmethod
    def expand(
        self,
        entity_names: list[str],
        max_hops: int = 2,
        rel_types: list[str] | None = None,
        max_nodes: int = 50,
    ) -> list[GraphNode]:
        raise NotImplementedError

    @abstractmethod
    def delete_by_file(self, file_path: str) -> tuple[int, int]:
        raise NotImplementedError

    @abstractmethod
    def fetch_nodes_by_file(self, file_path: str) -> tuple[list[GraphNode], list[GraphEdge]]:
        raise NotImplementedError

    @abstractmethod
    def restore(self, nodes: list[GraphNode], edges: list[GraphEdge]) -> None:
        raise NotImplementedError

    @abstractmethod
    def link_chunk_ids(self, chunk_mapping: dict[str, str]) -> None:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> bool:
        raise NotImplementedError
