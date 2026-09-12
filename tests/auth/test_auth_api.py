"""API tests for authentication."""

from httpx import AsyncClient


async def _register(client: AsyncClient, email: str, role: str = "candidate") -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "password123",
            "full_name": "Test User",
            "role": role,
        },
    )
    assert resp.status_code == 201, resp.text


async def test_register_and_login_and_me(client: AsyncClient) -> None:
    await _register(client, "grace@example.com", "recruiter")

    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "grace@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    tokens = login.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"] and tokens["refresh_token"]

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "grace@example.com"
    assert me.json()["role"] == "recruiter"


async def test_duplicate_registration_returns_409(client: AsyncClient) -> None:
    await _register(client, "dup@example.com")
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "dup@example.com",
            "password": "password123",
            "full_name": "Dup",
            "role": "candidate",
        },
    )
    assert resp.status_code == 409


async def test_wrong_password_returns_401(client: AsyncClient) -> None:
    await _register(client, "eve@example.com")
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "eve@example.com", "password": "wrong-password"},
    )
    assert resp.status_code == 401


async def test_refresh_returns_new_access_token(client: AsyncClient) -> None:
    await _register(client, "linus@example.com")
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "linus@example.com", "password": "password123"},
    )
    refresh_token = login.json()["refresh_token"]

    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_access_token_rejected_at_refresh(client: AsyncClient) -> None:
    await _register(client, "torvalds@example.com")
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "torvalds@example.com", "password": "password123"},
    )
    access_token = login.json()["access_token"]

    # Using an access token where a refresh token is expected must fail.
    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": access_token}
    )
    assert resp.status_code == 401


async def test_me_requires_valid_token(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    bad = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-token"}
    )
    assert bad.status_code == 401
