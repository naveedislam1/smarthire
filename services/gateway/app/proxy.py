"""Reverse-proxy an incoming request to an upstream service.

Each upstream has its own circuit breaker, so one failing service trips only its
own breaker — other routes stay healthy. On breaker-open or connection/timeout
errors the gateway returns a clean 503 instead of hanging.
"""

import httpx
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.circuit import AsyncCircuitBreaker, CircuitOpenError
from app.config import settings

_HOP_BY_HOP = {
    "host", "content-length", "connection", "keep-alive", "transfer-encoding",
}

_client: httpx.AsyncClient | None = None


def _http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=settings.request_timeout_seconds)
    return _client


class Upstream:
    def __init__(self, name: str, base_url: str) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.breaker = AsyncCircuitBreaker(
            fail_max=settings.breaker_fail_max,
            reset_seconds=settings.breaker_reset_seconds,
        )


async def forward(request: Request, upstream: Upstream) -> Response:
    target = f"{upstream.base_url}{request.url.path}"
    body = await request.body()
    headers = {
        k: v for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP
    }

    async def _do() -> httpx.Response:
        return await _http().request(
            request.method,
            target,
            params=request.query_params,
            content=body,
            headers=headers,
        )

    try:
        resp = await upstream.breaker.call(_do)
    except CircuitOpenError:
        return JSONResponse(
            status_code=503,
            content={"detail": f"{upstream.name} unavailable (circuit open)."},
        )
    except httpx.HTTPError as exc:
        return JSONResponse(
            status_code=503,
            content={"detail": f"{upstream.name} unavailable: {type(exc).__name__}."},
        )

    out_headers = {
        k: v for k, v in resp.headers.items() if k.lower() not in _HOP_BY_HOP
    }
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=out_headers,
        media_type=resp.headers.get("content-type"),
    )
