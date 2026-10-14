"""Tenant HTTP query refuses unsupported cursors before retrieval effects."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI

from context_graph.api.dependencies import get_retrieval
from context_graph.api.routes.query import router


@pytest.mark.asyncio
async def test_bound_tenant_rejects_body_cursor_before_retrieval():
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    app.state.tenant_binding = SimpleNamespace(tenant_id="a")
    retrieval = SimpleNamespace(
        get_subgraph=AsyncMock(side_effect=AssertionError("Unsupported cursor reached retrieval"))
    )
    app.dependency_overrides[get_retrieval] = lambda: retrieval
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/query/subgraph",
            json={
                "query": "find events",
                "session_id": "shared-session",
                "agent_id": "shared-agent",
                "cursor": "foreign-cursor",
            },
        )
    assert response.status_code == 400
    assert response.json() == {"detail": "Tenant cursor unavailable"}
    retrieval.get_subgraph.assert_not_awaited()
