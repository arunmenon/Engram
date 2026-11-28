"""Actual Spanner adapter over a transaction fake; not emulator/cloud acceptance."""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict
from threading import RLock

import pytest

from context_graph.adapters.spanner.graph import SpannerGraphStore
from context_graph.adapters.spanner.tenant_control import TenantFenceError
from context_graph.ports.pack_graph import EdgeWrite, NodeRef, NodeWrite
from tests.unit.test_spanner_tenant_reads import FENCE, RESOURCE


class Transaction:
    def __init__(self, database):
        self.database = database
        self.tables = deepcopy(database.tables)

    def read(self, table, columns, keys, **kwargs):
        if table == "TenantControl":
            return [list(self.database.owner)]
        rows = self.tables[table]
        explicit = {tuple(key) for key in keys.keys}
        prefixes = [tuple(r.start_closed) for r in keys.ranges]
        return [
            [row.get(c) for c in columns]
            for key, row in sorted(rows.items())
            if keys.all_ or key in explicit or any(key[: len(p)] == p for p in prefixes)
        ]

    def insert_or_update(self, table, columns, values):
        size = 2 if table == "GraphNodes" else 5
        for values_row in values:
            row = dict(zip(columns, values_row, strict=True))
            key = tuple(values_row[:size])
            self.tables[table][key] = row

    def insert(self, table, columns, values):
        size = 2 if table == "GraphNodes" else 5
        for row in values:
            assert tuple(row[:size]) not in self.tables[table]
        self.insert_or_update(table, columns, values)

    def execute_sql(self, sql, params=None, **kwargs):
        # Independent relational keyset semantics for the one native bounded scan.
        assert sql.startswith("SELECT props FROM GraphNodes WHERE label = @label")
        rows = [
            (key, row)
            for key, row in self.tables["GraphNodes"].items()
            if key[0] == params["label"] and key[1] > params["after"]
        ]
        return [[row["props"]] for _key, row in sorted(rows)[: params["limit"]]]


class Database:
    name = RESOURCE

    def __init__(self):
        self.owner = [
            FENCE.tenant_id,
            RESOURCE,
            FENCE.binding_id,
            FENCE.epoch,
            FENCE.bundle_digest,
            "active",
        ]
        self.tables = {"GraphNodes": {}, "GraphEdges": {}}
        self.lock = RLock()

    @contextmanager
    def snapshot(self, *, multi_use=False):
        assert multi_use
        with self.lock:
            yield Transaction(self)

    def run_in_transaction(self, callback):
        with self.lock:
            transaction = Transaction(self)
            result = callback(transaction)
            self.tables = transaction.tables
            return result


def setup():
    database = Database()
    return database, SpannerGraphStore(
        database, tenant_fence=FENCE, tenant_read_operation="processing"
    )


SOURCE = NodeRef("Contact", "Contact:ann")
TARGET = NodeRef("Account", "Account:acme")
EDGE = EdgeWrite("WORKS_AT", SOURCE, TARGET, {"link_status": "proposed"})


def intent(key="a", generation="first", order="0001"):
    return {
        "node_id": key,
        "event_id": "source-event",
        "bundle": "test-bundle",
        "authority": "test-authority",
        "effect_digest": "test-effect",
        "generation": generation,
        "order_key": order,
        "position": order,
        "source": asdict(SOURCE),
        "target": asdict(TARGET),
        "edge_type": "WORKS_AT",
        "required": True,
        "status": "endpoint_missing",
    }


async def test_native_atomic_recovery_waits_then_creates_once_and_keeps_reviewed_properties():
    _db, graph = setup()
    await graph.put_relationship_intent(intent())
    assert (
        await graph.settle_relationship_intent("a", "first", "waiting", EDGE) == "endpoint_missing"
    )
    await graph.upsert_nodes([NodeWrite(SOURCE), NodeWrite(TARGET)])
    assert await graph.settle_relationship_intent("a", "first", "waiting", EDGE) == "recovered"
    await graph.upsert_edges([EdgeWrite("WORKS_AT", SOURCE, TARGET, {"link_status": "rejected"})])
    assert (
        await graph.settle_relationship_intent("a", "first", "waiting", EDGE)
        == "existing_relationship_kept"
    )
    rows = await graph.neighbors([SOURCE], ["WORKS_AT"], "out", 10)
    assert len(rows) == 1 and rows[0]["properties"]["link_status"] == "rejected"
    await graph.put_relationship_intent(intent())
    assert (await graph.get_relationship_intents(["a"]))["a"][
        "status"
    ] == "existing_relationship_kept"


async def test_newer_pending_generation_fences_stale_writer_and_scan_is_keyset_bounded():
    _db, graph = setup()
    for key in ("a", "b", "c"):
        await graph.put_relationship_intent(intent(key))
    await graph.put_relationship_intent(intent("a", "newer", "0002"))
    assert await graph.settle_relationship_intent("a", "first", "waiting", EDGE) == "superseded"
    assert [r["node_id"] for r in await graph.relationship_intents("a", 1)] == ["b"]
    assert (await graph.get_relationship_intents(["a"]))["a"]["generation"] == "newer"


async def test_tenant_fence_refuses_before_changing_recovery_rows_or_edges():
    db, graph = setup()
    await graph.put_relationship_intent(intent())
    before = await graph.get_relationship_intents(["a"])
    db.owner[3] += 1
    with pytest.raises(TenantFenceError):
        await graph.settle_relationship_intent("a", "first", "waiting", EDGE)
    with pytest.raises(TenantFenceError):
        await graph.relationship_intents(None, 1)
    db.owner[3] -= 1
    assert await graph.get_relationship_intents(["a"]) == before
    assert await graph.neighbors([SOURCE], ["WORKS_AT"], "out", 10) == []
