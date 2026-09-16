"""Jobs test fixtures: RS256 keys, SQLite, fake Kafka + fake Temporal publisher."""

import os
import uuid

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PRIVATE_PEM = _key.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
).decode()
_PUBLIC_PEM = (
    _key.public_key()
    .public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    .decode()
)
os.environ["JWT_PUBLIC_KEY"] = _PUBLIC_PEM
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from collections.abc import AsyncGenerator  # noqa: E402

import app.models  # noqa: E402,F401
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.events import get_publisher  # noqa: E402
from app.publishing.temporal_client import get_temporal_publisher  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from smarthire_common.security import create_access_token  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.main import create_app  # noqa: E402


class FakePublisher:
    def __init__(self) -> None:
        self.events: list = []

    async def publish(self, topic, envelope) -> None:
        self.events.append((topic, envelope))


class FakeTemporalPublisher:
    def __init__(self) -> None:
        self.started: list[str] = []

    async def start(self, job_id: str) -> None:
        self.started.append(job_id)


def make_token(role: str) -> str:
    return create_access_token(
        subject=str(uuid.uuid4()),
        role=role,
        private_key=_PRIVATE_PEM,
        algorithm="RS256",
        expires_minutes=15,
    )


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    fake_temporal = FakeTemporalPublisher()

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_publisher] = lambda: FakePublisher()
    app.dependency_overrides[get_temporal_publisher] = lambda: fake_temporal

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.fake_temporal = fake_temporal
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def recruiter_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token('recruiter')}"}


@pytest.fixture
def candidate_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token('candidate')}"}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
