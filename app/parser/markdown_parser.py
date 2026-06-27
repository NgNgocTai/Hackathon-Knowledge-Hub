from pathlib import Path

from app.parser.base import BaseParser
from app.parser.models import IntermediateRepresentation, ParsedEntity, ParsedRelationship
from app.parser.utils import read_text_file, source_name


class MarkdownParser(BaseParser):
    def supported_extensions(self) -> list[str]:
        return [".md", ".markdown"]

    def parse(self, file_path: str, source_hash: str) -> IntermediateRepresentation:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(file_path)

        raw_content = read_text_file(file_path)
        source_file = source_name(file_path)
        entities = self._sections(raw_content, source_file)
        if not entities:
            entities.append(
                ParsedEntity(
                    entity_type="documentation",
                    name=path.stem,
                    qualified_name=f"{source_file}#document",
                    file_path=source_file,
                    line_start=1,
                    line_end=len(raw_content.splitlines()) or 1,
                    content=raw_content,
                    docstring=None,
                    language="markdown",
                )
            )

        relationships = [ParsedRelationship(source_file, entity.qualified_name, "DEFINES") for entity in entities]
        return IntermediateRepresentation(
            source_file=source_file,
            source_hash=source_hash,
            file_type="markdown",
            language_version=None,
            entities=entities,
            relationships=relationships,
            raw_content=raw_content,
        )

    def _sections(self, raw_content: str, source_file: str) -> list[ParsedEntity]:
        lines = raw_content.splitlines()
        headings: list[tuple[int, str]] = []
        for index, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                title = stripped.lstrip("#").strip()
                if title:
                    headings.append((index, title))

        sections: list[ParsedEntity] = []
        for idx, (line_start, title) in enumerate(headings):
            line_end = headings[idx + 1][0] - 1 if idx + 1 < len(headings) else len(lines)
            content = "\n".join(lines[line_start - 1 : line_end])
            anchor = title.lower().replace(" ", "-")
            sections.append(
                ParsedEntity(
                    entity_type="documentation",
                    name=title,
                    qualified_name=f"{source_file}#{anchor}",
                    file_path=source_file,
                    line_start=line_start,
                    line_end=line_end,
                    content=content,
                    docstring=None,
                    language="markdown",
                )
            )
        return sections
