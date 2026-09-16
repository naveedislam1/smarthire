"""Base settings shared by every service.

Each service subclasses :class:`BaseServiceSettings` and adds its own fields
(e.g. its `database_url`). Auth-related fields live here because every service
needs to *verify* JWTs; only the auth service uses the private key to *sign*.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    """Common configuration for a SmartHire service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Service identity ---
    service_name: str = "smarthire-service"
    environment: str = Field(default="local", description="local | dev | prod")
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    # --- Kafka (event backbone) ---
    kafka_bootstrap_servers: str = "localhost:9092"

    # --- JWT (RS256, asymmetric) ---
    # Verifiers need only the public key. The auth service additionally sets the
    # private key to sign tokens. Provide either an inline PEM or a file path.
    jwt_algorithm: str = "RS256"
    jwt_public_key: str | None = None
    jwt_public_key_path: str | None = None
    jwt_private_key: str | None = None
    jwt_private_key_path: str | None = None
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    def public_key_pem(self) -> str:
        """Return the JWT public key PEM (from inline value or file)."""
        if self.jwt_public_key:
            return self.jwt_public_key
        if self.jwt_public_key_path:
            with open(self.jwt_public_key_path) as fh:
                return fh.read()
        raise RuntimeError("No JWT public key configured (set JWT_PUBLIC_KEY[_PATH]).")

    def private_key_pem(self) -> str:
        """Return the JWT private key PEM (auth service only)."""
        if self.jwt_private_key:
            return self.jwt_private_key
        if self.jwt_private_key_path:
            with open(self.jwt_private_key_path) as fh:
                return fh.read()
        raise RuntimeError("No JWT private key configured (set JWT_PRIVATE_KEY[_PATH]).")
