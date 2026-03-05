"""Shared fixtures for engram-crewai tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from engram.models import (
    AtlasNode,
    AtlasResponse,
    IngestResult,
    NodeScores,
    Pagination,
    Provenance,
    QueryMeta,
)


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mock EngramClient with default return values."""
    client = AsyncMock()
    client.ingest.return_value = IngestResult(
        event_id=str(uuid.uuid4()), global_position="1707644400000-0"
    )
    client.query_subgraph.return_value = AtlasResponse(
        nodes={},
        edges=[],
        pagination=Pagination(),
        meta=QueryMeta(),
    )
    client.close.return_value = None
    return client


@pytest.fixture
def sample_search_response() -> AtlasResponse:
    """Create a sample AtlasResponse for search tests."""
    return AtlasResponse(
        nodes={
            "evt-001": AtlasNode(
                node_id="evt-001",
                node_type="Event",
                attributes={
                    "content": "The deploy pipeline uses GitHub Actions",
                    "event_type": "observation.output",
                },
                provenance=Provenance(
                    event_id="evt-001",
                    global_position="1707644400000-0",
                    source="redis",
                    occurred_at=datetime(2024, 2, 11, 12, 0, 0, tzinfo=UTC),
                    session_id="project-alpha",
                    agent_id="crewai-agent",
                    trace_id="trace-1",
                ),
                scores=NodeScores(decay_score=0.90, relevance_score=0.85, importance_score=6),
            ),
            "evt-002": AtlasNode(
                node_id="evt-002",
                node_type="Event",
                attributes={
                    "content": "CI runs on every PR merge",
                },
                provenance=Provenance(
                    event_id="evt-002",
                    global_position="1707644400001-0",
                    source="redis",
                    occurred_at=datetime(2024, 2, 11, 12, 0, 1, tzinfo=UTC),
                    session_id="project-alpha",
                    agent_id="crewai-agent",
                    trace_id="trace-1",
                ),
                scores=NodeScores(decay_score=0.88, relevance_score=0.70, importance_score=4),
            ),
        },
        edges=[],
        pagination=Pagination(),
        meta=QueryMeta(query_ms=30, nodes_returned=2),
    )
