"""Cross-cutting enumerations shared across services."""

from enum import StrEnum


class Role(StrEnum):
    """Access-control roles carried in the JWT and enforced by every service."""

    RECRUITER = "recruiter"
    CANDIDATE = "candidate"
