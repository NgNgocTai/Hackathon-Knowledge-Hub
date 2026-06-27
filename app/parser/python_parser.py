import ast
import sys
from collections import Counter
from pathlib import Path

from app.parser.base import BaseParser
from app.parser.exceptions import ParseError
from app.parser.models import IntermediateRepresentation, ParsedEntity, ParsedRelationship
from app.parser.utils import get_source_segment, read_text_file, source_name


class _CallCollector(ast.NodeVisitor):
    def __init__(self, current_class: str | None):
        self.current_class = current_class
        self.calls: Counter[str] = Counter()

    def visit_Call(self, node: ast.Call) -> None:
        target = self._call_name(node.func)
        if target:
            self.calls[target] += 1
        self.generic_visit(node)

    def _call_name(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            base = self._attribute_base(node.value)
            if base == "self" and self.current_class:
                return f"{self.current_class}.{node.attr}"
            if base:
                return f"{base}.{node.attr}"
            return node.attr
        return None

    def _attribute_base(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Call):
            return self._call_name(node.func)
        if isinstance(node, ast.Attribute):
            parent = self._attribute_base(node.value)
            return f"{parent}.{node.attr}" if parent else node.attr
        return None


class PythonParser(BaseParser):
    def supported_extensions(self) -> list[str]:
        return [".py"]

    def parse(self, file_path: str, source_hash: str) -> IntermediateRepresentation:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(file_path)

        raw_content = read_text_file(file_path)
        lines = raw_content.splitlines()
        try:
            tree = ast.parse(raw_content, filename=file_path)
        except SyntaxError as exc:
            raise ParseError(file_path, "SyntaxError", str(exc)) from exc

        source_file = source_name(file_path)
        entities: list[ParsedEntity] = [
            ParsedEntity(
                entity_type="file",
                name=path.name,
                qualified_name=source_file,
                file_path=source_file,
                line_start=1 if lines else None,
                line_end=len(lines) if lines else None,
                content=raw_content,
                docstring=ast.get_docstring(tree),
                language="python",
            )
        ]
        relationships: list[ParsedRelationship] = []

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_entity = self._class_entity(node, source_file, lines)
                entities.append(class_entity)
                relationships.append(ParsedRelationship(source_file, class_entity.qualified_name, "DEFINES"))
                relationships.extend(self._inherits_relationships(node, class_entity.qualified_name))

                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        function_entity = self._function_entity(child, source_file, lines, node.name)
                        entities.append(function_entity)
                        relationships.append(
                            ParsedRelationship(source_file, function_entity.qualified_name, "DEFINES")
                        )
                        relationships.extend(self._call_relationships(child, function_entity.qualified_name, node.name))

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_entity = self._function_entity(node, source_file, lines, None)
                entities.append(function_entity)
                relationships.append(ParsedRelationship(source_file, function_entity.qualified_name, "DEFINES"))
                relationships.extend(self._call_relationships(node, function_entity.qualified_name, None))

        return IntermediateRepresentation(
            source_file=source_file,
            source_hash=source_hash,
            file_type="python",
            language_version=f"{sys.version_info.major}.{sys.version_info.minor}",
            entities=entities,
            relationships=relationships,
            raw_content=raw_content,
        )

    def _class_entity(self, node: ast.ClassDef, source_file: str, lines: list[str]) -> ParsedEntity:
        line_end = getattr(node, "end_lineno", node.lineno)
        return ParsedEntity(
            entity_type="class",
            name=node.name,
            qualified_name=node.name,
            file_path=source_file,
            line_start=node.lineno,
            line_end=line_end,
            content=get_source_segment(lines, node.lineno, line_end),
            docstring=ast.get_docstring(node),
            language="python",
        )

    def _function_entity(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        source_file: str,
        lines: list[str],
        class_name: str | None,
    ) -> ParsedEntity:
        line_end = getattr(node, "end_lineno", node.lineno)
        qualified_name = f"{class_name}.{node.name}" if class_name else node.name
        return ParsedEntity(
            entity_type="function",
            name=node.name,
            qualified_name=qualified_name,
            file_path=source_file,
            line_start=node.lineno,
            line_end=line_end,
            content=get_source_segment(lines, node.lineno, line_end),
            docstring=ast.get_docstring(node),
            language="python",
        )

    def _inherits_relationships(self, node: ast.ClassDef, source_name_: str) -> list[ParsedRelationship]:
        relationships = []
        for base in node.bases:
            target = self._base_name(base)
            if target:
                relationships.append(ParsedRelationship(source_name_, target, "INHERITS"))
        return relationships

    def _base_name(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parts = []
            current: ast.AST | None = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return None

    def _call_relationships(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        source_name_: str,
        class_name: str | None,
    ) -> list[ParsedRelationship]:
        collector = _CallCollector(class_name)
        collector.visit(node)
        return [
            ParsedRelationship(source_name_, target, "CALLS", {"call_count": count})
            for target, count in collector.calls.items()
            if target != source_name_
        ]
