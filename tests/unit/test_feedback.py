"""Unit tests for the retrieval feedback domain model.

Tests for the RetrievalFeedback model and aggregate_feedback_for_node.
"""

from __future__ import annotations

from datetime import UTC, datetime

from context_graph.domain.feedback import RetrievalFeedback


class TestRetrievalFeedback:
    """Tests for RetrievalFeedback model."""

    def test_valid_feedback(self) -> None:
        fb = RetrievalFeedback(
            query_id="q1",
            session_id="s1",
            helpful_node_ids=["n1", "n2"],
            irrelevant_node_ids=["n3"],
        )
        assert fb.query_id == "q1"
        assert len(fb.helpful_node_ids) == 2
        assert len(fb.irrelevant_node_ids) == 1
        assert fb.timestamp is not None

    def test_defaults(self) -> None:
        fb = RetrievalFeedback(query_id="q1", session_id="s1")
        assert fb.helpful_node_ids == []
        assert fb.irrelevant_node_ids == []

    def test_custom_timestamp(self) -> None:
        ts = datetime(2025, 1, 1, tzinfo=UTC)
        fb = RetrievalFeedback(
            query_id="q1",
            session_id="s1",
            timestamp=ts,
        )
        assert fb.timestamp == ts


# ---------------------------------------------------------------------------
# Feedback API endpoint
# ---------------------------------------------------------------------------


class TestFeedbackEndpoint:
    """Tests for the /v1/feedback POST endpoint."""

    def _make_app(self):
        from unittest.mock import AsyncMock, MagicMock

        from fastapi import FastAPI

        from context_graph.api.routes.feedback import router

        app = FastAPI()
        app.include_router(router, prefix="/v1")

        mock_event_store = AsyncMock()
        mock_event_store.append.return_value = "1234-0"

        mock_graph_store = AsyncMock()
        mock_graph_store.adjust_node_importance.return_value = True

        app.state.settings = MagicMock()
        app.state.settings.auth.api_key = None
        app.state.event_store = mock_event_store
        app.state.graph_store = mock_graph_store

        return app, mock_event_store, mock_graph_store

    def test_submit_feedback_success(self) -> None:
        from fastapi.testclient import TestClient

        application, mock_event_store, mock_graph_store = self._make_app()
        client = TestClient(application)

        response = client.post(
            "/v1/feedback",
            json={
                "query_id": "q-001",
                "session_id": "sess-001",
                "helpful_node_ids": ["node-1", "node-2"],
                "irrelevant_node_ids": ["node-3"],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["query_id"] == "q-001"
        assert data["global_position"] == "1234-0"
        assert data["bumped"] == 2
        assert data["decremented"] == 1

    def test_submit_feedback_empty_lists(self) -> None:
        from fastapi.testclient import TestClient

        application, _, _ = self._make_app()
        client = TestClient(application)

        response = client.post(
            "/v1/feedback",
            json={
                "query_id": "q-002",
                "session_id": "sess-002",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["bumped"] == 0
        assert data["decremented"] == 0

    def test_submit_feedback_stores_event(self) -> None:
        from fastapi.testclient import TestClient

        application, mock_event_store, _ = self._make_app()
        client = TestClient(application)

        client.post(
            "/v1/feedback",
            json={
                "query_id": "q-003",
                "session_id": "sess-003",
                "helpful_node_ids": ["n1"],
            },
        )
        mock_event_store.append.assert_called_once()
