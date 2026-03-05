from __future__ import annotations

from engram.models import AtlasResponse, Pagination, QueryMeta
from engram.pagination import PageIterator


def _make_response(has_more: bool = False, cursor: str | None = None) -> AtlasResponse:
    """Build a minimal AtlasResponse for pagination testing."""
    return AtlasResponse(
        pagination=Pagination(has_more=has_more, cursor=cursor),
        meta=QueryMeta(),
    )


class TestSinglePage:
    async def test_single_page(self) -> None:
        """One page with has_more=False yields exactly one iteration."""
        call_count = 0

        async def fetch_fn(**kwargs) -> AtlasResponse:
            nonlocal call_count
            call_count += 1
            return _make_response(has_more=False)

        pages = []
        async for page in PageIterator(fetch_fn):
            pages.append(page)

        assert len(pages) == 1
        assert call_count == 1


class TestMultiPage:
    async def test_multi_page(self) -> None:
        """Three pages with cursors yields three iterations."""
        responses = [
            _make_response(has_more=True, cursor="cursor-1"),
            _make_response(has_more=True, cursor="cursor-2"),
            _make_response(has_more=False, cursor=None),
        ]
        call_index = 0

        async def fetch_fn(**kwargs) -> AtlasResponse:
            nonlocal call_index
            resp = responses[call_index]
            call_index += 1
            return resp

        pages = []
        async for page in PageIterator(fetch_fn):
            pages.append(page)

        assert len(pages) == 3
        assert call_index == 3


class TestEmptyResponse:
    async def test_empty_response(self) -> None:
        """Empty nodes but has_more=False yields one iteration."""

        async def fetch_fn(**kwargs) -> AtlasResponse:
            return _make_response(has_more=False)

        pages = []
        async for page in PageIterator(fetch_fn):
            pages.append(page)

        assert len(pages) == 1
        assert len(pages[0].nodes) == 0


class TestCursorPropagation:
    async def test_cursor_propagation(self) -> None:
        """Cursor from page N is passed to page N+1 request."""
        received_cursors: list[str | None] = []

        responses = [
            _make_response(has_more=True, cursor="cur-A"),
            _make_response(has_more=True, cursor="cur-B"),
            _make_response(has_more=False),
        ]
        call_index = 0

        async def fetch_fn(**kwargs) -> AtlasResponse:
            nonlocal call_index
            received_cursors.append(kwargs.get("cursor"))
            resp = responses[call_index]
            call_index += 1
            return resp

        pages = []
        async for page in PageIterator(fetch_fn):
            pages.append(page)

        assert received_cursors == [None, "cur-A", "cur-B"]
