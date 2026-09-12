"""Shared test fixtures.

Tests run against an in-memory SQLite database so they need no external
services. The app's models use portable JSON columns (JSONB on Postgres,
JSON on SQLite), so the same schema is exercised here.
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Import model modules so their tables register on Base.metadata.
import app.auth.models  # noqa: F401
import app.candidates.models  # noqa: F401
import app.jobs.models  # noqa: F401
from app.core.database import Base, get_db
from app.main import create_app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a session bound to a fresh in-memory schema per test."""
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client wired to the app with the test DB session injected."""
    app = create_app()

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


async def _auth_headers(client: AsyncClient, email: str, role: str) -> dict[str, str]:
    """Register a user with the given role and return a Bearer auth header."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "password123",
            "full_name": email.split("@")[0].title(),
            "role": role,
        },
    )
    assert resp.status_code == 201, resp.text
    token_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "password123"},
    )
    assert token_resp.status_code == 200, token_resp.text
    return {"Authorization": f"Bearer {token_resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def recruiter_headers(client: AsyncClient) -> dict[str, str]:
    return await _auth_headers(client, "recruiter@example.com", "recruiter")


@pytest_asyncio.fixture
async def candidate_headers(client: AsyncClient) -> dict[str, str]:
    return await _auth_headers(client, "user@example.com", "candidate")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
