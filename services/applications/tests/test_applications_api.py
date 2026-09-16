"""Applications service API tests (eligibility uses local read-models)."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import seed_candidate, seed_job

Headers = dict[str, str]


async def test_apply_ok(
    client: AsyncClient, db_session: AsyncSession, candidate_headers: Headers
) -> None:
    job = await seed_job(db_session, "ready")
    cand = await seed_candidate(db_session)
    resp = await client.post(
        "/api/v1/applications",
        json={"job_id": str(job), "candidate_id": str(cand)},
        headers=candidate_headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "applied"


async def test_duplicate_409(
    client: AsyncClient, db_session: AsyncSession, candidate_headers: Headers
) -> None:
    job = await seed_job(db_session)
    cand = await seed_candidate(db_session)
    body = {"job_id": str(job), "candidate_id": str(cand)}
    first = await client.post("/api/v1/applications", json=body, headers=candidate_headers)
    assert first.status_code == 201
    dup = await client.post("/api/v1/applications", json=body, headers=candidate_headers)
    assert dup.status_code == 409


async def test_idempotent_retry(
    client: AsyncClient, db_session: AsyncSession, candidate_headers: Headers
) -> None:
    job = await seed_job(db_session)
    cand = await seed_candidate(db_session)
    body = {"job_id": str(job), "candidate_id": str(cand)}
    hdrs = {**candidate_headers, "Idempotency-Key": "k1"}
    first = await client.post("/api/v1/applications", json=body, headers=hdrs)
    second = await client.post("/api/v1/applications", json=body, headers=hdrs)
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]


async def test_eligibility_unknown_or_not_ready(
    client: AsyncClient, db_session: AsyncSession, candidate_headers: Headers
) -> None:
    cand = await seed_candidate(db_session)
    # Unknown job (no read-model row) → 422
    resp = await client.post(
        "/api/v1/applications",
        json={"job_id": str(uuid.uuid4()), "candidate_id": str(cand)},
        headers=candidate_headers,
    )
    assert resp.status_code == 422
    # Draft job → not applyable
    draft = await seed_job(db_session, "draft")
    resp2 = await client.post(
        "/api/v1/applications",
        json={"job_id": str(draft), "candidate_id": str(cand)},
        headers=candidate_headers,
    )
    assert resp2.status_code == 422


async def test_limit(
    client: AsyncClient,
    db_session: AsyncSession,
    candidate_headers: Headers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "max_active_applications", 1)
    cand = await seed_candidate(db_session)
    j1 = await seed_job(db_session)
    j2 = await seed_job(db_session)
    ok = await client.post(
        "/api/v1/applications",
        json={"job_id": str(j1), "candidate_id": str(cand)},
        headers=candidate_headers,
    )
    assert ok.status_code == 201
    over = await client.post(
        "/api/v1/applications",
        json={"job_id": str(j2), "candidate_id": str(cand)},
        headers=candidate_headers,
    )
    assert over.status_code == 422


async def test_stage_and_authz(
    client: AsyncClient,
    db_session: AsyncSession,
    candidate_headers: Headers,
    recruiter_headers: Headers,
) -> None:
    job = await seed_job(db_session)
    cand = await seed_candidate(db_session)
    app_id = (
        await client.post(
            "/api/v1/applications",
            json={"job_id": str(job), "candidate_id": str(cand)},
            headers=candidate_headers,
        )
    ).json()["id"]

    # recruiter advances applied -> screening
    ok = await client.patch(
        f"/api/v1/applications/{app_id}/stage",
        json={"status": "screening"},
        headers=recruiter_headers,
    )
    assert ok.status_code == 200
    # candidate cannot advance
    forbidden = await client.patch(
        f"/api/v1/applications/{app_id}/stage",
        json={"status": "interview"},
        headers=candidate_headers,
    )
    assert forbidden.status_code == 403
    # invalid jump screening -> offer
    bad = await client.patch(
        f"/api/v1/applications/{app_id}/stage",
        json={"status": "offer"},
        headers=recruiter_headers,
    )
    assert bad.status_code == 422


async def test_unauthenticated(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/applications")).status_code == 401
