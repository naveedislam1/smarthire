"""Job data access."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import JobStatus
from app.models import Job


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, job: Job) -> Job:
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get(self, job_id: uuid.UUID) -> Job | None:
        return await self.session.get(Job, job_id)

    async def list(
        self, *, limit: int, offset: int, status: JobStatus | None = None
    ) -> tuple[list[Job], int]:
        stmt = select(Job)
        count_stmt = select(func.count()).select_from(Job)
        if status is not None:
            stmt = stmt.where(Job.status == status)
            count_stmt = count_stmt.where(Job.status == status)
        stmt = stmt.order_by(Job.created_at.desc()).limit(limit).offset(offset)
        items = list((await self.session.scalars(stmt)).all())
        total = (await self.session.scalar(count_stmt)) or 0
        return items, total

    async def update(self, job: Job) -> Job:
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def delete(self, job: Job) -> None:
        await self.session.delete(job)
        await self.session.commit()
