"""Starts the publishing workflow from the jobs API.

Behind a small protocol so the API can depend on it and tests can substitute a
fake that records calls instead of contacting Temporal.
"""

from typing import Protocol

from smarthire_common.logging import get_logger
from temporalio.client import Client

from app.config import settings
from app.publishing.constants import WORKFLOW_NAME

logger = get_logger(__name__)


class JobPublisher(Protocol):
    async def start(self, job_id: str) -> None: ...


class TemporalPublisher:
    async def start(self, job_id: str) -> None:
        client = await Client.connect(
            settings.temporal_host, namespace=settings.temporal_namespace
        )
        await client.start_workflow(
            WORKFLOW_NAME,
            job_id,
            id=f"publish-{job_id}",
            task_queue=settings.temporal_task_queue,
        )
        logger.info("Started publishing workflow for job %s", job_id)


_publisher = TemporalPublisher()


def get_temporal_publisher() -> JobPublisher:
    return _publisher
