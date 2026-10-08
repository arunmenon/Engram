"""Predeclared G06 inputs/outputs checked locally before real Spanner execution."""

import sys
from pathlib import Path

import orjson
import pytest
from pydantic import ValidationError

from context_graph.domain.models import Event
from context_graph.domain.pack_projection import PackProjector
from context_graph.domain.projection import event_to_node
from context_graph.retrieval.artifacts import ArtifactQuery, ArtifactRetriever
from context_graph.worker.pack_projection import apply_plan
from tests.unit.test_pack_projection import REGISTRY, Harness

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from engram_goal06_fixtures import fixtures  # noqa: E402


def test_goal06_contracts_and_retry_identity():
    data = fixtures("local-contract")
    originals = {}
    for step in data["steps"]:
        request = step["request"]
        contract = REGISTRY.event_types[request["event_type"]].definition.payload_contract
        if step["expected_status"] == 422:
            with pytest.raises(ValidationError):
                contract.validate_payload(request["payload"])
        else:
            contract.validate_payload(request["payload"])
        if step.get("duplicate"):
            assert request == originals[request["event_id"]]
        elif step["expected_status"] == 409:
            assert request != originals[request["event_id"]]
        else:
            originals[request["event_id"]] = request


async def test_goal06_exact_graph_lifecycle_evidence_and_retrieval():
    h = Harness()
    data = fixtures("local-incident")
    expected_nodes, expected_edges, sources, edge_props = {}, set(), {}, {}
    for index, step in enumerate(data["steps"]):
        if step["expected_status"] != 201 or step.get("duplicate"):
            continue
        request = step["request"]
        event = Event.model_validate(dict(request, global_position=f"{index + 1}-0"), strict=False)
        await h.graph.merge_event_node(event_to_node(event))
        plan = PackProjector(REGISTRY, frozenset({request["agent_id"]})).plan(
            event, dict(orjson.loads(event.model_dump_json()), payload=request["payload"])
        )
        assert not plan.rejected
        await apply_plan(h.graph, plan, 1000)
        nid = step["expected_node"]
        if nid:
            expected_nodes[nid] = step["expected_props"]
            if step.get("observes_node", True):
                sources.setdefault(nid, set()).add(str(event.event_id))
        for extra_id, props in step["extra_nodes"].items():
            expected_nodes[extra_id] = props
            if extra_id not in step.get("placeholders", []):
                sources.setdefault(extra_id, set()).add(str(event.event_id))
        expected_nodes.update(step.get("node_assertions", {}))
        expected_edges.update(tuple(e) for e in step["expected_edges"])
        for kind, source, target, properties in step.get("expected_edge_properties", []):
            edge_props[(kind, source, target)] = {
                k: event.global_position if v == "$receipt" else v for k, v in properties.items()
            }
        domain = {key for (label, key) in h.graph.nodes if label != "Event"}
        assert domain == set(expected_nodes), (step["scenario"], domain ^ set(expected_nodes))
        actual_edges = {
            (kind, source[1], target[1])
            for (source, kind, target) in h.graph.edges
            if kind != "DERIVED_FROM"
        }
        assert actual_edges == expected_edges, (step["scenario"], actual_edges ^ expected_edges)
        for key, props in expected_nodes.items():
            for name, value in props.items():
                assert h.node(key).get(name) == value, (step["scenario"], key, name)
        assert set(h.edges("DERIVED_FROM")) == {
            (key, event_id) for key, events in sources.items() for event_id in events
        }
        for key in step.get("placeholders", []):
            assert not any(source == key for source, target in h.edges("DERIVED_FROM"))
        for (kind, source, target), properties in edge_props.items():
            for key, value in properties.items():
                assert h.edges(kind)[(source, target)].get(key) == value
    engine = ArtifactRetriever(
        h.graph,
        REGISTRY,
        default_max_depth=3,
        seed_limit=20,
        neighbor_limit=100,
        provenance_source="memory",
    )
    for query in data["queries"]:
        answer = await engine.retrieve(
            ArtifactQuery(
                query=query["text"],
                seed_node_ids=tuple(query["seeds"]),
                intent=query["intent"],
                max_nodes=50,
                max_depth=query["max_depth"],
            )
        )
        required = set(query["required"])
        assert set(answer.nodes) == required, (query["scenario"], set(answer.nodes) ^ required)
        edges = {(e.edge_type, e.source, e.target) for e in answer.edges}
        assert edges == {tuple(e) for e in query["expected_edges"]}, query["scenario"]
        assert not answer.meta.truncated
        for nid in required:
            if nid in sources:
                assert answer.nodes[nid].provenance.event_id in sources[nid]
            else:
                assert answer.nodes[nid].provenance is None


