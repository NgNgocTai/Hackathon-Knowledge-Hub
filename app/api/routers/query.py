from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_retriever
from app.api.schemas.query import QueryRequest, QueryResponse, RetrievalResultSchema
from app.retrieval.models import RetrievalOptions
from app.retrieval.retriever import HybridRetriever
from app.storage.exceptions import VectorStoreError

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query_context(request: QueryRequest, retriever: HybridRetriever = Depends(get_retriever)) -> QueryResponse:
    options = RetrievalOptions(
        enable_graph_expansion=request.options.enable_graph_expansion,
        max_hops=request.options.max_hops,
        similarity_threshold=request.options.similarity_threshold,
        chunk_type_filter=request.options.filters.get("chunk_type"),
        language_filter=request.options.filters.get("language"),
    )
    try:
        results = retriever.query(request.query, top_k=request.top_k, options=options)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except VectorStoreError as exc:
        raise HTTPException(status_code=503, detail="Vector DB unavailable") from exc

    response_results = [
        RetrievalResultSchema(
            chunk_id=result.chunk_id,
            content=result.content,
            relevance_score=result.relevance_score,
            score_breakdown={"vector_score": result.vector_score, "graph_score": result.graph_score},
            metadata=result.metadata,
            graph_context=result.graph_context,
        )
        for result in results
    ]
    if not response_results:
        return QueryResponse(
            query=request.query,
            results=[],
            total_results=0,
            status="no_results",
            message="No relevant context found. Try rephrasing or check if relevant files have been ingested.",
        )
    return QueryResponse(query=request.query, results=response_results, total_results=len(response_results))
