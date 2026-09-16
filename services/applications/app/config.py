"""Applications service settings."""

from functools import lru_cache

from pydantic import Field
from smarthire_common.config import BaseServiceSettings


class ApplicationsSettings(BaseServiceSettings):
    service_name: str = "smarthire-applications"
    database_url: str = Field(
        default="postgresql+asyncpg://smarthire:smarthire@localhost:5436/applications"
    )
    max_active_applications: int = 10


@lru_cache
def get_settings() -> ApplicationsSettings:
    return ApplicationsSettings()


settings = get_settings()