@pytest.mark.parametrize("changed", [False, True])
def test_g05_guard_preserves_failure_exit_and_detects_retained_data_change(
    monkeypatch, tmp_path, changed
):
    import json
    from types import SimpleNamespace

    import engram_goal06_incident_demo as driver

    retained = (
        tmp_path
        / "docs/review/spanner-compatibility/runs/20261008-cloud-g05-all-01/retained-dataset.json"
    )
    retained.parent.mkdir(parents=True)
    retained.write_text(json.dumps(dict(fingerprints={"Events": "original"}, owner=["retained"])))
    monkeypatch.setattr(driver, "ROOT", tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["demo", "--credentials", "unused", "--run-id", "guard-test", "--expected-epoch", "1"],
    )
    monkeypatch.setattr(
        driver,
        "load_credentials",
        lambda _: dict(
            GOOGLE_CLOUD_PROJECT="portiq-mvp",
            SPANNER_INSTANCE_ID="engram-experiment",
            GOOGLE_OAUTH_ACCESS_TOKEN="test",
        ),
    )
    database = object()
    client = SimpleNamespace(
        instance=lambda _: SimpleNamespace(database=lambda *args, **kwargs: database)
    )
    monkeypatch.setattr(driver.spanner, "Client", lambda **kwargs: client)
    monkeypatch.setattr(driver, "prepare_cleanup", lambda *args: None)
    closed = []
    monkeypatch.setattr(driver, "close_database", closed.append)
    snapshots = iter([{"Events": "original"}, {"Events": "changed" if changed else "original"}])
    monkeypatch.setattr(driver, "fingerprint", lambda _: next(snapshots))
    monkeypatch.setattr(driver, "read_owner", lambda _: [["retained"]])

    def failed_demo(**kwargs):
        assert kwargs["target_database"] == "engram-g06-target"
        assert kwargs["retain_success"]
        raise SystemExit(7)

    monkeypatch.setattr(driver, "demo_main", failed_demo)
    if changed:
        with pytest.raises(AssertionError, match="retention guard failed"):
            driver.main()
    else:
        with pytest.raises(SystemExit) as failure:
            driver.main()
        assert failure.value.code == 7
    assert closed == [database]
    evidence = json.loads(
        (
            tmp_path / "docs/review/spanner-compatibility/runs/guard-test/g05-protection.json"
        ).read_text()
    )
    assert evidence["passed"] is not changed


@pytest.mark.parametrize("run_id", ["../escape", "already-used"])
def test_goal06_driver_refuses_unsafe_or_existing_run_before_credentials(
    monkeypatch, tmp_path, run_id
):
    import engram_goal06_incident_demo as driver

    previous = tmp_path / "docs/review/spanner-compatibility/runs/already-used"
    previous.mkdir(parents=True)
    evidence = previous / "g05-protection.json"
    evidence.write_text("original evidence")
    monkeypatch.setattr(driver, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["demo", "--credentials", "missing", "--run-id", run_id])

    def unexpected_credentials(_):
        pytest.fail("Refused run must not load credentials or contact Spanner")

    monkeypatch.setattr(driver, "load_credentials", unexpected_credentials)
    with pytest.raises(SystemExit) as error:
        driver.main()
    assert error.value.code == 2
    assert evidence.read_text() == "original evidence"
    assert not (tmp_path / "docs/review/spanner-compatibility/escape").exists()
