"""SmartHire API gateway.

Routes `/api/v1/auth/*` to the auth service with a circuit breaker + rate limit.
The gateway's own `/health` never depends on upstreams, so a single down service
never takes the gateway down — it just 503s that service's routes.

Run: uv run uvicorn app.main:app --port 8080
"""

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from smarthire_common.logging import configure_logging, get_logger

from app.config import settings
from app.proxy import Upstream, forward
from app.ratelimit import allow

logger = get_logger(__name__)

_PROXY_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]


def create_app() -> FastAPI:
    configure_logging(settings.log_level)
    app = FastAPI(title=settings.service_name, version="0.1.0")

    # One upstream (with its own breaker) per extracted service, so a failure in
    # one service trips only its own breaker.
    upstreams = {
        "auth": Upstream("auth", settings.auth_service_url),
        "candidates": Upstream("candidates", settings.candidates_service_url),
        "jobs": Upstream("jobs", settings.jobs_service_url),
        "applications": Upstream("applications", settings.applications_service_url),
    }

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.service_name}

    # A single catch-all under the API prefix. The first path segment selects the
    # upstream, so both collection roots (POST /api/v1/jobs) and sub-paths
    # (GET /api/v1/jobs/{id}) route correctly — no 307 redirects.
    @app.api_route(
        f"{settings.api_v1_prefix}/{{full_path:path}}", methods=_PROXY_METHODS
    )
    async def gateway_proxy(full_path: str, request: Request) -> Response:
        segment = full_path.split("/", 1)[0]
        upstream = upstreams.get(segment)
        if upstream is None:
            return JSONResponse(status_code=404, content={"detail": "Unknown route."})
        client_ip = request.client.host if request.client else "unknown"
        if not await allow(client_ip):
            return JSONResponse(
                status_code=429, content={"detail": "Rate limit exceeded."}
            )
        return await forward(request, upstream)

    return app


app = create_app()
