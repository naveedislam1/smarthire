"""Security primitives: password hashing (Argon2) and JWT encode/decode.

This module is the single place that knows how passwords are hashed and how
tokens are signed/verified. Everything else depends on these functions.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

# Argon2-based hasher (PasswordHash.recommended() selects Argon2id).
_password_hash = PasswordHash.recommended()

# Token "type" claim values, so an access token can't be used where a refresh
# token is expected and vice versa.
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def hash_password(plain: str) -> str:
    return _password_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _password_hash.verify(plain, hashed)


def _create_token(
    *, subject: str, role: str, token_type: str, expires_delta: timedelta
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
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(*, subject: str, role: str) -> str:
    return _create_token(
        subject=subject,
        role=role,
        token_type=ACCESS_TOKEN_TYPE,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(*, subject: str, role: str) -> str:
    return _create_token(
        subject=subject,
        role=role,
        token_type=REFRESH_TOKEN_TYPE,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode & verify a JWT. Raises jwt.PyJWTError on any problem."""
    return jwt.decode(
        token, settings.secret_key, algorithms=[settings.jwt_algorithm]
    )
