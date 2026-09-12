"""Centralised auth dependencies reused across every domain module.

This is the ONE place that turns a bearer token into an authenticated user and
enforces roles. Routers depend on these; the JWT logic lives nowhere else.
"""

import uuid
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.repository import UserRepository
from app.auth.security import ACCESS_TOKEN_TYPE, decode_token
from app.auth.service import AuthError
from app.common.enums import Role
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import SmartHireError

# tokenUrl powers the Swagger "Authorize" button (points at the login route).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")


class ForbiddenError(SmartHireError):
    """Authenticated, but not allowed to perform this action."""

    status_code = 403
    detail = "You do not have permission to perform this action."


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Decode the access token and load the corresponding active user."""
    try:
        claims = decode_token(token)
    except jwt.PyJWTError as exc:
        raise AuthError("Invalid or expired token.") from exc
    if claims.get("type") != ACCESS_TOKEN_TYPE:
        raise AuthError("Provided token is not an access token.")

    user = await UserRepository(db).get(uuid.UUID(claims["sub"]))
    if user is None or not user.is_active:
        raise AuthError("User no longer exists or is inactive.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: Role):
    """Build a dependency that allows only the given role(s)."""

    async def _checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ForbiddenError(
                f"Requires role: {', '.join(r.value for r in roles)}."
            )
        return user

    return _checker
