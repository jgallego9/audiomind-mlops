from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "AudioMind API Gateway"
    app_version: str = "0.1.0"

    # JWT
    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # Rate limiting (slowapi format: "N/period")
    rate_limit_default: str = "100/minute"
    rate_limit_auth: str = "10/minute"


settings = Settings()
