"""Application model + local read-models of jobs and candidates.

``JobRef`` / ``CandidateRef`` are **read-models** kept up to date from Kafka
events (`job.*` / `candidate.*`). Apply-time eligibility is checked against these
local copies, so Jobs or Candidates being down does not block applying.
"""

import uuid
from datetime import datetime

from smarthire_common.models import TimestampMixin, UUIDMixin
from sqlalchemy import JSON, DateTime, String, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.enums import ApplicationStatus

JSONList = JSON().with_variant(JSONB(), "postgresql")


class Application(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("job_id", "candidate_id", name="uq_application_job_candidate"),
    )

    # Plain UUIDs — jobs/candidates live in other services (no cross-service FK).
    job_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    candidate_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    status: Mapped[ApplicationStatus] = mapped_column(
        SAEnum(ApplicationStatus, name="application_status"),
        default=ApplicationStatus.APPLIED,
        nullable=False,
        index=True,
    )
    stage_history: Mapped[list[dict]] = mapped_column(
        JSONList, default=list, nullable=False
    )
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class JobRef(Base):
    """Read-model: minimal job state needed for eligibility (fed by job.* events)."""

    __tablename__ = "job_refs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class CandidateRef(Base):
    """Read-model: candidate existence (fed by candidate.* events)."""

    __tablename__ = "candidate_refs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
