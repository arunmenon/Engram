"""Slice1 prototype: contracts validate without coercing or changing payloads."""

import copy

import pytest
from pydantic import ValidationError

from context_graph.domain.ontology import EventDef
from context_graph.domain.pack_contracts import PayloadContract


def contract(**changes):
    declaration = {
        "version": 1,
        "properties": {
            "repo": {"type": "string", "required": True, "min_length": 1},
            "number": {"type": "integer", "required": True},
            "description": {"type": "string", "nullable": True},
            "files": {"type": "array", "items": {"type": "string"}, "max_length": 3},
            "metadata": {
                "type": "object",
                "properties": {"active": {"type": "boolean", "required": True}},
            },
        },
    }
    declaration.update(changes)
    return PayloadContract.model_validate(declaration)


def test_valid_payload_is_not_changed_or_defaulted():
    payload = {"repo": "payments", "number": 7, "files": ["a.py"], "extra": {"nested": 1}}
    before = copy.deepcopy(payload)
    contract().validate_payload(payload)
    assert payload == before
    assert "description" not in payload


@pytest.mark.parametrize(
    "change",
    [
        {"number": "7"},
        {"number": True},
        {"repo": ""},
        {"repo": None},
        {"files": [1]},
        {"files": ["a", "b", "c", "d"]},
        {"metadata": {"active": "true"}},
        {"metadata": {}},
    ],
)
def test_invalid_fields_do_not_coerce(change):
    with pytest.raises(ValidationError):
        contract().validate_payload({"repo": "payments", "number": 7, **change})


def test_required_missing_and_explicit_nullable():
    with pytest.raises(ValidationError):
        contract().validate_payload({"repo": "payments"})
    contract().validate_payload({"repo": "payments", "number": 7, "description": None})


def test_explicit_extra_policy():
    with pytest.raises(ValidationError):
        contract(additional_fields="forbid").validate_payload(
            {"repo": "a", "number": 1, "extra": 1}
        )


@pytest.mark.parametrize(
    "declaration",
    [
        {"version": 2},
        {"properties": {"x": {"type": "array"}}},
        {"properties": {"x": {"type": "string", "items": {"type": "string"}}}},
        {"properties": {"x": {"type": "integer", "min_length": 1}}},
        {"properties": {"x": {"type": "string", "min_length": 4, "max_length": 2}}},
        {"properties": {"x": {"type": "string", "$ref": "https://example.com/schema"}}},
    ],
)
def test_invalid_declarations_fail_at_load(declaration):
    with pytest.raises(ValidationError):
        PayloadContract.model_validate(declaration)


def test_contract_depth_is_bounded():
    field = {"type": "string"}
    for _ in range(17):
        field = {"type": "array", "items": field}
    with pytest.raises(ValidationError, match="depth"):
        PayloadContract.model_validate({"properties": {"nested": field}})


def test_contract_field_count_is_bounded():
    with pytest.raises(ValidationError, match="256"):
        PayloadContract.model_validate(
            {"properties": {f"f{i}": {"type": "string"} for i in range(257)}}
        )


def test_pack_event_contract_is_optional_for_legacy_declarations():
    assert EventDef().payload_contract is None
    declared = EventDef.model_validate(
        {"payload_contract": contract().model_dump(exclude_defaults=True)}
    )
    declared.payload_contract.validate_payload({"repo": "a", "number": 1})


def test_other_domain_has_no_pdlc_specific_validation():
    schema = PayloadContract.model_validate(
        {
            "properties": {
                "facility": {"type": "string", "required": True},
                "reading": {"type": "number", "required": True},
            }
        }
    )
    schema.validate_payload({"facility": "west", "reading": 1.25})
    for bad in ["1.25", True, float("nan"), float("inf")]:
        with pytest.raises(ValidationError):
            schema.validate_payload({"facility": "west", "reading": bad})


@pytest.mark.parametrize("payload", [[], None, "{}"])
def test_payload_must_be_an_object(payload):
    with pytest.raises(ValidationError):
        contract().validate_payload(payload)


def test_reserved_source_field_names_are_not_pydantic_methods():
    schema = PayloadContract.model_validate(
        {
            "properties": {
                "model_dump": {"type": "string", "required": True},
                "_private": {"type": "integer", "required": True},
            }
        }
    )
    schema.validate_payload({"model_dump": "source", "_private": 7})
    with pytest.raises(ValidationError):
        schema.validate_payload({"model_dump": "source", "_private": "7"})


def test_boolean_is_not_a_schema_version():
    with pytest.raises(ValidationError):
        PayloadContract.model_validate({"version": True})


def test_contract_full_model_dump_round_trip():
    schema = contract()
    restored = PayloadContract.model_validate(schema.model_dump())
    restored.validate_payload({"repo": "a", "number": 1})


@pytest.mark.parametrize(
    "declaration",
    [
        {"type": "string", "minimum": 1},
        {"type": "number", "minimum": 2, "maximum": 1},
        {"type": "number", "enum": ["x"]},
        {"type": "string", "enum": []},
    ],
)
def test_invalid_numeric_and_enum_declarations(declaration):
    with pytest.raises(ValidationError):
        PayloadContract.model_validate({"properties": {"value": declaration}})


def test_numeric_bounds_and_string_enum_are_strict():
    schema = PayloadContract.model_validate(
        {
            "properties": {
                "id": {"type": "integer", "required": True, "minimum": 1, "maximum": 10},
                "state": {"type": "string", "required": True, "enum": ["open", "closed"]},
            }
        }
    )
    schema.validate_payload({"id": 1, "state": "open"})
    for value in [0, 11, True, "1"]:
        with pytest.raises(ValidationError):
            schema.validate_payload({"id": value, "state": "open"})
    with pytest.raises(ValidationError):
        schema.validate_payload({"id": 1, "state": "unknown"})
