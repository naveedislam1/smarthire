"""The read-model consumer keeps JobRef/CandidateRef current from events."""

import uuid

import app.consumers as consumers
import pytest
from app.database import Base
from app.models import CandidateRef, JobRef
from smarthire_common.events import (
    CANDIDATE_UPSERTED,
    JOB_DELETED,
    JOB_UPSERTED,
    EventEnvelope,
)
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.fixture
async def factory(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    f = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(consumers, "SessionFactory", f)
    yield f
    await engine.dispose()


async def test_job_upserted_and_deleted(factory) -> None:
    jid = uuid.uuid4()
    await consumers.handle_event(
        EventEnvelope(type=JOB_UPSERTED, data={"id": str(jid), "status": "ready"})
    )
    async with factory() as s:
        ref = await s.get(JobRef, jid)
        assert ref is not None and ref.status == "ready"

    # status update
    await consumers.handle_event(
        EventEnvelope(type=JOB_UPSERTED, data={"id": str(jid), "status": "failed"})
    )
    async with factory() as s:
        assert (await s.get(JobRef, jid)).status == "failed"

    # delete
    await consumers.handle_event(
        EventEnvelope(type=JOB_DELETED, data={"id": str(jid)})
    )
    async with factory() as s:
        assert await s.get(JobRef, jid) is None


async def test_candidate_upserted(factory) -> None:
    cid = uuid.uuid4()
    await consumers.handle_event(
        EventEnvelope(type=CANDIDATE_UPSERTED, data={"id": str(cid)})
    )
    async with factory() as s:
        assert await s.get(CandidateRef, cid) is not None
