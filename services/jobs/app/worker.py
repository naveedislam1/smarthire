"""Temporal worker for the jobs service. Run: uv run python -m app.worker"""

import asyncio

from smarthire_common.logging import configure_logging, get_logger
from temporalio.client import Client
from temporalio.worker import Worker

from app.config import settings
from app.events import publisher
from app.publishing.activities import (
    breakdown_job,
    extract_job_skills_keywords,
    mark_job_failed,
    mark_job_ready,
)
from app.publishing.workflows import JobPublishingWorkflow

logger = get_logger(__name__)


async def main() -> None:
    configure_logging(settings.log_level)
    await publisher.start()  # activities emit job.* events on ready/failed
    client = await Client.connect(
        settings.temporal_host, namespace=settings.temporal_namespace
    )
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[JobPublishingWorkflow],
        activities=[
            breakdown_job,
            extract_job_skills_keywords,
            mark_job_ready,
            mark_job_failed,
        ],
    )
    logger.info("Jobs worker started on task queue '%s'", settings.temporal_task_queue)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
