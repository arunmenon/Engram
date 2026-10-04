"""Spanner client exceptions -> neutral storage errors (ADR-0019)."""

from __future__ import annotations

from google.api_core import exceptions as api_errors

from context_graph.ports.errors import (
    ConflictError,
    InvalidRequestError,
    NotFoundError,
    StorageError,
    StorageTimeoutError,
    UnavailableError,
)


def translate_spanner_error(exc: BaseException) -> StorageError | None:
    """Return the neutral error for a google-api-core exception, or None if not one."""
    if isinstance(exc, api_errors.DeadlineExceeded):
        return StorageTimeoutError(str(exc))
    if isinstance(exc, (api_errors.ServiceUnavailable, api_errors.Aborted)):
        return UnavailableError(str(exc))
    if isinstance(exc, api_errors.AlreadyExists):
        return ConflictError(str(exc))
    if isinstance(exc, api_errors.NotFound):
        return NotFoundError(str(exc))
    if isinstance(exc, (api_errors.InvalidArgument, api_errors.FailedPrecondition)):
        return InvalidRequestError(str(exc))
    if isinstance(exc, api_errors.GoogleAPICallError):
        return StorageError(str(exc))
    return None
