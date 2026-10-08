"""Opt-in property contract through actual pack load/planning/application."""

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import yaml
from pydantic import ValidationError

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.domain.ontology import OntologyError, OntologyRegistry, Pack, PropertyUpdateDef
from context_graph.domain.pack_bundle import PROCESSING_PROVIDERS, resolve_bundle
from context_graph.domain.pack_expressions import Scope
from context_graph.domain.pack_projection import PackProjector
from context_graph.domain.pack_properties import (
    PropertyUpdateError,
    coerce_property,
    property_action,
)
from context_graph.domain.projection import event_to_node
from context_graph.ontology import load_registry
from context_graph.ports.pack_graph import NodeRef
from context_graph.worker.pack_projection import apply_plan
from tests.fixtures.events import make_event

FIXTURES = Path("tests/fixtures/pack_contracts")


def raw():
    return yaml.safe_load((FIXTURES / "propertylab.pack.yaml").read_text())


def registry(data=None):
    return OntologyRegistry(
        [
            load_registry([], builtin_packs=[]).pack("core"),
            Pack.model_validate(raw() if data is None else data),
        ]
    )


def plan(payload, kind="propertylab.sample.updated", schema=None, event=None):
    schema = schema or registry()
    event = event or make_event(
        event_id=uuid4(), event_type=kind, occurred_at=datetime(2026, 10, 8, tzinfo=UTC)
    )
    return PackProjector(schema, frozenset()).plan(event, {"payload": payload})


@pytest.mark.asyncio
async def test_actual_pack_missing_preserves_and_null_clears_with_other_sets():
    graph = MemoryGraphStore()
    identity = {"facility": "west", "sample_id": "S-7"}
    ref = NodeRef("Sample", "Sample:west|S-7")
    events = [
        make_event(
            event_type="propertylab.sample.updated",
            global_position=f"{i}-0",
            occurred_at=datetime(2026, 10, 8, tzinfo=UTC),
        )
        for i in range(1, 4)
    ]
    for event in events:
        await graph.merge_event_node(event_to_node(event))
    await apply_plan(
        graph,
        plan(
            {**identity, "description": "old", "reading": 1, "names": ["one", "two"]},
            event=events[0],
        ),
        100,
    )
    await apply_plan(graph, plan({**identity, "reading": 2}, event=events[1]), 100)
    stored = (await graph.get_nodes([ref]))[ref]
    assert stored["description"] == "old" and stored["reading"] == 2
    assert stored["names"] == ["one", "two"]
    clearing = plan({**identity, "description": None, "names": None, "reading": 3}, event=events[2])
    assert clearing.nodes[0].remove_properties == ("description", "names")
    await apply_plan(graph, clearing, 100)
    stored = (await graph.get_nodes([ref]))[ref]
    assert "description" not in stored and "names" not in stored and stored["reading"] == 3
    assert stored["sample_id"] == "S-7"
    assert len(graph.edges) == 3  # each accepted observation keeps its evidence


@pytest.mark.asyncio
async def test_gap_zip_preserves_original_indexes_and_whole_list_broadcast():
    result = plan(
        {
            "facility": "west",
            "ids": ["A", "", "C"],
            "rows": [{"description": "first"}, {}, {"description": "third"}],
            "names": ["one", "two", "three"],
        },
        "propertylab.samples.updated",
    )
    graph = MemoryGraphStore()
    await apply_plan(graph, result, 100)
    nodes = await graph.get_nodes(
        [NodeRef("Sample", "Sample:west|A"), NodeRef("Sample", "Sample:west|C")]
    )
    assert [node["description"] for node in nodes.values()] == ["first", "third"]
    assert all(node["names"] == ["one", "two", "three"] for node in nodes.values())


@pytest.mark.asyncio
async def test_edge_explicit_clear_survives_planning_and_application():
    graph = MemoryGraphStore()
    payload = {"facility": "west", "from_id": "A", "to_id": "B", "label": "old"}
    kind = "propertylab.samples.linked"
    await apply_plan(graph, plan(payload, kind), 100)
    await apply_plan(graph, plan({**payload, "label": None}, kind), 100)
    assert next(iter(graph.edges.values())) == {"source_trust": "untrusted"}


