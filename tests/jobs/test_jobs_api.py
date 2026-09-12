"""API tests for the Jobs domain."""

import uuid

from httpx import AsyncClient


async def _create_job(client: AsyncClient, **overrides) -> dict:
    payload = {
        "title": "Backend Engineer",
        "description": "Build scalable services.",
        "location": "Remote",
        "employment_type": "full_time",
        "required_skills": ["python", "fastapi"],
        "hiring_stages": ["Screening", "Interview", "Offer"],
    }
    payload.update(overrides)
    resp = await client.post("/api/v1/jobs", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_create_job_starts_as_draft(client: AsyncClient) -> None:
    job = await _create_job(client)
    assert job["status"] == "draft"
    assert job["title"] == "Backend Engineer"
    assert job["required_skills"] == ["python", "fastapi"]


async def test_get_and_list_jobs(client: AsyncClient) -> None:
    created = await _create_job(client)

    got = await client.get(f"/api/v1/jobs/{created['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == created["id"]

    listed = await client.get("/api/v1/jobs")
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1


async def test_update_job(client: AsyncClient) -> None:
    created = await _create_job(client)
    resp = await client.patch(
        f"/api/v1/jobs/{created['id']}", json={"title": "Senior Backend Engineer"}
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Senior Backend Engineer"


async def test_publish_flow(client: AsyncClient) -> None:
    created = await _create_job(client)
    published = await client.post(f"/api/v1/jobs/{created['id']}/publish")
    assert published.status_code == 200
    assert published.json()["status"] == "published"

    # Publishing again is rejected.
    again = await client.post(f"/api/v1/jobs/{created['id']}/publish")
    assert again.status_code == 422

    # Filtering by status returns the published job.
    listed = await client.get("/api/v1/jobs", params={"status_filter": "published"})
    assert listed.json()["total"] == 1


async def test_delete_job(client: AsyncClient) -> None:
    created = await _create_job(client)
    resp = await client.delete(f"/api/v1/jobs/{created['id']}")
    assert resp.status_code == 204
    assert (await client.get(f"/api/v1/jobs/{created['id']}")).status_code == 404


async def test_get_missing_job_returns_404(client: AsyncClient) -> None:
    resp = await client.get(f"/api/v1/jobs/{uuid.uuid4()}")
    assert resp.status_code == 404
