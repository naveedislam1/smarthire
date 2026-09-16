"""Temporal activities — idempotent DB writes + job.* event emission."""

import uuid

from temporalio import activity

from app.database import SessionFactory
from app.enums import JobStatus
from app.events import publish_job_upserted, publisher
from app.models import Job
from app.publishing.constants import BREAKDOWN, EXTRACT, MARK_FAILED, MARK_READY
from app.publishing.content import (
    breakdown_description,
    extract_keywords,
    extract_skills,
)


async def _load(session, job_id: str) -> Job:
    job = await session.get(Job, uuid.UUID(job_id))
    if job is None:
        raise ValueError(f"Job {job_id} not found")
    return job


@activity.defn(name=BREAKDOWN)
async def breakdown_job(job_id: str) -> dict:
    async with SessionFactory() as session:
        job = await _load(session, job_id)
        job.structured_content = breakdown_description(job.description)
        await session.commit()
        return job.structured_content


@activity.defn(name=EXTRACT)
async def extract_job_skills_keywords(job_id: str) -> dict:
    async with SessionFactory() as session:
        job = await _load(session, job_id)
        text = f"{job.title}\n{job.description}"
        merged = list(dict.fromkeys([*job.required_skills, *extract_skills(text)]))
        job.required_skills = merged
        job.extracted_keywords = extract_keywords(text)
        await session.commit()
        return {"skills": merged, "keywords": job.extracted_keywords}


@activity.defn(name=MARK_READY)
async def mark_job_ready(job_id: str) -> None:
    async with SessionFactory() as session:
        job = await _load(session, job_id)
        job.status = JobStatus.READY
        await session.commit()
        await publish_job_upserted(publisher, job)


@activity.defn(name=MARK_FAILED)
async def mark_job_failed(job_id: str) -> None:
    async with SessionFactory() as session:
        job = await _load(session, job_id)
        job.status = JobStatus.FAILED
        await session.commit()
        await publish_job_upserted(publisher, job)
