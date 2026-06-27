import time
from abc import ABC, abstractmethod

from openai import OpenAI


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    def dimension(self) -> int:
        raise NotImplementedError


class LocalEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._load_model()
        embeddings = model.encode(texts, normalize_embeddings=True)
        return [embedding.tolist() for embedding in embeddings]

    def dimension(self) -> int:
        return 768

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]

    def dimension(self) -> int:
        return 1536


class RetryingEmbeddingProvider(EmbeddingProvider):
    def __init__(self, provider: EmbeddingProvider, retries: int = 3, delays: tuple[int, ...] = (1, 2, 4)):
        self.provider = provider
        self.retries = retries
        self.delays = delays

    def embed(self, texts: list[str]) -> list[list[float]]:
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                return self.provider.embed(texts)
            except Exception as exc:
                last_error = exc
                if attempt < self.retries - 1:
                    time.sleep(self.delays[min(attempt, len(self.delays) - 1)])
        raise RuntimeError(f"Embedding failed after {self.retries} attempts: {last_error}") from last_error

    def dimension(self) -> int:
        return self.provider.dimension()
