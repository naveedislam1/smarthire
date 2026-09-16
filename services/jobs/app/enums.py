"""Job domain enums (owned by the jobs service)."""

from enum import StrEnum


class JobStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class EmploymentType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"
