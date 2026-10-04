"""Translate driver exceptions to the neutral storage errors (ADR-0019).

``translate_errors(translator)`` is a class decorator: it wraps every
public coroutine method so a driver exception leaving the adapter becomes
a ``context_graph.ports.errors`` exception, chained to the original.
Exceptions that are not driver errors (``ValueError``, ``StorageError``,
cancellation) pass through unchanged.

Source: ADR-0019
"""

from __future__ import annotations

import functools
import inspect
from typing import TYPE_CHECKING, Any, TypeVar

from context_graph.ports.errors import StorageError

if TYPE_CHECKING:
    from collections.abc import Callable

ClassT = TypeVar("ClassT", bound=type)


def _wrap(method: Any, translator: Callable[[BaseException], StorageError | None]) -> Any:
    @functools.wraps(method)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await method(*args, **kwargs)
        except StorageError:
            raise
        except Exception as exc:
            neutral = translator(exc)
            if neutral is None:
                raise
            raise neutral from exc

    wrapper.__translates_errors__ = True  # type: ignore[attr-defined]
    return wrapper


def translate_errors(
    translator: Callable[[BaseException], StorageError | None],
) -> Callable[[ClassT], ClassT]:
    """Wrap the public coroutine methods of a class with ``translator``."""

    def decorate(cls: ClassT) -> ClassT:
        for name, member in list(vars(cls).items()):
            if name.startswith("_") or not inspect.iscoroutinefunction(member):
                continue
            if getattr(member, "__translates_errors__", False):
                continue
            setattr(cls, name, _wrap(member, translator))
        return cls

    return decorate
