"""Applications data access + read-model upserts."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import ACTIVE_APPLICATION_STATUSES, ApplicationStatus
from app.models import Application, CandidateRef, JobRef


class ApplicationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, application: Application) -> Application:
        self.session.add(application)
        await self.session.commit()
        await self.session.refresh(application)
        return application

    async def get(self, application_id: uuid.UUID) -> Application | None:
        return await self.session.get(Application, application_id)

    async def get_for_pair(
        self, job_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> Application | None:
        return await self.session.scalar(
            select(Application).where(
                Application.job_id == job_id,
                Application.candidate_id == candidate_id,
            )
        )

    async def count_active_for_candidate(self, candidate_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Application)
            .where(
                Application.candidate_id == candidate_id,
                Application.status.in_(tuple(ACTIVE_APPLICATION_STATUSES)),
            )
        )
        return (await self.session.scalar(stmt)) or 0

    async def list(
        self,
        *,
        limit: int,
        offset: int,
        job_id: uuid.UUID | None = None,
        candidate_id: uuid.UUID | None = None,
        status: ApplicationStatus | None = None,
    ) -> tuple[list[Application], int]:
        stmt = select(Application)
        count_stmt = select(func.count()).select_from(Application)
        for column, value in (
            (Application.job_id, job_id),
            (Application.candidate_id, candidate_id),
            (Application.status, status),
        ):
            if value is not None:
                stmt = stmt.where(column == value)
                count_stmt = count_stmt.where(column == value)
        stmt = stmt.order_by(Application.applied_at.desc()).limit(limit).offset(offset)
        items = list((await self.session.scalars(stmt)).all())
        total = (await self.session.scalar(count_stmt)) or 0
        return items, total

    async def save(self, application: Application) -> Application:
        await self.session.commit()
        await self.session.refresh(application)
        return application

    # --- Read-model helpers ---
    async def get_job_ref(self, job_id: uuid.UUID) -> JobRef | None:
        return await self.session.get(JobRef, job_id)

    async def get_candidate_ref(self, candidate_id: uuid.UUID) -> CandidateRef | None:
        return await self.session.get(CandidateRef, candidate_id)
