"""Candidates service settings."""

from functools import lru_cache

from pydantic import Field
from smarthire_common.config import BaseServiceSettings


class CandidatesSettings(BaseServiceSettings):
    service_name: str = "smarthire-candidates"
    database_url: str = Field(
        default="postgresql+asyncpg://smarthire:smarthire@localhost:5434/candidates"
    )


@lru_cache
def get_settings() -> CandidatesSettings:
    return CandidatesSettings()


settings = get_settings()
