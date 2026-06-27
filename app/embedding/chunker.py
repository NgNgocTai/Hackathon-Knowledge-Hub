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
            if not entity.content.strip():
                continue
            if self._should_skip_tiny_function(entity):
                continue

            tokens = self._tokens(entity.content)
            if len(tokens) <= self.MAX_TOKENS_PER_CHUNK:
                chunks.append(self._build_chunk(ir, entity, entity.content, version))
                continue

            windows = self._sliding_windows(tokens)
            for index, window_tokens in enumerate(windows):
                chunks.append(
                    self._build_chunk(
                        ir=ir,
                        entity=entity,
                        content=" ".join(window_tokens),
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

    def _sliding_windows(self, tokens: list[str]) -> list[list[str]]:
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
