"""Unit tests for the query API endpoints (context, subgraph, lineage, entities).

Tests use in-memory stubs for Redis/Neo4j — no external services required.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from tests.unit.conftest import StubGraphStore


# ---------------------------------------------------------------------------
# GET /v1/context/{session_id}
# ---------------------------------------------------------------------------


class TestGetContext:
    """Tests for the session context endpoint."""

    def test_get_context(self, test_client: TestClient) -> None:
        response = test_client.get("/v1/context/test-session")

        assert response.status_code == 200
        body = response.json()
        assert "nodes" in body
        assert "edges" in body
        assert "meta" in body
        assert "pagination" in body

    def test_get_context_with_query(self, test_client: TestClient) -> None:
        response = test_client.get("/v1/context/test-session?query=why")

        assert response.status_code == 200
        body = response.json()
        assert "nodes" in body

    def test_get_context_with_max_nodes(self, test_client: TestClient) -> None:
        response = test_client.get("/v1/context/test-session?max_nodes=50")

        assert response.status_code == 200

    def test_get_context_max_nodes_too_large(self, test_client: TestClient) -> None:
        response = test_client.get("/v1/context/test-session?max_nodes=999")

        assert response.status_code == 422

    def test_get_context_max_nodes_too_small(self, test_client: TestClient) -> None:
        response = test_client.get("/v1/context/test-session?max_nodes=0")

        assert response.status_code == 422

    def test_get_context_has_timing_header(self, test_client: TestClient) -> None:
        response = test_client.get("/v1/context/test-session")
        assert "x-request-time-ms" in response.headers


# ---------------------------------------------------------------------------
# POST /v1/query/subgraph
# ---------------------------------------------------------------------------


class TestQuerySubgraph:
    """Tests for the subgraph query endpoint."""

    def test_query_subgraph(self, test_client: TestClient) -> None:
        payload = {
            "query": "why did the tool fail?",
            "session_id": "test-session",
            "agent_id": "test-agent",
        }
        response = test_client.post("/v1/query/subgraph", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert "nodes" in body
        assert "edges" in body
        assert "meta" in body

    def test_query_subgraph_with_options(self, test_client: TestClient) -> None:
        payload = {
            "query": "when was the last deploy?",
            "session_id": "test-session",
            "agent_id": "test-agent",
            "max_nodes": 50,
            "max_depth": 5,
            "intent": "when",
        }
        response = test_client.post("/v1/query/subgraph", json=payload)

        assert response.status_code == 200

    def test_query_subgraph_missing_fields(self, test_client: TestClient) -> None:
        response = test_client.post("/v1/query/subgraph", json={})

        assert response.status_code == 422

    def test_query_subgraph_empty_query_rejected(self, test_client: TestClient) -> None:
        payload = {
            "query": "",
            "session_id": "test-session",
            "agent_id": "test-agent",
        }
        response = test_client.post("/v1/query/subgraph", json=payload)

        assert response.status_code == 422

    def test_query_subgraph_has_timing_header(self, test_client: TestClient) -> None:
        payload = {
            "query": "what happened?",
            "session_id": "test-session",
            "agent_id": "test-agent",
        }
        response = test_client.post("/v1/query/subgraph", json=payload)
        assert "x-request-time-ms" in response.headers


# ---------------------------------------------------------------------------
# GET /v1/nodes/{node_id}/lineage
# ---------------------------------------------------------------------------


class TestGetLineage:
    """Tests for the lineage traversal endpoint."""

    def test_get_lineage(self, test_client: TestClient) -> None:
        response = test_client.get("/v1/nodes/test-id/lineage")

        assert response.status_code == 200
        body = response.json()
        assert "nodes" in body
        assert "edges" in body
        assert "meta" in body

    def test_get_lineage_with_params(self, test_client: TestClient) -> None:
        response = test_client.get("/v1/nodes/test-id/lineage?max_depth=5&max_nodes=50")

        assert response.status_code == 200

    def test_get_lineage_with_intent(self, test_client: TestClient) -> None:
        response = test_client.get("/v1/nodes/test-id/lineage?intent=why")

        assert response.status_code == 200

    def test_get_lineage_max_depth_too_large(self, test_client: TestClient) -> None:
        response = test_client.get("/v1/nodes/test-id/lineage?max_depth=100")

        assert response.status_code == 422

    def test_get_lineage_max_nodes_too_large(self, test_client: TestClient) -> None:
        response = test_client.get("/v1/nodes/test-id/lineage?max_nodes=999")

        assert response.status_code == 422

    def test_get_lineage_has_timing_header(self, test_client: TestClient) -> None:
        response = test_client.get("/v1/nodes/test-id/lineage")
        assert "x-request-time-ms" in response.headers


# ---------------------------------------------------------------------------
# GET /v1/entities/{entity_id}
# ---------------------------------------------------------------------------


class TestGetEntity:
    """Tests for the entity endpoint."""

    def test_get_entity_not_found(self, test_client: TestClient) -> None:
        response = test_client.get("/v1/entities/nonexistent")

        assert response.status_code == 404
        body = response.json()
        assert body["detail"] == "Entity not found"

    def test_get_entity_found(
        self, test_client: TestClient, stub_graph_store: StubGraphStore
    ) -> None:
        stub_graph_store._entities["test-entity"] = {
            "entity_id": "test-entity",
            "name": "Test Entity",
            "entity_type": "concept",
            "events": [],
        }
        response = test_client.get("/v1/entities/test-entity")

        assert response.status_code == 200
        body = response.json()
        assert body["entity_id"] == "test-entity"
        assert body["name"] == "Test Entity"

    def test_get_entity_has_timing_header(self, test_client: TestClient) -> None:
        response = test_client.get("/v1/entities/some-entity")
        assert "x-request-time-ms" in response.headers


# ---------------------------------------------------------------------------
# Regression: max_depth on context endpoint (Fix 6)
# ---------------------------------------------------------------------------


class TestContextEndpointMaxDepth:
    def test_context_endpoint_accepts_max_depth(self, test_client: TestClient) -> None:
        """max_depth parameter should be accepted."""
        response = test_client.get("/v1/context/test-session?max_depth=5")
        assert response.status_code == 200

    def test_context_endpoint_rejects_invalid_max_depth(self, test_client: TestClient) -> None:
        """max_depth > 10 should be rejected."""
        response = test_client.get("/v1/context/test-session?max_depth=20")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Regression: lineage default intent (Fix 7)
# ---------------------------------------------------------------------------


class TestLineageDefaultIntent:
    def test_lineage_default_intent_is_why(self, test_client: TestClient) -> None:
        """Default intent should be 'why' for lineage queries."""
        response = test_client.get("/v1/nodes/test-id/lineage")
        assert response.status_code == 200
