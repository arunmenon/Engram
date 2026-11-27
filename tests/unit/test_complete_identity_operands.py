"""Incomplete identity operands cannot be hidden by text concatenation."""

import pytest

from context_graph.domain.ontology import OntologyRegistry, Pack
from context_graph.domain.pack_projection import PackProjector
from tests.fixtures.events import make_event
from tests.unit.test_pack_versioning import CORE


def registry(expression="$.merchant + ':' + $.payment_id"):
    return OntologyRegistry(
        [
            CORE,
            Pack.model_validate(
                {
                    "pack": {"name": "identitylab", "version": "1.0.0", "requires": ["core>=1.1"]},
                    "types": {
                        "nodes": {
                            "Payment": {
                                "key": ["id"],
                                "properties": {"id": "string", "description": "string"},
                            },
                        }
                    },
                    "events": {"identitylab.observed": {}},
                    "projection": [
                        {
                            "event": "identitylab.observed",
                            "upsert": [
                                {
                                    "type": "Payment",
                                    "key": {"id": expression},
                                    "set": {"description": "$.merchant + ':' + $.payment_id"},
                                },
                            ],
                        }
                    ],
                }
            ),
        ]
    )


def plan(payload, expression="$.merchant + ':' + $.payment_id"):
    event = make_event(event_type="identitylab.observed")
    return PackProjector(registry(expression), frozenset()).plan(event, {"payload": payload})


def test_missing_composite_operand_refuses_instead_of_creating_merchant_only_identity():
    with pytest.raises(ValueError, match="identity_operand"):
        plan({"merchant": "M1"})


@pytest.mark.parametrize(
    "payload",
    [
        {"merchant": "M1", "payment_id": None},
        {"merchant": "M1", "payment_id": ""},
        {"payment_id": "P1"},
    ],
)
def test_null_empty_or_missing_source_operand_is_not_hidden(payload):
    with pytest.raises(ValueError, match="identity_operand"):
        plan(payload)


@pytest.mark.parametrize(
    "expression",
    [
        "sha256($.merchant + ':' + $.payment_id)",
        "sha256($.payment_id)",
        "match($.payment_id, 'P')",
        "regex($.payment_id, '(.*)')",
        "map($.payment_id, {'P1': 'one'})",
        "regex_all($.payment_id, '(.*)') + ':suffix'",
    ],
)
def test_missing_input_produces_no_key_for_these_transform_cases(expression):
    if "+" in expression:
        with pytest.raises(ValueError, match="identity_operand"):
            plan({"merchant": "M1"}, expression)
    else:
        assert plan({"merchant": "M1"}, expression).empty


@pytest.mark.parametrize(
    "value,expected",
    [
        ("P1", "Payment:M1:P1"),
        (0, "Payment:M1:0"),
        (False, "Payment:M1:False"),
    ],
)
def test_complete_zero_and_false_identity_operands_are_preserved(value, expected):
    result = plan({"merchant": "M1", "payment_id": value})
    assert [n.ref.key for n in result.nodes] == [expected]


def test_explicit_empty_literal_is_not_a_missing_business_operand():
    result = plan({"payment_id": "P1"}, "$.payment_id + '' + ':fixed'")
    assert [n.ref.key for n in result.nodes] == ["Payment:P1:fixed"]


def test_legacy_property_text_still_treats_absent_operand_as_empty():
    result = plan({"merchant": "M1"}, "$.merchant")
    assert result.nodes[0].ref.key == "Payment:M1"
    assert result.nodes[0].properties["description"] == "M1:"


def test_invalid_parent_path_cannot_become_a_partial_composite():
    with pytest.raises(ValueError, match="identity_operand"):
        plan({"merchant": "M1", "payment": 42}, "$.merchant + ':' + $.payment.id")


