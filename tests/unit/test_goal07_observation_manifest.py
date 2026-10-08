"""Authored G07 observations, cleanup bounds and source tie oracles."""

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from context_graph.domain.models import Event
from context_graph.domain.pack_projection import PackProjector
from context_graph.ontology import load_registry

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))


def test_b_d_authored_observation_manifest_matches_public_plans():
    from engram_goal03_implementation_demo import fixture_observations, http_steps
    from engram_goal07_deployment_fixtures import fixtures as deployments
    from engram_goal07_lifecycle_fixtures import fixtures as lifecycle

    registry = load_registry(["pdlc"])
    projector = PackProjector(registry, frozenset())
    for factory in (lifecycle, deployments):
        for step in http_steps(factory("observations")):
            if step["expected_status"] != 201:
                continue
            event = Event.model_validate(step["request"], strict=False)
            plan = projector.plan(event, {"payload": step["request"]["payload"]})
            observed = {n.ref.key for n in plan.nodes if "source_trust" in n.properties}
            assert set(step["expected_observed_node_ids"]) == observed, step["scenario"]
            assert fixture_observations(step) == observed, step["scenario"]


def test_known_rollback_target_retains_observation_while_new_stubs_are_null():
    from engram_goal03_implementation_demo import fixture_observations, http_steps
    from engram_goal07_deployment_fixtures import fixtures

    data = fixtures("reference-proof")
    steps = {step["scenario"]: step for step in http_steps(data)}
    b = data["ids"]["deployment_b"]
    rollback = steps["D02-rollback-B"]
    assert b not in rollback["extra_nodes"]
    assert rollback["node_assertions"][b] == {"status": "rolled_back"}
    assert b not in rollback.get("placeholders", [])
    unknown = data["ids"]["unknown_target"]
    assert unknown in steps["D04-unknown"]["placeholders"]
    # Use the exact helper called by the HTTP harness for cumulative evidence.
    sources = {}
    for step in steps.values():
        if step["expected_status"] != 201:
            continue
        for key in fixture_observations(step):
            sources.setdefault(key, set()).add(step["request"]["event_id"])
        if step["scenario"] == "D02-rollback-B":
            assert sources[b] == {steps["D01-B"]["request"]["event_id"]}
        if step["scenario"] == "D04-unknown":
            assert unknown not in sources
        if step["scenario"] == "D04-late-fill":
            assert sources[unknown] == {step["request"]["event_id"]}
    assert steps["D04-late-fill"]["expected_observed_node_ids"] == sorted(
        [unknown, data["ids"]["component"]]
    )


def test_cleanup_registry_covers_every_literal_artifact_endpoint_without_runtime_discovery():
    from engram_goal03_implementation_demo import cleanup_artifact_ids, http_steps
    from engram_goal07_fixtures import fixtures

    data = fixtures("cleanup-proof")
    data["steps"] = http_steps(data)
    keys = cleanup_artifact_ids(data)
    declared = {value for value in data["ids"].values()}
    for step in data["steps"]:
        declared.update(step.get("extra_nodes", {}))
        declared.update(step.get("node_assertions", {}))
        if step.get("expected_node"):
            declared.add(step["expected_node"])
        for _, source, target in step["expected_edges"]:
            declared.update((source, target))
    assert keys == declared
    assert "Change:g07-d/cleanup-proof/app|9" in keys
    assert "Component:g07-d/cleanup-proof/worker" in keys
    assert "Change:outside/refuse-cleanup|999" not in keys


def test_latest_source_ties_allow_only_independently_declared_maximal_time_events():
    from engram_goal03_implementation_demo import assert_latest_source

    now = datetime(2026, 10, 8, tzinfo=UTC)
    times = {"one": now, "two": now, "old": now - timedelta(seconds=1)}
    for selected in ("one", "two"):
        assert_latest_source(selected, {"one", "two", "old"}, times)
    for selected in ("old", "unrelated"):
        with pytest.raises(AssertionError, match="latest source"):
            assert_latest_source(selected, {"one", "two", "old"}, times)


def test_combined_manifest_preserves_nested_validation_audit_metadata():
    from engram_goal07_fixtures import fixtures

    data = fixtures("nested-audit")
    assert len(data["nested_validation_baselines"]) == 15
    assert data["unpopulated_nested_branches"] == []
    for step in data["steps"]:
        if "validation_baseline" in step:
            assert step["validation_baseline"] in data["nested_validation_baselines"]


async def test_ledger_only_public_event_read_uses_actual_route_and_checks_available_envelope():
    import httpx
    from engram_goal03_implementation_demo import retrieve_ledger_only_event
    from engram_goal07_lifecycle_fixtures import fixtures
    from fastapi import FastAPI

    from context_graph.api.dependencies import get_retrieval
    from context_graph.api.routes.query import router
    from context_graph.domain.models import AtlasResponse

    fixture = next(s for s in fixtures("event/read")["steps"] if s.get("ledger_only"))
    expected = fixture["request"]
    eid = expected["event_id"]
    node = dict(
        node_id=eid,
        node_type="Event",
        attributes=dict(event_type=expected["event_type"], occurred_at=expected["occurred_at"]),
        provenance=dict(
            source="spanner",
            global_position="900-0",
            occurred_at=expected["occurred_at"],
            **{k: expected[k] for k in ("event_id", "session_id", "agent_id", "trace_id")},
        ),
    )

    class PublicRetrievalBoundary:
        async def get_subgraph(self, query):
            assert query.seed_nodes == [eid]
            assert query.session_id == expected["session_id"]
            assert query.agent_id == expected["agent_id"]
            assert query.intent == "what"
            return AtlasResponse.model_validate({"nodes": {eid: node}})

    app = FastAPI()
    app.include_router(router, prefix="/v1")
    app.dependency_overrides[get_retrieval] = lambda: PublicRetrievalBoundary()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as http:
        result = await retrieve_ledger_only_event(http, fixture, "900-0")
        assert result["unavailable_public_fields"] == ["payload_ref", "payload"]
        for field, bad in (
            ("event_type", "pdlc.change.created"),
            ("occurred_at", "2000-01-01T00:00:00Z"),
        ):
            original = node["attributes"][field]
            node["attributes"][field] = bad
            with pytest.raises(AssertionError, match="public Event"):
                await retrieve_ledger_only_event(http, fixture, "900-0")
            node["attributes"][field] = original
        node["provenance"]["global_position"] = "wrong-position"
        with pytest.raises(AssertionError, match="public Event position"):
            await retrieve_ledger_only_event(http, fixture, "900-0")


def test_unobserved_this_event_does_not_null_an_earlier_observation():
    from engram_goal03_implementation_demo import fixture_observations, http_steps

    data = dict(
        steps=[
            dict(expected_node="Change:known", expected_status=201, extra_nodes={}),
            dict(
                expected_node="Action:new",
                expected_status=201,
                extra_nodes={"Change:known": {}, "Change:unknown": {}},
                expected_observed_node_ids=["Action:new"],
            ),
        ]
    )
    _, reference = http_steps(data)
    assert reference["unobserved_this_event"] == ["Change:known", "Change:unknown"]
    assert reference["placeholders"] == ["Change:unknown"]
    assert fixture_observations(reference) == {"Action:new"}
