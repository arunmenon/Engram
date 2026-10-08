"""A transient dependency failure is deliberately retryable, not a generic500 (#28)."""

import httpx
import pytest
from fastapi import FastAPI

from context_graph.api.middleware import register_middleware
from context_graph.ports.errors import StorageTimeoutError, UnavailableError


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [UnavailableError, StorageTimeoutError])
async def test_transient_storage_error_returns_safe_503(error):
    app = FastAPI()
    register_middleware(app)

    @app.post("/events")
    async def fail():
        raise error("private driver detail")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        response = await client.post("/events")
    assert response.status_code == 503
    assert response.headers["retry-after"] == "1"
    assert "private driver detail" not in response.text
