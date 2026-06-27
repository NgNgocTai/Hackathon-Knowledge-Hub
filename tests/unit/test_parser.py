import pytest

from app.parser.exceptions import ParseError, UnsupportedFileTypeError
from app.parser.markdown_parser import MarkdownParser
from app.parser.python_parser import PythonParser
from app.parser.registry import ParserRegistry


def test_python_parser_extracts_entities_and_relationships(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text(
        "\n".join(
            [
                "class Base:",
                "    pass",
                "",
                "class Service(Base):",
                "    def run(self):",
                "        return helper()",
                "",
                "def helper():",
                "    return 1",
            ]
        ),
        encoding="utf-8",
    )

    ir = PythonParser().parse(str(sample), "sha256:test")

    names = {entity.qualified_name for entity in ir.entities}
    assert "Service" in names
    assert "Service.run" in names
    assert "helper" in names
    assert any(rel.relationship_type == "INHERITS" and rel.target_qualified_name == "Base" for rel in ir.relationships)
    assert any(rel.relationship_type == "CALLS" and rel.target_qualified_name == "helper" for rel in ir.relationships)


def test_python_parser_raises_parse_error_for_syntax_error(tmp_path):
    sample = tmp_path / "broken.py"
    sample.write_text("def nope(:\n    pass\n", encoding="utf-8")

    with pytest.raises(ParseError):
        PythonParser().parse(str(sample), "sha256:test")


def test_markdown_parser_extracts_heading_sections(tmp_path):
    sample = tmp_path / "README.md"
    sample.write_text("# Title\nIntro\n\n## Usage\nRun it\n", encoding="utf-8")

    ir = MarkdownParser().parse(str(sample), "sha256:test")

    assert ir.file_type == "markdown"
    assert [entity.name for entity in ir.entities] == ["Title", "Usage"]
    assert ir.entities[1].content == "## Usage\nRun it"


def test_registry_rejects_unsupported_extension(tmp_path):
    sample = tmp_path / "notes.txt"
    sample.write_text("hello", encoding="utf-8")

    with pytest.raises(UnsupportedFileTypeError):
        ParserRegistry().get_parser(str(sample))
