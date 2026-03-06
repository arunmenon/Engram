"""Shared fixtures for engram-langchain tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from engram.models import (
    AtlasNode,
    AtlasResponse,
    BatchResult,
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
    client.ingest_batch.return_value = BatchResult(accepted=1, rejected=0, results=[], errors=[])
    client.get_context.return_value = _empty_atlas()
    client.query_subgraph.return_value = _empty_atlas()
    return client


@pytest.fixture
def sample_atlas_response() -> AtlasResponse:
    """Create a sample AtlasResponse with a few nodes."""
    return AtlasResponse(
        nodes={
            "evt-001": AtlasNode(
                node_id="evt-001",
                node_type="Event",
                attributes={
                    "content": "User asked about billing",
                    "event_type": "chat.human",
                },
                provenance=Provenance(
                    event_id="evt-001",
                    global_position="1707644400000-0",
                    source="redis",
                    occurred_at=datetime(2024, 2, 11, 12, 0, 0, tzinfo=UTC),
                    session_id="sess-abc",
                    agent_id="agent-1",
                    trace_id="trace-1",
                ),
                scores=NodeScores(decay_score=0.95, relevance_score=0.88, importance_score=7),
                retrieval_reason="direct",
            ),
            "evt-002": AtlasNode(
                node_id="evt-002",
                node_type="Event",
                attributes={
                    "content": "Billing is managed through Stripe",
                    "event_type": "chat.ai",
                },
                provenance=Provenance(
                    event_id="evt-002",
                    global_position="1707644400001-0",
                    source="redis",
                    occurred_at=datetime(2024, 2, 11, 12, 0, 1, tzinfo=UTC),
                    session_id="sess-abc",
                    agent_id="agent-1",
                    trace_id="trace-1",
                ),
                scores=NodeScores(decay_score=0.93, relevance_score=0.75, importance_score=5),
                retrieval_reason="traversal",
            ),
        },
        edges=[],
        pagination=Pagination(cursor=None, has_more=False),
        meta=QueryMeta(query_ms=42, nodes_returned=2),
    )


def _empty_atlas() -> AtlasResponse:
    return AtlasResponse(
        nodes={},
        edges=[],
        pagination=Pagination(),
        meta=QueryMeta(),
    )
