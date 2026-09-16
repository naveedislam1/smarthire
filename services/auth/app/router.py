"""Auth HTTP routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from smarthire_common.exceptions import NotFoundError
from smarthire_common.security import CurrentIdentity
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_auth_service, security
from app.repository import UserRepository
from app.schemas import RefreshRequest, RegisterRequest, TokenResponse, UserRead
from app.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

ServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, service: ServiceDep) -> UserRead:
    return await service.register(payload)


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: ServiceDep,
) -> TokenResponse:
    return await service.login(form_data.username, form_data.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, service: ServiceDep) -> TokenResponse:
    return await service.refresh(payload.refresh_token)


@router.get("/me", response_model=UserRead)
async def me(
    identity: Annotated[CurrentIdentity, Depends(security.get_current_identity)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRead:
    # The token carries only identity; load the full user from this service's DB.
    user = await UserRepository(db).get(identity.user_id)
    if user is None:
        raise NotFoundError("User not found.")
    return UserRead.model_validate(user)
