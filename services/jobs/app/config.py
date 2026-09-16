"""Jobs service settings."""

from functools import lru_cache

from pydantic import Field
from smarthire_common.config import BaseServiceSettings


class JobsSettings(BaseServiceSettings):
    service_name: str = "smarthire-jobs"
    database_url: str = Field(
        default="postgresql+asyncpg://smarthire:smarthire@localhost:5435/jobs"
    )

    # Temporal (publishing workflow)
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "smarthire-publishing"


@lru_cache
def get_settings() -> JobsSettings:
    return JobsSettings()


settings = get_settings()
