"""Jobs service API tests."""

import uuid

from httpx import AsyncClient

Headers = dict[str, str]


async def _create(client: AsyncClient, headers: Headers, **overrides) -> dict:
    payload = {"title": "Backend Engineer", "description": "Build services."}
    payload.update(overrides)
    resp = await client.post("/api/v1/jobs", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_create_starts_draft(client: AsyncClient, recruiter_headers: Headers) -> None:
    job = await _create(client, recruiter_headers)
    assert job["status"] == "draft"
    assert job["recruiter_id"] is not None


async def test_publish_starts_workflow(
    client: AsyncClient, recruiter_headers: Headers
) -> None:
    job = await _create(client, recruiter_headers)
    resp = await client.post(
        f"/api/v1/jobs/{job['id']}/publish", headers=recruiter_headers
    )
    assert resp.status_code == 202
    assert resp.json()["status"] == "processing"
    assert client.fake_temporal.started == [job["id"]]
    # re-publish while processing → 422
    again = await client.post(
        f"/api/v1/jobs/{job['id']}/publish", headers=recruiter_headers
    )
    assert again.status_code == 422


async def test_authz(
    client: AsyncClient, recruiter_headers: Headers, candidate_headers: Headers
) -> None:
    assert (await client.get("/api/v1/jobs")).status_code == 401
    resp = await client.post(
        "/api/v1/jobs",
        json={"title": "x", "description": "y"},
        headers=candidate_headers,
    )
    assert resp.status_code == 403
    assert (await client.get("/api/v1/jobs", headers=candidate_headers)).status_code == 200


async def test_missing_404(client: AsyncClient, recruiter_headers: Headers) -> None:
    resp = await client.get(f"/api/v1/jobs/{uuid.uuid4()}", headers=recruiter_headers)
    assert resp.status_code == 404
