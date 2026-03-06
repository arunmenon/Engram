"""Unit tests for Prometheus metrics and RequestIDMiddleware.

Validates that metric objects are correctly defined and that the
request ID middleware generates / propagates X-Request-ID headers.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

if TYPE_CHECKING:
    from collections.abc import Generator

import pytest
from prometheus_client import REGISTRY, Counter, Gauge, Histogram
from starlette.testclient import TestClient

from context_graph.adapters.metrics import (
    CONSUMER_LAG,
    CONSUMER_MESSAGE_ERRORS,
    CONSUMER_MESSAGES_PROCESSED,
    EVENTS_BATCH_SIZE,
    EVENTS_INGESTED_TOTAL,
    GRAPH_QUERY_DURATION,
    HTTP_REQUEST_DURATION,
    HTTP_REQUESTS_TOTAL,
)

# ---------------------------------------------------------------------------
# Metric definition tests
# ---------------------------------------------------------------------------


class TestMetricDefinitions:
    """Verify all 8 metrics exist with the expected types and labels."""

    def test_http_requests_total_is_counter(self) -> None:
        assert isinstance(HTTP_REQUESTS_TOTAL, Counter)

    def test_http_requests_total_labels(self) -> None:
        assert HTTP_REQUESTS_TOTAL._labelnames == ("method", "endpoint", "status")

    def test_http_request_duration_is_histogram(self) -> None:
        assert isinstance(HTTP_REQUEST_DURATION, Histogram)

    def test_http_request_duration_labels(self) -> None:
        assert HTTP_REQUEST_DURATION._labelnames == ("method", "endpoint")

    def test_events_ingested_total_is_counter(self) -> None:
        assert isinstance(EVENTS_INGESTED_TOTAL, Counter)

    def test_events_batch_size_is_histogram(self) -> None:
        assert isinstance(EVENTS_BATCH_SIZE, Histogram)

    def test_consumer_messages_processed_is_counter(self) -> None:
        assert isinstance(CONSUMER_MESSAGES_PROCESSED, Counter)

    def test_consumer_messages_processed_labels(self) -> None:
        assert CONSUMER_MESSAGES_PROCESSED._labelnames == ("consumer",)

    def test_consumer_message_errors_is_counter(self) -> None:
        assert isinstance(CONSUMER_MESSAGE_ERRORS, Counter)

    def test_consumer_message_errors_labels(self) -> None:
        assert CONSUMER_MESSAGE_ERRORS._labelnames == ("consumer",)

    def test_consumer_lag_is_gauge(self) -> None:
        assert isinstance(CONSUMER_LAG, Gauge)

    def test_consumer_lag_labels(self) -> None:
        assert CONSUMER_LAG._labelnames == ("group",)

    def test_graph_query_duration_is_histogram(self) -> None:
        assert isinstance(GRAPH_QUERY_DURATION, Histogram)

    def test_graph_query_duration_labels(self) -> None:
        assert GRAPH_QUERY_DURATION._labelnames == ("query_type",)


class TestMetricOperations:
    """Verify metrics can be incremented/observed without errors."""

    def test_events_ingested_total_increment(self) -> None:
        before = REGISTRY.get_sample_value("engram_events_ingested_total") or 0.0
        EVENTS_INGESTED_TOTAL.inc()
        after = REGISTRY.get_sample_value("engram_events_ingested_total") or 0.0
        assert after == before + 1.0

    def test_events_batch_size_observe(self) -> None:
        EVENTS_BATCH_SIZE.observe(42)
        count = REGISTRY.get_sample_value("engram_events_batch_size_count") or 0.0
        assert count >= 1.0

    def test_consumer_messages_processed_labeled(self) -> None:
        CONSUMER_MESSAGES_PROCESSED.labels(consumer="graph-projection").inc()
        value = REGISTRY.get_sample_value(
            "engram_consumer_messages_processed_total",
            {"consumer": "graph-projection"},
        )
        assert value is not None and value >= 1.0

    def test_consumer_message_errors_labeled(self) -> None:
        CONSUMER_MESSAGE_ERRORS.labels(consumer="graph-projection").inc()
        value = REGISTRY.get_sample_value(
            "engram_consumer_message_errors_total",
            {"consumer": "graph-projection"},
        )
        assert value is not None and value >= 1.0

    def test_graph_query_duration_observe(self) -> None:
        GRAPH_QUERY_DURATION.labels(query_type="context").observe(0.045)
        count = REGISTRY.get_sample_value(
            "engram_graph_query_duration_seconds_count",
            {"query_type": "context"},
        )
        assert count is not None and count >= 1.0


# ---------------------------------------------------------------------------
# RequestIDMiddleware tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def _mock_stores():
    """Patch store creation so create_app() doesn't need live Redis/Neo4j."""
    mock_event_store = AsyncMock()
    mock_event_store.ensure_indexes = AsyncMock()
    mock_event_store.close = AsyncMock()
    mock_event_store.health_ping = AsyncMock(return_value=True)

    mock_graph_store = AsyncMock()
    mock_graph_store.ensure_constraints = AsyncMock()
    mock_graph_store.close = AsyncMock()
    mock_graph_store.health_ping = AsyncMock(return_value=True)

    with (
        patch(
            "context_graph.api.app.RedisEventStore.create",
            new_callable=AsyncMock,
            return_value=mock_event_store,
        ),
        patch(
            "context_graph.api.app.Neo4jGraphStore",
            return_value=mock_graph_store,
        ),
    ):
        yield


@pytest.fixture()
def client(_mock_stores: None) -> Generator[TestClient, None, None]:
    """Create a TestClient against the real app factory (enters lifespan)."""
    from context_graph.api.app import create_app

    app = create_app()
    with TestClient(app) as tc:
        yield tc


class TestRequestIDMiddleware:
    """Verify X-Request-ID propagation and generation."""

    def test_generates_request_id_when_missing(self, client: TestClient) -> None:
        response = client.get("/v1/health")
        request_id = response.headers.get("x-request-id")
        assert request_id is not None
        # Should be a valid UUID4
        parsed = uuid.UUID(request_id, version=4)
        assert str(parsed) == request_id

    def test_passes_through_existing_request_id(self, client: TestClient) -> None:
        custom_id = "my-custom-trace-id-12345"
        response = client.get("/v1/health", headers={"X-Request-ID": custom_id})
        assert response.headers.get("x-request-id") == custom_id

    def test_request_time_header_still_present(self, client: TestClient) -> None:
        response = client.get("/v1/health")
        assert "x-request-time-ms" in response.headers


class TestMetricsLabelCardinality:
    """Verify that HTTP metrics use route templates, not resolved paths."""

    def test_dynamic_route_uses_template_label(self, test_client: TestClient) -> None:
        """Hit /v1/context/{session_id} with a unique ID and verify the
        Prometheus label uses the template path, not the resolved one."""
        unique_id = "cardinality-test-sess-xyz"
        resolved_path = f"/v1/context/{unique_id}"

        test_client.get(resolved_path)

        # The resolved path should NOT appear as a metric label
        resolved_value = REGISTRY.get_sample_value(
            "engram_http_requests_total",
            {"method": "GET", "endpoint": resolved_path, "status": "200"},
        )
        assert resolved_value is None or resolved_value == 0.0

        # The template path should be used instead
        template_value = REGISTRY.get_sample_value(
            "engram_http_requests_total",
            {"method": "GET", "endpoint": "/v1/context/{session_id}", "status": "200"},
        )
        assert template_value is not None and template_value >= 1.0
