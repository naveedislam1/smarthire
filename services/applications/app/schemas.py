"""Applications API schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.enums import ApplicationStatus


class ApplicationCreate(BaseModel):
    job_id: uuid.UUID
    candidate_id: uuid.UUID


class StageUpdate(BaseModel):
    status: ApplicationStatus


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    status: ApplicationStatus
    stage_history: list[dict]
    applied_at: datetime
    created_at: datetime
    updated_at: datetime
