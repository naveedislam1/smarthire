"""Application configuration.

Settings are loaded from environment variables (and an optional `.env` file)
using pydantic-settings, giving us a single, typed, validated source of truth
for configuration across the app, Alembic, and tests.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings sourced from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_name: str = "SmartHire"
    environment: str = Field(default="local", description="local | dev | prod")
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # --- Database ---
    # Async SQLAlchemy URL. Defaults to a local docker-compose Postgres instance.
    database_url: str = Field(
        default="postgresql+asyncpg://smarthire:smarthire@localhost:5432/smarthire",
        description="Async SQLAlchemy database URL (postgresql+asyncpg://...).",
    )

    # --- Auth / JWT ---
    # NOTE: override secret_key via the environment in any non-local deployment.
    secret_key: str = Field(
        default="dev-insecure-secret-change-me-in-production-0123456789",
        description="Signing key for JWTs. MUST be overridden outside local dev.",
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # --- Logging ---
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (built once per process)."""
    return Settings()


settings = get_settings()