def test_empty_fanout_and_original_position_filtering_still_work():
    data = registry("each($.ids)").pack("identitylab").model_dump(by_alias=True)
    data["projection"][0]["upsert"][0]["set"]["description"] = "$.descriptions"
    schema = OntologyRegistry([CORE, Pack.model_validate(data)])
    projector = PackProjector(schema, frozenset())
    event = make_event(event_type="identitylab.observed")
    assert projector.plan(event, {"payload": {"ids": []}}).empty
    result = projector.plan(
        event,
        {
            "payload": {
                "ids": ["P1", "", None, "P3"],
                "descriptions": ["one", "two", "three", "four"],
            }
        },
    )
    assert [(n.ref.key, n.properties["description"]) for n in result.nodes] == [
        ("Payment:P1", "one"),
        ("Payment:P3", "four"),
    ]


@pytest.mark.parametrize("missing", [None, ""])
def test_scalar_transform_cannot_drop_missing_list_cells_to_form_an_id(missing):
    assert plan({"ids": ["P1", missing, "P3"]}, "sha256($.ids)").empty


async def test_invalid_late_part_cannot_apply_partial_event_or_change_existing_record():
    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.ports.pack_graph import NodeRef, NodeWrite
    from context_graph.worker.pack_projection import apply_plan

    data = registry("root").pack("identitylab").model_dump(by_alias=True)
    data["types"]["edges"] = {"IDENTITY_LINK": {"from": ["Payment"], "to": ["Payment"]}}
    data["projection"][0]["edges"] = [
        {
            "type": "IDENTITY_LINK",
            "from": {"type": "Payment", "key": {"id": "root"}},
            "to": {"node_id": "$.node_prefix + $.merchant + ':' + $.payment_id"},
        }
    ]
    schema = OntologyRegistry([CORE, Pack.model_validate(data)])
    graph, ref = MemoryGraphStore(), NodeRef("Payment", "Payment:root")
    await graph.upsert_nodes([NodeWrite(ref, {"id": "root", "description": "original"})])
    before = await graph.get_nodes([ref])
    event = make_event(event_type="identitylab.observed")
    with pytest.raises(ValueError, match="identity_operand") as error:
        result = PackProjector(schema, frozenset()).plan(
            event, {"payload": {"node_prefix": "Payment:", "merchant": "sensitive"}}
        )
        await apply_plan(graph, result, 100)
    assert "sensitive" not in str(error.value)
    assert await graph.get_nodes([ref]) == before
    assert len(await graph.find_nodes("Payment", {}, 10)) == 1
    assert not await graph.neighbors([ref], ["IDENTITY_LINK"], "out", 10)


def test_transition_identity_uses_the_same_complete_operand_rule():
    data = registry().pack("identitylab").model_dump(by_alias=True)
    node = data["types"]["nodes"]["Payment"]
    node["interfaces"] = ["Lifecycled"]
    node["lifecycle"] = {"initial": "pending", "states": ["pending", "paid"]}
    data["events"]["identitylab.paid"] = {}
    data["projection"].append(
        {
            "event": "identitylab.paid",
            "transition": {
                "type": "Payment",
                "to": "paid",
                "key": {"id": "$.merchant + ':' + $.payment_id"},
            },
        }
    )
    schema = OntologyRegistry([CORE, Pack.model_validate(data)])
    event = make_event(event_type="identitylab.paid")
    with pytest.raises(ValueError, match="identity_operand"):
        PackProjector(schema, frozenset()).plan(event, {"payload": {"merchant": "M1"}})


def test_pattern_search_text_may_have_optional_fragments_before_key_extraction():
    result = plan({"title": "Payment P7"}, "regex($.title + ' ' + $.body, '(P[0-9]+)')")
    assert [node.ref.key for node in result.nodes] == ["Payment:P7"]


def test_invalid_identity_expression_fails_pack_validation_before_planning():
    from context_graph.domain.ontology import OntologyError

    with pytest.raises(OntologyError):
        registry("sha256(")


def test_pattern_search_text_list_keeps_matches_from_nonempty_cells():
    result = plan(
        {"messages": ["fix ABC-1", "", "see ABC-2"]},
        "regex_all($.messages[*], '([A-Z]+-[0-9]+)')",
    )
    assert [node.ref.key for node in result.nodes] == ["Payment:ABC-1", "Payment:ABC-2"]


