from app.config import Settings
from app.embedding.embedder import LocalEmbeddingProvider, OpenAIEmbeddingProvider, RetryingEmbeddingProvider


def create_embedding_provider(settings: Settings):
    if settings.embedding_provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
        return RetryingEmbeddingProvider(
            OpenAIEmbeddingProvider(settings.openai_api_key, model=settings.openai_embedding_model)
        )
    return RetryingEmbeddingProvider(LocalEmbeddingProvider())
