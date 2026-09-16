"""Candidates service API tests."""

import uuid

from httpx import AsyncClient

Headers = dict[str, str]


async def _register(client: AsyncClient, headers: Headers, **overrides) -> dict:
    payload = {"email": "ada@example.com", "full_name": "Ada Lovelace"}
    payload.update(overrides)
    resp = await client.post("/api/v1/candidates", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_register(client: AsyncClient, recruiter_headers: Headers) -> None:
    body = await _register(client, recruiter_headers)
    assert body["email"] == "ada@example.com"
    assert body["profile"] is None


async def test_duplicate_email_409(client: AsyncClient, recruiter_headers: Headers) -> None:
    await _register(client, recruiter_headers)
    resp = await client.post(
        "/api/v1/candidates",
        json={"email": "ada@example.com", "full_name": "Dup"},
        headers=recruiter_headers,
    )
    assert resp.status_code == 409


async def test_profile_upsert_get(client: AsyncClient, recruiter_headers: Headers) -> None:
    cid = (await _register(client, recruiter_headers))["id"]
    assert (
        await client.get(f"/api/v1/candidates/{cid}/profile", headers=recruiter_headers)
    ).status_code == 404
    up = await client.put(
        f"/api/v1/candidates/{cid}/profile",
        json={"headline": "First programmer", "skills": ["math"]},
        headers=recruiter_headers,
    )
    assert up.status_code == 200
    assert up.json()["skills"] == ["math"]


async def test_authz(client: AsyncClient, candidate_headers: Headers) -> None:
    assert (await client.get("/api/v1/candidates")).status_code == 401  # no token
    # candidate role cannot list the pool
    resp = await client.get("/api/v1/candidates", headers=candidate_headers)
    assert resp.status_code == 403


async def test_missing_404(client: AsyncClient, recruiter_headers: Headers) -> None:
    resp = await client.get(
        f"/api/v1/candidates/{uuid.uuid4()}", headers=recruiter_headers
    )
    assert resp.status_code == 404
