"""The imported journey must retain the fixture's delivery and oracle semantics."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from context_graph.workbench.journeys import Journey, implementation_journey

FIXTURE = Path("src/context_graph/workbench/fixtures/pdlc/implementation.source.json")


def test_implementation_import_preserves_events_and_assertions():
    source = json.loads(FIXTURE.read_text())
    journey = implementation_journey()
    assert [e.request for e in journey.events] == [s["request"] for s in source["steps"]]
    for index, step in enumerate(source["steps"]):
        checks = [c for c in journey.checks if c.after_step == index]
        assert any(
            c.kind == "disposition" and c.expected["http_status"] == step["expected_status"]
            for c in checks
        )
        if step["expected_status"] != 201 or "duplicate" in step["scenario"]:
            assert any(c.kind == "unchanged" for c in checks)
        else:
            for kind, start, end in step["expected_edges"]:
                assert any(
                    c.kind == "edge_present"
                    and c.expected == dict(type=kind, source=start, target=end)
                    for c in checks
                )
    actual = [c.expected for c in journey.checks if c.kind == "retrieval"]
    assert len(actual) == len(source["queries"])
    for adapted, original in zip(actual, source["queries"], strict=True):
        assert {key: adapted[key] for key in original} == original
        assert adapted["not_truncated"] is True
        assert "properties" in adapted and "edges" in adapted and "evidence" in adapted
    # Save/reload does not regenerate timestamps, IDs or expectations.
    assert Journey.model_validate_json(journey.model_dump_json()) == journey
    assert implementation_journey() == journey


def test_missing_checkpoint_is_rejected():
    raw = implementation_journey().model_dump()
    raw["checks"][0]["after_step"] = len(raw["events"])
    with pytest.raises(ValidationError, match="missing event checkpoint"):
        Journey.model_validate(raw)


async def test_prepared_journey_runs_without_author_and_rejects_conflicting_ids(tmp_path):
    import asyncio

    import httpx

    from context_graph.workbench.api import create_app

    app = create_app(database=tmp_path / "journey.db", operators={"a": "alice", "b": "bob"})
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app),
        base_url="http://test",
        headers={"Authorization": "Bearer a"},
    ) as client:
        prepared = await client.post("/admin/journeys/implementation")
        assert prepared.status_code == 201
        draft = prepared.json()
        assert draft["content"]["data_policy"] == "local_only"
        assert draft["readiness"]["run"]["ready"]
        root = f"/admin/tenants/{draft['id']}"
        assert (await client.get(root, headers={"Authorization": "Bearer b"})).status_code == 404
        assert (
            await client.post(root + "/journey-run", json={"revision": draft["revision"]})
        ).status_code == 202
        for _ in range(300):
            draft = (await client.get(root)).json()
            if draft["job"]["status"] != "running":
                break
            await asyncio.sleep(0.01)
        assert draft["job"]["status"] == "completed", draft["job"]
        result = draft["journey_result"]
        assert len(result["steps"]) == 23
        assert len(result["checks"]) == len(implementation_journey().checks)
        assert result["passed"]
        conflict = next(c for c in result["checks"] if c["expected"] == {"http_status": 409})
        assert conflict["status"] == "passed"
        assert conflict["actual"]["semantic_outcome"] == "conflict"
        assert conflict["actual"]["http_exercised"] is False
        assert not any(c["status"] == "unsupported" for c in result["checks"])
        assert (
            await client.post(root + "/approve", json={"revision": draft["revision"]})
        ).status_code == 409


def test_exact_graph_check_detects_extra_edges_and_stale_properties():
    from context_graph.workbench.journey_runner import evaluate_check

    journey = implementation_journey()
    check = next(c for c in journey.checks if c.kind == "graph_exact")
    node, props = next(iter(check.expected["nodes"].items()))
    event = check.expected["evidence"][node][0]
    snapshot = {
        "nodes": [{"id": node, "type": "Spec", "properties": props}],
        "edges": [{"type": "DERIVED_FROM", "source": node, "target": event}],
    }
    assert evaluate_check(check, snapshot, {}, "created").status == "passed"
    snapshot["edges"].append({"type": "REFINES", "source": node, "target": node})
    assert evaluate_check(check, snapshot, {}, "created").status == "failed"
    snapshot["edges"].pop()
    snapshot["nodes"][0]["properties"] = {"title": "incorrect"}
    result = evaluate_check(check, snapshot, {}, "created")
    assert result.status == "failed" and result.actual["wrong_properties"]


async def test_journey_cancellation_does_not_save_a_late_result(tmp_path, monkeypatch):
    import asyncio

    import httpx

    from context_graph.workbench.api import create_app

    entered = asyncio.Event()
    stopped = asyncio.Event()

    async def slow_run(_journey):
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()

    monkeypatch.setattr("context_graph.workbench.api.run_journey", slow_run)
    app = create_app(database=tmp_path / "journey.db", operators={"a": "alice"})
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app),
        base_url="http://test",
        headers={"Authorization": "Bearer a"},
    ) as client:
        draft = (await client.post("/admin/journeys/implementation")).json()
        root = f"/admin/tenants/{draft['id']}"
        draft = (
            await client.post(root + "/journey-run", json={"revision": draft["revision"]})
        ).json()
        await asyncio.wait_for(entered.wait(), 2)
        assert (
            await client.post(root + "/cancel", json={"revision": draft["revision"]})
        ).status_code == 200
        await asyncio.wait_for(stopped.wait(), 2)
        latest = (await client.get(root)).json()
        assert latest["job"]["status"] == "cancelled"
        assert not latest.get("journey_result")


async def test_old_journey_result_is_labelled_stale(tmp_path):
    import httpx

    from context_graph.workbench.api import create_app
    from context_graph.workbench.store import Store

    database = tmp_path / "journey.db"
    app = create_app(database=database, operators={"a": "alice"})
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app),
        base_url="http://test",
        headers={"Authorization": "Bearer a"},
    ) as client:
        draft = (await client.post("/admin/journeys/implementation")).json()
        draft["journey_result"] = {"engine_revision": "older-engine", "journey_digest": "old"}
        Store(database).put("alice", draft, draft["revision"], "test_old_result")
        latest = (await client.get(f"/admin/tenants/{draft['id']}")).json()
        assert latest["journey_result_stale"] is True


async def test_planning_checkpoint_preserves_placeholder_and_approval_semantics():
    from context_graph.workbench.journey_runner import run_journey
    from context_graph.workbench.journeys import planning_journey

    journey = planning_journey()
    assert journey.id == "pdlc-planning"
    assert journey.trusted_producers == ["planning.publisher"]
    result = await run_journey(journey)
    by_id = {r["check_id"]: r for r in result["checks"]}
    critical = [
        c
        for c in journey.checks
        if c.kind in {"graph_exact", "property_absent", "evidence_absent", "edge_absent"}
    ]
    assert critical
    assert all(by_id[c.id]["status"] == "passed" for c in critical)
    # The earlier checkpoint stays an empty placeholder after the later event fills it.
    before = next(s for s in result["steps"] if s["id"] == "PL09-before")
    after = next(s for s in result["steps"] if s["id"] == "PL09-after")
    absent = next(c.expected["node"] for c in journey.checks if c.kind == "property_absent")
    assert "body" not in next(n["properties"] for n in before["nodes"] if n["id"] == absent)
    assert (
        next(n["properties"] for n in after["nodes"] if n["id"] == absent)["body"]
        == "Late-arriving storage architecture"
    )
    assert not any(r["status"] == "failed" for r in result["checks"])
    conflict = next(r for r in result["checks"] if r["expected"] == {"http_status": 409})
    assert conflict["actual"]["semantic_outcome"] == "conflict"


async def test_release_replays_adapter_outputs_and_original_eval_questions():
    from context_graph.ontology.evaluation import load_eval_set
    from context_graph.sources.github import translate as github
    from context_graph.sources.jira import translate as jira
    from context_graph.workbench.journey_runner import run_journey
    from context_graph.workbench.journeys import release_journey

    root = FIXTURE.parent
    rows = json.loads((root / "release.source.json").read_text())
    journey = release_journey()
    for row, event in zip(rows, journey.events, strict=True):
        translated = (
            github(row["source_event"], row["source_payload"])
            if row["provider"] == "github"
            else jira(row["source_payload"])
        )
        assert len(translated) == 1
        assert event.request["payload"] == translated[0].payload
        assert event.request["event_type"] == translated[0].event_type
    original = load_eval_set(root / "release.eval.yaml")
    checks = [c for c in journey.checks if c.kind == "evaluation"]
    # The new default is semantically equivalent; frozen source/digests stay unchanged.
    from context_graph.ontology.evaluation import EvalQuestion

    assert [
        EvalQuestion.model_validate(c.expected["question"]) for c in checks
    ] == original.questions
    result = await run_journey(journey)
    assert all(
        c["status"] == "passed" for c in result["checks"] if c["check_id"] in {q.id for q in checks}
    )
    assert len(checks) == 11
    assert not result["passed"]  # Supplemental webhook/extraction/API checks are not run.
    assert sum(c["status"] == "unsupported" for c in result["checks"]) == 1


async def test_agent_variant_requires_consent_review_and_preserves_baseline(tmp_path, monkeypatch):
    import asyncio

    import httpx

    from context_graph.workbench.api import create_app
    from context_graph.workbench.journey_authoring import JourneyOutline

    calls = []

    async def proposed(model, baseline, brief, outline=None, decisions=""):
        calls.append((outline, decisions))
        if outline is None:
            return JourneyOutline(
                title="Test outline",
                story="Retain the original semantics",
                steps=["Replay the existing events"],
                sources=["operator-specification"],
            )
        variant = baseline.model_copy(deep=True)
        variant.id = "reviewed-variant"
        variant.expectations_reviewed = False
        return variant

    monkeypatch.setattr("context_graph.workbench.api.propose_journey", proposed)
    app = create_app(
        database=tmp_path / "journey.db", operators={"a": "alice"}, model_label="test-model"
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app),
        base_url="http://test",
        headers={"Authorization": "Bearer a"},
    ) as client:
        draft = (await client.post("/admin/journeys/implementation")).json()
        original = draft["journey"]
        root = f"/admin/tenants/{draft['id']}"
        brief = dict(
            revision=draft["revision"],
            goal="Exercise existing semantics",
            specification="Keep the fixture's original expected outcomes",
        )
        assert (await client.post(root + "/journey-outline", json=brief)).status_code == 409
        assert not calls

        async def finish():
            for _ in range(100):
                latest = (await client.get(root)).json()
                if latest["job"]["status"] != "running":
                    return latest
                await asyncio.sleep(0.01)
            pytest.fail("Agent task did not finish")

        await client.post(root + "/journey-outline", json={**brief, "provider_allowed": True})
        draft = await finish()
        assert draft["journey_outline"] and draft["journey"] == original
        generate = dict(
            revision=draft["revision"], decisions="Keep all existing domain rules unchanged."
        )
        assert (await client.post(root + "/journey-generate", json=generate)).status_code == 409
        await client.post(root + "/journey-generate", json={**generate, "outline_reviewed": True})
        draft = await finish()
        assert draft["journey_proposal"]["expectations_reviewed"] is False
        assert draft["journey"] == original
        accepted = await client.post(
            root + "/journey-accept",
            json={
                "revision": draft["revision"],
                "accepted_checks": [c["id"] for c in draft["journey_proposal"]["checks"]],
            },
        )
        assert accepted.status_code == 201, accepted.text
        variant = accepted.json()
        assert variant["id"] != draft["id"]
        assert variant["journey"]["expectations_reviewed"] is True
        assert not variant.get("journey_result")
        assert (await client.get(root)).json()["journey"] == original


async def test_model_validation_feedback_omits_generated_input(monkeypatch):
    from types import SimpleNamespace

    from context_graph.workbench.journey_authoring import JourneyProposalError, propose_journey

    calls = []

    async def malformed(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content='{"title": "PRIVATE-SAMPLE-CONTENT"}')
                )
            ]
        )

    monkeypatch.setattr("litellm.acompletion", malformed)
    with pytest.raises(JourneyProposalError) as error:
        await propose_journey("test-model", implementation_journey(), {"goal": "test"})
    assert "story: missing" in str(error.value)
    assert "PRIVATE-SAMPLE-CONTENT" not in str(error.value)
    assert len(calls) == 2


def test_generated_questions_validate_before_review():
    from context_graph.workbench.journey_authoring import JourneyProposalError, validate_variant
    from context_graph.workbench.journeys import JourneyCheck

    baseline = implementation_journey()
    variant = baseline.model_copy(deep=True)
    question = next(c for c in variant.checks if c.kind == "retrieval")
    question.after_step = 0
    with pytest.raises(JourneyProposalError, match="final graph"):
        validate_variant(variant, baseline)
    question.after_step = None
    variant.checks.append(
        JourneyCheck(
            id="bad-eval",
            description="Bad evaluation",
            source="operator-specification",
            kind="evaluation",
            expected={"question": {}},
        )
    )
    with pytest.raises(JourneyProposalError, match="min_f1"):
        validate_variant(variant, baseline)
    variant.checks[-1].expected["min_f1"] = 1.0
    with pytest.raises(ValidationError):
        validate_variant(variant, baseline)
    variant.checks[-1].expected["question"] = {
        "id": "filter-mismatch",
        "query": "Which designs?",
        "intent": "status",
        "expected": ["DesignApproval:approval"],
        "answer": {"node_type": "DesignElement"},
    }
    with pytest.raises(JourneyProposalError, match="answer.node_type"):
        validate_variant(variant, baseline)


async def test_reference_journey_preserves_source_events_and_oracles(monkeypatch):
    import importlib.util

    from context_graph.domain.pack_projection import PackProjector
    from context_graph.workbench.journey_runner import run_journey
    from context_graph.workbench.journeys import reference_journey

    def source_module(name):
        spec = importlib.util.spec_from_file_location(name, f"tests/unit/{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    planning = source_module("test_planning_journey")
    implementation = source_module("test_implementation_journey")
    captured = []
    original = PackProjector.plan

    def record(self, event, payload):
        captured.append((event.event_type, payload["payload"]))
        return original(self, event, payload)

    with monkeypatch.context() as scope:
        scope.setattr(PackProjector, "plan", record)
        await planning.test_connected_paths_keep_edges_without_expanding_to_siblings()
        implementation.test_multiple_explicit_references_keep_each_complete_identity()
    journey = reference_journey()
    assert [(e.request["event_type"], e.request["payload"]) for e in journey.events] == captured
    result = await run_journey(journey)
    assert sum(c["status"] == "passed" for c in result["checks"]) == 13
    assert not any(c["status"] == "unsupported" for c in result["checks"])
    assert not any(c["status"] in {"error", "failed"} for c in result["checks"])


def test_exact_parent_and_deployment_checks_reject_extras():
    from context_graph.workbench.journey_runner import evaluate_check
    from context_graph.workbench.journeys import release_journey

    journey = release_journey()
    parent = next(c for c in journey.checks if c.kind == "edge_targets")
    deployments = next(c for c in journey.checks if c.kind == "nodes_matching")
    snapshot = {
        "nodes": [
            {
                "id": deployments.expected["ids"][0],
                "type": "Deployment",
                "properties": {"environment": "production"},
            }
        ],
        "edges": [
            {
                "type": "DECOMPOSES_INTO",
                "source": "WorkItem:jira|PAY-300",
                "target": "WorkItem:jira|PAY-341",
                "properties": {},
            }
        ],
    }
    assert evaluate_check(parent, snapshot, snapshot, "created").status == "passed"
    assert evaluate_check(deployments, snapshot, snapshot, "created").status == "passed"
    snapshot["edges"].append({**snapshot["edges"][0], "source": "WorkItem:jira|EXTRA"})
    snapshot["nodes"].append({**snapshot["nodes"][0], "id": "Deployment:extra"})
    assert evaluate_check(parent, snapshot, snapshot, "created").status == "failed"
    assert evaluate_check(deployments, snapshot, snapshot, "created").status == "failed"


def test_source_inventory_links_to_pinned_current_checks():
    from context_graph.workbench.engine import digest
    from context_graph.workbench.journeys import (
        RETRIEVAL_VARIANTS,
        planning_journey,
        reference_journey,
        release_journey,
        retrieval_trust_journey,
        retrieval_variant_journey,
        source_coverage,
    )

    manifest = json.loads(
        Path("src/context_graph/workbench/fixtures/pdlc/manifest.json").read_text()
    )
    journeys = {
        j.id: j
        for j in [
            implementation_journey(),
            planning_journey(),
            reference_journey(),
            release_journey(),
            retrieval_trust_journey(),
            *(retrieval_variant_journey(name) for name in RETRIEVAL_VARIANTS),
        ]
    }
    assert len(manifest["assertions"]) == 144
    for row in manifest["assertions"]:
        assert (
            row["status"] in {"implemented", "supplemental", "pending-migration"} and row["reason"]
        )
        if row["status"] == "implemented":
            assert row["checks"]
            for name in row["journeys"]:
                assert set(row["checks"]) <= {c.id for c in journeys[name].checks}
    for name, journey in journeys.items():
        assert manifest["journey_digests"][name] == digest(journey.model_dump())
        assert source_coverage(journey.model_dump())
    old = release_journey().model_dump()
    old["checks"].pop()
    assert "predates" in source_coverage(old)[0]["reason"]


async def test_graph_fixture_replays_original_trust_queries_without_ingestion(monkeypatch):
    import importlib.util
    import sys
    from uuid import NAMESPACE_URL, uuid5

    from fastapi.encoders import jsonable_encoder

    from context_graph.workbench.journey_runner import frozen_registry, graph_snapshot, run_journey
    from context_graph.workbench.journeys import retrieval_trust_journey

    spec = importlib.util.spec_from_file_location(
        "frozen_retrieval_source", "tests/unit/test_pdlc_retrieval_eval.py"
    )
    source = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, source)
    spec.loader.exec_module(source)
    counter = 0

    def fixed_uuid():
        nonlocal counter
        counter += 1
        return uuid5(NAMESPACE_URL, f"engram/frozen-pdlc-retrieval/{counter}")

    monkeypatch.setattr(source, "uuid4", fixed_uuid)
    original = jsonable_encoder(graph_snapshot(await source.build_graph()))
    journey = retrieval_trust_journey()
    assert frozen_registry(journey.pack_digest).version == source.REGISTRY.version
    initial = journey.starting_state.model_dump()
    assert {k: initial[k] for k in ("nodes", "edges")} == original
    result = await run_journey(journey)
    assert result["passed"] and not result["steps"] and not result["dead_letters"]
    assert result["initial_graph"] == original
    hidden, shown = result["checks"][:2]
    assert "WorkItem:jira|PAY-999" not in hidden["actual"]["nodes"]
    assert "WorkItem:jira|PAY-999" in shown["actual"]["nodes"]
    assert (
        shown["actual"]["node_details"]["WorkItem:jira|PAY-999"]["attributes"]["source_trust"]
        == "untrusted"
    )
    assert shown["actual"]["query_options"]["include_untrusted"] is True
    by_id = {c["check_id"]: c for c in result["checks"]}
    assert by_id["file-context"]["actual"]["metadata"]["seed_nodes"] == ["Change:acme/app|7"]
    assert by_id["file-preflight"]["actual"]["metadata"]["inferred_intents"] == {"preflight": 1.0}
    # A metadata regression must fail even when the expected answer nodes still match.
    changed = journey.model_copy(deep=True)
    changed.checks = [next(c for c in changed.checks if c.id == "file-context")]
    changed.checks[0].expected["metadata"]["seed_nodes"] = ["Change:acme/app|999"]
    mismatch = await run_journey(changed)
    assert not mismatch["passed"]
    assert mismatch["checks"][0]["actual"]["wrong_metadata"]
    assert journey.starting_state.retrieval_limits.model_dump() == {
        "default_max_depth": 3,
        "seed_limit": 10,
        "neighbor_limit": 200,
    }


def test_graph_fixture_rejects_dangling_edges_and_agent_bypass():
    from context_graph.workbench.journey_authoring import JourneyProposalError, validate_variant
    from context_graph.workbench.journeys import GraphFixture, QueryOptions, retrieval_trust_journey

    with pytest.raises(ValidationError, match="missing node"):
        GraphFixture.model_validate(
            {
                "nodes": [{"id": "Spec:a", "type": "Spec"}],
                "edges": [{"type": "REFINES", "source": "Spec:a", "target": "Spec:b"}],
            }
        )
    with pytest.raises(ValidationError):
        QueryOptions.model_validate({"max_nodes": 5000})
    with pytest.raises(JourneyProposalError, match="start empty"):
        validate_variant(retrieval_trust_journey(), implementation_journey())
    baseline = implementation_journey()
    oversized = baseline.model_copy(deep=True)
    next(c for c in oversized.checks if c.kind == "retrieval").expected["query_options"] = {
        "max_nodes": 5000
    }
    with pytest.raises(ValidationError):
        validate_variant(oversized, baseline)


async def test_retrieval_exact_sets_and_reasons_cannot_silently_pass():
    from context_graph.workbench.journey_runner import run_journey
    from context_graph.workbench.journeys import retrieval_trust_journey

    journey = retrieval_trust_journey()
    original = next(c for c in journey.checks if c.id == "missing-tests")
    wrong_set = original.model_copy(deep=True)
    wrong_set.id = "omit-proposed"
    wrong_set.expected["exact_nodes"] = ["Requirement:refunds|2|R2"]
    wrong_reason = original.model_copy(deep=True)
    wrong_reason.id = "wrong-reason"
    wrong_reason.expected["reasons"]["Requirement:refunds|2|R3"] = "no_link"
    journey.checks = [wrong_set, wrong_reason]
    result = await run_journey(journey)
    assert not result["passed"]
    assert [c["status"] for c in result["checks"]] == ["failed", "failed"]
    assert result["checks"][0]["actual"]["unexpected_nodes"] == ["Requirement:refunds|2|R3"]
    assert result["checks"][1]["actual"]["wrong_reasons"] == [
        {"node": "Requirement:refunds|2|R3", "expected": "no_link"}
    ]


async def test_retrieval_bounds_and_partial_metadata_are_enforced():
    from context_graph.workbench.journey_runner import run_journey
    from context_graph.workbench.journeys import retrieval_trust_journey

    journey = retrieval_trust_journey()
    bounded = next(c for c in journey.checks if c.id == "explicit-bounds")
    wrong_capacity = bounded.model_copy(deep=True)
    wrong_capacity.id = "wrong-capacity"
    wrong_capacity.expected["metadata_fields"]["capacity"]["max_depth"] = 2
    wrong_count = bounded.model_copy(deep=True)
    wrong_count.id = "wrong-count"
    wrong_count.expected["max_node_count"] = 0
    numbered = next(c for c in journey.checks if c.id == "numbered-reference")
    numbered.expected["first_seed"] = "Change:acme/app|999"
    journey.checks = [wrong_capacity, wrong_count, numbered]
    result = await run_journey(journey)
    assert [c["status"] for c in result["checks"]] == ["failed"] * 3
    assert result["checks"][0]["actual"]["wrong_metadata"]
    assert result["checks"][1]["actual"]["wrong_bounds"]
    assert result["checks"][2]["actual"]["wrong_metadata"]


async def test_retrieval_provenance_types_and_seed_expectations_fail_closed():
    from context_graph.workbench.journey_runner import run_journey
    from context_graph.workbench.journeys import retrieval_trust_journey

    journey = retrieval_trust_journey()
    checks = {c.id: c for c in journey.checks}
    checks["ticket-deployment"].expected["first_of_type"]["Deployment"]["provenance"][
        "agent_id"
    ] = "spoofed"
    checks["artifact-only"].expected["types"] = {"required": ["Event"]}
    checks["shared-release"].expected["nodes_by_type"]["Change"].append("Change:acme/app|9")
    checks["all-explicit-seeds"].expected["required_seeds"].append("Change:acme/app|999")
    journey.checks = [
        checks[k]
        for k in ("ticket-deployment", "artifact-only", "shared-release", "all-explicit-seeds")
    ]
    result = await run_journey(journey)
    assert [c["status"] for c in result["checks"]] == ["failed"] * 4
    assert all(c["actual"]["wrong_shape"] for c in result["checks"][:3])
    assert result["checks"][3]["actual"]["missing_seeds"] == ["Change:acme/app|999"]


async def test_frozen_retrieval_variants_match_source_setups_and_run():
    from scripts.engram_freeze_pdlc_retrieval_variants import build_variants

    from context_graph.workbench.journey_runner import run_journey
    from context_graph.workbench.journeys import retrieval_variant_journey

    rebuilt = await build_variants()
    assert len(rebuilt) == 12
    for name, source in rebuilt.items():
        saved = retrieval_variant_journey(name)
        assert saved.model_dump() == source.model_dump(), name
        result = await run_journey(saved)
        assert result["passed"], (name, result["checks"])
        assert not result["steps"]


async def test_truncation_and_exact_answer_count_are_assertions():
    from context_graph.workbench.journey_runner import run_journey
    from context_graph.workbench.journeys import retrieval_variant_journey

    journey = retrieval_variant_journey("paging-truncated")
    original = journey.checks[0]
    wrong_truncation = original.model_copy(deep=True)
    wrong_truncation.id = "incorrect-truncation"
    wrong_truncation.expected["truncated"] = False
    wrong_count = original.model_copy(deep=True)
    wrong_count.id = "incorrect-count"
    wrong_count.expected["node_count"] = 99
    journey.checks = [wrong_truncation, wrong_count]
    result = await run_journey(journey)
    assert [c["status"] for c in result["checks"]] == ["failed", "failed"]
    assert result["checks"][0]["actual"]["wrong_truncation"]
    assert result["checks"][1]["actual"]["wrong_bounds"]


async def test_category_benchmark_preserves_source_scoring_and_rejects_wrong_target():
    import sys

    from scripts.engram_freeze_pdlc_retrieval_variants import build_variants

    from context_graph.workbench.journey_runner import run_journey

    variants = await build_variants()
    source = sys.modules["pdlc_variant_source"]
    graph = await source.build_graph()
    original_scores = await source.evaluate(graph, source._retriever(graph))
    journey = variants["category-evaluation"]
    result = await run_journey(journey)
    assert result["passed"]
    assert result["checks"][0]["actual"]["categories"] == original_scores
    assert len(result["checks"][0]["actual"]["questions"]) == len(source.QUESTIONS)
    journey.checks[0].expected["expected_mean_f1"]["negation"] = 0.0
    result = await run_journey(journey)
    assert not result["passed"]


async def test_query_work_budget_is_counted_and_restored():
    from context_graph.workbench.journey_runner import run_journey
    from context_graph.workbench.journeys import retrieval_variant_journey

    journey = retrieval_variant_journey("query-budget")
    result = await run_journey(journey)
    actual = result["checks"][0]["actual"]
    assert result["passed"] and actual["truncated"]
    assert 0 < sum(actual["graph_calls"].values()) <= 50
    journey.checks[0].expected["max_observed_graph_calls"] = 0
    assert not (await run_journey(journey))["passed"]


async def test_forbidden_retrieval_edge_fails_when_it_is_returned():
    from context_graph.workbench.journey_runner import run_journey
    from context_graph.workbench.journeys import retrieval_variant_journey

    journey = retrieval_variant_journey("rejected-refinement")
    journey.checks[0].expected["forbidden_edges"] = [
        ["REFINES", "DesignElement:lld|storage|1", "DesignElement:hld|tokens|1"]
    ]
    result = await run_journey(journey)
    assert not result["passed"]
    assert result["checks"][0]["actual"]["forbidden_edges"]


async def test_explicit_seed_error_is_a_failed_journey_check_not_a_crash():
    from context_graph.workbench.journey_runner import run_journey
    from context_graph.workbench.journeys import JourneyCheck, retrieval_trust_journey

    journey = retrieval_trust_journey()
    journey.checks.insert(
        0,
        JourneyCheck(
            id="missing-explicit-seed",
            description="Missing starting entity is an error",
            source="seed-mode regression",
            kind="retrieval",
            expected={
                "text": "trace",
                "intent": "trace",
                "seeds": ["Change:absent|9"],
                "query_options": {"seed_mode": "explicit"},
                "required": [],
                "forbidden": [],
            },
        ),
    )
    result = await run_journey(journey)
    checks = result["checks"]
    failed = next(c for c in checks if c["check_id"] == "missing-explicit-seed")
    assert failed["status"] == "failed"
    assert failed["actual"]["reason"] == "missing"
    assert failed["actual"]["unresolved_seed_ids"] == ["Change:absent|9"]
    assert len(checks) == len(journey.checks)
    assert any(c["status"] == "passed" for c in checks)
