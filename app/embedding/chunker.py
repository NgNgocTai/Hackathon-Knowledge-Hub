import uuid

from app.embedding.models import Chunk
from app.parser.models import IntermediateRepresentation, ParsedEntity


CHUNK_NAMESPACE = uuid.UUID("5cb52f77-f2f6-4e26-9d4b-6f6737c9c60e")


class Chunker:
    MAX_TOKENS_PER_CHUNK = 500
    WINDOW_SIZE = 400
    OVERLAP_SIZE = 50
    MIN_ENTITY_TOKENS = 10

    def chunk(self, ir: IntermediateRepresentation, version: str) -> list[Chunk]:
        chunks: list[Chunk] = []
        for entity in ir.entities:
            if entity.entity_type == "commit":
                continue
            if entity.entity_type == "file" and entity.language == "python":
                continue
            if not entity.content.strip():
                continue
            if self._should_skip_tiny_function(entity):
                continue

            tokens = self._tokens(entity.content)
            if len(tokens) <= self.MAX_TOKENS_PER_CHUNK:
                chunks.append(self._build_chunk(ir, entity, entity.content, version))
                continue

            windows = self._sliding_windows(entity.content)
            for index, window_content in enumerate(windows):
                chunks.append(
                    self._build_chunk(
                        ir=ir,
                        entity=entity,
                        content=window_content,
                        version=version,
                        chunk_index=index,
                        total_chunks=len(windows),
                    )
                )
        return chunks

    def _build_chunk(
        self,
        ir: IntermediateRepresentation,
        entity: ParsedEntity,
        content: str,
        version: str,
        chunk_index: int = 0,
        total_chunks: int = 1,
    ) -> Chunk:
        chunk_name = f"{entity.qualified_name}:{ir.source_hash}:{chunk_index}"
        return Chunk(
            chunk_id=str(uuid.uuid5(CHUNK_NAMESPACE, chunk_name)),
            content=content,
            entity_name=entity.qualified_name,
            chunk_type=self._chunk_type(entity),
            source_file=ir.source_file,
            source_hash=ir.source_hash,
            line_start=entity.line_start,
            line_end=entity.line_end,
            language=entity.language,
            version=version,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
        )

    def _chunk_type(self, entity: ParsedEntity) -> str:
        if entity.entity_type == "function":
            return "code_function"
        if entity.entity_type == "class":
            return "code_class"
        if entity.entity_type in {"documentation", "requirement"}:
            return "doc_section"
        if entity.entity_type == "file":
            return "doc_paragraph" if entity.language in {"markdown", "pdf"} else "code_file"
        return entity.entity_type

    def _should_skip_tiny_function(self, entity: ParsedEntity) -> bool:
        return (
            entity.entity_type == "function"
            and "." in entity.qualified_name
            and len(self._tokens(entity.content)) < self.MIN_ENTITY_TOKENS
        )

    def _sliding_windows(self, content: str) -> list[str]:
        lines = content.splitlines()
        if not lines:
            return []

        windows: list[str] = []
        current_lines: list[str] = []
        current_token_count = 0
        overlap_lines: list[str] = []

        for line in lines:
            line_tokens = self._tokens(line)
            if len(line_tokens) > self.WINDOW_SIZE:
                if current_lines:
                    windows.append("\n".join(current_lines))
                    overlap_lines = self._tail_lines_for_overlap(current_lines)
                    current_lines = []
                    current_token_count = 0
                token_windows = self._token_sliding_windows(line_tokens)
                windows.extend(" ".join(window) for window in token_windows)
                overlap_lines = []
                continue

            if current_lines and current_token_count + len(line_tokens) > self.WINDOW_SIZE:
                windows.append("\n".join(current_lines))
                overlap_lines = self._tail_lines_for_overlap(current_lines)
                current_lines = [*overlap_lines, line]
                current_token_count = sum(len(self._tokens(item)) for item in current_lines)
                continue

            current_lines.append(line)
            current_token_count += len(line_tokens)

        if current_lines:
            windows.append("\n".join(current_lines))
        return windows

    def _tail_lines_for_overlap(self, lines: list[str]) -> list[str]:
        overlap: list[str] = []
        token_count = 0
        for line in reversed(lines):
            line_token_count = len(self._tokens(line))
            if overlap and token_count + line_token_count > self.OVERLAP_SIZE:
                break
            overlap.insert(0, line)
            token_count += line_token_count
            if token_count >= self.OVERLAP_SIZE:
                break
        return overlap

    def _token_sliding_windows(self, tokens: list[str]) -> list[list[str]]:
        if not tokens:
            return []
        windows: list[list[str]] = []
        step = self.WINDOW_SIZE - self.OVERLAP_SIZE
        for start in range(0, len(tokens), step):
            window = tokens[start : start + self.WINDOW_SIZE]
            if window:
                windows.append(window)
            if start + self.WINDOW_SIZE >= len(tokens):
                break
        return windows

    def _tokens(self, content: str) -> list[str]:
        return content.split()
