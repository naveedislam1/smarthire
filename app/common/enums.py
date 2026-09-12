"""Shared enumerations used across domain modules."""

from enum import StrEnum


class JobStatus(StrEnum):
    """Lifecycle states of a job posting.

    Week 1 uses only ``DRAFT`` and ``PUBLISHED``. ``PROCESSING`` and ``READY``
    are reserved for the Week 2 Temporal publishing workflow (skill/keyword
    extraction, content breakdown) and are defined now so the schema is stable.
    """

    DRAFT = "draft"
    PUBLISHED = "published"
    PROCESSING = "processing"
    READY = "ready"


class Role(StrEnum):
    """Access-control roles for authenticated users."""

    RECRUITER = "recruiter"
    CANDIDATE = "candidate"


class EmploymentType(StrEnum):
    """Type of employment offered by a job."""

    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"
