"""Gateway settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "smarthire-gateway"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    # Upstream services (one entry per extracted service).
    auth_service_url: str = "http://localhost:8001"
    candidates_service_url: str = "http://localhost:8002"
    jobs_service_url: str = "http://localhost:8003"
    applications_service_url: str = "http://localhost:8004"

    # Resilience
    request_timeout_seconds: float = 5.0
    breaker_fail_max: int = 5
    breaker_reset_seconds: float = 15.0

    # Rate limiting (fail-open if Redis is unavailable)
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 120


@lru_cache
def get_settings() -> GatewaySettings:
    return GatewaySettings()


settings = get_settings()
