"""Auth service settings."""

from functools import lru_cache

from pydantic import Field
from smarthire_common.config import BaseServiceSettings


class AuthSettings(BaseServiceSettings):
    service_name: str = "smarthire-auth"

    database_url: str = Field(
        default="postgresql+asyncpg://smarthire:smarthire@localhost:5433/auth",
        description="Auth service database (its own Postgres).",
    )


@lru_cache
def get_settings() -> AuthSettings:
    return AuthSettings()


settings = get_settings()
