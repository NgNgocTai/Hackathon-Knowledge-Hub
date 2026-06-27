import pytest

from app.embedding.models import Chunk
from app.graph.models import GraphNode
from app.retrieval.models import RetrievalOptions, RetrievalResult
from app.retrieval.retriever import HybridRetriever
from app.storage.interfaces import SearchResult


class FakeEmbedder:
    def embed(self, texts):
        return [[1.0, 0.0] for _ in texts]

    def dimension(self):
        return 2


class FakeVectorStore:
    def __init__(self):
        self.chunks = {
            "vector-1": Chunk(
                "vector-1",
                "def get_movie(): pass",
                "get_movie",
                "code_function",
                "app/routers/movies.py",
                "sha256:a",
                1,
                1,
                "python",
                "dev",
            ),
            "graph-1": Chunk(
                "graph-1",
                "def get_current_user(): pass",
                "get_current_user",
                "code_function",
                "app/services/auth.py",
                "sha256:b",
                1,
                1,
                "python",
                "dev",
            ),
        }

    def search(self, query_vector, top_k, filters=None, score_threshold=0.5):
        chunk = self.chunks["vector-1"]
        return [SearchResult("vector-1", 0.9, chunk.payload())]

    def fetch(self, chunk_ids):
        return [self.chunks[chunk_id] for chunk_id in chunk_ids if chunk_id in self.chunks]


class FakeGraphStore:
    def expand(self, entity_names, max_hops=2, rel_types=None, max_nodes=50):
        return [
            GraphNode(
                "Function",
                {
                    "qualified_name": "get_current_user",
                    "file_path": "app/services/auth.py",
                    "chunk_id": "graph-1",
                    "hop": 1,
                    "relationship": "CALLS",
                },
            )
        ]


def test_hybrid_retriever_fuses_vector_and_graph_results():
    retriever = HybridRetriever(FakeVectorStore(), FakeGraphStore(), FakeEmbedder())

    results = retriever.query("How does movies API authenticate users?", top_k=5)

    assert [result.chunk_id for result in results] == ["vector-1", "graph-1"]
    assert results[0].relevance_score == pytest.approx(0.63)
    assert results[1].relevance_score == pytest.approx(0.3)
    assert results[1].graph_context[0]["entity"] == "get_current_user"


def test_retriever_filters_below_similarity_threshold():
    class LowScoreVectorStore(FakeVectorStore):
        def search(self, query_vector, top_k, filters=None, score_threshold=0.5):
            chunk = self.chunks["vector-1"]
            return [SearchResult("vector-1", 0.2, chunk.payload())]

    retriever = HybridRetriever(LowScoreVectorStore(), FakeGraphStore(), FakeEmbedder())

    results = retriever.query("irrelevant", top_k=5)

    assert results == []


def test_retriever_gracefully_degrades_when_graph_fails():
    class FailingGraphStore:
        def expand(self, *args, **kwargs):
            raise RuntimeError("graph down")

    retriever = HybridRetriever(FakeVectorStore(), FailingGraphStore(), FakeEmbedder())

    results = retriever.query("movies", top_k=5)

    assert len(results) == 1
    assert results[0].chunk_id == "vector-1"


def test_retriever_validates_query():
    retriever = HybridRetriever(FakeVectorStore(), FakeGraphStore(), FakeEmbedder())

    with pytest.raises(ValueError):
        retriever.query("", top_k=5)


def test_context_builder_sorts_and_trims():
    from app.api.context_builder import ContextBuilder

    results = [
        RetrievalResult("doc", "one two", 0.8, 0.8, 0.0, {"chunk_type": "doc_section"}),
        RetrievalResult("code", "one two three", 0.8, 0.8, 0.0, {"chunk_type": "code_function"}),
        RetrievalResult("low", " ".join(["x"] * 20), 0.1, 0.1, 0.0, {"chunk_type": "doc_section"}),
    ]

    built = ContextBuilder().build(results, token_limit=6)

    assert [result.chunk_id for result in built] == ["code", "doc"]
