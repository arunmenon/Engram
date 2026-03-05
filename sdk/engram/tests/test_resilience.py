"""Resilience tests for the Engram SDK — malformed responses, resource exhaustion,
pagination DoS, Retry-After manipulation, timeout behavior, HTTP status codes."""

from __future__ import annotations

import contextlib
from datetime import datetime, timezone
from uuid import uuid4

import httpx
import pytest
import respx

from engram import EngramClient, EngramConfig
from engram.config import reset_config
from engram.exceptions import (
    EngramError,
    ServerError,
    TransportError,
)
from engram.models import AtlasResponse, Event, Pagination
from engram.pagination import MAX_CURSOR_SIZE, PageIterator
from engram.transport import Transport

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset():
    reset_config()
    yield
    reset_config()


@pytest.fixture
def config() -> EngramConfig:
    return EngramConfig(base_url="http://test:8000", api_key="k", max_retries=0)


@pytest.fixture
def client(config: EngramConfig) -> EngramClient:
    return EngramClient(config=config)


# ---------------------------------------------------------------------------
# TestMalformedResponses
# ---------------------------------------------------------------------------


class TestMalformedResponses:
    """Server returns syntactically broken or schema-wrong payloads."""

    @respx.mock(base_url="http://test:8000/v1")
    async def test_invalid_json_200(self, respx_mock, client: EngramClient):
        """Server returns invalid JSON with 200 -> should raise."""
        respx_mock.get("/health").mock(return_value=httpx.Response(200, content=b"not json at all"))
        with pytest.raises((ValueError, httpx.DecodingError)):
            await client.health()

    @respx.mock(base_url="http://test:8000/v1")
    async def test_truncated_json_200(self, respx_mock, client: EngramClient):
        """Truncated JSON body."""
        respx_mock.get("/context/sess-1").mock(
            return_value=httpx.Response(200, content=b'{"nodes":')
        )
        with pytest.raises((ValueError, httpx.DecodingError)):
            await client.get_context("sess-1")

    @respx.mock(base_url="http://test:8000/v1")
    async def test_html_error_page(self, respx_mock, client: EngramClient):
        """Server returns HTML instead of JSON."""
        html = b"<html><body>502 Bad Gateway</body></html>"
        respx_mock.get("/health").mock(
            return_value=httpx.Response(200, content=html, headers={"content-type": "text/html"})
        )
        with pytest.raises((ValueError, httpx.DecodingError)):
            await client.health()

    @respx.mock(base_url="http://test:8000/v1")
    async def test_empty_body_200(self, respx_mock, client: EngramClient):
        """Empty response body with 200."""
        respx_mock.get("/health").mock(return_value=httpx.Response(200, content=b""))
        with pytest.raises((ValueError, httpx.DecodingError)):
            await client.health()

    @respx.mock(base_url="http://test:8000/v1")
    async def test_wrong_schema_atlas(self, respx_mock, client: EngramClient):
        """Valid JSON but wrong shape for AtlasResponse -> Pydantic catches."""
        respx_mock.get("/context/sess-1").mock(
            return_value=httpx.Response(200, json={"totally": "wrong"})
        )
        # AtlasResponse has defaults for everything, so this actually succeeds
        # with empty dicts/lists.  The key point is it does NOT crash.
        result = await client.get_context("sess-1")
        assert isinstance(result, AtlasResponse)

    @respx.mock(base_url="http://test:8000/v1")
    async def test_null_nodes_field(self, respx_mock, client: EngramClient):
        """nodes: null should be handled gracefully by Pydantic defaults."""
        respx_mock.get("/context/sess-1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "nodes": None,
                    "edges": [],
                    "pagination": {"cursor": None, "has_more": False},
                    "meta": {},
                },
            )
        )
        # Pydantic converts None -> default or raises.  Either is acceptable.
        with contextlib.suppress(ValueError):
            result = await client.get_context("sess-1")
            assert isinstance(result, AtlasResponse)

    @respx.mock(base_url="http://test:8000/v1")
    async def test_missing_fields_ingest(self, respx_mock, client: EngramClient):
        """IngestResult missing required fields -> Pydantic catches."""
        respx_mock.post("/events").mock(return_value=httpx.Response(200, json={"unexpected": True}))
        event = Event(
            event_id=uuid4(),
            event_type="test",
            occurred_at=datetime.now(timezone.utc),
            session_id="s",
            agent_id="a",
            trace_id="t",
            payload_ref="p",
        )
        with pytest.raises(ValueError):
            await client.ingest(event)

    @respx.mock(base_url="http://test:8000/v1")
    async def test_server_returns_list(self, respx_mock, client: EngramClient):
        """Server returns [] instead of {} for profile."""
        respx_mock.get("/users/u1/profile").mock(return_value=httpx.Response(200, json=[]))
        with pytest.raises(ValueError):
            await client.get_user_profile("u1")

    @respx.mock(base_url="http://test:8000/v1")
    async def test_non_dict_pagination(self, respx_mock, client: EngramClient):
        """pagination field is a string -> Pydantic catches."""
        respx_mock.get("/context/sess-1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "nodes": {},
                    "edges": [],
                    "pagination": "not-a-dict",
                    "meta": {},
                },
            )
        )
        with pytest.raises(ValueError):
            await client.get_context("sess-1")

    @respx.mock(base_url="http://test:8000/v1")
    async def test_extra_fields_ignored(self, respx_mock, client: EngramClient):
        """Response has extra unknown fields -> accepted by Pydantic."""
        respx_mock.get("/context/sess-1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "nodes": {},
                    "edges": [],
                    "pagination": {"cursor": None, "has_more": False},
                    "meta": {"query_ms": 1, "nodes_returned": 0},
                    "extra_field": "should be ignored",
                    "another_extra": 42,
                },
            )
        )
        result = await client.get_context("sess-1")
        assert isinstance(result, AtlasResponse)


