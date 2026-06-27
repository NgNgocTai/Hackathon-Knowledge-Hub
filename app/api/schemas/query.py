from typing import Any

from pydantic import BaseModel, Field


class QueryOptionsSchema(BaseModel):
    enable_graph_expansion: bool = True
    max_hops: int = Field(default=2, ge=1, le=2)
    filters: dict[str, list[str]] = Field(default_factory=dict)


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    options: QueryOptionsSchema = Field(default_factory=QueryOptionsSchema)


class RetrievalResultSchema(BaseModel):
    chunk_id: str
    content: str
    relevance_score: float
    score_breakdown: dict[str, float]
    metadata: dict[str, Any]
    graph_context: list[dict[str, Any]]


class QueryResponse(BaseModel):
    query: str
    results: list[RetrievalResultSchema]
    total_results: int
    retrieval_method: str = "hybrid"
    status: str | None = None
    message: str | None = None
