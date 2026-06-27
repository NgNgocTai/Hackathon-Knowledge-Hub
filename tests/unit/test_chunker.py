from app.embedding.chunker import Chunker
from app.embedding.indexer import ChunkIndexer
from app.parser.models import IntermediateRepresentation, ParsedEntity


def _ir(entity: ParsedEntity) -> IntermediateRepresentation:
    return IntermediateRepresentation(
        source_file="app/sample.py",
        source_hash="sha256:test",
        file_type="python",
        language_version="3.11",
        entities=[entity],
        relationships=[],
        raw_content=entity.content,
    )


def test_chunk_entity_level_creates_stable_uuid():
    entity = ParsedEntity(
        entity_type="function",
        name="run",
        qualified_name="run",
        file_path="app/sample.py",
        line_start=1,
        line_end=2,
        content="def run():\n    return helper()",
        docstring=None,
        language="python",
    )

    chunks_a = Chunker().chunk(_ir(entity), version="dev")
    chunks_b = Chunker().chunk(_ir(entity), version="dev")

    assert len(chunks_a) == 1
    assert chunks_a[0].chunk_id == chunks_b[0].chunk_id
    assert chunks_a[0].chunk_type == "code_function"


def test_chunk_entity_over_limit_splits_with_overlap():
    content = " ".join(f"token{i}" for i in range(900))
    entity = ParsedEntity("documentation", "Long", "README.md#long", "README.md", 1, 1, content, None, "markdown")

    chunks = Chunker().chunk(_ir(entity), version="dev")

    assert len(chunks) == 3
    assert chunks[0].total_chunks == 3
    assert chunks[1].chunk_index == 1
    assert "token350" in chunks[1].content


def test_chunk_entity_over_limit_preserves_code_formatting():
    content = "\n".join(["def run():", *[f"    value_{index} = {index}" for index in range(260)]])
    entity = ParsedEntity("function", "run", "run", "app/sample.py", 1, 261, content, None, "python")

    chunks = Chunker().chunk(_ir(entity), version="dev")

    assert len(chunks) > 1
    assert chunks[0].content.startswith("def run():\n    value_0 = 0")
    assert "\n    value_" in chunks[1].content


def test_chunk_indexer_embeds_and_upserts_chunks():
    class FakeEmbedder:
        def embed(self, texts):
            return [[1.0, 0.0] for _ in texts]

        def dimension(self):
            return 2

    class FakeStore:
        def __init__(self):
            self.upserted = []

        def upsert(self, chunks):
            self.upserted.extend(chunks)

        def delete_by_file(self, source_file):
            return 0

    entity = ParsedEntity("function", "run", "run", "app/sample.py", 1, 1, "def run(): pass", None, "python")
    chunks = Chunker().chunk(_ir(entity), version="dev")
    store = FakeStore()

    indexed = ChunkIndexer(FakeEmbedder(), store).index(chunks)

    assert indexed[0].embedding == [1.0, 0.0]
    assert store.upserted == indexed
