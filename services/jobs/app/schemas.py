"""Jobs API schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums import EmploymentType, JobStatus


class JobBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    location: str | None = Field(default=None, max_length=255)
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    required_skills: list[str] = Field(default_factory=list)
    hiring_stages: list[str] = Field(default_factory=list)


class JobCreate(JobBase):
    """recruiter_id is taken from the authenticated recruiter, not the payload."""


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    location: str | None = Field(default=None, max_length=255)
    employment_type: EmploymentType | None = None
    required_skills: list[str] | None = None
    hiring_stages: list[str] | None = None


class JobRead(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: JobStatus
    recruiter_id: uuid.UUID | None = None
    structured_content: dict | None = None
    extracted_keywords: list[str] = []
    created_at: datetime
    updated_at: datetime
