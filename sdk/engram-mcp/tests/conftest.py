"""Shared fixtures for MCP server tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from engram.models import (
    AtlasEdge,
    AtlasNode,
    AtlasResponse,
    IngestResult,
    NodeScores,
    Pagination,
    Provenance,
    QueryMeta,
    UserProfile,
)
from engram_mcp.server import EngramMCPServer


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mock EngramClient with all methods pre-configured."""
    client = AsyncMock()

    # Default ingest returns a valid IngestResult
    client.ingest.return_value = IngestResult(
        event_id=str(uuid.uuid4()),
        global_position="1707644400000-0",
    )

    # Default get_context returns an empty AtlasResponse
    client.get_context.return_value = AtlasResponse()

    # Default query_subgraph returns an empty AtlasResponse
    client.query_subgraph.return_value = AtlasResponse()

    # Default get_lineage returns an empty AtlasResponse
    client.get_lineage.return_value = AtlasResponse()

    # Default user endpoints
    client.get_user_profile.return_value = UserProfile()
    client.get_user_preferences.return_value = []
    client.get_user_skills.return_value = []
    client.get_user_patterns.return_value = []
    client.get_user_interests.return_value = []

    # Default delete_user
    client.delete_user.return_value = {"deleted_count": 5}

    # Default close
    client.close.return_value = None

    return client


@pytest.fixture
def mcp_server(mock_client: AsyncMock) -> EngramMCPServer:
    """Create an EngramMCPServer with a mocked client."""
    server = EngramMCPServer()
    server._client = mock_client
    return server


def make_atlas_response(
    num_nodes: int = 3,
    node_type: str = "Event",
    has_more: bool = False,
    query_ms: int = 50,
) -> AtlasResponse:
    """Helper to create a populated AtlasResponse."""
    nodes: dict[str, AtlasNode] = {}
    edges: list[AtlasEdge] = []

    for i in range(num_nodes):
        node_id = f"evt-{uuid.uuid4()}"
        nodes[node_id] = AtlasNode(
            node_id=node_id,
            node_type=node_type,
            attributes={
                "payload_ref": f"Event content {i}",
                "event_type": "observation.output",
            },
            provenance=Provenance(
                event_id=str(uuid.uuid4()),
                global_position=f"{1707644400000 + i}-0",
                occurred_at=datetime.now(timezone.utc),
                session_id="test-session",
                agent_id="test-agent",
                trace_id="test-trace",
            ),
            scores=NodeScores(
                decay_score=0.9 - (i * 0.1),
                relevance_score=0.8,
                importance_score=5,
            ),
        )

    # Add edges between consecutive nodes
    node_ids = list(nodes.keys())
    for i in range(len(node_ids) - 1):
        edges.append(
            AtlasEdge(
                source=node_ids[i],
                target=node_ids[i + 1],
                edge_type="FOLLOWS",
                properties={"delta_ms": 1000},
            )
        )

    return AtlasResponse(
        nodes=nodes,
        edges=edges,
        pagination=Pagination(
            cursor="next-cursor" if has_more else None,
            has_more=has_more,
        ),
        meta=QueryMeta(
            query_ms=query_ms,
            nodes_returned=num_nodes,
            truncated=False,
            inferred_intents={"general": 0.8},
        ),
    )
