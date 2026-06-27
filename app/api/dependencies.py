from functools import lru_cache

from app.config import Settings, get_settings
from app.embedding.factory import create_embedding_provider
from app.embedding.indexer import ChunkIndexer
from app.graph.indexer import GraphIndexer
from app.parser.registry import ParserRegistry
from app.retrieval.retriever import HybridRetriever
from app.storage.neo4j_store import Neo4jGraphStore
from app.storage.qdrant_store import QdrantVectorStore


def get_app_settings() -> Settings:
    return get_settings()


@lru_cache
def get_parser_registry() -> ParserRegistry:
    return ParserRegistry()


@lru_cache
def get_embedding_provider():
    return create_embedding_provider(get_settings())


@lru_cache
def get_vector_store():
    settings = get_settings()
    return QdrantVectorStore(settings.qdrant_url, vector_size=get_embedding_provider().dimension())


@lru_cache
def get_graph_store():
    settings = get_settings()
    return Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)


def get_chunk_indexer() -> ChunkIndexer:
    return ChunkIndexer(get_embedding_provider(), get_vector_store())


def get_graph_indexer() -> GraphIndexer:
    return GraphIndexer(get_graph_store())


def get_retriever() -> HybridRetriever:
    return HybridRetriever(get_vector_store(), get_graph_store(), get_embedding_provider())
