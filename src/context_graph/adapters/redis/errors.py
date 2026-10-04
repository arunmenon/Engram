"""Redis driver exceptions -> neutral storage errors (ADR-0019)."""

from __future__ import annotations

from redis import exceptions as redis_errors

from context_graph.ports.errors import (
    InvalidRequestError,
    StorageError,
    StorageTimeoutError,
    UnavailableError,
)


def translate_redis_error(exc: BaseException) -> StorageError | None:
    """Return the neutral error for a redis-py exception, or None if not one."""
    if isinstance(exc, redis_errors.TimeoutError):
        return StorageTimeoutError(str(exc))
    if isinstance(exc, redis_errors.ConnectionError):
        return UnavailableError(str(exc))
    if isinstance(exc, redis_errors.ResponseError):
        return InvalidRequestError(str(exc))
    if isinstance(exc, redis_errors.RedisError):
        return StorageError(str(exc))
    return None
