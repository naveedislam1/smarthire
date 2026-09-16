"""Candidates service dependencies (JWT verify, DB session, service)."""

from typing import Annotated

from fastapi import Depends
from smarthire_common.events import KafkaEventPublisher
from smarthire_common.security import build_security
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.events import get_publisher
from app.repository import CandidateRepository
from app.service import CandidateService

security = build_security(
    public_key=settings.public_key_pem(),
    algorithm=settings.jwt_algorithm,
    token_url=f"{settings.api_v1_prefix}/auth/login",
)


def get_candidate_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[KafkaEventPublisher, Depends(get_publisher)],
) -> CandidateService:
    return CandidateService(CandidateRepository(db), publisher)
