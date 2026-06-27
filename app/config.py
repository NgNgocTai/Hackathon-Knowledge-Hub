import logging
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    api_key: str = Field(default="dev-secret-key", alias="API_KEY")
    embedding_provider: str = Field(default="openai", alias="EMBEDDING_PROVIDER")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    qdrant_url: str = Field(default="http://qdrant:6333", alias="QDRANT_URL")
    neo4j_uri: str = Field(default="bolt://neo4j:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="password", alias="NEO4J_PASSWORD")
    max_graph_hops: int = Field(default=2, alias="MAX_GRAPH_HOPS")
    max_inherit_hops: int = Field(default=1, alias="MAX_INHERIT_HOPS")
    git_poll_interval_sec: int = Field(default=60, alias="GIT_POLL_INTERVAL_SEC")
    max_concurrent_ingest: int = Field(default=2, alias="MAX_CONCURRENT_INGEST")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def api_keys(self) -> set[str]:
        return {key.strip() for key in self.api_key.split(",") if key.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format=LOG_FORMAT,
    )
