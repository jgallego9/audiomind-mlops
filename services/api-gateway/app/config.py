from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # tolerate unrecognised env vars (common in Docker)
    )

    app_name: str = "AudioMind API Gateway"
    app_version: str = "0.1.0"

    # JWT
    jwt_secret_key: SecretStr
    jwt_algorithm: Literal["HS256", "RS256", "ES256"] = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # Rate limiting (slowapi format: "N/period")
    rate_limit_default: str = "100/minute"
    rate_limit_auth: str = "10/minute"


@lru_cache
def get_settings() -> Settings:
    """Return the cached Settings instance.

    Using ``@lru_cache`` keeps Settings as a singleton while allowing tests
    to override it via ``get_settings.cache_clear()`` + dependency override.
    """
    return Settings()
