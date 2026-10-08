"""G07 harness transport checks at the public HTTP boundary, without databases."""

import hashlib
import hmac
from datetime import UTC, datetime

import httpx
import orjson
import pytest
from engram_goal03_implementation_demo import http_steps, submit_fixture
from engram_goal07_skipped_fixtures import fixtures


async def test_signed_raw_webhook_preserves_independent_oracle_and_retry_identity():
    data = fixtures("transport", start=datetime(2026, 10, 8, tzinfo=UTC))
    steps = http_steps(data)
    raw = [step for step in steps if step.get("webhook")]
    assert len(raw) == 4  # skipped, identical replay, neutral, identical replay
    first, retry = raw[:2]
    assert first["request"] == retry["request"]
    assert retry["duplicate"]
    assert first["expected_authority"] == "webhook.github"
    assert first["expected_status"] == 202
    assert first["request"]["payload"] == {
        **data["webhook_cases"][0]["expected_payload"],
        "cdevents_type": "dev.cdevents.testcaserun.skipped",
    }
    sent = []

    def handle(request):
        assert request.url.path == "/v1/webhooks/github"
        assert request.headers["x-github-event"] == "check_run"
        assert (
            request.headers["x-hub-signature-256"]
            == "sha256="
            + hmac.new(b"transport-secret", request.content, hashlib.sha256).hexdigest()
        )
        assert orjson.loads(request.content) == data["webhook_cases"][0]["body"]
        sent.append(request.content)
        return httpx.Response(202, json={"event_ids": [first["request"]["event_id"]]})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle), base_url="http://test"
    ) as client:
        await submit_fixture(client, first, "transport-secret")
        await submit_fixture(client, retry, "transport-secret")
    assert sent[0] == sent[1]


def test_retrieval_policy_rejects_missing_historical_label_and_false_placeholder_evidence():
    from engram_goal03_implementation_demo import assert_retrieval_policy

    policy = dict(
        expected_retrieval_reasons={"Decision:old": "superseded"},
        expected_observation_events={"Deployment:unknown": None},
    )
    answer = dict(
        nodes={
            "Decision:old": dict(retrieval_reason="direct"),
            "Deployment:unknown": dict(provenance=None),
        }
    )
    with pytest.raises(AssertionError, match="retrieval reason"):
        assert_retrieval_policy(answer, policy)
    answer["nodes"]["Decision:old"]["retrieval_reason"] = "superseded"
    assert_retrieval_policy(answer, policy)
    answer["nodes"]["Deployment:unknown"]["provenance"] = dict(event_id="rollback-observation")
    with pytest.raises(AssertionError, match="observation evidence"):
        assert_retrieval_policy(answer, policy)


def test_forbidden_edges_check_observed_node_and_extra_testcase_without_cross_scope_false_alarm():
    from engram_goal03_implementation_demo import assert_forbidden_edges

    fixture = dict(
        expected_node="TestRun:skip",
        extra_nodes={"TestCase:tests": {}},
        forbidden_edge_types=["VERIFIES"],
        forbidden_outgoing_edge_types=["RAN_AGAINST"],
    )
    state = dict(
        edges=[
            ["TestCase", "TestCase:other", "VERIFIES", "Requirement", "Requirement:elsewhere", {}]
        ]
    )
    assert_forbidden_edges(state, fixture)
    state["edges"].append(
        ["TestCase", "TestCase:tests", "VERIFIES", "Requirement", "Requirement:expiry", {}]
    )
    with pytest.raises(AssertionError, match="Forbidden"):
        assert_forbidden_edges(state, fixture)
    state["edges"] = [["TestRun", "TestRun:skip", "RAN_AGAINST", "Change", "Change:wrong", {}]]
    with pytest.raises(AssertionError, match="Forbidden"):
        assert_forbidden_edges(state, fixture)


async def test_normalized_receipt_and_wrong_webhook_identity_fail_at_http_boundary():
    data = fixtures("receipts", start=datetime(2026, 10, 8, tzinfo=UTC))
    step = http_steps(data)[0]

    def handle(request):
        assert request.url.path == "/v1/events"
        return httpx.Response(
            201,
            json=dict(
                event_id=step["request"]["event_id"], global_position="1-0", status="created"
            ),
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle), base_url="http://test"
    ) as client:
        await submit_fixture(client, step, "unused")
    raw = next(s for s in http_steps(data) if s.get("webhook"))
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(202, json={"event_ids": ["wrong-id"]})
        ),
        base_url="http://test",
    ) as client:
        with pytest.raises(AssertionError):
            await submit_fixture(client, raw, "secret")


async def test_signed_webhooks_match_oracle_through_public_route_and_retry_has_no_append():
    from fastapi import FastAPI
    from pydantic import SecretStr

    from context_graph.api.routes.webhooks import router
    from context_graph.domain.models import Event
    from context_graph.ontology import load_registry
    from context_graph.ports.event_store import AppendOutcome
    from context_graph.settings import Settings

    expected_steps = [
        s
        for s in http_steps(fixtures("route", start=datetime(2026, 10, 8, tzinfo=UTC)))
        if s.get("webhook")
    ]

    # This is a boundary fake for the external append service, not a graph backend.
    class EventWriter:
        def __init__(self):
            self.accepted = {}
            self.writes = 0

        async def append_batch_outcomes(self, events, payloads):
            event, payload = events[0], payloads[0]
            oracle = next(
                s["request"]
                for s in expected_steps
                if s["request"]["event_id"] == str(event.event_id)
            )
            expected_event = Event.model_validate(oracle, strict=False)
            assert event == expected_event
            assert payload == oracle["payload"]
            if event.event_id in self.accepted:
                assert self.accepted[event.event_id] == (event, payload)
                return [AppendOutcome("duplicate", position="1-0")]
            self.accepted[event.event_id] = (event, payload)
            self.writes += 1
            return [AppendOutcome("created", position="1-0")]

    writer = EventWriter()
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    app.state.settings = Settings()
    app.state.settings.webhooks.github_secret = SecretStr("route-secret")
    app.state.ontology = load_registry(["pdlc"])
    app.state.event_store = writer
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        for step in expected_steps:
            before = writer.writes
            await submit_fixture(client, step, "route-secret")
            assert writer.writes == before + (0 if step.get("duplicate") else 1)
    assert writer.writes == 2


def test_reference_nodes_from_catalog_metadata_never_claim_observation_provenance():
    step = dict(
        scenario="reference",
        request={},
        expected_status=201,
        expected_node="DeploymentRollback:declared",
        extra_nodes={"Deployment:unknown": {}, "Component:observed": {}},
        expected_observed_node_ids=["DeploymentRollback:declared", "Component:observed"],
    )
    transformed = http_steps(dict(steps=[step]))[0]
    assert transformed["observes_node"]
    assert transformed["placeholders"] == ["Deployment:unknown"]
    assert "placeholders" not in step  # author-owned source oracle remains untouched
