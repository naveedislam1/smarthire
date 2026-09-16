"""Candidate + CandidateProfile models (owned by the candidates service)."""

import uuid

from smarthire_common.models import TimestampMixin, UUIDMixin
from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

JSONList = JSON().with_variant(JSONB(), "postgresql")


class Candidate(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "candidates"

    email: Mapped[str] = mapped_column(
        String(320), unique=True, index=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    profile: Mapped["CandidateProfile | None"] = relationship(
        back_populates="candidate",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CandidateProfile(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "candidate_profiles"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    headline: Mapped[str | None] = mapped_column(String(255), nullable=True)
    skills: Mapped[list[str]] = mapped_column(JSONList, default=list, nullable=False)
    experience_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resume_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    bio: Mapped[str | None] = mapped_column(String, nullable=True)

    candidate: Mapped[Candidate] = relationship(back_populates="profile")
