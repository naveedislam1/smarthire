"""A minimal async circuit breaker.

States: CLOSED (normal) → OPEN (fail fast) after `fail_max` consecutive failures
→ HALF_OPEN (one trial) after `reset_seconds` → CLOSED on success / OPEN on
failure. Self-contained (no external dep) so the fault-isolation behaviour is
predictable and testable.
"""

import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class CircuitOpenError(Exception):
    """Raised when the breaker is open and the call is rejected fast."""


class AsyncCircuitBreaker:
    def __init__(self, *, fail_max: int, reset_seconds: float) -> None:
        self.fail_max = fail_max
        self.reset_seconds = reset_seconds
        self._failures = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> str:
        if self._opened_at is None:
            return "closed"
        if time.monotonic() - self._opened_at >= self.reset_seconds:
            return "half_open"
        return "open"

    async def call(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        if self.state == "open":
            raise CircuitOpenError("circuit open")
        try:
            result = await func(*args, **kwargs)
        except Exception:
            self._on_failure()
            raise
        self._on_success()
        return result

    def _on_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def _on_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.fail_max:
            self._opened_at = time.monotonic()
