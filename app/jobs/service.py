"""Business logic for the Jobs domain.

The service enforces domain rules (state transitions, existence checks) and
orchestrates the repository. It raises framework-agnostic domain exceptions,
which the API layer maps to HTTP responses.
"""

import uuid

from app.common.enums import JobStatus
from app.common.pagination import Page
from app.core.exceptions import NotFoundError, ValidationError
from app.jobs.models import Job
from app.jobs.repository import JobRepository
from app.jobs.schemas import JobCreate, JobRead, JobUpdate


class JobService:
    def __init__(self, repository: JobRepository) -> None:
        self.repository = repository

    async def create_job(self, payload: JobCreate) -> JobRead:
        job = Job(
            title=payload.title,
            description=payload.description,
            location=payload.location,
            employment_type=payload.employment_type,
            required_skills=payload.required_skills,
            hiring_stages=payload.hiring_stages,
            recruiter_id=payload.recruiter_id,
            status=JobStatus.DRAFT,
        )
        job = await self.repository.create(job)
        return JobRead.model_validate(job)

    async def get_job(self, job_id: uuid.UUID) -> JobRead:
        job = await self._get_or_404(job_id)
        return JobRead.model_validate(job)

    async def list_jobs(
        self, *, limit: int, offset: int, status: JobStatus | None
    ) -> Page[JobRead]:
        items, total = await self.repository.list(
            limit=limit, offset=offset, status=status
        )
        return Page[JobRead](
            items=[JobRead.model_validate(j) for j in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def update_job(self, job_id: uuid.UUID, payload: JobUpdate) -> JobRead:
        job = await self._get_or_404(job_id)
        # Apply only the fields the client actually sent.
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(job, field, value)
        job = await self.repository.update(job)
        return JobRead.model_validate(job)

    async def publish_job(self, job_id: uuid.UUID) -> JobRead:
        """Basic Week-1 posting flow: DRAFT -> PUBLISHED.

        Week 2 replaces this with a Temporal workflow that moves the job through
        PROCESSING -> READY after skill extraction and content breakdown.
        """
        job = await self._get_or_404(job_id)
        if job.status == JobStatus.PUBLISHED:
            raise ValidationError("Job is already published.")
        if job.status != JobStatus.DRAFT:
            raise ValidationError(
                f"Only draft jobs can be published (current status: {job.status})."
            )
        job.status = JobStatus.PUBLISHED
        job = await self.repository.update(job)
        return JobRead.model_validate(job)

    async def delete_job(self, job_id: uuid.UUID) -> None:
        job = await self._get_or_404(job_id)
        await self.repository.delete(job)

    async def _get_or_404(self, job_id: uuid.UUID) -> Job:
        job = await self.repository.get(job_id)
        if job is None:
            raise NotFoundError(f"Job {job_id} not found.")
        return job
