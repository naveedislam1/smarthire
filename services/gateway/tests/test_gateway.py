"""Gateway tests: health isolation + circuit-breaker fault handling."""

import pytest
from app.circuit import AsyncCircuitBreaker, CircuitOpenError
from httpx import AsyncClient


async def test_health_is_independent_of_upstreams(client: AsyncClient) -> None:
    # Auth upstream is dead, but the gateway's own health is still 200.
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_dead_upstream_returns_503(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/login", data={"username": "x", "password": "y"}
    )
    assert resp.status_code == 503


async def test_breaker_opens_after_repeated_failures(client: AsyncClient) -> None:
    # fail_max=3 (conftest). After 3 failures the breaker opens and fails fast.
    for _ in range(3):
        r = await client.get("/api/v1/auth/me")
        assert r.status_code == 503
    opened = await client.get("/api/v1/auth/me")
    assert opened.status_code == 503
    assert "circuit open" in opened.json()["detail"]


# --- Unit tests for the breaker itself ---
async def test_circuit_breaker_transitions() -> None:
    breaker = AsyncCircuitBreaker(fail_max=2, reset_seconds=0.05)

    async def boom() -> None:
        raise ValueError("nope")

    async def ok() -> str:
        return "ok"

    assert breaker.state == "closed"
    for _ in range(2):
        with pytest.raises(ValueError):
            await breaker.call(boom)
    assert breaker.state == "open"
    with pytest.raises(CircuitOpenError):
        await breaker.call(ok)

    import asyncio

    await asyncio.sleep(0.06)
    assert breaker.state == "half_open"
    assert await breaker.call(ok) == "ok"  # success closes it
    assert breaker.state == "closed"
