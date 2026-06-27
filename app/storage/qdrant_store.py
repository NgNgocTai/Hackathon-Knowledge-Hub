from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.embedding.models import Chunk
from app.storage.exceptions import VectorStoreError
from app.storage.interfaces import SearchResult, VectorStore


class QdrantVectorStore(VectorStore):
    def __init__(
        self,
        url: str,
        collection_name: str = "knowledge_chunks",
        vector_size: int = 768,
        distance: models.Distance = models.Distance.COSINE,
    ):
        self.client = QdrantClient(url=url)
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.distance = distance
        self.ensure_collection()

    def ensure_collection(self) -> None:
        try:
            collections = self.client.get_collections().collections
            if any(collection.name == self.collection_name for collection in collections):
                return
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(size=self.vector_size, distance=self.distance),
            )
            self.client.create_payload_index(self.collection_name, "source_file", models.PayloadSchemaType.KEYWORD)
            self.client.create_payload_index(self.collection_name, "chunk_type", models.PayloadSchemaType.KEYWORD)
        except Exception as exc:
            raise VectorStoreError(f"Failed to ensure Qdrant collection: {exc}") from exc

    def upsert(self, chunks: list[Chunk]) -> None:
        points = []
        for chunk in chunks:
            if chunk.embedding is None:
                continue
            points.append(
                models.PointStruct(
                    id=chunk.chunk_id,
                    vector=chunk.embedding,
                    payload=chunk.payload(),
                )
            )
        if not points:
            return
        try:
            self.client.upsert(collection_name=self.collection_name, points=points)
        except Exception as exc:
            raise VectorStoreError(f"Failed to upsert chunks into Qdrant: {exc}") from exc

    def search(
        self,
        query_vector: list[float],
        top_k: int,
        filters: dict | None = None,
        score_threshold: float = 0.5,
    ) -> list[SearchResult]:
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=self._build_filter(filters),
                limit=top_k,
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=False,
            )
        except Exception as exc:
            raise VectorStoreError(f"Qdrant search failed: {exc}") from exc

        return [
            SearchResult(chunk_id=str(point.id), score=point.score, payload=point.payload or {})
            for point in results
        ]

    def delete_by_file(self, source_file: str) -> int:
        qdrant_filter = models.Filter(
            must=[models.FieldCondition(key="source_file", match=models.MatchValue(value=source_file))]
        )
        try:
            count_result = self.client.count(self.collection_name, count_filter=qdrant_filter, exact=True)
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(filter=qdrant_filter),
            )
            return count_result.count
        except Exception as exc:
            raise VectorStoreError(f"Failed to delete chunks for {source_file}: {exc}") from exc

    def fetch(self, chunk_ids: list[str]) -> list[Chunk]:
        if not chunk_ids:
            return []
        try:
            points = self.client.retrieve(
                collection_name=self.collection_name,
                ids=chunk_ids,
                with_payload=True,
                with_vectors=True,
            )
        except Exception as exc:
            raise VectorStoreError(f"Failed to fetch chunks from Qdrant: {exc}") from exc

        chunks: list[Chunk] = []
        for point in points:
            vector = point.vector if isinstance(point.vector, list) else None
            chunks.append(Chunk.from_payload(str(point.id), point.payload or {}, vector))
        return chunks

    def health_check(self) -> bool:
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False

    def _build_filter(self, filters: dict | None) -> models.Filter | None:
        if not filters:
            return None

        conditions = []
        for key, value in filters.items():
            if value is None:
                continue
            if isinstance(value, list):
                conditions.append(models.FieldCondition(key=key, match=models.MatchAny(any=value)))
            else:
                conditions.append(models.FieldCondition(key=key, match=models.MatchValue(value=value)))

        return models.Filter(must=conditions) if conditions else None
