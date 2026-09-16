"""Applications business logic.

Eligibility is checked against **local read-models** (JobRef/CandidateRef) fed by
Kafka events — so applying does not depend on the Jobs/Candidates services being
up. Publishes application.* events.
"""

import uuid
from datetime import UTC, datetime

from smarthire_common.config import BaseServiceSettings
from smarthire_common.events import (
    APPLICATION_CREATED,
    APPLICATION_STAGE_CHANGED,
    APPLICATION_WITHDRAWN,
    TOPIC_APPLICATION,
    EventEnvelope,
    KafkaEventPublisher,
)
from smarthire_common.exceptions import ConflictError, NotFoundError, ValidationError
from smarthire_common.pagination import Page

from app.enums import APPLICATION_TRANSITIONS, ApplicationStatus
from app.models import Application
from app.repository import ApplicationRepository
from app.schemas import ApplicationRead

# Job statuses that are open for applications (mirrors the jobs service).
_APPLYABLE = {"published", "ready"}


class ApplicationService:
    def __init__(
        self,
        repository: ApplicationRepository,
        publisher: KafkaEventPublisher,
        settings: BaseServiceSettings,
    ) -> None:
        self.repository = repository
        self.publisher = publisher
        self.max_active = getattr(settings, "max_active_applications", 10)

    async def apply(
        self,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
        *,
        idempotent: bool = False,
    ) -> ApplicationRead:
        # Eligibility checked against local read-models (resilient to Jobs/
        # Candidates downtime).
        if await self.repository.get_candidate_ref(candidate_id) is None:
            raise ValidationError(f"Unknown candidate {candidate_id}.")
        job_ref = await self.repository.get_job_ref(job_id)
        if job_ref is None:
            raise ValidationError(f"Unknown job {job_id}.")
        if job_ref.status not in _APPLYABLE:
            raise ValidationError(
                f"Job is not open for applications (status: {job_ref.status})."
            )

        existing = await self.repository.get_for_pair(job_id, candidate_id)
        if existing is not None:
            if idempotent:
                return ApplicationRead.model_validate(existing)
            raise ConflictError("This candidate has already applied to this job.")

        if await self.repository.count_active_for_candidate(candidate_id) >= self.max_active:
            raise ValidationError(
                f"Candidate has reached the active application limit ({self.max_active})."
            )

        application = Application(
            job_id=job_id,
            candidate_id=candidate_id,
            status=ApplicationStatus.APPLIED,
            stage_history=[_entry(ApplicationStatus.APPLIED)],
        )
        application = await self.repository.create(application)
        await self._publish(APPLICATION_CREATED, application)
        return ApplicationRead.model_validate(application)

    async def get(self, application_id: uuid.UUID) -> ApplicationRead:
        return ApplicationRead.model_validate(await self._get_or_404(application_id))

    async def list(
        self,
        *,
        limit: int,
        offset: int,
        job_id: uuid.UUID | None = None,
        candidate_id: uuid.UUID | None = None,
        status: ApplicationStatus | None = None,
    ) -> Page[ApplicationRead]:
        items, total = await self.repository.list(
            limit=limit, offset=offset, job_id=job_id, candidate_id=candidate_id, status=status
        )
        return Page[ApplicationRead](
            items=[ApplicationRead.model_validate(a) for a in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def advance_stage(
        self, application_id: uuid.UUID, new_status: ApplicationStatus
    ) -> ApplicationRead:
        application = await self._get_or_404(application_id)
        if new_status not in APPLICATION_TRANSITIONS.get(application.status, set()):
            raise ValidationError(
                f"Cannot move application from {application.status} to {new_status}."
            )
        application.status = new_status
        application.stage_history = [*application.stage_history, _entry(new_status)]
        application = await self.repository.save(application)
        await self._publish(APPLICATION_STAGE_CHANGED, application)
        return ApplicationRead.model_validate(application)

    async def withdraw(self, application_id: uuid.UUID) -> ApplicationRead:
        application = await self._get_or_404(application_id)
        if application.status in {
            ApplicationStatus.HIRED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        }:
            raise ValidationError(
                f"Cannot withdraw an application in state {application.status}."
            )
        application.status = ApplicationStatus.WITHDRAWN
        application.stage_history = [
            *application.stage_history,
            _entry(ApplicationStatus.WITHDRAWN),
        ]
        application = await self.repository.save(application)
        await self._publish(APPLICATION_WITHDRAWN, application)
        return ApplicationRead.model_validate(application)

    async def _get_or_404(self, application_id: uuid.UUID) -> Application:
        application = await self.repository.get(application_id)
        if application is None:
            raise NotFoundError(f"Application {application_id} not found.")
        return application

    async def _publish(self, event_type: str, application: Application) -> None:
        await self.publisher.publish(
            TOPIC_APPLICATION,
            EventEnvelope(
                type=event_type,
                data={
                    "id": str(application.id),
                    "job_id": str(application.job_id),
                    "candidate_id": str(application.candidate_id),
                    "status": application.status.value,
                },
            ),
        )


def _entry(status: ApplicationStatus) -> dict:
    return {"status": status.value, "at": datetime.now(UTC).isoformat()}
