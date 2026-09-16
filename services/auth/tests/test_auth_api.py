"""Auth service API tests (RS256)."""

from httpx import AsyncClient


async def _register(client: AsyncClient, email: str, role: str = "candidate") -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "T", "role": role},
    )
    assert resp.status_code == 201, resp.text


async def test_register_login_me(client: AsyncClient) -> None:
    await _register(client, "grace@example.com", "recruiter")
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "grace@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    tokens = login.json()
    assert tokens["access_token"] and tokens["refresh_token"]

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "grace@example.com"
    assert me.json()["role"] == "recruiter"


async def test_duplicate_registration_409(client: AsyncClient) -> None:
    await _register(client, "dup@example.com")
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "password123", "full_name": "D"},
    )
    assert resp.status_code == 409


async def test_wrong_password_401(client: AsyncClient) -> None:
    await _register(client, "eve@example.com")
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "eve@example.com", "password": "nope"},
    )
    assert resp.status_code == 401


async def test_refresh_and_type_guard(client: AsyncClient) -> None:
    await _register(client, "linus@example.com")
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "linus@example.com", "password": "password123"},
    )
    tokens = login.json()
    ok = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert ok.status_code == 200
    # An access token is rejected where a refresh token is expected.
    bad = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]}
    )
    assert bad.status_code == 401


async def test_me_requires_token(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/auth/me")).status_code == 401
