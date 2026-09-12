"""Pydantic request/response schemas for the Jobs domain."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import EmploymentType, JobStatus


class JobBase(BaseModel):
    """Fields common to create/update payloads."""

    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    location: str | None = Field(default=None, max_length=255)
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    required_skills: list[str] = Field(default_factory=list)
    hiring_stages: list[str] = Field(default_factory=list)
    recruiter_id: uuid.UUID | None = None


class JobCreate(JobBase):
    """Payload to create a new job (created in DRAFT state)."""


class JobUpdate(BaseModel):
    """Partial update payload — every field is optional."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    location: str | None = Field(default=None, max_length=255)
    employment_type: EmploymentType | None = None
    required_skills: list[str] | None = None
    hiring_stages: list[str] | None = None


class JobRead(JobBase):
    """Job as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: JobStatus
    created_at: datetime
    updated_at: datetime
