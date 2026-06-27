import logging

from app.embedding.embedder import EmbeddingProvider
from app.embedding.models import Chunk
from app.graph.models import GraphNode
from app.retrieval.models import RetrievalOptions, RetrievalResult
from app.storage.interfaces import GraphStore, SearchResult, VectorStore

logger = logging.getLogger(__name__)


class HybridRetriever:
    def __init__(
        self,
        vector_store: VectorStore,
        graph_store: GraphStore,
        embedding_provider: EmbeddingProvider,
    ):
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.embedding_provider = embedding_provider

    def query(
        self,
        query_text: str,
        top_k: int = 5,
        options: RetrievalOptions | None = None,
    ) -> list[RetrievalResult]:
        options = options or RetrievalOptions()
        self._validate_query(query_text, top_k)

        query_vector = self._embed_query(query_text)
        vector_results = self._vector_search(query_vector, top_k * 2, self._filters(options), options)
        vector_results = [
            result for result in vector_results if result.score >= options.similarity_threshold
        ]
        graph_nodes: list[GraphNode] = []

        if options.enable_graph_expansion and vector_results:
            entity_names = self._entity_names(vector_results)
            try:
                graph_nodes = self._graph_expand(entity_names, options)
            except Exception as exc:
                logger.warning("Graph expansion failed; falling back to vector-only retrieval: %s", exc)

        fused = self._score_fusion(vector_results, graph_nodes, options)
        return fused[:top_k]

    def _embed_query(self, query_text: str) -> list[float]:
        return self.embedding_provider.embed([query_text])[0]

    def _vector_search(
        self,
        query_vector: list[float],
        top_k: int,
        filters: dict | None,
        options: RetrievalOptions,
    ) -> list[SearchResult]:
        return self.vector_store.search(
            query_vector=query_vector,
            top_k=top_k,
            filters=filters,
            score_threshold=options.similarity_threshold,
        )

    def _graph_expand(self, entity_names: list[str], options: RetrievalOptions) -> list[GraphNode]:
        nodes = self.graph_store.expand(
            entity_names=entity_names,
            max_hops=options.max_hops,
            rel_types=["CALLS", "IMPLEMENTS", "DESCRIBES"],
            max_nodes=options.max_graph_nodes,
        )
        inherit_nodes = self.graph_store.expand(
            entity_names=entity_names,
            max_hops=options.inherit_hops,
            rel_types=["INHERITS"],
            max_nodes=options.max_graph_nodes,
        )
        return (nodes + inherit_nodes)[: options.max_graph_nodes]

    def _score_fusion(
        self,
        vector_results: list[SearchResult],
        graph_nodes: list[GraphNode],
        options: RetrievalOptions,
    ) -> list[RetrievalResult]:
        vector_map = {result.chunk_id: result for result in vector_results if result.score >= options.similarity_threshold}
        graph_score_map = self._graph_score_map(graph_nodes)
        graph_context_map = self._graph_context_map(graph_nodes)
        graph_chunks = self._fetch_graph_chunks(list(graph_score_map.keys()))
        graph_chunk_map = {chunk.chunk_id: chunk for chunk in graph_chunks}

        all_chunk_ids = set(vector_map) | set(graph_chunk_map)
        results: list[RetrievalResult] = []
        for chunk_id in all_chunk_ids:
            vector_result = vector_map.get(chunk_id)
            graph_chunk = graph_chunk_map.get(chunk_id)
            chunk = vector_result.chunk if vector_result else graph_chunk
            if chunk is None:
                continue

            vector_score = vector_result.score if vector_result else 0.0
            graph_score = graph_score_map.get(chunk_id, 0.0)
            final_score = options.vector_weight * vector_score + options.graph_weight * graph_score
            results.append(
                RetrievalResult(
                    chunk_id=chunk_id,
                    content=chunk.content,
                    relevance_score=final_score,
                    vector_score=vector_score,
                    graph_score=graph_score,
                    metadata=self._metadata(chunk),
                    graph_context=graph_context_map.get(chunk_id, []),
                )
            )

        results.sort(key=lambda result: result.relevance_score, reverse=True)
        return results

    def _fetch_graph_chunks(self, chunk_ids: list[str]) -> list[Chunk]:
        if not chunk_ids:
            return []
        return self.vector_store.fetch(chunk_ids)

    def _graph_score_map(self, graph_nodes: list[GraphNode]) -> dict[str, float]:
        scores: dict[str, float] = {}
        for node in graph_nodes:
            chunk_id = node.properties.get("chunk_id")
            if not chunk_id:
                continue
            hop = node.properties.get("hop", 1)
            score = 1.0 if hop <= 1 else 0.5
            scores[chunk_id] = max(scores.get(chunk_id, 0.0), score)
        return scores

    def _graph_context_map(self, graph_nodes: list[GraphNode]) -> dict[str, list[dict]]:
        context: dict[str, list[dict]] = {}
        seen: set[tuple[str, str | None, str | None, int]] = set()
        for node in graph_nodes:
            chunk_id = node.properties.get("chunk_id")
            if not chunk_id:
                continue
            item = (
                node.properties.get("qualified_name") or node.properties.get("name"),
                node.properties.get("file_path") or node.properties.get("source_file"),
                node.properties.get("relationship"),
                node.properties.get("hop", 1),
            )
            if (chunk_id, *item) in seen:
                continue
            seen.add((chunk_id, *item))
            context.setdefault(chunk_id, []).append(
                {
                    "entity": item[0],
                    "file": item[1],
                    "relationship": item[2],
                    "hop": item[3],
                }
            )
        return context

    def _entity_names(self, vector_results: list[SearchResult]) -> list[str]:
        names = []
        for result in vector_results:
            entity_name = result.payload.get("entity_name")
            if entity_name:
                names.append(entity_name)
        return list(dict.fromkeys(names))

    def _filters(self, options: RetrievalOptions) -> dict | None:
        filters = {}
        if options.chunk_type_filter:
            filters["chunk_type"] = options.chunk_type_filter
        if options.language_filter:
            filters["language"] = options.language_filter
        return filters or None

    def _metadata(self, chunk: Chunk) -> dict:
        return {
            "source_file": chunk.source_file,
            "entity_name": chunk.entity_name,
            "chunk_type": chunk.chunk_type,
            "line_start": chunk.line_start,
            "line_end": chunk.line_end,
            "language": chunk.language,
            "version": chunk.version,
        }

    def _validate_query(self, query_text: str, top_k: int) -> None:
        if not query_text.strip():
            raise ValueError("Query must not be empty")
        if len(query_text) > 2000:
            raise ValueError("Query too long (max 2000 chars)")
        if top_k < 1 or top_k > 20:
            raise ValueError("top_k must be between 1 and 20")
