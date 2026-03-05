"""Unit tests for RateLimitMiddleware integration with FastAPI."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from httpx import ASGITransport, AsyncClient

from context_graph.api.middleware import RateLimitMiddleware


def _make_app(*, enabled: bool = True, standard_rpm: int = 5, admin_rpm: int = 2) -> FastAPI:
    """Build a minimal FastAPI app with rate limiting enabled."""
    settings = MagicMock()
    settings.rate_limit.enabled = enabled
    settings.rate_limit.standard_rpm = standard_rpm
    settings.rate_limit.admin_rpm = admin_rpm
    settings.rate_limit.max_clients = 100

    app = FastAPI(default_response_class=ORJSONResponse)
    app.add_middleware(RateLimitMiddleware, settings=settings)

    @app.get("/v1/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/v1/events")
    async def events():
        return {"events": []}

    @app.get("/v1/admin/stats")
    async def admin_stats():
        return {"stats": {}}

    return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRateLimitMiddleware:
    @pytest.mark.asyncio()
    async def test_health_not_rate_limited(self):
        """Health endpoint is exempt from rate limiting."""
        app = _make_app(standard_rpm=2)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Hit health many times — should never get 429
            for _ in range(10):
                resp = await client.get("/v1/health")
                assert resp.status_code == 200

    @pytest.mark.asyncio()
    async def test_standard_endpoint_returns_429_after_exceeding_limit(self):
        """Standard endpoint returns 429 once the bucket is exhausted."""
        app = _make_app(standard_rpm=3)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 3 allowed requests
            for _ in range(3):
                resp = await client.get("/v1/events")
                assert resp.status_code == 200

            # 4th should be rate limited
            resp = await client.get("/v1/events")
            assert resp.status_code == 429

    @pytest.mark.asyncio()
    async def test_429_response_has_proper_headers(self):
        """429 response includes Retry-After and X-RateLimit-* headers."""
        app = _make_app(standard_rpm=1)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.get("/v1/events")  # consume the single token
            resp = await client.get("/v1/events")  # should be 429

            assert resp.status_code == 429
            assert "Retry-After" in resp.headers
            assert "X-RateLimit-Limit" in resp.headers
            assert resp.headers["X-RateLimit-Remaining"] == "0"
            body = resp.json()
            assert body["detail"] == "Rate limit exceeded"
            assert "retry_after" in body

    @pytest.mark.asyncio()
    async def test_200_response_has_rate_limit_headers(self):
        """Successful responses include X-RateLimit-* headers."""
        app = _make_app(standard_rpm=10)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/events")
            assert resp.status_code == 200
            assert "X-RateLimit-Limit" in resp.headers
            assert "X-RateLimit-Remaining" in resp.headers
            assert resp.headers["X-RateLimit-Limit"] == "10"

    @pytest.mark.asyncio()
    async def test_disabled_setting_bypasses_limiting(self):
        """When enabled=False, no rate limiting is applied."""
        app = _make_app(enabled=False, standard_rpm=1)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Even with RPM=1, all requests should succeed when disabled
            for _ in range(10):
                resp = await client.get("/v1/events")
                assert resp.status_code == 200

    @pytest.mark.asyncio()
    async def test_admin_endpoint_has_separate_limit(self):
        """Admin endpoints use a separate (lower) rate limit."""
        app = _make_app(standard_rpm=100, admin_rpm=2)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Admin has only 2 RPM
            for _ in range(2):
                resp = await client.get("/v1/admin/stats")
                assert resp.status_code == 200

            resp = await client.get("/v1/admin/stats")
            assert resp.status_code == 429

            # Standard endpoint should still work
            resp = await client.get("/v1/events")
            assert resp.status_code == 200
