"""Redis fixed-window rate limiter (fail-open).

If Redis is unreachable the limiter allows the request (fail-open) so the gateway
never becomes a single point of failure for rate limiting.
"""

import time

import redis.asyncio as aioredis
from smarthire_common.logging import get_logger

from app.config import settings

logger = get_logger(__name__)

_redis: aioredis.Redis | None = None


def _client() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    return _redis


async def allow(identifier: str) -> bool:
    """Return True if the caller is under the per-minute limit."""
    if not settings.rate_limit_enabled:
        return True
    window = int(time.time() // 60)
    key = f"rl:{identifier}:{window}"
    try:
        client = _client()
        count = await client.incr(key)
        if count == 1:
            await client.expire(key, 60)
        return count <= settings.rate_limit_per_minute
    except Exception as exc:  # Redis down → fail open.
        logger.warning("Rate limiter unavailable, failing open: %s", exc)
        return True
