from pathlib import Path

from pypdf import PdfReader

from app.parser.base import BaseParser
from app.parser.exceptions import ParseError
from app.parser.models import IntermediateRepresentation, ParsedEntity, ParsedRelationship
from app.parser.utils import source_name


class PDFParser(BaseParser):
    def supported_extensions(self) -> list[str]:
        return [".pdf"]

    def parse(self, file_path: str, source_hash: str) -> IntermediateRepresentation:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(file_path)

        try:
            reader = PdfReader(file_path)
            page_texts = [page.extract_text() or "" for page in reader.pages]
        except Exception as exc:
            raise ParseError(file_path, "PDFReadError", str(exc)) from exc

        source_file = source_name(file_path)
        entities = [
            ParsedEntity(
                entity_type="documentation",
                name=f"page-{index}",
                qualified_name=f"{source_file}#page-{index}",
                file_path=source_file,
                line_start=None,
                line_end=None,
                content=text,
                docstring=None,
                language="pdf",
            )
            for index, text in enumerate(page_texts, start=1)
            if text.strip()
        ]
        relationships = [ParsedRelationship(source_file, entity.qualified_name, "DEFINES") for entity in entities]
        return IntermediateRepresentation(source_file, source_hash, "pdf", None, entities, relationships, "\n".join(page_texts))
