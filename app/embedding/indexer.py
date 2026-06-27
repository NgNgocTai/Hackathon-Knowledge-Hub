from app.embedding.embedder import EmbeddingProvider
from app.embedding.models import Chunk
from app.storage.interfaces import VectorStore


class ChunkIndexer:
    def __init__(self, embedder: EmbeddingProvider, store: VectorStore):
        self.embedder = embedder
        self.store = store

    def index(self, chunks: list[Chunk]) -> list[Chunk]:
        indexable_chunks = [chunk for chunk in chunks if chunk.content.strip()]
        if not indexable_chunks:
            return []

        embeddings = self.embedder.embed([chunk.content for chunk in indexable_chunks])
        for chunk, embedding in zip(indexable_chunks, embeddings, strict=True):
            chunk.embedding = embedding

        self.store.upsert(indexable_chunks)
        return indexable_chunks

    def delete_by_file(self, source_file: str) -> int:
        return self.store.delete_by_file(source_file)
