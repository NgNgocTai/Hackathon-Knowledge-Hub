from app.embedding.models import Chunk
from app.graph.models import GraphNode
from app.storage.interfaces import SearchResult


def test_chunk_payload_round_trip():
    chunk = Chunk(
        chunk_id="chunk-1",
        content="def hello(): pass",
        entity_name="hello",
        chunk_type="code_function",
        source_file="app/example.py",
        source_hash="sha256:test",
        line_start=1,
        line_end=1,
        language="python",
        version="dev",
        embedding=[0.1, 0.2],
    )

    restored = Chunk.from_payload(chunk.chunk_id, chunk.payload(), chunk.embedding)

    assert restored == chunk


def test_search_result_exposes_chunk_view():
    result = SearchResult(
        chunk_id="chunk-1",
        score=0.9,
        payload={
            "content": "hello",
            "entity_name": "hello",
            "chunk_type": "doc_section",
            "source_file": "README.md",
            "source_hash": "sha256:test",
            "language": "markdown",
            "version": "dev",
        },
    )

    assert result.chunk.content == "hello"
    assert result.chunk.source_file == "README.md"


def test_graph_node_is_plain_contract_object():
    node = GraphNode("Function", {"qualified_name": "Service.run"})

    assert node.label == "Function"
    assert node.properties["qualified_name"] == "Service.run"
