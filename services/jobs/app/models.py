"""Job model (owned by the jobs service)."""

import uuid

from smarthire_common.models import TimestampMixin, UUIDMixin
from sqlalchemy import JSON, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.enums import EmploymentType, JobStatus

JSONList = JSON().with_variant(JSONB(), "postgresql")
JSONMap = JSON().with_variant(JSONB(), "postgresql")


class Job(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "jobs"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employment_type: Mapped[EmploymentType] = mapped_column(
        SAEnum(EmploymentType, name="employment_type"),
        default=EmploymentType.FULL_TIME,
        nullable=False,
    )
    required_skills: Mapped[list[str]] = mapped_column(
        JSONList, default=list, nullable=False
    )
    hiring_stages: Mapped[list[str]] = mapped_column(
        JSONList, default=list, nullable=False
    )
    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, name="job_status"),
        default=JobStatus.DRAFT,
        nullable=False,
        index=True,
    )
    structured_content: Mapped[dict | None] = mapped_column(JSONMap, nullable=True)
    extracted_keywords: Mapped[list[str]] = mapped_column(
        JSONList, default=list, nullable=False
    )
    # Owner recruiter. A plain UUID (users live in the auth service; no cross-
    # service FK) set from the authenticated recruiter's token.
    recruiter_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
