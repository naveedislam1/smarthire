"""API tests for the Candidates domain."""

import uuid

from httpx import AsyncClient


async def _register(client: AsyncClient, **overrides) -> dict:
    payload = {
        "email": "ada@example.com",
        "full_name": "Ada Lovelace",
        "phone": "+1-555-0100",
    }
    payload.update(overrides)
    resp = await client.post("/api/v1/candidates", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_register_candidate(client: AsyncClient) -> None:
    candidate = await _register(client)
    assert candidate["email"] == "ada@example.com"
    assert candidate["profile"] is None


async def test_duplicate_email_returns_409(client: AsyncClient) -> None:
    await _register(client)
    resp = await client.post(
        "/api/v1/candidates",
        json={"email": "ada@example.com", "full_name": "Ada II"},
    )
    assert resp.status_code == 409


async def test_upsert_and_get_profile(client: AsyncClient) -> None:
    candidate = await _register(client)
    cid = candidate["id"]

    # No profile yet.
    assert (await client.get(f"/api/v1/candidates/{cid}/profile")).status_code == 404

    upsert = await client.put(
        f"/api/v1/candidates/{cid}/profile",
        json={
            "headline": "Mathematician & first programmer",
            "skills": ["analytical-engine", "mathematics"],
            "experience_years": 10,
        },
    )
    assert upsert.status_code == 200
    assert upsert.json()["skills"] == ["analytical-engine", "mathematics"]

    got = await client.get(f"/api/v1/candidates/{cid}/profile")
    assert got.status_code == 200
    assert got.json()["headline"] == "Mathematician & first programmer"

    # Second upsert updates in place (still one profile).
    again = await client.put(
        f"/api/v1/candidates/{cid}/profile",
        json={"headline": "Countess of Lovelace", "skills": []},
    )
    assert again.status_code == 200
    assert again.json()["headline"] == "Countess of Lovelace"


async def test_update_and_delete_candidate(client: AsyncClient) -> None:
    candidate = await _register(client)
    cid = candidate["id"]

    updated = await client.patch(
        f"/api/v1/candidates/{cid}", json={"phone": "+1-555-9999"}
    )
    assert updated.status_code == 200
    assert updated.json()["phone"] == "+1-555-9999"

    assert (await client.delete(f"/api/v1/candidates/{cid}")).status_code == 204
    assert (await client.get(f"/api/v1/candidates/{cid}")).status_code == 404


async def test_get_missing_candidate_returns_404(client: AsyncClient) -> None:
    resp = await client.get(f"/api/v1/candidates/{uuid.uuid4()}")
    assert resp.status_code == 404
