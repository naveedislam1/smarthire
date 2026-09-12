"""Business logic for the Candidates domain."""

import uuid

from app.candidates.models import Candidate, CandidateProfile
from app.candidates.repository import CandidateRepository
from app.candidates.schemas import (
    CandidateCreate,
    CandidateProfileRead,
    CandidateProfileUpsert,
    CandidateRead,
    CandidateUpdate,
)
from app.common.pagination import Page
from app.core.exceptions import ConflictError, NotFoundError


class CandidateService:
    def __init__(self, repository: CandidateRepository) -> None:
        self.repository = repository

    async def register_candidate(self, payload: CandidateCreate) -> CandidateRead:
        # Enforce unique email as a business rule so we can return a clean 409
        # rather than leaking a database IntegrityError.
        existing = await self.repository.get_by_email(payload.email)
        if existing is not None:
            raise ConflictError(f"A candidate with email {payload.email} already exists.")
        candidate = Candidate(
            email=payload.email,
            full_name=payload.full_name,
            phone=payload.phone,
        )
        candidate = await self.repository.create(candidate)
        return CandidateRead.model_validate(candidate)

    async def get_candidate(self, candidate_id: uuid.UUID) -> CandidateRead:
        candidate = await self._get_or_404(candidate_id)
        return CandidateRead.model_validate(candidate)

    async def list_candidates(self, *, limit: int, offset: int) -> Page[CandidateRead]:
        items, total = await self.repository.list(limit=limit, offset=offset)
        return Page[CandidateRead](
            items=[CandidateRead.model_validate(c) for c in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def update_candidate(
        self, candidate_id: uuid.UUID, payload: CandidateUpdate
    ) -> CandidateRead:
        candidate = await self._get_or_404(candidate_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(candidate, field, value)
        candidate = await self.repository.save(candidate)
        return CandidateRead.model_validate(candidate)

    async def delete_candidate(self, candidate_id: uuid.UUID) -> None:
        candidate = await self._get_or_404(candidate_id)
        await self.repository.delete(candidate)

    # --- Profile ---
    async def upsert_profile(
        self, candidate_id: uuid.UUID, payload: CandidateProfileUpsert
    ) -> CandidateProfileRead:
        candidate = await self._get_or_404(candidate_id)
        profile = candidate.profile
        if profile is None:
            profile = CandidateProfile(candidate_id=candidate.id)
            candidate.profile = profile
        for field, value in payload.model_dump().items():
            setattr(profile, field, value)
        await self.repository.save(candidate)
        return CandidateProfileRead.model_validate(profile)

    async def get_profile(self, candidate_id: uuid.UUID) -> CandidateProfileRead:
        await self._get_or_404(candidate_id)
        profile = await self.repository.get_profile(candidate_id)
        if profile is None:
            raise NotFoundError(f"Candidate {candidate_id} has no profile yet.")
        return CandidateProfileRead.model_validate(profile)

    async def _get_or_404(self, candidate_id: uuid.UUID) -> Candidate:
        candidate = await self.repository.get(candidate_id)
        if candidate is None:
            raise NotFoundError(f"Candidate {candidate_id} not found.")
        return candidate
