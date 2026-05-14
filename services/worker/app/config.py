from functools import lru_cache

from pydantic import AnyHttpUrl, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    redis_url: RedisDsn = RedisDsn("redis://redis:6379/0")
    log_level: str = "INFO"

    # Qdrant — vector store for RAG pipeline
    qdrant_url: AnyHttpUrl = AnyHttpUrl("http://qdrant:6333")
    qdrant_collection: str = "transcriptions"
    embedding_model: str = "BAAI/bge-small-en-v1.5"


@lru_cache
def get_settings() -> Settings:
    """Return the cached Settings singleton."""
    return Settings()
