"""Evidence reads are bounded, consistent and fenced (no live database required)."""

from contextlib import contextmanager

import pytest

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.workbench.storage_views import observed_graph, spanner_snapshot


class Database:
    def __init__(self):
        self.queries = []
        self.opens = 0

    @contextmanager
    def snapshot(self, *, multi_use):
        assert multi_use
        self.opens += 1
        yield self

    def execute_sql(self, query):
        self.queries.append(query)
        if "GraphNodes" in query:
            return [["Incident", "Incident:a|1", {"title": "Stored title"}]]
        return [["Incident:a|1", "AFFECTS", "Service:a|checkout", {"confirmed": True}]]


class Fence:
    def __init__(self, database, active=True):
        self.database = database
        self.active = active
        self.checked = False

    def check_database(self, database):
        assert database is self.database

    def check(self, transaction, *, operation):
        assert operation == "read" and transaction is self.database
        assert not self.database.queries
        if not self.active:
            raise PermissionError("stale binding")
        self.checked = True


def test_spanner_evidence_uses_one_snapshot_and_checks_owner_before_reading():
    db = Database()
    fence = Fence(db)
    result = spanner_snapshot(db, fence)
    assert fence.checked and db.opens == 1
    assert "LIMIT 501" in db.queries[0] and "LIMIT 2001" in db.queries[1]
    assert result["nodes"][0]["properties"]["title"] == "Stored title"
    assert result["edges"][0]["properties"] == {"confirmed": True}


def test_spanner_evidence_refuses_missing_or_stale_ownership():
    db = Database()
    with pytest.raises(ValueError, match="owned sandbox"):
        spanner_snapshot(db, None)
    with pytest.raises(PermissionError, match="stale binding"):
        spanner_snapshot(db, Fence(db, active=False))
    assert not db.queries


@pytest.mark.asyncio
async def test_observed_memory_evidence_is_detached_and_never_silently_truncated():
    graph = MemoryGraphStore()
    graph.nodes[("Incident", "one")] = {"nested": {"title": "before"}}
    snapshot = await observed_graph(graph)
    graph.nodes[("Incident", "one")]["nested"]["title"] = "after"
    assert snapshot["nodes"][0]["properties"]["nested"]["title"] == "before"
    graph.nodes.update({("Incident", str(i)): {} for i in range(500)})
    with pytest.raises(ValueError, match="budget"):
        await observed_graph(graph)
