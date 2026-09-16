"""Applications HTTP routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from smarthire_common.enums import Role
from smarthire_common.pagination import Page, PaginationParams

from app.dependencies import get_application_service, security
from app.enums import ApplicationStatus
from app.schemas import ApplicationCreate, ApplicationRead, StageUpdate
from app.service import ApplicationService

router = APIRouter(
    prefix="/applications",
    tags=["applications"],
    dependencies=[Depends(security.get_current_identity)],
)

ServiceDep = Annotated[ApplicationService, Depends(get_application_service)]


@router.post(
    "",
    response_model=ApplicationRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(security.require_role(Role.CANDIDATE))],
)
async def apply(
    payload: ApplicationCreate,
    service: ServiceDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ApplicationRead:
    return await service.apply(
        payload.job_id, payload.candidate_id, idempotent=idempotency_key is not None
    )


@router.get("", response_model=Page[ApplicationRead])
async def list_applications(
    service: ServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    job_id: uuid.UUID | None = None,
    candidate_id: uuid.UUID | None = None,
    status_filter: ApplicationStatus | None = None,
) -> Page[ApplicationRead]:
    return await service.list(
        limit=pagination.limit,
        offset=pagination.offset,
        job_id=job_id,
        candidate_id=candidate_id,
        status=status_filter,
    )


@router.get("/{application_id}", response_model=ApplicationRead)
async def get_application(
    application_id: uuid.UUID, service: ServiceDep
) -> ApplicationRead:
    return await service.get(application_id)


@router.patch(
    "/{application_id}/stage",
    response_model=ApplicationRead,
    dependencies=[Depends(security.require_role(Role.RECRUITER))],
)
async def advance_stage(
    application_id: uuid.UUID, payload: StageUpdate, service: ServiceDep
) -> ApplicationRead:
    return await service.advance_stage(application_id, payload.status)


@router.post(
    "/{application_id}/withdraw",
    response_model=ApplicationRead,
    dependencies=[Depends(security.require_role(Role.CANDIDATE))],
)
async def withdraw(application_id: uuid.UUID, service: ServiceDep) -> ApplicationRead:
    return await service.withdraw(application_id)
