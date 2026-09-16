"""Candidate data access."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Candidate, CandidateProfile


class CandidateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, candidate: Candidate) -> Candidate:
        self.session.add(candidate)
        await self.session.commit()
        await self.session.refresh(candidate)
        return candidate

    async def get(self, candidate_id: uuid.UUID) -> Candidate | None:
        return await self.session.get(Candidate, candidate_id)

    async def get_by_email(self, email: str) -> Candidate | None:
        return await self.session.scalar(
            select(Candidate).where(Candidate.email == email)
        )

    async def list(self, *, limit: int, offset: int) -> tuple[list[Candidate], int]:
        stmt = (
            select(Candidate)
            .order_by(Candidate.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list((await self.session.scalars(stmt)).all())
        total = (
            await self.session.scalar(select(func.count()).select_from(Candidate))
        ) or 0
        return items, total

    async def save(self, candidate: Candidate) -> Candidate:
        await self.session.commit()
        await self.session.refresh(candidate)
        return candidate

    async def delete(self, candidate: Candidate) -> None:
        await self.session.delete(candidate)
        await self.session.commit()

    async def get_profile(self, candidate_id: uuid.UUID) -> CandidateProfile | None:
        return await self.session.scalar(
            select(CandidateProfile).where(
                CandidateProfile.candidate_id == candidate_id
            )
        )
