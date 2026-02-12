"""Unit tests for the event ingestion API endpoints.

Tests use in-memory stubs for Redis/Neo4j — no external services required.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def _make_event_payload(**overrides: object) -> dict:
    """Build a valid event JSON payload with sensible defaults."""
    defaults: dict = {
        "event_id": str(uuid4()),
        "event_type": "tool.execute",
        "occurred_at": datetime.now(UTC).isoformat(),
        "session_id": "test-session",
        "agent_id": "test-agent",
        "trace_id": "test-trace",
        "payload_ref": "payload:test",
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# POST /v1/events
# ---------------------------------------------------------------------------


class TestIngestEvent:
    """Tests for the single event ingestion endpoint."""

    def test_ingest_valid_event(self, test_client: TestClient) -> None:
        payload = _make_event_payload()
        response = test_client.post("/v1/events", json=payload)

        assert response.status_code == 201
        body = response.json()
        assert body["event_id"] == payload["event_id"]
        assert "global_position" in body

    def test_ingest_returns_global_position(self, test_client: TestClient) -> None:
        payload = _make_event_payload()
        response = test_client.post("/v1/events", json=payload)

        body = response.json()
        assert body["global_position"]  # non-empty string

    def test_ingest_with_optional_fields(self, test_client: TestClient) -> None:
        payload = _make_event_payload(
            tool_name="search-tool",
            status="completed",
            importance_hint=7,
            schema_version=1,
        )
        response = test_client.post("/v1/events", json=payload)
        assert response.status_code == 201

    def test_ingest_missing_required_field(self, test_client: TestClient) -> None:
        payload = _make_event_payload()
        del payload["session_id"]
        response = test_client.post("/v1/events", json=payload)
        assert response.status_code == 422

    def test_ingest_invalid_event_type_format(self, test_client: TestClient) -> None:
        payload = _make_event_payload(event_type="INVALID")
        response = test_client.post("/v1/events", json=payload)
        assert response.status_code == 422

    def test_ingest_self_referential_parent(self, test_client: TestClient) -> None:
        event_id = str(uuid4())
        payload = _make_event_payload(event_id=event_id, parent_event_id=event_id)
        response = test_client.post("/v1/events", json=payload)
        # Domain validation catches self-referential parent
        assert response.status_code == 422

    def test_ingest_ended_at_before_occurred_at(self, test_client: TestClient) -> None:
        occurred = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        ended = datetime(2025, 1, 1, 11, 0, 0, tzinfo=UTC)
        payload = _make_event_payload(
            occurred_at=occurred.isoformat(),
            ended_at=ended.isoformat(),
        )
        response = test_client.post("/v1/events", json=payload)
        assert response.status_code == 422

    def test_response_has_timing_header(self, test_client: TestClient) -> None:
        payload = _make_event_payload()
        response = test_client.post("/v1/events", json=payload)
        assert "x-request-time-ms" in response.headers


# ---------------------------------------------------------------------------
# POST /v1/events/batch
# ---------------------------------------------------------------------------


class TestIngestBatch:
    """Tests for the batch event ingestion endpoint."""

    def test_batch_all_valid(self, test_client: TestClient) -> None:
        events = [_make_event_payload() for _ in range(3)]
        response = test_client.post("/v1/events/batch", json={"events": events})

        assert response.status_code == 201
        body = response.json()
        assert body["accepted"] == 3
        assert body["rejected"] == 0
        assert len(body["results"]) == 3

    def test_batch_partial_invalid(self, test_client: TestClient) -> None:
        valid_event = _make_event_payload()
        # Self-referential parent -> domain validation error
        bad_id = str(uuid4())
        invalid_event = _make_event_payload(event_id=bad_id, parent_event_id=bad_id)

        events = [valid_event, invalid_event]
        response = test_client.post("/v1/events/batch", json={"events": events})

        assert response.status_code == 201
        body = response.json()
        assert body["accepted"] == 1
        assert body["rejected"] == 1
        assert len(body["errors"]) == 1
        assert body["errors"][0]["index"] == 1

    def test_batch_empty_rejected(self, test_client: TestClient) -> None:
        response = test_client.post("/v1/events/batch", json={"events": []})
        assert response.status_code == 422  # Pydantic min_length=1

    def test_batch_results_contain_positions(self, test_client: TestClient) -> None:
        events = [_make_event_payload() for _ in range(2)]
        response = test_client.post("/v1/events/batch", json={"events": events})
        body = response.json()
        for result in body["results"]:
            assert "global_position" in result
            assert result["global_position"]


# ---------------------------------------------------------------------------
# GET /v1/health
# ---------------------------------------------------------------------------


class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_health_healthy(self, test_client: TestClient) -> None:
        response = test_client.get("/v1/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert body["redis"] is True
        assert body["neo4j"] is True
        assert body["version"] == "0.1.0"

    def test_health_response_has_timing_header(self, test_client: TestClient) -> None:
        response = test_client.get("/v1/health")
        assert "x-request-time-ms" in response.headers