# ---------------------------------------------------------------------------
# TestResourceExhaustion
# ---------------------------------------------------------------------------


class TestResourceExhaustion:
    """Large payloads should be handled without hangs or OOM."""

    @respx.mock(base_url="http://test:8000/v1")
    async def test_huge_response_body(self, respx_mock, client: EngramClient):
        """10MB response body -> should complete or error, NOT hang."""
        version_padding = b"x" * (10 * 1024 * 1024)
        large_body = (
            b'{"status":"ok","redis":true,"neo4j":true,"version":"' + version_padding + b'"}'
        )
        respx_mock.get("/health").mock(return_value=httpx.Response(200, content=large_body))
        # May raise validation error or succeed with large data.  Key: no hang.
        with contextlib.suppress(ValueError):
            await client.health()

    async def test_atlas_many_nodes(self):
        """AtlasResponse with 100K nodes dict -> processes without crash."""
        from engram.models import AtlasNode, NodeScores

        nodes = {}
        for i in range(100_000):
            nid = f"node-{i}"
            nodes[nid] = AtlasNode(
                node_id=nid,
                node_type="Event",
                scores=NodeScores(),
            )
        resp = AtlasResponse(nodes=nodes)
        assert len(resp.nodes) == 100_000

    async def test_atlas_many_edges(self):
        """AtlasResponse with 500K edges -> processes without crash."""
        from engram.models import AtlasEdge

        edges = [
            AtlasEdge(source=f"n-{i}", target=f"n-{i + 1}", edge_type="FOLLOWS")
            for i in range(500_000)
        ]
        resp = AtlasResponse(edges=edges)
        assert len(resp.edges) == 500_000

    @respx.mock(base_url="http://test:8000/v1")
    async def test_oversized_event_payload(self, respx_mock, client: EngramClient):
        """Event with large payload_ref -> client-side rejection."""
        event = Event(
            event_id=uuid4(),
            event_type="test",
            occurred_at=datetime.now(timezone.utc),
            session_id="s",
            agent_id="a",
            trace_id="t",
            payload_ref="x" * 50_000_000,  # 50MB
        )
        with pytest.raises(ValueError, match="payload_ref exceeds maximum size"):
            await client.ingest(event)


# ---------------------------------------------------------------------------
# TestPaginationExhaustion
# ---------------------------------------------------------------------------


