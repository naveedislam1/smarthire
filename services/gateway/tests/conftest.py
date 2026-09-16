"""Gateway test fixtures — point auth at a dead upstream, small breaker."""

import os

# Configure BEFORE importing the app (settings is cached).
os.environ["AUTH_SERVICE_URL"] = "http://127.0.0.1:59999"  # nothing listens here
os.environ["BREAKER_FAIL_MAX"] = "3"
os.environ["BREAKER_RESET_SECONDS"] = "30"
os.environ["RATE_LIMIT_ENABLED"] = "false"

from collections.abc import AsyncGenerator  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.main import create_app  # noqa: E402


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
