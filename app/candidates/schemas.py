"""Pydantic request/response schemas for the Candidates domain."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Candidate ---
class CandidateBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=50)


class CandidateCreate(CandidateBase):
    """Payload to register a new candidate."""


class CandidateUpdate(BaseModel):
    """Partial update payload for a candidate."""

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=50)


# --- Candidate profile ---
class CandidateProfileUpsert(BaseModel):
    """Payload to create or replace a candidate's profile."""

    headline: str | None = Field(default=None, max_length=255)
    skills: list[str] = Field(default_factory=list)
    experience_years: int | None = Field(default=None, ge=0, le=80)
    resume_url: str | None = Field(default=None, max_length=1024)
    bio: str | None = None


class CandidateProfileRead(CandidateProfileUpsert):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class CandidateRead(CandidateBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    profile: CandidateProfileRead | None = None
