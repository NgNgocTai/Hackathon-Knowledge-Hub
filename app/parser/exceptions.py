class ParseError(Exception):
    def __init__(self, file_path: str, error_type: str, detail: str):
        self.file_path = file_path
        self.error_type = error_type
        self.detail = detail
        super().__init__(f"{file_path}: {error_type}: {detail}")


class UnsupportedFileTypeError(Exception):
    def __init__(self, file_path: str, extension: str):
        self.file_path = file_path
        self.extension = extension
        super().__init__(f"Unsupported file type for {file_path}: {extension}")