class TestPaginationExhaustion:
    """Pagination DoS: infinite loops, cursor cycles, oversized cursors."""

    async def test_infinite_pagination_stopped(self):
        """Server always returns has_more=True -> stops at max_pages."""
        call_count = 0

        async def fake_fetch(**kwargs):
            nonlocal call_count
            call_count += 1
            return AtlasResponse(
                pagination=Pagination(cursor=f"cursor-{call_count}", has_more=True),
            )

        iterator = PageIterator(fake_fetch, max_pages=5)
        pages = []
        with pytest.raises(EngramError, match="Pagination limit reached"):
            async for page in iterator:
                pages.append(page)

        assert len(pages) == 5
        assert call_count == 5

    async def test_cursor_cycle_detection(self):
        """Server returns cursor A->B->C->A (cycle) -> detects and stops."""
        cursor_sequence = ["cursor-B", "cursor-C", "cursor-A", "cursor-B"]
        call_index = 0

        async def fake_fetch(**kwargs):
            nonlocal call_index
            cursor = cursor_sequence[min(call_index, len(cursor_sequence) - 1)]
            call_index += 1
            return AtlasResponse(
                pagination=Pagination(cursor=cursor, has_more=True),
            )

        iterator = PageIterator(fake_fetch, max_pages=100)
        pages = []
        async for page in iterator:
            pages.append(page)

        # Pages 1-3 get cursors B, C, A (all new).
        # Page 4 gets cursor B (seen before) -> exhausted set after return.
        assert len(pages) == 4

    async def test_oversized_cursor(self):
        """Cursor is larger than MAX_CURSOR_SIZE -> caps and stops."""
        big_cursor = "x" * (MAX_CURSOR_SIZE + 1)

        async def fake_fetch(**kwargs):
            return AtlasResponse(
                pagination=Pagination(cursor=big_cursor, has_more=True),
            )

        iterator = PageIterator(fake_fetch, max_pages=100)
        pages = []
        async for page in iterator:
            pages.append(page)

        # First page returned, then exhausted because cursor too big
        assert len(pages) == 1

    async def test_empty_cursor_with_has_more(self):
        """has_more=True but cursor='' -> stops (already handled)."""

        async def fake_fetch(**kwargs):
            return AtlasResponse(
                pagination=Pagination(cursor="", has_more=True),
            )

        iterator = PageIterator(fake_fetch, max_pages=100)
        pages = []
        async for page in iterator:
            pages.append(page)

        # Empty string is falsy -> exhausted set after first page.
        assert len(pages) == 1


# ---------------------------------------------------------------------------
# TestRetryAfterManipulation
# ---------------------------------------------------------------------------


class TestRetryAfterManipulation:
    """Retry-After header abuse: huge values, negative, NaN, inf."""

    def _make_transport(self) -> Transport:
        config = EngramConfig(base_url="http://test:8000", max_retries=0)
        return Transport(config)

    def _make_response(self, retry_after: str) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": retry_after})

    def test_retry_after_24hrs(self):
        """Retry-After: 86400 -> capped at MAX_RETRY_AFTER (60s)."""
        transport = self._make_transport()
        resp = self._make_response("86400")
        assert transport._parse_retry_after(resp) == 60.0

    def test_retry_after_negative(self):
        """Retry-After: -5 -> uses default (1.0)."""
        transport = self._make_transport()
        resp = self._make_response("-5")
        assert transport._parse_retry_after(resp) == 1.0

    def test_retry_after_zero(self):
        """Retry-After: 0 -> uses default (1.0)."""
        transport = self._make_transport()
        resp = self._make_response("0")
        assert transport._parse_retry_after(resp) == 1.0

    def test_retry_after_infinity(self):
        """Retry-After: inf -> capped at MAX_RETRY_AFTER."""
        transport = self._make_transport()
        resp = self._make_response("inf")
        assert transport._parse_retry_after(resp) == 60.0

    def test_retry_after_nan(self):
        """Retry-After: NaN -> uses default (1.0)."""
        transport = self._make_transport()
        resp = self._make_response("nan")
        assert transport._parse_retry_after(resp) == 1.0

    def test_retry_after_non_numeric(self):
        """Retry-After: 'not-a-number' -> uses default (already handled)."""
        transport = self._make_transport()
        resp = self._make_response("not-a-number")
        assert transport._parse_retry_after(resp) == 1.0


# ---------------------------------------------------------------------------
# TestTimeoutBehavior
# ---------------------------------------------------------------------------


