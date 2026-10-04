"""Neo4j driver exceptions -> neutral storage errors (ADR-0019)."""

from __future__ import annotations

from neo4j import exceptions as neo4j_errors

from context_graph.ports.errors import (
    ConflictError,
    InvalidRequestError,
    StorageError,
    StorageTimeoutError,
    UnavailableError,
)


def translate_neo4j_error(exc: BaseException) -> StorageError | None:
    """Return the neutral error for a neo4j driver exception, or None if not one."""
    if isinstance(exc, neo4j_errors.ConnectionAcquisitionTimeoutError):
        return StorageTimeoutError(str(exc))
    if isinstance(exc, (neo4j_errors.ServiceUnavailable, neo4j_errors.SessionExpired)):
        return UnavailableError(str(exc))
    if isinstance(exc, neo4j_errors.TransientError):
        return UnavailableError(str(exc))
    if isinstance(exc, neo4j_errors.ConstraintError):
        return ConflictError(str(exc))
    if isinstance(exc, neo4j_errors.Neo4jError) and "TimedOut" in (exc.code or ""):
        return StorageTimeoutError(str(exc))
    if isinstance(exc, neo4j_errors.ClientError):
        return InvalidRequestError(str(exc))
    if isinstance(exc, (neo4j_errors.Neo4jError, neo4j_errors.DriverError)):
        return StorageError(str(exc))
    return None
