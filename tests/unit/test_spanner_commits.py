"""Spanner commit budgets and database opening (maturity review S5, S7, F1).

Unit tests cover the budget arithmetic, the schema the code expects and
the refusal to create a database on a real instance. Tests marked
``integration`` run on the Spanner emulator (``CG_SPANNER_EMULATOR_HOST``)
with a tiny budget, so every write path has to split its commits.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from context_graph.adapters.spanner.commits import (
    EVENT_ROW_MUTATIONS,
    NODE_ROW_MUTATIONS,
    CommitBudget,
    CommitTooLarge,
    event_row_cost,
    group_by_key,
)
from context_graph.adapters.spanner.schema import (
    SchemaMismatchError,
    expected_schema,
    open_database,
)
from context_graph.settings import SpannerSettings
from tests.fixtures.events import make_event


class TestBudget:
    def test_chunks_keep_order_and_fit(self):
        budget = CommitBudget(max_mutations=10, max_bytes=1_000)
        runs = budget.chunks(list(range(7)), lambda _item: (3, 10))
        assert runs == [[0, 1, 2], [3, 4, 5], [6]]

    def test_bytes_also_split(self):
        budget = CommitBudget(max_mutations=1_000, max_bytes=100)
        runs = budget.chunks(["a", "b", "c"], lambda _item: (1, 60))
        assert runs == [["a"], ["b"], ["c"]]

    def test_oversized_item_gets_its_own_run(self):
        budget = CommitBudget(max_mutations=10, max_bytes=100)
        runs = budget.chunks([1, 50, 2], lambda item: (item, 0))
        assert runs == [[1], [50], [2]]

    def test_check_raises_over_budget(self):
        budget = CommitBudget(max_mutations=10, max_bytes=100)
        budget.check([(5, 50), (5, 50)])
        with pytest.raises(CommitTooLarge):
            budget.check([(5, 50), (6, 50)])

    def test_group_by_key_keeps_first_seen_order(self):
        items = [("a", 1), ("b", 2), ("a", 3)]
        assert group_by_key(items, lambda item: item[0]) == [[("a", 1), ("a", 3)], [("b", 2)]]

    def test_event_cost_counts_indexed_text_twice(self):
        mutations, size = event_row_cost({"summary": "x" * 100, "payload": {}})
        assert mutations == EVENT_ROW_MUTATIONS
        assert size >= 300

    def test_default_import_chunk_fits_the_default_budget(self):
        """500 small events, the import chunk size, stay in one commit."""
        budget = CommitBudget()
        runs = budget.chunks([{"payload": {"x": 1}}] * 500, event_row_cost)
        assert len(runs) == 1


class TestExpectedSchema:
    def test_tables_columns_indexes_and_graph(self):
        expected = expected_schema(384)
        assert "search_text" in expected["table:Events"]
        assert "text_tokens" in expected["table:Events"]
        node_columns = {"label", "node_id", "props", "session_id", "embedding"}
        assert expected["table:GraphNodes"] == node_columns
        assert "GraphNodesByEmbedding" in expected["indexes"]
        assert "EventsText" in expected["indexes"]
        assert expected["graphs"] == {"EngramGraph"}


class TestOpenDatabase:
    """Database creation is deliberate on a real instance (review F1)."""

    def _open(self, settings: SpannerSettings, *, exists: bool) -> MagicMock:
        pytest.importorskip("google.cloud.spanner")
        database = MagicMock()
        database.exists.return_value = exists
        client = MagicMock()
        client.instance.return_value.database.return_value = database
        with patch("google.cloud.spanner.Client", return_value=client):
            open_database(settings)
        return database

    def test_missing_database_without_create_is_refused(self):
        with pytest.raises(SchemaMismatchError, match="does not exist"):
            self._open(SpannerSettings(project="p", instance="i", emulator_host=None), exists=False)

    def test_create_if_missing_does_not_create_on_a_real_instance(self):
        settings = SpannerSettings(
            project="p", instance="i", emulator_host=None, create_if_missing=True
        )
        with pytest.raises(SchemaMismatchError, match="ALLOW_CREATE_ON_INSTANCE"):
            self._open(settings, exists=False)

    def test_real_instance_creation_needs_both_settings(self):
        settings = SpannerSettings(
            project="p", instance="i", create_if_missing=True, allow_create_on_instance=True
        )
        database = self._open(settings, exists=False)
        database.create.assert_called_once()


# ---------------------------------------------------------------------------
# On the emulator
# ---------------------------------------------------------------------------

EMULATOR = os.environ.get("CG_SPANNER_EMULATOR_HOST") or os.environ.get("SPANNER_EMULATOR_HOST")
needs_emulator = [
    pytest.mark.integration,
    pytest.mark.skipif(not EMULATOR, reason="Spanner emulator not configured"),
]


@contextlib.asynccontextmanager
async def _database(**overrides: Any) -> Any:
    pytest.importorskip("google.cloud.spanner")
    settings = SpannerSettings(
        emulator_host=EMULATOR,
        database=f"cmt{uuid.uuid4().hex[:12]}",
        create_if_missing=True,
        **overrides,
    )
    database = await asyncio.to_thread(open_database, settings)
    try:
        yield database
    finally:
        with contextlib.suppress(Exception):
            await asyncio.to_thread(database.drop)


def _counting(store: Any) -> list[int]:
    """Count the transactions a store runs."""
    calls: list[int] = []
    original = store._transact

    async def transact(fn: Any) -> Any:
        calls.append(1)
        return await original(fn)

    store._transact = transact
    return calls


class TestSpannerOnEmulator:
    pytestmark = needs_emulator

    async def test_existing_database_matching_schema_opens(self):
        async with _database() as database:
            settings = SpannerSettings(emulator_host=EMULATOR, database=database.database_id)
            await asyncio.to_thread(open_database, settings)

    async def test_schema_mismatch_is_reported(self):
        async with _database() as database:
            operation = database.update_ddl(["DROP INDEX EventsBySessionTag"])
            await asyncio.to_thread(operation.result, 120)
            settings = SpannerSettings(emulator_host=EMULATOR, database=database.database_id)
            with pytest.raises(SchemaMismatchError, match="index EventsBySessionTag is missing"):
                await asyncio.to_thread(open_database, settings)

    async def test_append_splits_into_ordered_commits(self):
        from context_graph.adapters.spanner.log import SpannerEventLog

        async with _database() as database:
            budget = CommitBudget(max_mutations=EVENT_ROW_MUTATIONS * 2)
            log = SpannerEventLog(database, commit_budget=budget)
            events = [make_event(session_id="s1") for _ in range(5)]
            outcomes = await log.append_batch_outcomes([*events, events[0]])

            assert [o.status for o in outcomes] == ["created"] * 5 + ["duplicate"]
            positions = [o.position for o in outcomes[:5]]
            assert positions == sorted(positions)
            assert outcomes[5].position == outcomes[0].position
            entries = await log.read_after(None, 10)
            assert [e.event_id for e in entries] == [str(e.event_id) for e in events]

    async def test_failed_later_chunk_reports_the_rest_failed(self):
        from context_graph.adapters.spanner.log import SpannerEventLog

        async with _database() as database:
            log = SpannerEventLog(
                database, commit_budget=CommitBudget(max_mutations=EVENT_ROW_MUTATIONS * 2)
            )
            original = log._append_chunk_sync
            calls: list[int] = []

            def fail_second(entries: Any) -> Any:
                calls.append(1)
                if len(calls) == 2:
                    raise RuntimeError("commit refused")
                return original(entries)

            log._append_chunk_sync = fail_second  # type: ignore[method-assign]
            events = [make_event(session_id="s1") for _ in range(5)]
            outcomes = await log.append_batch_outcomes(events)

            assert [o.status for o in outcomes] == ["created"] * 2 + ["failed"] * 3
            assert "commit refused" in (outcomes[2].error or "")
            assert len(await log.read_after(None, 10)) == 2

    async def test_retention_runs_in_batches(self):
        from context_graph.adapters.spanner.log import SpannerEventLog

        async with _database() as database:
            log = SpannerEventLog(database, retention_batch_rows=2)
            await log.append_batch([make_event(session_id="s1") for _ in range(5)])
            assert await log.trim(max_age_days=0, consumer_groups=[]) == 5
            assert await log.stream_length() == 0
            archived, deleted = await log.expire(max_age_days=-1)
            assert (archived, deleted) == (0, 5)
            counts = await log.housekeep(retention_ceiling_days=-1, session_index_max_age_hours=0)
            assert counts["dedup_entries_removed"] == 5
            with database.snapshot() as snapshot:
                (row,) = list(snapshot.execute_sql("SELECT COUNT(*) FROM Events"))
            assert row[0] == 0

    async def test_node_writes_split_and_keep_per_key_order(self):
        from context_graph.adapters.spanner.graph import SpannerGraphStore

        async with _database() as database:
            graph = SpannerGraphStore(
                database, commit_budget=CommitBudget(max_mutations=NODE_ROW_MUTATIONS * 2)
            )
            calls = _counting(graph)
            items = [(("Thing", f"t{i}"), {"n": i}) for i in range(5)]
            items.append((("Thing", "t0"), {"n": 99}))
            await graph._upsert_nodes(items)

            nodes = await graph._get_nodes([("Thing", f"t{i}") for i in range(5)])
            assert nodes[("Thing", "t0")]["n"] == 99
            assert {nodes[("Thing", f"t{i}")]["n"] for i in range(1, 5)} == {1, 2, 3, 4}
            assert len(calls) == 3

    async def test_run_larger_than_estimated_is_split(self):
        """Stored properties are only known in the transaction: a run over budget splits."""
        from context_graph.adapters.spanner.graph import SpannerGraphStore

        async with _database() as database:
            loose = SpannerGraphStore(database)
            big = "x" * 4_000
            await loose._upsert_nodes([(("Thing", f"t{i}"), {"body": big}) for i in range(4)])

            graph = SpannerGraphStore(database, commit_budget=CommitBudget(max_bytes=20_000))
            calls = _counting(graph)
            await graph._upsert_nodes([(("Thing", f"t{i}"), {"seen": True}) for i in range(4)])

            nodes = await graph._get_nodes([("Thing", f"t{i}") for i in range(4)])
            assert all(n["seen"] and n["body"] == big for n in nodes.values())
            assert len(calls) > 1

    async def test_state_changes_split_by_node(self):
        from context_graph.adapters.spanner.graph import SpannerGraphStore
        from context_graph.ports.pack_graph import NodeRef, StateChange

        async with _database() as database:
            graph = SpannerGraphStore(
                database, commit_budget=CommitBudget(max_mutations=NODE_ROW_MUTATIONS)
            )
            await graph._upsert_nodes([(("Ticket", f"k{i}"), {"status": "open"}) for i in range(3)])
            changes = [
                StateChange(NodeRef("Ticket", "k0"), "doing", "2026-10-05T00:00:00Z"),
                StateChange(NodeRef("Ticket", "k1"), "doing", "2026-10-05T00:00:00Z"),
                StateChange(NodeRef("Ticket", "k0"), "done", "2026-10-05T00:00:01Z", ("doing",)),
                StateChange(NodeRef("Ticket", "k2"), "done", "2026-10-05T00:00:01Z", ("doing",)),
            ]
            assert await graph._apply_state_changes(changes) == 3
            nodes = await graph._get_nodes([("Ticket", f"k{i}") for i in range(3)])
            assert [nodes[("Ticket", f"k{i}")]["status"] for i in range(3)] == [
                "done",
                "doing",
                "open",
            ]

    async def test_payload_floats_round_trip(self):
        from context_graph.adapters.spanner.log import SpannerEventLog

        async with _database() as database:
            log = SpannerEventLog(database)
            event = make_event(session_id="s1")
            payload = {"scores": TestJsonFloats.REFUSED, "weight": 0.25}
            await log.append_batch([event], [payload])
            (document,) = await log.get_documents([str(event.event_id)])
            assert document is not None
            assert document["payload"] == payload

    async def test_hub_node_delete_removes_edges_first(self):
        from context_graph.adapters.spanner.graph import SpannerGraphStore

        async with _database() as database:
            graph = SpannerGraphStore(database, commit_budget=CommitBudget(max_mutations=30))
            spokes = [("Spoke", f"s{i}") for i in range(12)]
            await graph._upsert_nodes([(("Hub", "h"), {}), *[(key, {}) for key in spokes]])
            written = await graph._upsert_edges(
                [((key, "LINKS", ("Hub", "h")), {"w": 1}) for key in spokes]
            )
            assert written == 12

            assert await graph._delete_nodes([("Hub", "h")]) == 1
            assert await graph._edges(targets=[("Hub", "h")]) == []
            assert await graph._get_nodes([("Hub", "h")]) == {}
            assert len(await graph._get_nodes(spokes)) == 12


class TestJsonFloats:
    """Floats reach Spanner JSON as tagged strings (real Spanner refuses some numbers)."""

    # Refused by a real instance on 2026-10-05 (docs/review/2026-10-05-spanner-trial-results.md)
    REFUSED = [0.0928069675519494, 0.770496225183326, -0.707176497086, 5.81439691724e-05]

    def test_floats_are_encoded_and_decoded_exactly(self):
        pytest.importorskip("google.cloud.spanner")
        import math

        from context_graph.adapters.spanner.log import FLOAT_TAG, json_param, json_value

        value = {
            "scores": self.REFUSED,
            "nested": {"x": 0.1, "inf": float("inf"), "nan": float("nan")},
            "count": 3,
            "whole": 2.0,
            "text": "0.5",
        }
        cell = json_param(value)
        assert f'"{FLOAT_TAG}"' in cell.serialize()
        assert '"whole":2.0' in cell.serialize()  # integral floats stay numbers
        decoded = json_value(cell)
        assert decoded["scores"] == self.REFUSED
        assert decoded["nested"]["x"] == 0.1
        assert math.isinf(decoded["nested"]["inf"])
        assert math.isnan(decoded["nested"]["nan"])
        assert (decoded["count"], decoded["whole"], decoded["text"]) == (3, 2.0, "0.5")

    def test_a_lookalike_dict_with_more_keys_is_kept(self):
        pytest.importorskip("google.cloud.spanner")
        from context_graph.adapters.spanner.log import json_param, json_value

        value = {"$float": "1.5", "other": 1}
        assert json_value(json_param(value)) == value
