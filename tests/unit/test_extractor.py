from app.graph.extractor import EntityExtractor
from app.graph.indexer import GraphIndexer
from app.parser.models import IntermediateRepresentation, ParsedEntity, ParsedRelationship


def test_extractor_creates_nodes_edges_and_belongs_to_links():
    ir = IntermediateRepresentation(
        source_file="app/services/auth.py",
        source_hash="sha256:test",
        file_type="python",
        language_version="3.11",
        entities=[
            ParsedEntity("file", "auth.py", "app/services/auth.py", "app/services/auth.py", 1, 20, "", None, "python"),
            ParsedEntity("class", "AuthService", "AuthService", "app/services/auth.py", 1, 10, "", None, "python"),
            ParsedEntity(
                "function",
                "authenticate",
                "AuthService.authenticate",
                "app/services/auth.py",
                2,
                8,
                "",
                None,
                "python",
            ),
        ],
        relationships=[
            ParsedRelationship("AuthService", "BaseService", "INHERITS"),
            ParsedRelationship("AuthService.authenticate", "AuthDataManager.get_user", "CALLS", {"call_count": 1}),
        ],
        raw_content="",
    )

    nodes, edges = EntityExtractor().extract(ir)

    assert {node.label for node in nodes} == {"File", "Class", "Function"}
    assert any(edge.relationship_type == "INHERITS" for edge in edges)
    assert any(edge.relationship_type == "CALLS" for edge in edges)
    assert any(edge.relationship_type == "BELONGS_TO" for edge in edges)


def test_graph_indexer_delegates_to_store():
    class FakeStore:
        def __init__(self):
            self.nodes = None
            self.edges = None
            self.mapping = None

        def merge_nodes(self, nodes):
            self.nodes = nodes

        def merge_edges(self, edges):
            self.edges = edges

        def link_chunk_ids(self, chunk_mapping):
            self.mapping = chunk_mapping

        def delete_by_file(self, file_path):
            return 1, 2

    store = FakeStore()
    indexer = GraphIndexer(store)

    indexer.index(["node"], ["edge"])
    indexer.link_chunk_ids({"AuthService": "chunk-1"})

    assert store.nodes == ["node"]
    assert store.edges == ["edge"]
    assert store.mapping == {"AuthService": "chunk-1"}
    assert indexer.delete_by_file("app/services/auth.py") == (1, 2)
