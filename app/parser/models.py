from dataclasses import dataclass, field
from typing import Literal


EntityType = Literal["function", "class", "file", "requirement", "documentation", "commit"]
RelationshipType = Literal["CALLS", "INHERITS", "DEFINES", "IMPLEMENTS", "DESCRIBES", "MODIFIES"]
FileType = Literal["python", "java", "csharp", "markdown", "pdf", "git_log", "srs"]


@dataclass
class ParsedEntity:
    entity_type: EntityType
    name: str
    qualified_name: str
    file_path: str
    line_start: int | None
    line_end: int | None
    content: str
    docstring: str | None
    language: str


@dataclass
class ParsedRelationship:
    source_qualified_name: str
    target_qualified_name: str
    relationship_type: RelationshipType
    metadata: dict = field(default_factory=dict)


@dataclass
class IntermediateRepresentation:
    source_file: str
    source_hash: str
    file_type: FileType
    language_version: str | None
    entities: list[ParsedEntity]
    relationships: list[ParsedRelationship]
    raw_content: str
