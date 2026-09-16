"""Candidates HTTP routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from smarthire_common.enums import Role
from smarthire_common.pagination import Page, PaginationParams

from app.dependencies import get_candidate_service, security
from app.schemas import (
    CandidateCreate,
    CandidateProfileRead,
    CandidateProfileUpsert,
    CandidateRead,
    CandidateUpdate,
)
from app.service import CandidateService

router = APIRouter(
    prefix="/candidates",
    tags=["candidates"],
    dependencies=[Depends(security.get_current_identity)],
)

ServiceDep = Annotated[CandidateService, Depends(get_candidate_service)]


@router.post("", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
async def register_candidate(
    payload: CandidateCreate, service: ServiceDep
) -> CandidateRead:
    return await service.register_candidate(payload)


@router.get(
    "",
    response_model=Page[CandidateRead],
    dependencies=[Depends(security.require_role(Role.RECRUITER))],
)
async def list_candidates(
    service: ServiceDep, pagination: Annotated[PaginationParams, Depends()]
) -> Page[CandidateRead]:
    return await service.list_candidates(
        limit=pagination.limit, offset=pagination.offset
    )


@router.get("/{candidate_id}", response_model=CandidateRead)
async def get_candidate(candidate_id: uuid.UUID, service: ServiceDep) -> CandidateRead:
    return await service.get_candidate(candidate_id)


@router.patch("/{candidate_id}", response_model=CandidateRead)
async def update_candidate(
    candidate_id: uuid.UUID, payload: CandidateUpdate, service: ServiceDep
) -> CandidateRead:
    return await service.update_candidate(candidate_id, payload)


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_candidate(candidate_id: uuid.UUID, service: ServiceDep) -> None:
    await service.delete_candidate(candidate_id)


@router.put("/{candidate_id}/profile", response_model=CandidateProfileRead)
async def upsert_profile(
    candidate_id: uuid.UUID, payload: CandidateProfileUpsert, service: ServiceDep
) -> CandidateProfileRead:
    return await service.upsert_profile(candidate_id, payload)


@router.get("/{candidate_id}/profile", response_model=CandidateProfileRead)
async def get_profile(
    candidate_id: uuid.UUID, service: ServiceDep
) -> CandidateProfileRead:
    return await service.get_profile(candidate_id)
