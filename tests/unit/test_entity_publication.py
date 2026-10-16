"""Dependency/atomicity regressions; live Spanner acceptance remains separate."""

import asyncio
from copy import deepcopy
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.adapters.memory.log import MemoryEventLog
from context_graph.adapters.memory.subscription import MemorySubscription
from context_graph.adapters.spanner.commits import CommitBudget, CommitTooLarge
from context_graph.adapters.spanner.graph import SpannerGraphStore
from context_graph.domain.models import Edge, EntityNode
from context_graph.domain.projection import event_to_node
from context_graph.ports.errors import RuntimeFencedError, UnavailableError
from context_graph.settings import OntologySettings, Settings
from context_graph.worker.extraction import ExtractionConsumer
from tests.fixtures.events import make_event


def entity(eid="entity:OrionVault"):
    return EntityNode(
        entity_id=eid,
        name="OrionVault",
        entity_type="service",
        first_seen=datetime(2026, 1, 1, tzinfo=UTC),
        last_seen=datetime(2026, 1, 2, tzinfo=UTC),
        embedding=[0.1, 0.2, 0.3],
    )


def sources(graph, ids=("one", "two")):
    for eid in ids:
        graph.nodes[("Event", eid)] = {"event_id": eid}


async def test_missing_projection_has_no_partial_publication_and_replay_is_idempotent():
    graph = MemoryGraphStore()
    sources(graph, ("one",))
    before = deepcopy((graph.nodes, graph.edges))
    with pytest.raises(UnavailableError):
        await graph.publish_extracted_entity("entity:OrionVault", ["one", "two"], node=entity())
    assert (graph.nodes, graph.edges) == before
    sources(graph, ("two",))
    await graph.publish_extracted_entity("entity:OrionVault", ["one", "two", "one"], node=entity())
    expected = deepcopy((graph.nodes, graph.edges))
    await graph.publish_extracted_entity("entity:OrionVault", ["one", "two"], node=entity())
    assert (graph.nodes, graph.edges) == expected
    assert len(graph.edges) == 2
    assert graph.nodes[("Entity", "entity:OrionVault")]["mention_count"] == 1


async def test_existing_canonical_and_rejected_reference_are_preserved():
    graph = MemoryGraphStore()
    sources(graph)
    key = ("Entity", "canonical")
    old = {
        "entity_id": "canonical",
        "name": "Original",
        "first_seen": "old",
        "mention_count": 8,
        "embedding": [0.9],
    }
    graph.nodes[key] = deepcopy(old)
    edge = (("Event", "one"), "REFERENCES", key)
    graph.edges[edge] = {"link_status": "rejected", "confidence": 0.2}
    await graph.publish_extracted_entity("canonical", ["one", "two"])
    assert graph.nodes[key] == old and graph.edges[edge]["link_status"] == "rejected"
    assert (("Event", "two"), "REFERENCES", key) in graph.edges


@pytest.mark.parametrize("kind", ["SAME_AS", "RELATED_TO"])
async def test_resolution_publishes_with_sources_or_nothing(kind):
    graph = MemoryGraphStore()
    sources(graph)
    relation = Edge(
        source="entity:OrionVault",
        target="canonical",
        edge_type=kind,
        properties={"confidence": 0.8},
    )
    before = deepcopy((graph.nodes, graph.edges))
    with pytest.raises(UnavailableError):
        await graph.publish_extracted_entity(
            "entity:OrionVault", ["one", "two"], node=entity(), resolution=relation
        )
    assert (graph.nodes, graph.edges) == before
    graph.nodes[("Entity", "canonical")] = {"entity_id": "canonical", "name": "Original"}
    await graph.publish_extracted_entity(
        "entity:OrionVault", ["one", "two"], node=entity(), resolution=relation
    )
    assert len(graph.edges) == 3
    assert (
        graph.edges[(("Entity", "entity:OrionVault"), kind, ("Entity", "canonical"))]["confidence"]
        == 0.8
    )


