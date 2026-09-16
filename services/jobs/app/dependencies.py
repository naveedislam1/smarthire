"""Jobs service dependencies (JWT verify, DB, publisher, service)."""

from typing import Annotated

from fastapi import Depends
from smarthire_common.events import KafkaEventPublisher
from smarthire_common.security import build_security
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.events import get_publisher
from app.repository import JobRepository
from app.service import JobService

security = build_security(
    public_key=settings.public_key_pem(),
    algorithm=settings.jwt_algorithm,
    token_url=f"{settings.api_v1_prefix}/auth/login",
)


def get_job_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[KafkaEventPublisher, Depends(get_publisher)],
) -> JobService:
    return JobService(JobRepository(db), publisher)
