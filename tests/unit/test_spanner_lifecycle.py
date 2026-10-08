"""Engram owns cleanup of SDK resources, including failed cleanup (#26)."""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from context_graph.adapters.spanner.lifecycle import close_database, prepare_cleanup


def resources():
    manager = SimpleNamespace(_MAINTENANCE_THREAD_POLLING_INTERVAL=timedelta(minutes=10))
    database = SimpleNamespace(
        sessions_manager=manager,
        close=MagicMock(),
        _spanner_api=SimpleNamespace(transport=SimpleNamespace(close=MagicMock())),
    )
    client = SimpleNamespace(
        _database_admin_api=None,
        _instance_admin_api=None,
        close=MagicMock(),
    )
    pool = SimpleNamespace(clear=MagicMock())
    return database, client, pool


def test_owned_resources_close_once_and_manager_poll_is_bounded():
    database, client, pool = resources()
    prepare_cleanup(database, client, pool)
    assert database.sessions_manager._MAINTENANCE_THREAD_POLLING_INTERVAL.total_seconds() == 1
    close_database(database)
    close_database(database)
    database.close.assert_called_once()
    pool.clear.assert_called_once()
    database._spanner_api.transport.close.assert_called_once()
    client.close.assert_called_once()


def test_failed_database_cleanup_does_not_skip_other_resources():
    database, client, pool = resources()
    database.close.side_effect = RuntimeError("SDK close fault")
    prepare_cleanup(database, client, pool)
    with pytest.raises(ExceptionGroup, match="cleanup failed"):
        close_database(database)
    pool.clear.assert_called_once()
    client.close.assert_called_once()


@pytest.mark.asyncio
async def test_spanner_handle_closes_if_later_startup_fails(monkeypatch):
    from unittest.mock import patch

    from context_graph.adapters.registry import open_stores
    from context_graph.settings import Settings

    for name in ("EVENT_LOG", "GRAPH", "SUBSCRIPTION", "KEYWORD_INDEX", "VECTOR_INDEX"):
        monkeypatch.setenv("CG_STORAGE_" + name, "spanner")
    database = SimpleNamespace(close=MagicMock())
    with (
        patch("context_graph.adapters.spanner.schema.open_database", return_value=database),
        patch(
            "context_graph.adapters.registry._open_spanner_log",
            return_value=(MagicMock(), MagicMock()),
        ),
        patch(
            "context_graph.adapters.spanner.graph.SpannerGraphStore",
            side_effect=RuntimeError("graph startup failure"),
        ),
        pytest.raises(RuntimeError, match="graph startup failure"),
    ):
        await open_stores(Settings())
    database.close.assert_called_once()
