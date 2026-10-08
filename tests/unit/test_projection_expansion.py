"""Generic plan bounds, whole-event refusal and original-position correlation."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from context_graph.domain import pack_projection as projection
from context_graph.domain.models import Event
from context_graph.domain.ontology import OntologyRegistry, Pack
from context_graph.ontology import load_registry


def registry():
    return load_registry(["expansion"], [Path("tests/fixtures/pack_contracts")], builtin_packs=[])


def plan(payload, event_type="expansion.recorded", schema=None):
    schema = schema or registry()
    event = Event(
        event_id=uuid4(),
        event_type=event_type,
        occurred_at=datetime(2026, 10, 7, tzinfo=UTC),
        session_id="expansion-fixture",
        agent_id="fixture",
        trace_id="fixture",
        payload_ref="fixture",
    )
    schema.event_types[event_type].definition.payload_contract.validate_payload(payload)
    return projection.PackProjector(schema, frozenset()).plan(event, {"payload": payload})


@pytest.mark.parametrize("groups,items", [(["g"], ["a", "b"]), ([], ["a"])])
def test_contract_valid_unequal_keys_refuse_whole_plan(groups, items):
    with pytest.raises(projection.ProjectionExpansionError) as error:
        plan({"groups": groups, "items": items})
    assert error.value.reason == "unequal_key_lengths"
    assert "secret" not in str(error.value)


def test_equal_keys_and_all_empty_have_exact_outputs():
    result = plan({"groups": ["g", "h"], "items": ["a", "b"]})
    assert [node.ref.key for node in result.nodes] == ["ExpansionRecord:g|a", "ExpansionRecord:h|b"]
    assert len(result.edges) == len(result.states) == 2
    assert plan({"groups": [], "items": []}).empty


def test_scalar_keys_broadcast_and_preserve_original_positions():
    result = plan({"sources": ["a", "", "c"], "targets": ["x", "y", "z"]}, "expansion.stubbed")
    assert [(e.source.key, e.target.key) for e in result.edges] == [
        ("ExpansionRecord:left|a", "ExpansionRecord:right|x"),
        ("ExpansionRecord:left|c", "ExpansionRecord:right|z"),
    ]


def test_equal_fanout_uses_index_join_not_quadratic_scan(monkeypatch):
    # Each keyed index should be examined only a constant number of times.
    original = projection._Keyed.__getattribute__
    reads = 0

    def tracked(self, name):
        nonlocal reads
        reads += name == "index"
        return original(self, name)

    monkeypatch.setattr(projection._Keyed, "__getattribute__", tracked)
    ids = [f"ExpansionRecord:g|{i}" for i in range(100)]
    assert len(plan({"sources": ids, "targets": ids}, "expansion.linked").edges) == 100
    assert reads < 1000


def test_unequal_endpoints_retain_bounded_product():
    result = plan({"sources": ["a", "b"], "targets": ["x", "y", "z"]}, "expansion.stubbed")
    assert len(result.nodes) == 5 and len(result.edges) == 6


def test_product_overflow_is_checked_before_edge_property_evaluation(monkeypatch):
    monkeypatch.setattr(projection, "MAX_PROJECTION_OPERATIONS", 10)

    def forbidden(*args):
        raise AssertionError("Product evaluation began before budget refusal")

    monkeypatch.setattr(projection.PackProjector, "_edge_properties", forbidden)
    with pytest.raises(projection.ProjectionExpansionError, match="plan_limit_exceeded"):
        plan({"sources": ["a", "b"], "targets": ["x", "y", "z"]}, "expansion.stubbed")


def test_budget_counts_provenance_and_states_at_boundary(monkeypatch):
    monkeypatch.setattr(projection, "MAX_PROJECTION_OPERATIONS", 3)
    result = plan({"groups": ["g"], "items": ["a"]})
    assert len(result.nodes) + len(result.edges) + len(result.states) == 3
    monkeypatch.setattr(projection, "MAX_PROJECTION_OPERATIONS", 2)
    with pytest.raises(projection.ProjectionExpansionError, match="plan_limit_exceeded"):
        plan({"groups": ["g"], "items": ["a"]})


@pytest.mark.parametrize(
    "event_type,payload,limit",
    [
        ("expansion.recorded", {"groups": ["g"] * 4, "items": ["a"] * 4}, 3),
        ("expansion.linked", {"sources": ["invalid"] * 4, "targets": []}, 3),
        ("expansion.stubbed", {"sources": ["a", "b"], "targets": ["x", "y", "z"]}, 10),
        ("expansion.looked_up", {"items": ["a", "b"], "target_group": "right"}, 3),
    ],
)
def test_keys_references_products_stubs_and_lookups_are_bounded(
    monkeypatch, event_type, payload, limit
):
    monkeypatch.setattr(projection, "MAX_PROJECTION_OPERATIONS", limit)
    with pytest.raises(projection.ProjectionExpansionError, match="plan_limit_exceeded"):
        plan(payload, event_type)


def test_budget_is_shared_across_subscriber_rules(monkeypatch):
    base = registry()
    subscriber = Pack.model_validate(
        {
            "pack": {"name": "observer", "version": "0.1.0", "requires": ["expansion>=0.1"]},
            "projection": [
                {
                    "event": "expansion:expansion.recorded",
                    "upsert": [
                        {
                            "type": "expansion:ExpansionRecord",
                            "key": {"group": "extra", "item": "record"},
                        }
                    ],
                }
            ],
        }
    )
    schema = OntologyRegistry([*base.packs, subscriber])
    monkeypatch.setattr(projection, "MAX_PROJECTION_OPERATIONS", 4)
    with pytest.raises(projection.ProjectionExpansionError, match="plan_limit_exceeded"):
        plan({"groups": ["g"], "items": ["a"]}, schema=schema)


def test_prefix_list_refuses_before_copying_or_converting_values(monkeypatch):
    class NoConversion(str):
        def __str__(self):
            raise AssertionError("Prefix conversion began before size refusal")

    monkeypatch.setattr(projection, "MAX_PROJECTION_OPERATIONS", 3)
    with pytest.raises(projection.ProjectionExpansionError, match="plan_limit_exceeded"):
        plan({"items": ["one"], "prefixes": [NoConversion("path")] * 4}, "expansion.prefixed")


@pytest.mark.asyncio
async def test_worker_discards_late_failed_plan_and_applies_valid_sibling(monkeypatch):
    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.adapters.memory.subscription import MemorySubscription
    from context_graph.settings import Settings
    from context_graph.worker.projection import ProjectionConsumer

    monkeypatch.setattr(projection, "MAX_PROJECTION_OPERATIONS", 5)
    ledger, graph = MemoryEventLog(), MemoryGraphStore()
    subscription = MemorySubscription(ledger.stream, "expansion-fixture", "worker")
    await subscription.ensure_group()
    events = []
    for name, payload in (
        ("bad", {"groups": ["bad", "bad"], "items": ["a", "b"]}),
        ("good", {"groups": ["good"], "items": ["a"]}),
    ):
        event = Event(
            event_id=uuid4(),
            event_type="expansion.recorded",
            occurred_at=datetime(2026, 10, 7, tzinfo=UTC),
            session_id=name,
            agent_id="fixture",
            trace_id="fixture",
            payload_ref="fixture",
        )
        await ledger.append(event, payload)
        events.append(event)
    settings = Settings()
    settings.consumer.projection_batch_size = 2
    consumer = ProjectionConsumer(
        subscription,
        ledger,
        graph,
        settings,
        projection.PackProjector(registry(), frozenset()),
    )
    for delivery in await subscription.read_new(10, 0):
        await consumer.process_message(delivery.position, delivery.fields)
    await consumer.on_stop()
    # Common history is retained; no first-row domain writes from the bad plan leak.
    assert {key for label, key in graph.nodes if label == "Event"} == {
        str(event.event_id) for event in events
    }
    assert {key for label, key in graph.nodes if label == "ExpansionRecord"} == {
        "ExpansionRecord:good|a"
    }
    assert {row["event_id"] for row in subscription.dead_letters} == {str(events[0].event_id)}
    assert not await subscription.read_pending(10)
    assert len(graph.edges) == 1