@pytest.mark.parametrize(
    "payload,reason",
    [
        ({"reading": "SECRET-invalid"}, "invalid_value"),
        ({"names": ["one", None]}, "invalid_value"),
        ({"description": {"accident": "object"}}, "invalid_value"),
    ],
)
def test_runtime_invalid_values_refuse_instead_of_silent_coercion(payload, reason):
    with pytest.raises(PropertyUpdateError) as error:
        plan({"facility": "west", "sample_id": "A", **payload})
    assert error.value.reason == reason
    assert "SECRET" not in str(error.value)


@pytest.mark.parametrize(
    "value",
    ["sha256($.description)", "$.description + 'suffix'", "map(sha256($.description), {'x': y})"],
)
def test_unsupported_strict_ast_refuses_at_load(value):
    data = raw()
    data["projection"][0]["upsert"][0]["set"]["description"]["value"] = value
    with pytest.raises(ValidationError):
        Pack.model_validate(data)


def test_explicit_null_canonical_roundtrip_and_missing_value_refusal():
    data = raw()
    data["projection"][0]["upsert"][0]["set"]["description"]["value"] = None
    pack = Pack.model_validate(data)
    canonical = pack.canonical_json()
    assert (
        json.loads(canonical)["projection"][0]["upsert"][0]["set"]["description"]["value"] is None
    )
    assert Pack.model_validate_json(canonical).canonical_json() == canonical
    del data["projection"][0]["upsert"][0]["set"]["description"]["value"]
    with pytest.raises(ValidationError):
        Pack.model_validate(data)


@pytest.mark.parametrize("field", ["sample_id", "source_trust", "updated_at"])
def test_strict_protected_set_is_load_refusal(field):
    data = raw()
    data["projection"][0]["upsert"][0]["set"][field] = {"value": "bad"}
    with pytest.raises(OntologyError, match="protected"):
        registry(data)


def test_missing_capability_or_unavailable_engine_refuses():
    data = raw()
    data["processing"]["requires"] = []
    with pytest.raises(OntologyError, match="pack.properties.v1"):
        registry(data)
    with pytest.raises(OntologyError, match="unsupported"):
        resolve_bundle(
            registry(), {k: v for k, v in PROCESSING_PROVIDERS.items() if k != "pack.properties.v1"}
        )
    bundle = resolve_bundle(registry())
    assert not bundle.enables("pack.properties.v1")  # requirement, not another worker


@pytest.mark.parametrize(
    "payload,expected", [({}, "preserve"), ({"x": None}, "clear"), ({"x": ""}, "set")]
)
def test_direct_path_presence_actions(payload, expected):
    definition = PropertyUpdateDef(value="$.x", on_null="clear")
    action, value = property_action(definition, Scope(payload, {}), "string")
    assert action == expected


@pytest.mark.parametrize(
    "payload,reason", [({"x": 2}, "invalid_path"), ({"x": [1]}, "invalid_path")]
)
def test_wrong_container_is_not_missing(payload, reason):
    with pytest.raises(PropertyUpdateError) as error:
        property_action(PropertyUpdateDef(value="$.x.y"), Scope(payload, {}), "string")
    assert error.value.reason == reason


def test_zip_shape_and_scalar_target_refusals():
    definition = PropertyUpdateDef(value="$.x", select="zip")
    with pytest.raises(PropertyUpdateError, match="zip_requires_fanout"):
        property_action(definition, Scope({"x": ["a"]}, {}), "string")
    with pytest.raises(PropertyUpdateError, match="zip_shape_mismatch"):
        property_action(definition, Scope({"x": ["a"]}, {}), "string", fanned=True, count=2)


