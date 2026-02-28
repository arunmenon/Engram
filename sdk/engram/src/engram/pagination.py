from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from engram.exceptions import EngramError
from engram.models import AtlasResponse

MAX_CURSOR_SIZE = 4096  # 4KB max cursor


class PageIterator:
    """Async iterator that automatically follows pagination cursors."""

    def __init__(
        self,
        fetch_fn: Callable[..., Awaitable[AtlasResponse]],
        *,
        max_pages: int = 100,
        **kwargs: Any,
    ) -> None:
        self._fetch_fn = fetch_fn
        self._kwargs = kwargs
        self._cursor: str | None = None
        self._exhausted: bool = False
        self._max_pages = max_pages
        self._page_count: int = 0
        self._seen_cursors: set[str] = set()

    def __aiter__(self) -> AsyncIterator[AtlasResponse]:
        return self

    async def __anext__(self) -> AtlasResponse:
        if self._exhausted:
            raise StopAsyncIteration

        if self._page_count >= self._max_pages:
            raise EngramError(f"Pagination limit reached ({self._max_pages} pages)")

        response = await self._fetch_fn(**self._kwargs, cursor=self._cursor)
        self._page_count += 1

        if response.pagination.has_more and response.pagination.cursor:
            cursor = response.pagination.cursor
            # Cap cursor size or detect cursor cycles
            if len(cursor) > MAX_CURSOR_SIZE or cursor in self._seen_cursors:
                self._exhausted = True
            else:
                self._seen_cursors.add(cursor)
                self._cursor = cursor
        else:
            self._exhausted = True

        return response
