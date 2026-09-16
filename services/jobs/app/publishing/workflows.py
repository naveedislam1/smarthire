"""The Temporal job-publishing workflow (breakdown → extract → ready)."""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from app.publishing.constants import (
    BREAKDOWN,
    EXTRACT,
    MARK_FAILED,
    MARK_READY,
    WORKFLOW_NAME,
)

_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=10),
    maximum_attempts=3,
)
_TIMEOUT = timedelta(seconds=30)


@workflow.defn(name=WORKFLOW_NAME)
class JobPublishingWorkflow:
    @workflow.run
    async def run(self, job_id: str) -> str:
        try:
            await workflow.execute_activity(
                BREAKDOWN, job_id, start_to_close_timeout=_TIMEOUT, retry_policy=_RETRY
            )
            await workflow.execute_activity(
                EXTRACT, job_id, start_to_close_timeout=_TIMEOUT, retry_policy=_RETRY
            )
            await workflow.execute_activity(
                MARK_READY, job_id, start_to_close_timeout=_TIMEOUT, retry_policy=_RETRY
            )
            return "ready"
        except Exception:
            await workflow.execute_activity(
                MARK_FAILED, job_id, start_to_close_timeout=_TIMEOUT
            )
            raise
