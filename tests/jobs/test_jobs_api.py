"""API tests for the Jobs domain (with auth enforced)."""

import uuid

from httpx import AsyncClient

Headers = dict[str, str]


async def _create_job(client: AsyncClient, headers: Headers, **overrides) -> dict:
    payload = {
        "title": "Backend Engineer",
        "description": "Build scalable services.",
        "location": "Remote",
        "employment_type": "full_time",
        "required_skills": ["python", "fastapi"],
        "hiring_stages": ["Screening", "Interview", "Offer"],
    }
    payload.update(overrides)
    resp = await client.post("/api/v1/jobs", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_create_job_starts_as_draft(
    client: AsyncClient, recruiter_headers: Headers
) -> None:
    job = await _create_job(client, recruiter_headers)
    assert job["status"] == "draft"
    assert job["title"] == "Backend Engineer"
    assert job["required_skills"] == ["python", "fastapi"]
    # recruiter_id is derived from the authenticated recruiter.
    assert job["recruiter_id"] is not None


async def test_get_and_list_jobs(
    client: AsyncClient, recruiter_headers: Headers
) -> None:
    created = await _create_job(client, recruiter_headers)

    got = await client.get(f"/api/v1/jobs/{created['id']}", headers=recruiter_headers)
    assert got.status_code == 200
    assert got.json()["id"] == created["id"]

    listed = await client.get("/api/v1/jobs", headers=recruiter_headers)
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1


async def test_publish_flow(client: AsyncClient, recruiter_headers: Headers) -> None:
    created = await _create_job(client, recruiter_headers)
    published = await client.post(
        f"/api/v1/jobs/{created['id']}/publish", headers=recruiter_headers
    )
    assert published.status_code == 200
    assert published.json()["status"] == "published"

    again = await client.post(
        f"/api/v1/jobs/{created['id']}/publish", headers=recruiter_headers
    )
    assert again.status_code == 422


async def test_delete_job(client: AsyncClient, recruiter_headers: Headers) -> None:
    created = await _create_job(client, recruiter_headers)
    resp = await client.delete(
        f"/api/v1/jobs/{created['id']}", headers=recruiter_headers
    )
    assert resp.status_code == 204


async def test_get_missing_job_returns_404(
    client: AsyncClient, recruiter_headers: Headers
) -> None:
    resp = await client.get(
        f"/api/v1/jobs/{uuid.uuid4()}", headers=recruiter_headers
    )
    assert resp.status_code == 404


# --- Authorization ---
async def test_unauthenticated_is_rejected(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/jobs")).status_code == 401
    resp = await client.post("/api/v1/jobs", json={"title": "x", "description": "y"})
    assert resp.status_code == 401


async def test_candidate_cannot_create_job(
    client: AsyncClient, candidate_headers: Headers
) -> None:
    resp = await client.post(
        "/api/v1/jobs",
        json={"title": "x", "description": "y"},
        headers=candidate_headers,
    )
    assert resp.status_code == 403

    # ...but a candidate may still browse jobs.
    assert (await client.get("/api/v1/jobs", headers=candidate_headers)).status_code == 200
