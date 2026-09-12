"""Pydantic schemas for authentication."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.common.enums import Role


class RegisterRequest(BaseModel):
    """Payload to create a new user account."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    role: Role = Role.CANDIDATE


class UserRead(BaseModel):
    """A user as returned by the API (never includes the password hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    """Access + refresh token pair issued on login/refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Payload to exchange a refresh token for a new access token."""

    refresh_token: str
