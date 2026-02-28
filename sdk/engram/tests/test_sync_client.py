from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import httpx
import pytest
import respx

from engram.config import EngramConfig
from engram.models import AtlasResponse, Event, HealthStatus, IngestResult
from engram.sync_client import EngramSyncClient


@pytest.fixture
def config() -> EngramConfig:
    return EngramConfig(base_url="http://test:8000", api_key="test-key")


@pytest.fixture
def mock_api():
    with respx.mock(base_url="http://test:8000/v1") as router:
        yield router


def _sample_event() -> Event:
    return Event(
        event_id=uuid4(),
        event_type="tool.execute",
        occurred_at=datetime.now(timezone.utc),
        session_id="sess-1",
        agent_id="agent-1",
        trace_id="trace-1",
        payload_ref="test data",
    )


class TestSyncClient:
    def test_sync_ingest(self, config: EngramConfig, mock_api: respx.MockRouter):
        mock_api.post("/events").mock(
            return_value=httpx.Response(200, json={"event_id": "e1", "global_position": "100-0"})
        )
        client = EngramSyncClient(config=config)
        try:
            result = client.ingest(_sample_event())
            assert isinstance(result, IngestResult)
            assert result.event_id == "e1"
        finally:
            client.close()

    def test_sync_get_context(self, config: EngramConfig, mock_api: respx.MockRouter):
        mock_api.get("/context/sess-1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "nodes": {},
                    "edges": [],
                    "pagination": {"cursor": None, "has_more": False},
                    "meta": {},
                },
            )
        )
        client = EngramSyncClient(config=config)
        try:
            result = client.get_context("sess-1")
            assert isinstance(result, AtlasResponse)
        finally:
            client.close()

    def test_sync_health(self, config: EngramConfig, mock_api: respx.MockRouter):
        mock_api.get("/health").mock(
            return_value=httpx.Response(
                200,
                json={"status": "healthy", "redis": True, "neo4j": True, "version": "0.1.0"},
            )
        )
        client = EngramSyncClient(config=config)
        try:
            result = client.health()
            assert isinstance(result, HealthStatus)
            assert result.status == "healthy"
        finally:
            client.close()

    def test_sync_context_manager(self, config: EngramConfig, mock_api: respx.MockRouter):
        mock_api.get("/health").mock(
            return_value=httpx.Response(
                200,
                json={"status": "healthy", "redis": True, "neo4j": True, "version": "0.1.0"},
            )
        )
        with EngramSyncClient(config=config) as client:
            result = client.health()
            assert result.status == "healthy"

    def test_sync_close(self, config: EngramConfig, mock_api: respx.MockRouter):
        client = EngramSyncClient(config=config)
        client.close()
        # After close, the loop should be stopped
        assert not client._loop.is_running()
