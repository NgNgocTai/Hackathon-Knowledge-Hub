from dataclasses import dataclass


@dataclass
class Chunk:
    chunk_id: str
    content: str
    entity_name: str
    chunk_type: str
    source_file: str
    source_hash: str
    line_start: int | None
    line_end: int | None
    language: str
    version: str
    embedding: list[float] | None = None
    chunk_index: int = 0
    total_chunks: int = 1

    def payload(self) -> dict:
        return {
            "content": self.content,
            "entity_name": self.entity_name,
            "chunk_type": self.chunk_type,
            "source_file": self.source_file,
            "source_hash": self.source_hash,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "language": self.language,
            "version": self.version,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
        }

    @classmethod
    def from_payload(cls, chunk_id: str, payload: dict, embedding: list[float] | None = None) -> "Chunk":
        return cls(
            chunk_id=chunk_id,
            content=payload.get("content", ""),
            entity_name=payload.get("entity_name", ""),
            chunk_type=payload.get("chunk_type", ""),
            source_file=payload.get("source_file", ""),
            source_hash=payload.get("source_hash", ""),
            line_start=payload.get("line_start"),
            line_end=payload.get("line_end"),
            language=payload.get("language", ""),
            version=payload.get("version", ""),
            embedding=embedding,
            chunk_index=payload.get("chunk_index", 0),
            total_chunks=payload.get("total_chunks", 1),
        )
