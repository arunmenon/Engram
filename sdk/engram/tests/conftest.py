from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import respx

from engram import EngramClient, EngramConfig
from engram.config import reset_config


@pytest.fixture(autouse=True)
def _reset_global_config():
    """Reset global config between tests for isolation."""
    reset_config()
    yield
    reset_config()


@pytest.fixture
def config() -> EngramConfig:
    """Default test config."""
    return EngramConfig(base_url="http://test:8000", api_key="test-key", admin_key="admin-key")


@pytest.fixture
def mock_api():
    """respx mock router scoped to the test base URL."""
    with respx.mock(base_url="http://test:8000/v1") as router:
        yield router


@pytest.fixture
def client(config: EngramConfig) -> EngramClient:
    """EngramClient configured for testing."""
    return EngramClient(config=config)


def make_event_dict(**overrides):
    """Create a sample event dict for API response mocking."""
    base = {
        "event_id": str(uuid4()),
        "event_type": "tool.execute",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "session_id": "sess-001",
        "agent_id": "agent-001",
        "trace_id": "trace-001",
        "payload_ref": "test payload",
        "schema_version": 1,
    }
    base.update(overrides)
    return base


def make_atlas_response(**overrides):
    """Create a sample Atlas response dict."""
    base = {
        "nodes": {},
        "edges": [],
        "pagination": {"cursor": None, "has_more": False},
        "meta": {
            "query_ms": 42,
            "nodes_returned": 0,
            "truncated": False,
            "inferred_intents": {},
            "seed_nodes": [],
            "proactive_nodes_count": 0,
            "scoring_weights": {"recency": 1.0, "importance": 1.0, "relevance": 1.0},
        },
    }
    base.update(overrides)
    return base


def make_ingest_response(event_id: str | None = None):
    """Create a sample ingest response dict."""
    return {
        "event_id": event_id or str(uuid4()),
        "global_position": "1707644400000-0",
    }
