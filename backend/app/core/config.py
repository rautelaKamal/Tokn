from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Tokn Prompt Optimizer"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://localhost:3000",
            "chrome-extension://*",
        ]
    )

    # Gemini (Google AI Studio — free tier: 1,500 req/day with 2.5-flash-lite once billing is enabled)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-lite"

    # Simple API-key auth for extension → backend calls
    tokn_api_key: str = ""  # Set in .env; empty = auth disabled (dev only)

    # Rate limiting
    rate_limit: str = "10/minute"

    # Prompt cache
    prompt_cache_maxsize: int = 256
    prompt_cache_ttl_seconds: int = 3600

    tiktoken_encoding: str = "cl100k_base"

    # USD per 1M tokens (Gemini 2.5 Flash pricing)
    input_cost_per_million: float = 0.15
    output_cost_per_million: float = 0.60

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    database_url: str = "postgresql+asyncpg://tokn:tokn@localhost:5432/tokn"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
