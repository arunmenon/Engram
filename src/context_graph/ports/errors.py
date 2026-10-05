"""Backend-neutral storage errors (ADR-0019 §1).

Every storage port raises these, never a driver exception. Adapters
translate driver errors at their public methods and chain the original
(``raise UnavailableError(...) from exc``) so logs keep the backend detail.

All subclass ``StorageError``, which subclasses ``Exception``, so code
that catches ``Exception`` behaves as before. ``StorageTimeoutError`` also subclasses
the built-in ``TimeoutError``.

Source: ADR-0019
"""

from __future__ import annotations


class StorageError(Exception):
    """Base class for errors raised through a storage port."""


class ConflictError(StorageError):
    """The write conflicts with existing data (for example a uniqueness constraint)."""


class NotFoundError(StorageError):
    """The addressed record, index or container does not exist."""


class UnavailableError(StorageError):
    """The backend cannot be reached or is temporarily unable to serve."""


class StorageTimeoutError(StorageError, TimeoutError):
    """The operation exceeded its time bound."""


class InvalidRequestError(StorageError):
    """The backend rejected the request as malformed or not permitted."""


# Errors a retry can fix: the backend was unreachable or slow, not the request wrong
TRANSIENT_ERRORS: tuple[type[StorageError], ...] = (UnavailableError, StorageTimeoutError)


def is_transient(exc: BaseException) -> bool:
    """Whether ``exc`` is a storage error that retrying the same request may fix."""
    return isinstance(exc, TRANSIENT_ERRORS)
