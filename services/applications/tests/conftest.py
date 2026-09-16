"""Applications test fixtures: RS256 keys, SQLite, fake publisher."""

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
from app.models import CandidateRef, JobRef  # noqa: E402
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

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_publisher] = lambda: FakePublisher()

    # Skip the app lifespan (no Kafka in tests) by not triggering startup.
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def seed_job(db_session: AsyncSession, status: str = "ready") -> uuid.UUID:
    jid = uuid.uuid4()
    db_session.add(JobRef(id=jid, status=status))
    await db_session.commit()
    return jid


async def seed_candidate(db_session: AsyncSession) -> uuid.UUID:
    cid = uuid.uuid4()
    db_session.add(CandidateRef(id=cid))
    await db_session.commit()
    return cid


@pytest.fixture
def candidate_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token('candidate')}"}


@pytest.fixture
def recruiter_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token('recruiter')}"}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
