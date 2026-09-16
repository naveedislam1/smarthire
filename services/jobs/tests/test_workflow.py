"""Temporal orchestration tests with stand-in activities (no DB)."""

import uuid

import pytest
from temporalio import activity
from temporalio.client import WorkflowFailureError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from app.publishing.constants import (
    BREAKDOWN,
    EXTRACT,
    MARK_FAILED,
    MARK_READY,
    WORKFLOW_NAME,
)
from app.publishing.workflows import JobPublishingWorkflow

TASK_QUEUE = "test-publishing"


def _activities(calls: list[str], *, fail_on: str | None = None):
    @activity.defn(name=BREAKDOWN)
    async def breakdown(job_id: str) -> dict:
        calls.append(BREAKDOWN)
        if fail_on == BREAKDOWN:
            raise RuntimeError("boom")
        return {}

    @activity.defn(name=EXTRACT)
    async def extract(job_id: str) -> dict:
        calls.append(EXTRACT)
        if fail_on == EXTRACT:
            raise RuntimeError("boom")
        return {}

    @activity.defn(name=MARK_READY)
    async def mark_ready(job_id: str) -> None:
        calls.append(MARK_READY)

    @activity.defn(name=MARK_FAILED)
    async def mark_failed(job_id: str) -> None:
        calls.append(MARK_FAILED)

    return [breakdown, extract, mark_ready, mark_failed]


async def test_happy_path() -> None:
    calls: list[str] = []
    job_id = str(uuid.uuid4())
    async with (
        await WorkflowEnvironment.start_time_skipping() as env,
        Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[JobPublishingWorkflow],
            activities=_activities(calls),
        ),
    ):
        result = await env.client.execute_workflow(
            WORKFLOW_NAME, job_id, id=f"wf-{job_id}", task_queue=TASK_QUEUE
        )
    assert result == "ready"
    assert calls == [BREAKDOWN, EXTRACT, MARK_READY]


async def test_failure_marks_failed() -> None:
    calls: list[str] = []
    job_id = str(uuid.uuid4())
    async with (
        await WorkflowEnvironment.start_time_skipping() as env,
        Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[JobPublishingWorkflow],
            activities=_activities(calls, fail_on=EXTRACT),
        ),
    ):
        with pytest.raises(WorkflowFailureError):
            await env.client.execute_workflow(
                WORKFLOW_NAME, job_id, id=f"wf-{job_id}", task_queue=TASK_QUEUE
            )
    assert MARK_FAILED in calls
    assert MARK_READY not in calls
