"""HTTP routes for the Jobs domain."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.common.enums import JobStatus, Role
from app.common.pagination import Page, PaginationParams
from app.core.database import get_db
from app.jobs.repository import JobRepository
from app.jobs.schemas import JobCreate, JobRead, JobUpdate
from app.jobs.service import JobService

# All job routes require a logged-in user; writes additionally require the
# recruiter role (declared per-route below).
router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
    dependencies=[Depends(get_current_user)],
)

RecruiterDep = Annotated[User, Depends(require_role(Role.RECRUITER))]


def get_job_service(db: Annotated[AsyncSession, Depends(get_db)]) -> JobService:
    """Wire repository + service for a request."""
    return JobService(JobRepository(db))


ServiceDep = Annotated[JobService, Depends(get_job_service)]


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreate, service: ServiceDep, recruiter: RecruiterDep
) -> JobRead:
    return await service.create_job(payload, recruiter_id=recruiter.id)


@router.get("", response_model=Page[JobRead])
async def list_jobs(
    service: ServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    status_filter: JobStatus | None = None,
) -> Page[JobRead]:
    return await service.list_jobs(
        limit=pagination.limit, offset=pagination.offset, status=status_filter
    )


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: uuid.UUID, service: ServiceDep) -> JobRead:
    return await service.get_job(job_id)


@router.patch("/{job_id}", response_model=JobRead)
async def update_job(
    job_id: uuid.UUID,
    payload: JobUpdate,
    service: ServiceDep,
    recruiter: RecruiterDep,
) -> JobRead:
    return await service.update_job(job_id, payload)


@router.post("/{job_id}/publish", response_model=JobRead)
async def publish_job(
    job_id: uuid.UUID, service: ServiceDep, recruiter: RecruiterDep
) -> JobRead:
    return await service.publish_job(job_id)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: uuid.UUID, service: ServiceDep, recruiter: RecruiterDep
) -> None:
    await service.delete_job(job_id)
