"""Auth service dependencies (DB session, service, JWT verification)."""

from typing import Annotated

from fastapi import Depends
from smarthire_common.security import build_security
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.repository import UserRepository
from app.service import AuthService

# Built once from this service's public key; reused for verifying access tokens
# on protected routes (e.g. /auth/me).
security = build_security(
    public_key=settings.public_key_pem(),
    algorithm=settings.jwt_algorithm,
    token_url=f"{settings.api_v1_prefix}/auth/login",
)


def get_auth_service(db: Annotated[AsyncSession, Depends(get_db)]) -> AuthService:
    return AuthService(UserRepository(db))
