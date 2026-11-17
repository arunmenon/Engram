"""Acceptance identity, canonical request semantics, and contract/epoch separation."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from context_graph.domain.event_acceptance import (
    EventAcceptance,
    EventIdentityConflictError,
    EventInterpretationError,
    request_fingerprint,
    stamp_acceptance,
)
from context_graph.domain.models import Event
from context_graph.tenancy import (
    Principal,
    TenantAuthorizationError,
    TenantCatalog,
    TenantConfigurationError,
)
from tests.unit.test_tenant_catalog import bind, grant


def event():
    return Event(
        event_id=UUID("00000000-0000-4000-8000-000000000001"),
        event_type="tool.execute",
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        session_id="session",
        agent_id="agent",
        trace_id="trace",
        payload_ref="fixture:1",
    )


def context(binding=None, source="producer", credential="credential"):
    return (binding or bind()).admission_context(
        Principal(credential, "a", frozenset({"api"}), source_id=source)
    )


def test_canonical_object_order_utc_normalization_and_server_position_do_not_change_identity():
    original = event()
    equivalent = Event.model_validate(
        {
            **original.model_dump(),
            "occurred_at": datetime(
                2026, 1, 1, 5, 30, tzinfo=timezone(timedelta(hours=5, minutes=30))
            ),
            "global_position": "server-assigned",
        }
    )
    assert request_fingerprint(original, {"b": 2, "a": [1, 2]}) == request_fingerprint(
        equivalent, {"a": [1, 2], "b": 2}
    )


@pytest.mark.parametrize(
    "left,right",
    [
        (None, {}),
        ({"x": 1}, {"x": 1.0}),
        ({"x": False}, {"x": 0}),
        ({"x": -0.0}, {"x": 0.0}),
        ({"x": [1, 2]}, {"x": [2, 1]}),
        ({"x": {"y": 1}}, {"x": {"y": 2}}),
    ],
)
def test_semantic_payload_differences_change_request_digest(left, right):
    assert request_fingerprint(event(), left) != request_fingerprint(event(), right)


@pytest.mark.parametrize(
    "field,value",
    [
        ("trace_id", "another"),
        ("agent_id", "another"),
        ("session_id", "another"),
        ("payload_ref", "another"),
        ("event_id", UUID("00000000-0000-4000-8000-000000000002")),
        ("event_type", "agent.invoke"),
        ("tool_name", "another"),
        ("schema_version", 2),
        ("importance_hint", 9),
        ("occurred_at", datetime(2026, 1, 2, tzinfo=UTC)),
        ("ended_at", datetime(2026, 1, 2, tzinfo=UTC)),
    ],
)
def test_every_semantic_event_field_affects_request_identity(field, value):
    assert request_fingerprint(event(), None) != request_fingerprint(
        event().model_copy(update={field: value}), None
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"x": float("nan")},
        {"x": float("inf")},
        {"x": b"bytes"},
        {1: "non-string key"},
        {"x": (1, 2)},
        {"x": "\ud800"},
        [],
        False,
        "text",
    ],
)
def test_non_lossless_or_non_json_payloads_are_rejected(payload):
    with pytest.raises(ValueError):
        request_fingerprint(event(), payload)


def test_payload_cycles_rejected_without_hanging():
    payload = {}
    payload["cycle"] = payload
    with pytest.raises(ValueError, match="cycles"):
        request_fingerprint(event(), payload)


def test_immutable_acceptance_survives_caller_payload_mutation_and_credential_rotation():
    payload = {"nested": {"value": 1}}
    receipt = stamp_acceptance(context(), event(), payload)
    original = receipt.model_dump()
    receipt.require_same_request(context(credential="rotated"), event(), {"nested": {"value": 1}})
    assert receipt.model_dump() == original
    payload["nested"]["value"] = 2
    with pytest.raises(EventIdentityConflictError):
        receipt.require_same_request(context(), event(), payload)
    with pytest.raises(ValidationError):
        receipt.source_id = "changed"


def test_other_producer_conflicts_even_with_identical_content():
    receipt = stamp_acceptance(context(), event(), None)
    with pytest.raises(EventIdentityConflictError):
        receipt.require_same_request(context(source="another"), event(), None)


def test_epoch_only_advance_allows_pending_processing_and_identical_retry():
    old = bind()
    new = replace(old, epoch=2)
    receipt = stamp_acceptance(context(old), event(), None)
    receipt.require_interpretation(new)
    receipt.require_same_request(context(new), event(), None)
    assert receipt.accepted_epoch == 1


@pytest.mark.parametrize(
    "changes",
    [{"epoch": 0}, {"engine_revision": "changed"}, {"tenant_id": "b"}, {"binding_id": "changed"}],
)
def test_unknown_or_future_interpretation_refuses_processing(changes):
    old = bind()
    receipt = stamp_acceptance(context(old), event(), None)
    from types import SimpleNamespace

    authority = SimpleNamespace(
        **{
            key: getattr(old, key)
            for key in (
                "tenant_id",
                "database_resource",
                "binding_id",
                "epoch",
                "bundle_digest",
                "engine_revision",
            )
        }
    )
    for key, value in changes.items():
        setattr(authority, key, value)
    with pytest.raises(EventInterpretationError):
        receipt.require_interpretation(authority)


@pytest.mark.parametrize("version", [True, 1.0, "1", 2, None])
def test_malformed_envelope_version_is_not_coerced(version):
    receipt = stamp_acceptance(context(), event(), None).model_dump()
    with pytest.raises(ValidationError):
        EventAcceptance.model_validate({**receipt, "envelope_version": version})


def test_catalog_requires_explicit_source_and_rotation_keeps_it():
    from context_graph.tenancy import CredentialGrant

    missing = CredentialGrant.from_token(Principal("credential", "a", frozenset({"api"})), "x" * 32)
    with pytest.raises(TenantConfigurationError, match="source_id"):
        TenantCatalog([bind()], [missing])
    catalog = TenantCatalog(
        [bind()], [grant("a"), grant("a", token="r" * 32, credential_id="rotated")]
    )
    assert catalog.authenticate("a" * 32).source_id == catalog.authenticate("r" * 32).source_id


@pytest.mark.parametrize(
    "principal",
    [
        Principal("c", "b", frozenset({"api"}), source_id="p"),
        Principal("c", "a", frozenset({"admin"}), source_id="p"),
        Principal("c", "a", frozenset({"api"})),
    ],
)
def test_admission_context_cannot_invent_identity_for_unbound_or_unauthorized_principal(principal):
    with pytest.raises(TenantAuthorizationError):
        bind().admission_context(principal)


def test_json_v1_encoder_golden_fixture():
    assert request_fingerprint(event(), {"text": "é", "negative": -0.0}) == (
        "sha256:json-v1:07a7443ee01cd779b8549a43c26bd0b9b531e11389b29cb40896392a92230a64"
    )


def test_missing_envelope_version_is_not_silently_assumed():
    receipt = stamp_acceptance(context(), event(), None).model_dump()
    del receipt["envelope_version"]
    with pytest.raises(ValidationError):
        EventAcceptance.model_validate(receipt)
