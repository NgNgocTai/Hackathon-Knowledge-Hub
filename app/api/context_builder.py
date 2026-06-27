from app.retrieval.models import RetrievalResult


class ContextBuilder:
    TOKEN_LIMIT = 8000
    CHUNK_TYPE_PRIORITY = {
        "code_function": 3,
        "code_class": 2,
        "doc_section": 1,
        "doc_paragraph": 0,
        "git_log": -1,
    }

    def build(self, results: list[RetrievalResult], token_limit: int = TOKEN_LIMIT) -> list[RetrievalResult]:
        ordered = sorted(
            results,
            key=lambda result: (
                result.relevance_score,
                self.CHUNK_TYPE_PRIORITY.get(result.metadata.get("chunk_type", ""), 0),
            ),
            reverse=True,
        )

        selected: list[RetrievalResult] = []
        total_tokens = 0
        for result in ordered:
            token_count = self._count_tokens(result.content)
            if selected and total_tokens + token_count > token_limit:
                continue
            if not selected and token_count > token_limit:
                continue
            selected.append(result)
            total_tokens += token_count
        return selected

    def _count_tokens(self, content: str) -> int:
        return len(content.split())