async def test_stale_orphan_selection_cannot_delete_newly_linked_memory_entity():
    graph = MemoryGraphStore()
    sources(graph)
    graph.nodes[("Entity", "canonical")] = {"entity_id": "canonical"}
    selected = [("Entity", "canonical")]
    await graph.publish_extracted_entity("canonical", ["one", "two"])
    assert await graph._delete_orphan_candidates(selected) == []
    assert ("Entity", "canonical") in graph.nodes and len(graph.edges) == 2


def native(rows, budget=None, fence=None):
    tx = MagicMock()
    tx.read.side_effect = [rows, []]
    db = MagicMock()
    scheduled = []
    committed = []
    tx.insert_or_update.side_effect = lambda table, columns, values: scheduled.append(
        (table, values)
    )

    def boundary(callback):
        out = callback(tx)
        committed.extend(scheduled)
        return out

    db.run_in_transaction.side_effect = boundary
    graph = SpannerGraphStore(db, embedding_dimensions=3, commit_budget=budget, tenant_fence=fence)
    return graph, db, tx, scheduled, committed


@pytest.mark.parametrize("failure", ["dependency", "budget", "fence", "schedule"])
async def test_spanner_publication_rejection_cannot_commit_half_an_entity(failure):
    rows = [["Event", "one", {"event_id": "one"}]]
    if failure != "dependency":
        rows.append(["Event", "two", {"event_id": "two"}])
    fence = None
    if failure == "fence":
        fence = MagicMock()
        fence.run.side_effect = RuntimeFencedError("stale binding")
    graph, db, tx, scheduled, committed = native(
        rows, CommitBudget(max_mutations=1) if failure == "budget" else None, fence
    )
    if failure == "schedule":

        def fail(table, columns, values):
            scheduled.append((table, values))
            if table == "GraphEdges":
                raise RuntimeError("SDK scheduling failure")

        tx.insert_or_update.side_effect = fail
    error = {
        "dependency": UnavailableError,
        "budget": CommitTooLarge,
        "fence": RuntimeFencedError,
        "schedule": RuntimeError,
    }[failure]
    with pytest.raises(error):
        await graph.publish_extracted_entity("entity:OrionVault", ["one", "two"], node=entity())
    assert not committed
    if failure != "schedule":
        assert not scheduled
    if failure == "fence":
        db.run_in_transaction.assert_not_called()


async def test_spanner_entity_and_all_references_share_one_transaction():
    graph, db, tx, scheduled, committed = native(
        [["Event", eid, {"event_id": eid}] for eid in ("one", "two")]
    )
    await graph.publish_extracted_entity("entity:OrionVault", ["one", "two"], node=entity())
    db.run_in_transaction.assert_called_once()
    assert [t for t, _ in committed] == ["GraphNodes", "GraphEdges"]
    assert len(committed[0][1]) == 1 and len(committed[1][1]) == 2


@pytest.mark.parametrize("linked", [True, False])
async def test_spanner_orphan_delete_rechecks_connectivity_in_its_transaction(linked):
    tx = MagicMock()
    tx.read.return_value = [["Entity", "canonical"]]
    db = MagicMock()
    db.run_in_transaction.side_effect = lambda callback: callback(tx)
    graph = SpannerGraphStore(db)
    graph._incident_edges_sync = MagicMock(
        return_value=[["Event", "one", "REFERENCES", "Entity", "canonical"]] if linked else []
    )
    result = await graph._delete_orphan_candidates([("Entity", "canonical")])
    assert result == ([] if linked else [("Entity", "canonical")])
    if linked:
        tx.delete.assert_not_called()
    else:
        assert tx.delete.call_args.args[0] == "GraphNodes"
    graph._incident_edges_sync.assert_called_once_with(tx, [("Entity", "canonical")])


