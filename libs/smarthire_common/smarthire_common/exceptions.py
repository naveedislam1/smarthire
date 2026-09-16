"""Framework-agnostic domain errors + a FastAPI handler registrar."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class SmartHireError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "An error occurred."

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class NotFoundError(SmartHireError):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Resource not found."


class ConflictError(SmartHireError):
    status_code = status.HTTP_409_CONFLICT
    detail = "Resource conflict."


class ValidationError(SmartHireError):
    status_code = 422
    detail = "Validation failed."


class AuthError(SmartHireError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Could not validate credentials."


class ForbiddenError(SmartHireError):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "You do not have permission to perform this action."


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(SmartHireError)
    async def _handle(_: Request, exc: SmartHireError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
