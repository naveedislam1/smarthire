"""Auth business logic: register, login, refresh. Signs RS256 JWTs."""

import uuid

import jwt
from smarthire_common.exceptions import AuthError, ConflictError
from smarthire_common.security import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

from app.config import settings
from app.models import User
from app.repository import UserRepository
from app.schemas import RegisterRequest, TokenResponse, UserRead


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
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthError("Incorrect email or password.")
        if not user.is_active:
            raise AuthError("User account is inactive.")
        return self._issue_tokens(user)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            claims = decode_token(
                refresh_token, settings.public_key_pem(), settings.jwt_algorithm
            )
        except jwt.PyJWTError as exc:
            raise AuthError("Invalid or expired refresh token.") from exc
        if claims.get("type") != REFRESH_TOKEN_TYPE:
            raise AuthError("Provided token is not a refresh token.")
        user = await self.repository.get(uuid.UUID(claims["sub"]))
        if user is None or not user.is_active:
            raise AuthError("User no longer exists or is inactive.")
        return self._issue_tokens(user)

    def _issue_tokens(self, user: User) -> TokenResponse:
        private_key = settings.private_key_pem()
        return TokenResponse(
            access_token=create_access_token(
                subject=str(user.id),
                role=user.role,
                private_key=private_key,
                algorithm=settings.jwt_algorithm,
                expires_minutes=settings.access_token_expire_minutes,
            ),
            refresh_token=create_refresh_token(
                subject=str(user.id),
                role=user.role,
                private_key=private_key,
                algorithm=settings.jwt_algorithm,
                expires_days=settings.refresh_token_expire_days,
            ),
        )
