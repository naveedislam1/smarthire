"""Data-access layer for the Jobs domain.

The repository is the only place that talks to the database for jobs. It
returns ORM objects (or ``None``) and performs no business-rule logic — that
lives in the service layer.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import JobStatus
from app.jobs.models import Job


class JobRepository:
    """Async CRUD operations for :class:`Job`."""

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
        self,
        *,
        limit: int,
        offset: int,
        status: JobStatus | None = None,
    ) -> tuple[list[Job], int]:
        """Return a page of jobs plus the total count for the filter."""
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
