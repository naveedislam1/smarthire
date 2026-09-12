"""Database engine, session factory, and the declarative Base.

Uses SQLAlchemy 2.0 async APIs (`AsyncEngine` / `AsyncSession`). The
`get_db` dependency yields a session per request and guarantees cleanup.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model in the project."""


# `echo=settings.debug` surfaces emitted SQL during local development.
engine = create_async_engine(settings.database_url, echo=settings.debug, future=True)

# `expire_on_commit=False` keeps attributes usable after commit, which is
# convenient when returning ORM objects from request handlers.
SessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a scoped async session."""
    async with SessionFactory() as session:
        yield session
