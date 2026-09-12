"""Authentication business logic: register, login, refresh."""

import uuid

import jwt

from app.auth.models import User
from app.auth.repository import UserRepository
from app.auth.schemas import RegisterRequest, TokenResponse, UserRead
from app.auth.security import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.exceptions import ConflictError, SmartHireError


class AuthError(SmartHireError):
    """Authentication failed (bad credentials / invalid token)."""

    status_code = 401
    detail = "Could not validate credentials."


class AuthService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def register(self, payload: RegisterRequest) -> UserRead:
        if await self.repository.get_by_email(payload.email) is not None:
            raise ConflictError(f"A user with email {payload.email} already exists.")
        user = User(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            role=payload.role,
        )
        user = await self.repository.create(user)
        return UserRead.model_validate(user)

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self.repository.get_by_email(email)
        # Verify even when the user is missing is not required here; we simply
        # return the same generic error to avoid leaking which emails exist.
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthError("Incorrect email or password.")
        if not user.is_active:
            raise AuthError("User account is inactive.")
        return self._issue_tokens(user)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            claims = decode_token(refresh_token)
        except jwt.PyJWTError as exc:
            raise AuthError("Invalid or expired refresh token.") from exc
        if claims.get("type") != REFRESH_TOKEN_TYPE:
            raise AuthError("Provided token is not a refresh token.")
        user = await self.repository.get(uuid.UUID(claims["sub"]))
        if user is None or not user.is_active:
            raise AuthError("User no longer exists or is inactive.")
        return self._issue_tokens(user)

    @staticmethod
    def _issue_tokens(user: User) -> TokenResponse:
        return TokenResponse(
            access_token=create_access_token(subject=str(user.id), role=user.role),
            refresh_token=create_refresh_token(subject=str(user.id), role=user.role),
        )
