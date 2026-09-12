"""Domain exceptions and their FastAPI handlers.

Domain/service code raises these framework-agnostic exceptions; the handlers
registered on the app translate them into consistent JSON HTTP responses.
This keeps HTTP concerns out of the service/repository layers.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class SmartHireError(Exception):
    """Base class for all domain errors."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "An error occurred."

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class NotFoundError(SmartHireError):
    """A requested resource does not exist."""

    status_code = status.HTTP_404_NOT_FOUND
    detail = "Resource not found."


class ConflictError(SmartHireError):
    """The request conflicts with existing state (e.g. duplicate unique field)."""

    status_code = status.HTTP_409_CONFLICT
    detail = "Resource conflict."


class ValidationError(SmartHireError):
    """A business-rule validation failed (beyond schema validation)."""

    status_code = 422
    detail = "Validation failed."


def register_exception_handlers(app: FastAPI) -> None:
    """Attach a single handler that renders any SmartHireError as JSON."""

    @app.exception_handler(SmartHireError)
    async def _handle_smarthire_error(_: Request, exc: SmartHireError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
