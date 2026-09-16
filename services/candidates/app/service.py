"""Candidates business logic. Publishes candidate.* events for read-models."""

import uuid

from smarthire_common.events import (
    CANDIDATE_DELETED,
    CANDIDATE_UPSERTED,
    TOPIC_CANDIDATE,
    EventEnvelope,
    KafkaEventPublisher,
)
from smarthire_common.exceptions import ConflictError, NotFoundError
from smarthire_common.pagination import Page

from app.models import Candidate, CandidateProfile
from app.repository import CandidateRepository
from app.schemas import (
    CandidateCreate,
    CandidateProfileRead,
    CandidateProfileUpsert,
    CandidateRead,
    CandidateUpdate,
)


class CandidateService:
    def __init__(
        self, repository: CandidateRepository, publisher: KafkaEventPublisher
    ) -> None:
        self.repository = repository
        self.publisher = publisher

    async def register_candidate(self, payload: CandidateCreate) -> CandidateRead:
        if await self.repository.get_by_email(payload.email) is not None:
            raise ConflictError(
                f"A candidate with email {payload.email} already exists."
            )
        candidate = Candidate(
            email=payload.email, full_name=payload.full_name, phone=payload.phone
        )
        candidate = await self.repository.create(candidate)
        await self._publish_upserted(candidate.id)
        return CandidateRead.model_validate(candidate)

    async def get_candidate(self, candidate_id: uuid.UUID) -> CandidateRead:
        return CandidateRead.model_validate(await self._get_or_404(candidate_id))

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
        await self._publish_upserted(candidate.id)
        return CandidateRead.model_validate(candidate)

    async def delete_candidate(self, candidate_id: uuid.UUID) -> None:
        candidate = await self._get_or_404(candidate_id)
        await self.repository.delete(candidate)
        await self.publisher.publish(
            TOPIC_CANDIDATE,
            EventEnvelope(type=CANDIDATE_DELETED, data={"id": str(candidate_id)}),
        )

    async def upsert_profile(
        self, candidate_id: uuid.UUID, payload: CandidateProfileUpsert
    ) -> CandidateProfileRead:
        candidate = await self._get_or_404(candidate_id)
        profile = candidate.profile or CandidateProfile(candidate_id=candidate.id)
        if candidate.profile is None:
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

    async def _publish_upserted(self, candidate_id: uuid.UUID) -> None:
        await self.publisher.publish(
            TOPIC_CANDIDATE,
            EventEnvelope(type=CANDIDATE_UPSERTED, data={"id": str(candidate_id)}),
        )
