"""API tests for the Candidates domain (with auth enforced)."""

import uuid

from httpx import AsyncClient

Headers = dict[str, str]


async def _register(client: AsyncClient, headers: Headers, **overrides) -> dict:
    payload = {
        "email": "ada@example.com",
        "full_name": "Ada Lovelace",
        "phone": "+1-555-0100",
    }
    payload.update(overrides)
    resp = await client.post("/api/v1/candidates", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_register_candidate(
    client: AsyncClient, recruiter_headers: Headers
) -> None:
    candidate = await _register(client, recruiter_headers)
    assert candidate["email"] == "ada@example.com"
    assert candidate["profile"] is None


async def test_duplicate_email_returns_409(
    client: AsyncClient, recruiter_headers: Headers
) -> None:
    await _register(client, recruiter_headers)
    resp = await client.post(
        "/api/v1/candidates",
        json={"email": "ada@example.com", "full_name": "Ada II"},
        headers=recruiter_headers,
    )
    assert resp.status_code == 409


async def test_upsert_and_get_profile(
    client: AsyncClient, recruiter_headers: Headers
) -> None:
    candidate = await _register(client, recruiter_headers)
    cid = candidate["id"]

    missing = await client.get(
        f"/api/v1/candidates/{cid}/profile", headers=recruiter_headers
    )
    assert missing.status_code == 404

    upsert = await client.put(
        f"/api/v1/candidates/{cid}/profile",
        json={
            "headline": "Mathematician & first programmer",
            "skills": ["analytical-engine", "mathematics"],
            "experience_years": 10,
        },
        headers=recruiter_headers,
    )
    assert upsert.status_code == 200
    assert upsert.json()["skills"] == ["analytical-engine", "mathematics"]

    got = await client.get(
        f"/api/v1/candidates/{cid}/profile", headers=recruiter_headers
    )
    assert got.status_code == 200
    assert got.json()["headline"] == "Mathematician & first programmer"


async def test_update_and_delete_candidate(
    client: AsyncClient, recruiter_headers: Headers
) -> None:
    candidate = await _register(client, recruiter_headers)
    cid = candidate["id"]

    updated = await client.patch(
        f"/api/v1/candidates/{cid}",
        json={"phone": "+1-555-9999"},
        headers=recruiter_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["phone"] == "+1-555-9999"

    deleted = await client.delete(
        f"/api/v1/candidates/{cid}", headers=recruiter_headers
    )
    assert deleted.status_code == 204


async def test_get_missing_candidate_returns_404(
    client: AsyncClient, recruiter_headers: Headers
) -> None:
    resp = await client.get(
        f"/api/v1/candidates/{uuid.uuid4()}", headers=recruiter_headers
    )
    assert resp.status_code == 404


# --- Authorization ---
async def test_unauthenticated_is_rejected(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/candidates")).status_code == 401


async def test_candidate_role_cannot_list_pool(
    client: AsyncClient, candidate_headers: Headers
) -> None:
    resp = await client.get("/api/v1/candidates", headers=candidate_headers)
    assert resp.status_code == 403