@pytest.mark.parametrize("expression", ["'pay-' + $.payment_id", "prefix:$event.event_id"])
def test_unrecognized_literal_led_identity_expression_is_rejected(expression):
    from context_graph.domain.ontology import OntologyError

    with pytest.raises(OntologyError, match="identity expression"):
        registry(expression)


def test_partial_composite_lookup_never_selects_a_merchant_only_record():
    data = registry("root").pack("identitylab").model_dump(by_alias=True)
    data["types"]["edges"] = {"IDENTITY_LINK": {"from": ["Payment"], "to": ["Payment"]}}
    data["projection"][0]["edges"] = [
        {
            "type": "IDENTITY_LINK",
            "from": {"type": "Payment", "key": {"id": "root"}},
            "to": {"type": "Payment", "match": {"description": "$.merchant + ':' + $.parent_id"}},
        }
    ]
    schema = OntologyRegistry([CORE, Pack.model_validate(data)])
    event = make_event(event_type="identitylab.observed")
    result = PackProjector(schema, frozenset()).plan(event, {"payload": {"merchant": "M1"}})
    assert not result.lookups
    assert any("lookup_identity_operand" in r for r in result.rejected)


def test_pattern_capture_is_defined_by_the_pattern_not_inferred_business_components():
    # Search text retains legacy semantics. A permissive pattern is not an
    # engine proof that its capture contains every domain-required ID field.
    result = plan({"merchant": "M1"}, "regex($.merchant + ':' + $.payment_id, '(.+)')")
    assert [node.ref.key for node in result.nodes] == ["Payment:M1:"]


@pytest.mark.parametrize("position", ["node_id", "transition"])
def test_literal_led_identity_validation_covers_other_reference_positions(position):
    from context_graph.domain.ontology import OntologyError

    data = registry("root").pack("identitylab").model_dump(by_alias=True)
    if position == "node_id":
        data["types"]["edges"] = {"IDENTITY_LINK": {"from": ["Payment"], "to": ["Payment"]}}
        data["projection"][0]["edges"] = [
            {
                "type": "IDENTITY_LINK",
                "from": {"type": "Payment", "key": {"id": "root"}},
                "to": {"node_id": "'Payment:' + $.payment_id"},
            }
        ]
    else:
        data["types"]["nodes"]["Payment"].update(
            interfaces=["Lifecycled"],
            lifecycle={"initial": "pending", "states": ["pending", "paid"]},
        )
        data["projection"][0]["transition"] = {
            "type": "Payment",
            "to": "paid",
            "key": {"id": "'pay-' + $.payment_id"},
        }
    with pytest.raises(OntologyError, match="identity expression"):
        OntologyRegistry([CORE, Pack.model_validate(data)])


@pytest.mark.parametrize("payload", [{"ids": ["P1"]}, {"ids": ["P1"], "text": ""}])
def test_absent_pattern_fanout_keeps_unequal_length_refusal(payload):
    from context_graph.domain.pack_projection import ProjectionExpansionError

    data = registry().pack("identitylab").model_dump(by_alias=True)
    node = data["types"]["nodes"]["Payment"]
    node["key"] = ["id", "description"]
    data["projection"][0]["upsert"][0]["key"] = {
        "id": "$.ids[*]",
        "description": "regex_all($.text, '([A-Z]+-[0-9]+)')",
    }
    schema = OntologyRegistry([CORE, Pack.model_validate(data)])
    event = make_event(event_type="identitylab.observed")
    with pytest.raises(ProjectionExpansionError, match="unequal_key_lengths"):
        PackProjector(schema, frozenset()).plan(event, {"payload": payload})


def test_literal_dollar_dot_without_a_path_name_is_still_an_explicit_id():
    result = plan({}, "US$.50")
    assert [node.ref.key for node in result.nodes] == ["Payment:US$.50"]
