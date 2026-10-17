"""Smoke acceptance oracles with local doubles, never customer cloud proof."""

import json
from unittest.mock import MagicMock

import pytest

from context_graph import deployment as operator
from context_graph import deployment_verify as smoke
from tests.unit.test_deployment import prepared  # noqa: F401


@pytest.mark.parametrize(
    "failure", [None, "source", "receipt", "replay", "conflict", "tenant", "storage", "enrichment"]
)
def test_smoke_requires_each_independent_contract(prepared, monkeypatch, tmp_path, failure):  # noqa: F811
    deployment = operator.Deployment(prepared[1])
    monkeypatch.setenv("CUSTOMER_A_TOKEN", "private-producer-token-1234")
    monkeypatch.setattr(smoke, "check_binding", lambda _: {"pending": 0, "dead_letters": 0})
    writes = []

    def request(base, token, path, body, *, hint=None):
        if path.endswith("subgraph"):
            eid = writes[0]["event_id"]
            return 200, {
                "nodes": {
                    eid: {
                        "node_type": "Event",
                        "attributes": {
                            "importance_score": 9,
                            "keywords": [] if failure == "enrichment" else ["observation", "input"],
                        },
                        "provenance": {
                            "event_id": eid,
                            "global_position": "42",
                            "source": "redis" if failure == "source" else "spanner",
                        },
                    }
                }
            }
        if hint:
            return (201 if failure == "tenant" else 401), {}
        if writes and body["payload"] != writes[0]["payload"]:
            return (201 if failure == "conflict" else 409), {}
        writes.append(body)
        status = "created" if len(writes) == 1 else "duplicate"
        if failure == "receipt" and len(writes) == 1:
            status = "duplicate"
        if failure == "replay" and len(writes) == 2:
            status = "created"
        return 201, {"status": status, "global_position": "42"}

    async def storage(*_):
        return {"ready": failure != "storage", "ledger_matches": True}

    monkeypatch.setattr(smoke, "request", request)
    monkeypatch.setattr(smoke, "storage_proof", storage)
    output = tmp_path / "evidence.json"
    args = (
        deployment,
        "customer-a",
        "https://customer.example",
        deployment.bindings[0].database_resource,
        output,
    )
    if failure:
        with pytest.raises(operator.DeploymentError):
            smoke.verify(*args, timeout=0)
    else:
        smoke.verify(*args, timeout=0)
    report = json.loads(output.read_text())
    assert report["state"] == ("failed" if failure else "passed-core-deployment-proof")
    assert "private-producer-token" not in output.read_text()
    assert output.stat().st_mode & 0o777 == 0o600


def test_smoke_rejects_redirect_without_forwarding_bearer():
    handler = smoke._NoRedirect()
    assert (
        handler.redirect_request(None, None, 302, "redirect", {}, "https://other.example") is None
    )


def test_require_is_explicit_not_an_optimizable_assert():
    with pytest.raises(operator.DeploymentError, match="required"):
        smoke.require(False, "required")


@pytest.mark.parametrize(
    "origin", ["https://user:secret@example.com", "https://example.com/path", "file:///tmp/service"]
)
def test_bad_origin_cannot_contact_service(origin, tmp_path):
    deployment = MagicMock()
    with pytest.raises(operator.DeploymentError, match="origin"):
        smoke.verify(deployment, "a", origin, "target", tmp_path / "evidence.json")
    deployment.binding.assert_not_called()


@pytest.mark.parametrize("stored_position", ["42", "wrong-position"])
@pytest.mark.asyncio
async def test_storage_proof_ties_receipt_to_ledger_and_closes(
    prepared, monkeypatch, stored_position  # noqa: F811
):
    from unittest.mock import AsyncMock

    binding = operator.Deployment(prepared[1]).bindings[0]
    event = {"event_id": "probe", "occurred_at": "2026-10-17T00:00:00+00:00"}
    stores = MagicMock()
    stores.close = AsyncMock()
    stores.event_log.get_documents = AsyncMock(
        return_value=[{**event, "global_position": stored_position}]
    )
    stores.subscription.return_value.lag = AsyncMock(return_value=0)
    from context_graph.worker.__main__ import CONSUMER_SUBSCRIPTIONS

    groups = [
        getattr(binding.settings().consumer, field) for field, _ in CONSUMER_SUBSCRIPTIONS.values()
    ]
    monkeypatch.setattr(
        "context_graph.adapters.registry.open_stores", AsyncMock(return_value=stores)
    )
    monkeypatch.setattr(
        smoke,
        "check_binding",
        lambda _: {"registered_groups": groups, "pending": 0, "dead_letters": 0},
    )
    result = await smoke.storage_proof(binding, event, "42")
    assert result["ready"] is (stored_position == "42")
    assert len(result["lags"]) == 5
    stores.close.assert_awaited_once()
