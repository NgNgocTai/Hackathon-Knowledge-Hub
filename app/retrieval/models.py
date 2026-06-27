from dataclasses import dataclass, field


@dataclass
class RetrievalOptions:
    enable_graph_expansion: bool = True
    max_hops: int = 2
    inherit_hops: int = 1
    vector_weight: float = 0.7
    graph_weight: float = 0.3
    similarity_threshold: float = 0.5
    chunk_type_filter: list[str] | None = None
    language_filter: list[str] | None = None
    max_graph_nodes: int = 50


@dataclass
class RetrievalResult:
    chunk_id: str
    content: str
    relevance_score: float
    vector_score: float
    graph_score: float
    metadata: dict
    graph_context: list[dict] = field(default_factory=list)
