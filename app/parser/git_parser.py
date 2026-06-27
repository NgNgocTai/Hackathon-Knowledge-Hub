from pathlib import Path

from app.parser.base import BaseParser
from app.parser.exceptions import ParseError
from app.parser.models import IntermediateRepresentation, ParsedEntity, ParsedRelationship
from app.parser.utils import source_name


class GitLogParser(BaseParser):
    def supported_extensions(self) -> list[str]:
        return [".git"]

    def parse(self, file_path: str, source_hash: str) -> IntermediateRepresentation:
        path = Path(file_path)
        repo_path = path.parent if path.name == ".git" else path
        if not repo_path.exists():
            raise FileNotFoundError(file_path)

        try:
            from git import Repo

            repo = Repo(repo_path)
            commits = list(repo.iter_commits(max_count=100))
        except Exception as exc:
            raise ParseError(file_path, "GitLogError", str(exc)) from exc

        source_file = source_name(str(repo_path))
        entities: list[ParsedEntity] = []
        relationships: list[ParsedRelationship] = []
        for commit in commits:
            commit_name = commit.hexsha
            entities.append(
                ParsedEntity(
                    entity_type="commit",
                    name=commit.hexsha[:7],
                    qualified_name=commit_name,
                    file_path=source_file,
                    line_start=None,
                    line_end=None,
                    content=commit.message,
                    docstring=None,
                    language="git_log",
                )
            )
            for changed_file in commit.stats.files:
                relationships.append(ParsedRelationship(commit_name, changed_file, "MODIFIES"))

        return IntermediateRepresentation(source_file, source_hash, "git_log", None, entities, relationships, "")
