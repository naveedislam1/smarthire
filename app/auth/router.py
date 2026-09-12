"""HTTP routes for authentication."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.auth.repository import UserRepository
from app.auth.schemas import (
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserRead,
)
from app.auth.service import AuthService
from app.core.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(db: Annotated[AsyncSession, Depends(get_db)]) -> AuthService:
    return AuthService(UserRepository(db))


ServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, service: ServiceDep) -> UserRead:
    return await service.register(payload)


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: ServiceDep,
) -> TokenResponse:
    # OAuth2 form uses `username`; we treat it as the email.
    return await service.login(form_data.username, form_data.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, service: ServiceDep) -> TokenResponse:
    return await service.refresh(payload.refresh_token)


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
