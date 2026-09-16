"""RS256 JWT + password hashing + reusable auth dependencies.

Asymmetric JWT is the microservice-friendly choice: the **auth** service signs
with a private key; every other service **verifies** with the public key — no
shared secret, and auth being down does not block verification.

A service builds its auth dependencies once with :func:`build_security`, passing
its public key. Only the auth service also holds the private key (to sign).
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from pydantic import BaseModel

from smarthire_common.enums import Role
from smarthire_common.exceptions import AuthError, ForbiddenError

_password_hash = PasswordHash.recommended()

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


# --- Passwords ---
def hash_password(plain: str) -> str:
    return _password_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _password_hash.verify(plain, hashed)


# --- Tokens ---
def _create_token(
    *,
    subject: str,
    role: str,
    token_type: str,
    expires_delta: timedelta,
    private_key: str,
    algorithm: str,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, private_key, algorithm=algorithm)


def create_access_token(
    *, subject: str, role: str, private_key: str, algorithm: str, expires_minutes: int
) -> str:
    return _create_token(
        subject=subject,
        role=role,
        token_type=ACCESS_TOKEN_TYPE,
        expires_delta=timedelta(minutes=expires_minutes),
        private_key=private_key,
        algorithm=algorithm,
    )


def create_refresh_token(
    *, subject: str, role: str, private_key: str, algorithm: str, expires_days: int
) -> str:
    return _create_token(
        subject=subject,
        role=role,
        token_type=REFRESH_TOKEN_TYPE,
        expires_delta=timedelta(days=expires_days),
        private_key=private_key,
        algorithm=algorithm,
    )


def decode_token(token: str, public_key: str, algorithm: str) -> dict[str, Any]:
    """Verify signature + expiry; raises jwt.PyJWTError on any problem."""
    return jwt.decode(token, public_key, algorithms=[algorithm])


# --- Identity carried in a verified access token ---
class CurrentIdentity(BaseModel):
    user_id: uuid.UUID
    role: Role


@dataclass
class Security:
    """Bundle of a service's auth dependencies, built from its public key."""

    oauth2_scheme: OAuth2PasswordBearer
    get_current_identity: Callable
    require_role: Callable


def build_security(
    *, public_key: str, algorithm: str = "RS256", token_url: str
) -> Security:
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl=token_url)

    async def get_current_identity(
        token: Annotated[str, Depends(oauth2_scheme)],
    ) -> CurrentIdentity:
        try:
            claims = decode_token(token, public_key, algorithm)
        except jwt.PyJWTError as exc:
            raise AuthError("Invalid or expired token.") from exc
        if claims.get("type") != ACCESS_TOKEN_TYPE:
            raise AuthError("Provided token is not an access token.")
        return CurrentIdentity(user_id=uuid.UUID(claims["sub"]), role=Role(claims["role"]))

    def require_role(*roles: Role) -> Callable:
        async def _checker(
            identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
        ) -> CurrentIdentity:
            if identity.role not in roles:
                raise ForbiddenError(
                    f"Requires role: {', '.join(r.value for r in roles)}."
                )
            return identity

        return _checker

    return Security(
        oauth2_scheme=oauth2_scheme,
        get_current_identity=get_current_identity,
        require_role=require_role,
    )