@pytest.mark.parametrize(
    "value,spec,expected",
    [
        (0, "int", 0),
        (False, "bool", False),
        ("", "string", ""),
        ([], "list<string>", []),
        ("7", "int", 7),
        ({"nested": None}, "json", {"nested": None}),
    ],
)
def test_strict_real_values_are_not_clear_requests(value, spec, expected):
    assert coerce_property(value, spec) == expected


@pytest.mark.parametrize(
    "value,spec",
    [
        (True, "int"),
        (True, "float"),
        (2**63, "int"),
        (float("nan"), "float"),
        ({}, "string"),
        ("2026-10-08T00:00:00", "datetime"),
        ("one", "list<string>"),
        ({"bad": float("inf")}, "json"),
    ],
)
def test_strict_conversion_boundaries_refuse(value, spec):
    with pytest.raises(PropertyUpdateError):
        coerce_property(value, spec)


def test_nested_wildcard_cells_refuse_null_members_but_keep_nesting():
    definition = PropertyUpdateDef(value="$.rows[*].items[*]")
    with pytest.raises(PropertyUpdateError, match="invalid_list_member"):
        property_action(definition, Scope({"rows": [{"items": ["a", None]}]}, {}), "json")
    assert property_action(
        definition, Scope({"rows": [{"items": ["a"]}, {"items": []}]}, {}), "json"
    ) == ("set", [["a"], []])


def test_nested_missing_and_null_policies_remain_distinct():
    definition = PropertyUpdateDef(value="$.parent.child", on_missing="refuse", on_null="clear")
    with pytest.raises(PropertyUpdateError, match="missing_value"):
        property_action(definition, Scope({}, {}), "string")
    assert property_action(definition, Scope({"parent": None}, {}), "string") == ("clear", None)
    with pytest.raises(PropertyUpdateError, match="missing_value"):
        property_action(definition, Scope({"parent": {}}, {}), "string")


def test_foreign_strict_writer_refuses_even_with_schema_dependency():
    owner = Pack.model_validate(raw())
    observer = Pack.model_validate(
        {
            "pack": {"name": "observer", "version": "0.1.0", "requires": ["propertylab>=0.1"]},
            "processing": {"requires": ["pack.properties.v1"]},
            "projection": [
                {
                    "event": "propertylab:propertylab.sample.updated",
                    "upsert": [
                        {
                            "type": "propertylab:Sample",
                            "key": {"facility": "$.facility", "sample_id": "$.sample_id"},
                            "set": {"description": {"value": None, "on_null": "clear"}},
                        }
                    ],
                }
            ],
        }
    )
    with pytest.raises(OntologyError, match="foreign"):
        OntologyRegistry([load_registry([], builtin_packs=[]).pack("core"), owner, observer])


def test_late_subscriber_failure_discards_combined_event_plan():
    owner = Pack.model_validate(raw())
    observer = Pack.model_validate(
        {
            "pack": {"name": "observer", "version": "0.1.0", "requires": ["propertylab>=0.1"]},
            "processing": {"requires": ["pack.properties.v1"]},
            "types": {
                "nodes": {
                    "Observation": {
                        "key": ["sample_id"],
                        "properties": {"sample_id": "string", "score": "int"},
                    }
                }
            },
            "projection": [
                {
                    "event": "propertylab:propertylab.sample.updated",
                    "upsert": [
                        {
                            "type": "Observation",
                            "key": {"sample_id": "$.sample_id"},
                            "set": {"score": {"value": "$.description"}},
                        }
                    ],
                }
            ],
        }
    )
    composed = OntologyRegistry([load_registry([], builtin_packs=[]).pack("core"), owner, observer])
    with pytest.raises(PropertyUpdateError, match="invalid_value"):
        plan({"facility": "west", "sample_id": "A", "description": "not-a-score"}, schema=composed)


def test_required_edge_field_cannot_be_cleared():
    data = raw()
    data["types"]["edges"]["OBSERVED"]["requires"] = ["label"]
    with pytest.raises(OntologyError, match="cannot clear required"):
        registry(data)
