"""Common ingress rejects lost payloads and spoofed authority before store writes."""

import json

import pytest

from context_graph.api.ingest import check_events
from tests.unit.test_event_acceptance import event


@pytest.mark.parametrize(
    "field,value",
    [
        ("acceptance", {"tenant_id": "foreign"}),
        ("tenant_id", "foreign"),
        ("source_id", "claimed"),
        ("binding_id", "claimed"),
        ("bundle_digest", "claimed"),
        ("accepted_epoch", 9),
        ("global_position", "supplied"),
        ("payload", []),
        ("payload", False),
        ("payload", "lost text"),
    ],
)
@pytest.mark.parametrize("route", ["single", "batch", "import"])
def test_every_normalized_http_ingress_refuses_before_any_write(
    test_client, in_memory_event_store, field, value, route
):
    raw = {**event().model_dump(mode="json"), field: value}
    if route == "single":
        response = test_client.post("/v1/events", json=raw)
        assert response.status_code == 422
    elif route == "batch":
        response = test_client.post("/v1/events/batch", json={"events": [raw]})
        assert response.json()["accepted"] == 0
    else:
        from context_graph.api.routes.events import import_router

        test_client.app.include_router(import_router, prefix="/v1")
        response = test_client.post("/v1/events/import", content=json.dumps(raw) + "\n")
        assert '"status":"rejected"' in response.text
    assert not in_memory_event_store._events
    assert field in response.text


@pytest.mark.parametrize(
    "payload", [None, {}, {"source_id": "untrusted domain data", "acceptance": {"x": 1}}]
)
def test_domain_payload_names_are_not_confused_with_authority(payload):
    checked = check_events(
        [{**event().model_dump(mode="json"), "payload": payload}], lambda event: None
    )
    assert len(checked.events) == 1 and checked.payloads == [payload]
