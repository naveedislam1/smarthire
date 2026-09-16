"""Jobs HTTP routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from smarthire_common.enums import Role
from smarthire_common.pagination import Page, PaginationParams
from smarthire_common.security import CurrentIdentity

from app.dependencies import get_job_service, security
from app.enums import JobStatus
from app.publishing.temporal_client import JobPublisher, get_temporal_publisher
from app.schemas import JobCreate, JobRead, JobUpdate
from app.service import JobService

router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
    dependencies=[Depends(security.get_current_identity)],
)

ServiceDep = Annotated[JobService, Depends(get_job_service)]
RecruiterDep = Annotated[CurrentIdentity, Depends(security.require_role(Role.RECRUITER))]


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreate, service: ServiceDep, recruiter: RecruiterDep
) -> JobRead:
    return await service.create_job(payload, recruiter_id=recruiter.user_id)


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
    job_id: uuid.UUID, payload: JobUpdate, service: ServiceDep, recruiter: RecruiterDep
) -> JobRead:
    return await service.update_job(job_id, payload)


@router.post(
    "/{job_id}/publish", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED
)
async def publish_job(
    job_id: uuid.UUID,
    service: ServiceDep,
    recruiter: RecruiterDep,
    publisher: Annotated[JobPublisher, Depends(get_temporal_publisher)],
) -> JobRead:
    job = await service.request_publish(job_id)
    await publisher.start(str(job_id))
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: uuid.UUID, service: ServiceDep, recruiter: RecruiterDep
) -> None:
    await service.delete_job(job_id)
