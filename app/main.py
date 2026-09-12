"""FastAPI application factory and entry point.

Run locally with:  ``uv run uvicorn app.main:app --reload``
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.candidates.router import router as candidates_router
from app.core.config import settings
from app.core.database import engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.jobs.router import router as jobs_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Startup/shutdown hooks."""
    configure_logging()
    logger.info("Starting %s (env=%s)", settings.app_name, settings.environment)
    yield
    await engine.dispose()
    logger.info("Shutdown complete.")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="SmartHire — Core Recruitment Platform (Week 1).",
        lifespan=lifespan,
    )

    register_exception_handlers(app)

    # Domain routers, all under the versioned API prefix.
    app.include_router(jobs_router, prefix=settings.api_v1_prefix)
    app.include_router(candidates_router, prefix=settings.api_v1_prefix)

    @app.get("/", tags=["meta"])
    async def root() -> dict[str, str]:
        return {"service": settings.app_name, "version": "0.1.0"}

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
