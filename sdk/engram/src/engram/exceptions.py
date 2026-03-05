from __future__ import annotations

from typing import Any


class EngramError(Exception):
    """Base exception for all Engram SDK errors."""


class TransportError(EngramError):
    """HTTP transport-level error (connection, timeout)."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)


class AuthenticationError(TransportError):
    """401 Unauthorized — invalid or missing API key."""


class RateLimitError(TransportError):
    """429 Too Many Requests — rate limit exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: float | None = None,
        status_code: int | None = 429,
        response_body: dict[str, Any] | None = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message, status_code=status_code, response_body=response_body)


class ValidationError(EngramError):
    """422 Unprocessable Entity — server-side validation failure."""

    def __init__(self, message: str, errors: list[dict[str, Any]] | None = None) -> None:
        self.errors = errors or []
        super().__init__(message)


class NotFoundError(EngramError):
    """404 Not Found."""


class ServerError(TransportError):
    """5xx server error."""


class ConfigurationError(EngramError):
    """SDK misconfiguration (missing base_url, etc.)."""
