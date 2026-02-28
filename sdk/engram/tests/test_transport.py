from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from engram.config import EngramConfig
from engram.exceptions import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)
from engram.transport import Transport


@pytest.fixture
def config() -> EngramConfig:
    return EngramConfig(
        base_url="http://test:8000",
        api_key="test-key",
        admin_key="admin-key",
        timeout=5.0,
        max_retries=2,
    )


@pytest.fixture
def transport(config: EngramConfig) -> Transport:
    return Transport(config)


@pytest.fixture
def mock_api():
    with respx.mock(base_url="http://test:8000/v1") as router:
        yield router


class TestBasicRequests:
    async def test_get_request(self, transport: Transport, mock_api: respx.MockRouter):
        mock_api.get("/health").mock(return_value=httpx.Response(200, json={"status": "healthy"}))
        resp = await transport.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "healthy"}
        await transport.close()

    async def test_post_request(self, transport: Transport, mock_api: respx.MockRouter):
        mock_api.post("/events").mock(
            return_value=httpx.Response(200, json={"event_id": "e1", "global_position": "100-0"})
        )
        resp = await transport.post("/events", json={"event_type": "test"})
        assert resp.status_code == 200
        await transport.close()

    async def test_delete_request(self, transport: Transport, mock_api: respx.MockRouter):
        mock_api.delete("/users/u1").mock(return_value=httpx.Response(200, json={"deleted": 1}))
        resp = await transport.delete("/users/u1")
        assert resp.status_code == 200
        await transport.close()


class TestAuthHeaders:
    async def test_auth_header_api_key(self, transport: Transport, mock_api: respx.MockRouter):
        route = mock_api.get("/health").mock(return_value=httpx.Response(200, json={}))
        await transport.get("/health")
        request = route.calls[0].request
        assert request.headers["Authorization"] == "Bearer test-key"
        await transport.close()

    async def test_auth_header_admin_key(self, transport: Transport, mock_api: respx.MockRouter):
        route = mock_api.get("/admin/stats").mock(return_value=httpx.Response(200, json={}))
        await transport.get("/admin/stats", admin=True)
        request = route.calls[0].request
        assert request.headers["Authorization"] == "Bearer admin-key"
        await transport.close()

    async def test_no_auth_header_when_none(self, mock_api: respx.MockRouter):
        config = EngramConfig(base_url="http://test:8000")
        t = Transport(config)
        route = mock_api.get("/health").mock(return_value=httpx.Response(200, json={}))
        await t.get("/health")
        request = route.calls[0].request
        assert "Authorization" not in request.headers
        await t.close()


class TestRetryLogic:
    async def test_retry_on_429(self, transport: Transport, mock_api: respx.MockRouter):
        mock_api.get("/health").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "0.01"}, json={}),
                httpx.Response(200, json={"status": "ok"}),
            ]
        )
        resp = await transport.get("/health")
        assert resp.status_code == 200
        await transport.close()

    async def test_retry_on_503(self, transport: Transport, mock_api: respx.MockRouter):
        mock_api.get("/health").mock(
            side_effect=[
                httpx.Response(503, json={}),
                httpx.Response(200, json={"status": "ok"}),
            ]
        )
        with patch("engram.transport.asyncio.sleep", new_callable=AsyncMock):
            resp = await transport.get("/health")
        assert resp.status_code == 200
        await transport.close()

    async def test_retry_exhausted_raises(self, mock_api: respx.MockRouter):
        config = EngramConfig(base_url="http://test:8000", max_retries=1)
        t = Transport(config)
        mock_api.get("/health").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "0.01"}, json={}),
                httpx.Response(429, headers={"Retry-After": "0.01"}, json={}),
            ]
        )
        with pytest.raises(RateLimitError):
            await t.get("/health")
        await t.close()

    async def test_connection_error_retry(self, transport: Transport, mock_api: respx.MockRouter):
        mock_api.get("/health").mock(
            side_effect=[
                httpx.ConnectError("connection refused"),
                httpx.Response(200, json={"status": "ok"}),
            ]
        )
        with patch("engram.transport.asyncio.sleep", new_callable=AsyncMock):
            resp = await transport.get("/health")
        assert resp.status_code == 200
        await transport.close()

    async def test_timeout_error_retry(self, transport: Transport, mock_api: respx.MockRouter):
        mock_api.get("/health").mock(
            side_effect=[
                httpx.ReadTimeout("timeout"),
                httpx.Response(200, json={"status": "ok"}),
            ]
        )
        with patch("engram.transport.asyncio.sleep", new_callable=AsyncMock):
            resp = await transport.get("/health")
        assert resp.status_code == 200
        await transport.close()


class TestErrorMapping:
    async def test_map_error_401(self, transport: Transport, mock_api: respx.MockRouter):
        mock_api.get("/health").mock(
            return_value=httpx.Response(401, json={"detail": "unauthorized"})
        )
        with pytest.raises(AuthenticationError) as exc_info:
            await transport.get("/health")
        assert exc_info.value.status_code == 401
        await transport.close()

    async def test_map_error_404(self, transport: Transport, mock_api: respx.MockRouter):
        mock_api.get("/entities/missing").mock(
            return_value=httpx.Response(404, json={"detail": "not found"})
        )
        with pytest.raises(NotFoundError):
            await transport.get("/entities/missing")
        await transport.close()

    async def test_map_error_422(self, transport: Transport, mock_api: respx.MockRouter):
        errors = [{"loc": ["body", "event_type"], "msg": "required", "type": "missing"}]
        mock_api.post("/events").mock(return_value=httpx.Response(422, json={"detail": errors}))
        with pytest.raises(ValidationError) as exc_info:
            await transport.post("/events", json={})
        assert exc_info.value.errors == errors
        await transport.close()

    async def test_map_error_500(self, transport: Transport, mock_api: respx.MockRouter):
        mock_api.get("/health").mock(
            return_value=httpx.Response(500, json={"detail": "internal error"})
        )
        with pytest.raises(ServerError) as exc_info:
            await transport.get("/health")
        assert exc_info.value.status_code == 500
        await transport.close()


class TestRequestIdPropagation:
    async def test_request_id_propagation(self, transport: Transport, mock_api: respx.MockRouter):
        route = mock_api.get("/health").mock(return_value=httpx.Response(200, json={}))
        await transport.get("/health")
        request = route.calls[0].request
        assert "X-Request-ID" in request.headers
        # Should be a valid UUID4-ish string
        assert len(request.headers["X-Request-ID"]) == 36
        await transport.close()


class TestCloseClient:
    async def test_close_client(self, transport: Transport, mock_api: respx.MockRouter):
        # Ensure client is created
        mock_api.get("/health").mock(return_value=httpx.Response(200, json={}))
        await transport.get("/health")
        assert transport._client is not None
        await transport.close()
        assert transport._client is None