@pytest.mark.parametrize("canonical", [False, True])
async def test_delayed_projection_retries_publication_without_repeating_extraction(canonical):
    graph, ledger = MemoryGraphStore(), MemoryEventLog()
    old = {
        "entity_id": "entity:OrionVault",
        "name": "OrionVault",
        "entity_type": "service",
        "first_seen": "original",
        "mention_count": 8,
        "embedding": [0.9],
    }
    if canonical:
        graph.nodes[("Entity", "entity:OrionVault")] = deepcopy(old)
    records = []
    for kind, payload in [
        ("observation.input", {"content": "OrionVault is a service."}),
        ("system.session_end", {}),
    ]:
        event = make_event(event_type=kind, session_id="publication", agent_id="operator")
        pos = await ledger.append(event, payload)
        records.append((event, pos))
    provider = AsyncMock()
    provider.extract_from_session.return_value = {
        "entities": [
            {
                "name": "OrionVault",
                "entity_type": "service",
                "confidence": 1,
                "source_quote": "OrionVault is a service.",
            }
        ]
    }
    settings = Settings(ontology=OntologySettings(packs=[], builtin_packs=[]))
    worker = ExtractionConsumer(
        MemorySubscription(ledger.stream, "extraction", "test"),
        ledger,
        provider,
        settings,
        graph_store=graph,
    )
    worker._transient_backoff_ms = 1
    worker._transient_backoff_max_ms = 5
    task = asyncio.create_task(
        worker.process_message(records[-1][1], {"event_id": str(records[-1][0].event_id)})
    )
    try:
        await asyncio.sleep(0.02)
        assert not task.done()
        provider.extract_from_session.assert_awaited_once()
        assert graph.nodes.get(("Entity", "entity:OrionVault")) == (old if canonical else None)
        assert not graph.edges
        for event, pos in records:
            await graph.merge_event_node(
                event_to_node(event.model_copy(update={"global_position": pos}))
            )
        await asyncio.wait_for(task, 2)
        provider.extract_from_session.assert_awaited_once()
        assert len([k for k in graph.edges if k[1] == "REFERENCES"]) == 2
        if canonical:
            assert graph.nodes[("Entity", "entity:OrionVault")] == old
    finally:
        worker.stop()
        await asyncio.gather(task, return_exceptions=True)


class Result:
    def __init__(self, rows):
        self.rows = rows

    def __aiter__(self):
        async def items():
            for row in self.rows:
                yield row

        return items()

    async def single(self):
        return self.rows[0] if self.rows else None


class NeoTransaction:
    def __init__(self, nodes, edges, drop_before_edges=False):
        self.nodes = deepcopy(nodes)
        self.edges = deepcopy(edges)
        self.queries = []
        self.drop_before_edges = drop_before_edges

    async def run(self, query, params):
        import re

        self.queries.append(query)
        if "RETURN n." in query:
            label = "Event" if "n:Event" in query else "Entity"
            return Result(
                [
                    dict(id=eid, props=self.nodes[(label, eid)])
                    for eid in params["ids"]
                    if (label, eid) in self.nodes
                ]
            )
        if "properties(r) AS props" in query:
            kind = re.search(r"\[r:(\w+)\]", query)[1]
            label = "Event" if kind == "REFERENCES" else "Entity"
            return Result(
                [
                    dict(
                        source=row["source"],
                        target=row["target"],
                        props=self.edges[((label, row["source"]), kind, ("Entity", row["target"]))],
                    )
                    for row in params["pairs"]
                    if ((label, row["source"]), kind, ("Entity", row["target"])) in self.edges
                ]
            )
        if query.startswith("MERGE (n:Entity"):
            self.nodes.setdefault(("Entity", params["id"]), deepcopy(params["defaults"]))
            self.nodes[("Entity", params["id"])].update(deepcopy(params["updates"]))
            return Result([])
        if "MERGE (a)-[r:" in query:
            kind = re.search(r"\[r:(\w+)\]", query)[1]
            label = "Event" if kind == "REFERENCES" else "Entity"
            if self.drop_before_edges:
                self.nodes.pop(("Event", "two"), None)
            count = 0
            for row in params["rows"]:
                key = ((label, row["source"]), kind, ("Entity", row["target"]))
                if key[0] in self.nodes and key[2] in self.nodes:
                    self.edges[key] = deepcopy(row["props"])
                    count += 1
            return Result([dict(count=count)])
        raise AssertionError("Unexpected native statement")


class NeoSession:
    def __init__(self, driver):
        self.driver = driver

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def execute_write(self, callback):
        tx = NeoTransaction(self.driver.nodes, self.driver.edges, self.driver.drop)
        self.driver.transactions.append(tx)
        result = await callback(tx)
        self.driver.nodes, self.driver.edges = tx.nodes, tx.edges
        return result


