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


class JobCreate(JobBase):
    """Payload to create a new job (created in DRAFT state).

    ``recruiter_id`` is not accepted here — it is taken from the authenticated
    recruiter so a caller cannot post jobs on someone else's behalf.
    """


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
    recruiter_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
