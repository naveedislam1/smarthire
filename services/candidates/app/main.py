"""Candidates service app. Run: uv run uvicorn app.main:app --port 8002"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from smarthire_common.exceptions import register_exception_handlers
from smarthire_common.logging import configure_logging, get_logger
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.events import publisher
from app.router import router as candidates_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging(settings.log_level)
    await publisher.start()
    logger.info("Starting %s", settings.service_name)
    yield
    await publisher.stop()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.service_name, version="0.1.0", lifespan=lifespan)
    register_exception_handlers(app)
    app.include_router(candidates_router, prefix=settings.api_v1_prefix)

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.service_name}

    @app.get("/ready", tags=["meta"])
    async def ready() -> dict[str, str]:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ready"}

    return app


app = create_app()