@pytest.mark.parametrize("failure", [None, "missing-source", "disappearing-source"])
async def test_neo4j_publication_transaction_does_not_commit_partial_evidence(failure):
    from context_graph.adapters.neo4j.pack_graph import Neo4jPackGraph

    driver = MagicMock()
    driver.nodes = {("Event", eid): {"event_id": eid} for eid in ("one", "two")}
    driver.edges = {}
    driver.transactions = []
    driver.drop = failure == "disappearing-source"
    if failure == "missing-source":
        driver.nodes.pop(("Event", "two"))
    driver.session.side_effect = lambda **kwargs: NeoSession(driver)
    store = Neo4jPackGraph()
    store._driver = driver
    store._database = "neo4j"
    before = deepcopy((driver.nodes, driver.edges))
    if failure:
        with pytest.raises(UnavailableError):
            await store.publish_extracted_entity("entity:OrionVault", ["one", "two"], node=entity())
        assert (driver.nodes, driver.edges) == before
        if failure == "missing-source":
            assert not any("MERGE" in q for q in driver.transactions[0].queries)
    else:
        await store.publish_extracted_entity("entity:OrionVault", ["one", "two"], node=entity())
        assert ("Entity", "entity:OrionVault") in driver.nodes and len(driver.edges) == 2
        expected = deepcopy((driver.nodes, driver.edges))
        await store.publish_extracted_entity("entity:OrionVault", ["one", "two"], node=entity())
        assert (driver.nodes, driver.edges) == expected


async def test_neo4j_orphan_cleanup_reports_only_actual_conditional_deletions():
    from context_graph.adapters.neo4j.maintenance import _delete_orphan_entities

    class Tx:
        def __init__(self):
            self.queries = []

        async def run(self, q, params):
            self.queries.append(q)
            if "deleted_ids" in q:
                assert "WHERE NOT (n)--()" in q and "DETACH DELETE" not in q
                return Result([dict(deleted_count=1, deleted_ids=["orphan"])])
            return Result([dict(entity_id="orphan"), dict(entity_id="newly-linked")])

    tx = Tx()

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def execute_read(self, callback):
            return await callback(tx)

        async def execute_write(self, callback):
            return await callback(tx)

    driver = MagicMock()
    driver.session.return_value = Session()
    count, ids = await _delete_orphan_entities(driver, "neo4j", 500)
    assert count == 1 and ids == ["orphan"]


async def test_neo4j_stale_absent_read_preserves_concurrent_creator_origin():
    from context_graph.adapters.neo4j.pack_graph import Neo4jPackGraph

    winner = dict(
        entity_id="entity:OrionVault",
        name="Original name",
        entity_type="service",
        first_seen="2020-01-01T00:00:00+00:00",
        mention_count=19,
    )

    class ConcurrentTx(NeoTransaction):
        async def run(self, query, params):
            if query.startswith("MERGE (n:Entity"):
                # Another transaction won after our absent read and before MERGE.
                self.nodes[("Entity", params["id"])] = deepcopy(winner)
                assert "ON CREATE SET" in query
            return await super().run(query, params)

    class ConcurrentSession(NeoSession):
        async def execute_write(self, callback):
            tx = ConcurrentTx(self.driver.nodes, self.driver.edges)
            result = await callback(tx)
            self.driver.nodes, self.driver.edges = tx.nodes, tx.edges
            return result

    driver = MagicMock()
    driver.nodes = {("Event", eid): {"event_id": eid} for eid in ("one", "two")}
    driver.edges = {}
    driver.session.side_effect = lambda **kwargs: ConcurrentSession(driver)
    store = Neo4jPackGraph()
    store._driver, store._database = driver, "neo4j"
    await store.publish_extracted_entity("entity:OrionVault", ["one", "two"], node=entity())
    actual = driver.nodes[("Entity", "entity:OrionVault")]
    assert {key: actual[key] for key in winner} == winner
    assert actual["last_seen"] == entity().last_seen.isoformat()
    assert actual["embedding"] == entity().embedding
    assert len(driver.edges) == 2