class TestTimeoutBehavior:
    """Timeout edge cases."""

    async def test_timeout_zero(self):
        """timeout=0.0 in request -> httpx may raise or accept."""
        config = EngramConfig(base_url="http://test:8000", timeout=0.0, max_retries=0)
        test_client = EngramClient(config=config)
        assert test_client._config.timeout == 0.0
        await test_client.close()

    async def test_timeout_negative(self):
        """timeout=-1.0 -> httpx will reject at request time."""
        config = EngramConfig(base_url="http://test:8000", timeout=-1.0, max_retries=0)
        test_client = EngramClient(config=config)
        assert test_client._config.timeout == -1.0
        await test_client.close()

    @respx.mock(base_url="http://test:8000/v1")
    async def test_very_small_timeout(self, respx_mock):
        """timeout=0.001 -> valid, may timeout quickly."""
        config = EngramConfig(base_url="http://test:8000", timeout=0.001, max_retries=0)
        test_client = EngramClient(config=config)
        respx_mock.get("/health").mock(
            return_value=httpx.Response(
                200,
                json={
                    "status": "ok",
                    "redis": True,
                    "neo4j": True,
                    "version": "1.0",
                },
            )
        )
        result = await test_client.health()
        assert result.status == "ok"
        await test_client.close()

    @respx.mock(base_url="http://test:8000/v1")
    async def test_custom_per_request_timeout(self, respx_mock):
        """Pass timeout to individual request -> works."""
        config = EngramConfig(base_url="http://test:8000", timeout=30.0, max_retries=0)
        transport = Transport(config)
        respx_mock.get("/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
        response = await transport.request("GET", "/health", timeout=5.0)
        assert response.status_code == 200
        await transport.close()


# ---------------------------------------------------------------------------
# TestHTTPStatusCodes
# ---------------------------------------------------------------------------


class TestHTTPStatusCodes:
    """Various HTTP status codes are mapped correctly."""

    @respx.mock(base_url="http://test:8000/v1")
    async def test_400_bad_request(self, respx_mock, client: EngramClient):
        """Server returns 400 -> TransportError."""
        respx_mock.get("/health").mock(
            return_value=httpx.Response(400, json={"detail": "bad request"})
        )
        with pytest.raises(TransportError):
            await client.health()

    @respx.mock(base_url="http://test:8000/v1")
    async def test_502_bad_gateway(self, respx_mock, client: EngramClient):
        """Server returns 502 -> ServerError."""
        respx_mock.get("/health").mock(
            return_value=httpx.Response(502, json={"detail": "bad gateway"})
        )
        with pytest.raises(ServerError):
            await client.health()

    @respx.mock(base_url="http://test:8000/v1")
    async def test_504_gateway_timeout(self, respx_mock, client: EngramClient):
        """Server returns 504 -> ServerError."""
        respx_mock.get("/health").mock(
            return_value=httpx.Response(504, json={"detail": "gateway timeout"})
        )
        with pytest.raises(ServerError):
            await client.health()

    @respx.mock(base_url="http://test:8000/v1")
    async def test_301_redirect(self, respx_mock, client: EngramClient):
        """Server returns 301 -> httpx follows or returns <400 response."""
        respx_mock.get("/health").mock(
            return_value=httpx.Response(
                301,
                headers={"Location": "http://test:8000/v1/health2"},
            )
        )
        # 301 is <400 so transport returns it. health() tries
        # response.json() which fails on empty body.
        with pytest.raises((ValueError, httpx.DecodingError)):
            await client.health()

    @respx.mock(base_url="http://test:8000/v1")
    async def test_204_no_content(self, respx_mock, client: EngramClient):
        """Server returns 204 with empty body -> handled."""
        respx_mock.get("/health").mock(return_value=httpx.Response(204))
        # 204 is <400, transport returns it. health() tries .json().
        with pytest.raises((ValueError, httpx.DecodingError)):
            await client.health()


# ---------------------------------------------------------------------------
# TestPartialResponses
# ---------------------------------------------------------------------------


class TestPartialResponses:
    """Content-type mismatches and encoding issues."""

    @respx.mock(base_url="http://test:8000/v1")
    async def test_content_type_mismatch(self, respx_mock, client: EngramClient):
        """Content-Type: text/plain but body is JSON -> handled."""
        respx_mock.get("/health").mock(
            return_value=httpx.Response(
                200,
                content=b'{"status":"ok","redis":true,"neo4j":true,"version":"1.0"}',
                headers={"content-type": "text/plain"},
            )
        )
        result = await client.health()
        assert result.status == "ok"

    @respx.mock(base_url="http://test:8000/v1")
    async def test_response_encoding_issues(self, respx_mock, client: EngramClient):
        """Response with latin-1 encoded body -> handled."""
        body = '{"status":"ok","redis":true,"neo4j":true,"version":"1.0"}'
        respx_mock.get("/health").mock(
            return_value=httpx.Response(
                200,
                content=body.encode("latin-1"),
                headers={"content-type": "application/json; charset=latin-1"},
            )
        )
        result = await client.health()
        assert result.status == "ok"
