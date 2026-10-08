"""Admin pruning must inspect edge scores and bound live cold deletion (#33)."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from context_graph.adapters.graph_ops import GraphOperations
from context_graph.domain.forgetting import should_prune_warm
from tests.unit.test_api_admin import _make_admin_client


def test_missing_node_similarity_is_not_a_low_score():
    assert not should_prune_warm({"similarity_score": None})


def test_warm_preview_counts_edges_and_live_uses_same_predicate():
    client = _make_admin_client()
    graph = client.app.state.graph_store
    graph.count_edges_by_type_and_age = AsyncMock(return_value=2)
    graph.delete_edges_by_type_and_age = AsyncMock(return_value=2)
    graph.events_for_pruning = AsyncMock(side_effect=AssertionError("warm must inspect edges"))
    for dry in (True, False):
        response = client.post("/v1/admin/prune", json={"tier": "warm", "dry_run": dry})
        assert response.status_code == 200
        assert response.json()["pruned_edges"] == 2
    graph.count_edges_by_type_and_age.assert_awaited_once()
    graph.delete_edges_by_type_and_age.assert_awaited_once()
    assert (
        graph.count_edges_by_type_and_age.call_args == graph.delete_edges_by_type_and_age.call_args
    )


def test_cold_live_deletes_only_previewed_ids():
    old = (datetime.now(UTC) - timedelta(hours=200)).isoformat()
    client = _make_admin_client(
        session_query_results=[
            {
                "event_id": "cold-low",
                "occurred_at": old,
                "importance_score": 0,
                "access_count": 0,
                "similarity_score": None,
            },
            {
                "event_id": "cold-retained",
                "occurred_at": old,
                "importance_score": 10,
                "access_count": 10,
                "similarity_score": None,
            },
        ]
    )
    graph = client.app.state.graph_store
    graph.delete_archive_events = AsyncMock(return_value=1)
    graph.delete_cold_events = AsyncMock(side_effect=AssertionError("no unbounded rescan"))
    for dry in (True, False):
        response = client.post("/v1/admin/prune", json={"tier": "cold", "dry_run": dry})
        assert response.status_code == 200
        assert response.json()["pruned_nodes"] == 1
    graph.delete_archive_events.assert_awaited_once_with(event_ids=["cold-low"])


@pytest.mark.asyncio
async def test_generic_edge_preview_and_delete_share_real_scores():
    graph = GraphOperations()
    source = ("Event", "old")
    young = ("Event", "young")
    target = ("Event", "target")
    low = (source, "SIMILAR_TO", target)
    graph._edges = AsyncMock(
        return_value=[
            (low, {"similarity_score": 0.2}),
            ((source, "SIMILAR_TO", ("Event", "high")), {"similarity_score": 0.9}),
            ((young, "SIMILAR_TO", target), {"similarity_score": 0.1}),
            ((source, "SIMILAR_TO", ("Event", "missing-score")), {}),
        ]
    )
    graph._get_nodes = AsyncMock(
        return_value={
            source: {"occurred_at": (datetime.now(UTC) - timedelta(hours=2)).isoformat()},
            young: {"occurred_at": datetime.now(UTC).isoformat()},
        }
    )
    graph._delete_edges = AsyncMock()
    assert await graph.count_edges_by_type_and_age(0.7, 1) == 1
    graph._delete_edges.assert_not_awaited()
    assert await graph.delete_edges_by_type_and_age(0.7, 1) == 1
    graph._delete_edges.assert_awaited_once_with([low])
