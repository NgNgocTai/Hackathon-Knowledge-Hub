from pathlib import Path

from app.parser.base import BaseParser
from app.parser.exceptions import UnsupportedFileTypeError
from app.parser.git_parser import GitLogParser
from app.parser.markdown_parser import MarkdownParser
from app.parser.pdf_parser import PDFParser
from app.parser.python_parser import PythonParser


class ParserRegistry:
    def __init__(self, parsers: list[BaseParser] | None = None):
        self.parsers = parsers or [PythonParser(), MarkdownParser(), PDFParser(), GitLogParser()]

    def get_parser(self, file_path: str) -> BaseParser:
        path = Path(file_path)
        extension = path.name if path.name == ".git" else path.suffix.lower()
        for parser in self.parsers:
            if extension in parser.supported_extensions():
                return parser
        raise UnsupportedFileTypeError(file_path, extension)
