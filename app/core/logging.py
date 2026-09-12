"""Logging configuration.

A minimal, structured-ish stdlib logging setup. Week 3 of the assignment
introduces full observability (OpenTelemetry / Prometheus / Jaeger); this
module deliberately keeps things simple but centralised so that upgrade is
a single-file change.
"""

import logging

from app.core.config import settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging() -> None:
    """Configure root logging once, based on settings.log_level."""
    logging.basicConfig(
        level=settings.log_level.upper(),
        format=_LOG_FORMAT,
    )
    # Align uvicorn's loggers with our level so output is consistent.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).setLevel(settings.log_level.upper())


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger."""
    return logging.getLogger(name)
