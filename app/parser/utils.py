from pathlib import Path


def read_text_file(file_path: str) -> str:
    return Path(file_path).read_text(encoding="utf-8")


def source_name(file_path: str) -> str:
    path = Path(file_path)
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def get_source_segment(lines: list[str], line_start: int | None, line_end: int | None) -> str:
    if line_start is None or line_end is None:
        return ""
    return "\n".join(lines[line_start - 1 : line_end])
