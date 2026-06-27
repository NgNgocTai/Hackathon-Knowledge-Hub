from abc import ABC, abstractmethod

from app.parser.models import IntermediateRepresentation


class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: str, source_hash: str) -> IntermediateRepresentation:
        raise NotImplementedError

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        raise NotImplementedError
