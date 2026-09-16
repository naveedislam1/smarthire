"""Kafka consumer that maintains the job/candidate read-models.

Runs as a background task inside the applications service. Handlers are
idempotent (upsert/delete by id), so redelivered events are safe.
"""

import uuid

from smarthire_common.events import (
    CANDIDATE_DELETED,
    CANDIDATE_UPSERTED,
    JOB_DELETED,
    JOB_UPSERTED,
    TOPIC_CANDIDATE,
    TOPIC_JOB,
    EventEnvelope,
    run_consumer,
)
from smarthire_common.logging import get_logger

from app.database import SessionFactory
from app.models import CandidateRef, JobRef

logger = get_logger(__name__)

CONSUMER_GROUP = "applications-read-models"


async def handle_event(env: EventEnvelope) -> None:
    async with SessionFactory() as session:
        if env.type == JOB_UPSERTED:
            job_id = uuid.UUID(env.data["id"])
            status = env.data["status"]
            ref = await session.get(JobRef, job_id)
            if ref is None:
                session.add(JobRef(id=job_id, status=status))
            else:
                ref.status = status
            await session.commit()

        elif env.type == JOB_DELETED:
            ref = await session.get(JobRef, uuid.UUID(env.data["id"]))
            if ref is not None:
                await session.delete(ref)
                await session.commit()

        elif env.type == CANDIDATE_UPSERTED:
            cid = uuid.UUID(env.data["id"])
            if await session.get(CandidateRef, cid) is None:
                session.add(CandidateRef(id=cid))
                await session.commit()

        elif env.type == CANDIDATE_DELETED:
            ref = await session.get(CandidateRef, uuid.UUID(env.data["id"]))
            if ref is not None:
                await session.delete(ref)
                await session.commit()


async def run_read_model_consumer(bootstrap_servers: str) -> None:
    await run_consumer(
        bootstrap_servers=bootstrap_servers,
        topics=[TOPIC_JOB, TOPIC_CANDIDATE],
        group_id=CONSUMER_GROUP,
        handler=handle_event,
    )
