"""SQLAlchemy models for the Jobs domain."""

import uuid

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import EmploymentType, JobStatus
from app.common.models import TimestampMixin, UUIDMixin
from app.core.database import Base

# JSONB on PostgreSQL (production), plain JSON elsewhere (e.g. SQLite in tests).
JSONList = JSON().with_variant(JSONB(), "postgresql")


class Job(UUIDMixin, TimestampMixin, Base):
    """A job posting created and managed by a recruiter.

    Week 1 stores ``required_skills`` and ``hiring_stages`` as JSON lists that
    the recruiter supplies manually. Week 2 will populate/refine these via the
    Temporal publishing workflow (skill extraction, content breakdown).
    """

    __tablename__ = "jobs"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employment_type: Mapped[EmploymentType] = mapped_column(
        SAEnum(EmploymentType, name="employment_type"),
        default=EmploymentType.FULL_TIME,
        nullable=False,
    )

    # Manually supplied this week; auto-extraction lands in Week 2.
    required_skills: Mapped[list[str]] = mapped_column(
        JSONList, default=list, nullable=False
    )
    # Ordered list of stage names, e.g. ["Screening", "Interview", "Offer"].
    hiring_stages: Mapped[list[str]] = mapped_column(
        JSONList, default=list, nullable=False
    )

    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, name="job_status"),
        default=JobStatus.DRAFT,
        nullable=False,
        index=True,
    )

    # Set from the authenticated recruiter that created the job. Nullable so
    # existing/seed rows without an owner remain valid.
    recruiter_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
