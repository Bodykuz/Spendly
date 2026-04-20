"""Typed application errors mapped to HTTP responses."""

from __future__ import annotations

from fastapi import HTTPException, status


class AppError(HTTPException):
    default_status = status.HTTP_400_BAD_REQUEST
    code = "app_error"

    def __init__(self, detail: str | None = None, status_code: int | None = None):
        super().__init__(
            status_code=status_code or self.default_status,
            detail={"code": self.code, "message": detail or self.__doc__ or "Error"},
        )


class InvalidCredentials(AppError):
    """Invalid email or password."""
    default_status = status.HTTP_401_UNAUTHORIZED
    code = "invalid_credentials"


class NotAuthenticated(AppError):
    """Authentication required."""
    default_status = status.HTTP_401_UNAUTHORIZED
    code = "not_authenticated"


class Forbidden(AppError):
    """Access denied."""
    default_status = status.HTTP_403_FORBIDDEN
    code = "forbidden"


class NotFound(AppError):
    """Resource not found."""
    default_status = status.HTTP_404_NOT_FOUND
    code = "not_found"


class Conflict(AppError):
    """Resource already exists."""
    default_status = status.HTTP_409_CONFLICT
    code = "conflict"


class ProviderError(AppError):
    """PSD2 provider error."""
    default_status = status.HTTP_502_BAD_GATEWAY
    code = "provider_error"


class RateLimited(AppError):
    """Too many requests."""
    default_status = status.HTTP_429_TOO_MANY_REQUESTS
    code = "rate_limited"
