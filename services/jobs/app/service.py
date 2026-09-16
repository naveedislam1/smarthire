"""Jobs business logic. Publishes job.* events for cross-service read-models."""

import uuid

from smarthire_common.events import (
    JOB_DELETED,
    TOPIC_JOB,
    EventEnvelope,
    KafkaEventPublisher,
)
from smarthire_common.exceptions import NotFoundError, ValidationError
from smarthire_common.pagination import Page

from app.enums import JobStatus
from app.events import publish_job_upserted
from app.models import Job
from app.repository import JobRepository
from app.schemas import JobCreate, JobRead, JobUpdate


class JobService:
    def __init__(self, repository: JobRepository, publisher: KafkaEventPublisher) -> None:
        self.repository = repository
        self.publisher = publisher

    async def create_job(
        self, payload: JobCreate, *, recruiter_id: uuid.UUID
    ) -> JobRead:
        job = Job(
            title=payload.title,
            description=payload.description,
            location=payload.location,
            employment_type=payload.employment_type,
            required_skills=payload.required_skills,
            hiring_stages=payload.hiring_stages,
            recruiter_id=recruiter_id,
            status=JobStatus.DRAFT,
        )
        job = await self.repository.create(job)
        await publish_job_upserted(self.publisher, job)
        return JobRead.model_validate(job)

    async def get_job(self, job_id: uuid.UUID) -> JobRead:
        return JobRead.model_validate(await self._get_or_404(job_id))

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
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(job, field, value)
        job = await self.repository.update(job)
        await publish_job_upserted(self.publisher, job)
        return JobRead.model_validate(job)

    async def request_publish(self, job_id: uuid.UUID) -> JobRead:
        job = await self._get_or_404(job_id)
        if job.status not in {JobStatus.DRAFT, JobStatus.FAILED}:
            raise ValidationError(
                f"Only draft or failed jobs can be published "
                f"(current status: {job.status})."
            )
        job.status = JobStatus.PROCESSING
        job = await self.repository.update(job)
        await publish_job_upserted(self.publisher, job)
        return JobRead.model_validate(job)

    async def delete_job(self, job_id: uuid.UUID) -> None:
        job = await self._get_or_404(job_id)
        await self.repository.delete(job)
        await self.publisher.publish(
            TOPIC_JOB, EventEnvelope(type=JOB_DELETED, data={"id": str(job_id)})
        )

    async def _get_or_404(self, job_id: uuid.UUID) -> Job:
        job = await self.repository.get(job_id)
        if job is None:
            raise NotFoundError(f"Job {job_id} not found.")
        return job
