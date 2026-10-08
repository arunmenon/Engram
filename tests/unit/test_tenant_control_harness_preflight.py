"""Construct every cloud manifest without registering or making a cloud call."""

import importlib
import json
from pathlib import Path

import pytest


class PreflightCompleteError(Exception):
    pass


@pytest.mark.parametrize(
    "phase,required,forbidden",
    [
        ("runtime", "all5worker factories", "Actual private API HTTP requests"),
        ("responses", "Actual private API HTTP requests", "all5worker factories"),
        ("verify", "all7snapshot read", "Actual private API HTTP requests"),
        ("acceptance-prepare", "Explicit additive acceptance JSON", "worker loops"),
        ("acceptance", "Real adapter acceptance", "all5worker factories"),
        ("interpretation", "Real bound consumer loops", "all5worker factories"),
        ("terminal", "terminal ACK/DLQ", "all5worker factories"),
        ("source-trust", "Explicit empty-target CAS activation", "all5worker factories"),
        ("expansion", "Bounded projection expansion", "all5worker factories"),
    ],
)
def test_manifest_construction_reaches_registration_with_truthful_scope(
    monkeypatch, phase, required, forbidden
):
    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    module = importlib.import_module("engram_spanner_tenant_control")
    monkeypatch.setattr(
        module,
        "load_credentials",
        lambda path: {
            "GOOGLE_CLOUD_PROJECT": "portiq-mvp",
            "SPANNER_INSTANCE_ID": "engram-experiment",
            "SPANNER_DATABASE_ID": "engram",
            "GOOGLE_OAUTH_ACCESS_TOKEN": "synthetic-preflight-token",
        },
    )
    monkeypatch.setattr(
        "sys.argv", ["harness", phase, "--run-id", "preflight-only", "--credentials", "unused"]
    )

    def registration(command, **kwargs):
        assert command[2] == "start"
        manifest = json.loads(Path(command[command.index("--manifest") + 1]).read_text())
        assert required in manifest["scope"] and forbidden not in manifest["scope"]
        assert "synthetic-preflight-token" not in json.dumps(manifest)
        raise PreflightCompleteError

    monkeypatch.setattr(module.subprocess, "run", registration)
    with pytest.raises(PreflightCompleteError):
        module.main()


def test_acceptance_upgrade_preserves_exact_previous_schema(monkeypatch):
    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    module = importlib.import_module("engram_spanner_tenant_control")
    from context_graph.adapters.spanner.schema import schema_statements

    after = schema_statements(384)
    before = [statement.replace("            acceptance JSON,\n", "") for statement in after]
    assert module.schema_preserved(before, after, acceptance_upgrade=True)
    assert module.schema_preserved(after, after, acceptance_upgrade=True)
    assert not module.schema_preserved(before, after)
    for old, new in [
        ("acceptance JSON", "acceptance STRING(MAX)"),
        ("session_id STRING(MAX) NOT NULL", "session_id STRING(64) NOT NULL"),
        ("PRIMARY KEY (event_id)", "PRIMARY KEY (event_id, session_id)"),
    ]:
        changed = [statement.replace(old, new) for statement in after]
        assert not module.schema_preserved(before, changed, acceptance_upgrade=True)
    missing = [
        statement
        for statement in after
        if not statement.startswith("CREATE INDEX EventsBySession ")
    ]
    assert not module.schema_preserved(before, missing, acceptance_upgrade=True)


@pytest.mark.parametrize(
    "index,value",
    [
        (0, "foreign"),
        (1, "projects/x/instances/y/databases/z"),
        (2, "foreign"),
        (3, 99),
        (4, "sha256:" + "f" * 64),
    ],
)
def test_acceptance_cleanup_authority_refuses_foreign_owner(monkeypatch, index, value):
    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    module = importlib.import_module("engram_spanner_acceptance_cases")
    from context_graph.adapters.spanner.tenant_control import TenantFence
    from tests.unit.test_tenant_catalog import bind

    binding = bind()
    row = [*TenantFence.from_binding(binding)._identity(), "frozen"]
    module.assert_owned(row, binding, {binding.epoch})
    row[index] = value
    with pytest.raises(AssertionError):
        module.assert_owned(row, binding, {binding.epoch})


@pytest.mark.asyncio
async def test_case_cancellation_waits_for_sdk_write_and_cleanup(monkeypatch):
    import asyncio
    import threading

    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    module = importlib.import_module("engram_spanner_acceptance_cases")
    started, release = threading.Event(), threading.Event()
    effects = []

    def sdk_write():
        started.set()
        assert release.wait(2)
        effects.append("write")

    async def case():
        try:
            await asyncio.to_thread(sdk_write)
        finally:
            effects.append("cleanup")

    task = asyncio.create_task(module.await_settled(case()))
    try:
        assert await asyncio.to_thread(started.wait, 1)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done() and not effects
    finally:
        release.set()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, 2)
    assert effects == ["write", "cleanup"]


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["interpretation", "source_trust", "expansion"])
async def test_case_cancellation_records_failure_after_settling(monkeypatch, phase):
    import asyncio

    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    module = importlib.import_module(f"engram_spanner_{phase}_cases")
    effects = []

    async def cancelled(*args):
        effects.append("cleanup")
        raise asyncio.CancelledError

    monkeypatch.setattr(module, "_verify", cancelled)
    checks = []
    with pytest.raises(asyncio.CancelledError):
        await getattr(module, f"verify_{phase}")(
            None, {}, "unused", {}, checks, None, lambda evidence: effects.append("persist")
        )
    assert effects == ["cleanup", "persist"]
    assert checks == [
        {"name": f"{phase}_cancelled_after_cleanup", "passed": False, "scenarios": []}
    ]


@pytest.mark.parametrize("case", range(5))
def test_expansion_fixture_contract_and_plan_intent(monkeypatch, case):
    from datetime import UTC, datetime
    from uuid import UUID

    from context_graph.domain.models import Event
    from context_graph.domain.pack_projection import PackProjector, ProjectionExpansionError

    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    module = importlib.import_module("engram_spanner_expansion_cases")
    settings = module.runtime_settings(
        {"GOOGLE_CLOUD_PROJECT": "portiq-mvp", "SPANNER_INSTANCE_ID": "engram-experiment"}
    )
    settings.ontology.packs = ["expansion", "expansion_observer"]
    settings.ontology.pack_dirs = [str(Path("tests/fixtures/pack_contracts").resolve())]
    bound = module.binding(settings, 9)
    ids, names, payloads, kinds, domain, node_ids, edges, group = module.fixture_inputs("preflight")
    contract = bound.bundle.registry.event_types[kinds[case]].definition.payload_contract
    contract.validate_payload(payloads[case])
    event = Event(
        event_id=UUID(ids[case]),
        event_type=kinds[case],
        occurred_at=datetime(2026, 10, 7, tzinfo=UTC),
        session_id=ids[case],
        agent_id="fixture",
        trace_id="preflight",
        payload_ref="fixture:" + ids[case],
    )
    projector = PackProjector(bound.bundle.registry, frozenset({"fixture"}))
    if case < 3:
        with pytest.raises(ProjectionExpansionError) as refused:
            projector.plan(event, {"payload": payloads[case]})
        assert (
            refused.value.reason
            == ["unequal_key_lengths", "plan_limit_exceeded", "plan_limit_exceeded"][case]
        )
        return
    plan = projector.plan(event, {"payload": payloads[case]})
    expected_nodes = node_ids[:2] if case == 3 else node_ids[2:]
    assert {node.ref.key for node in plan.nodes} == set(expected_nodes)
    expected_edges = edges[:2] if case == 3 else edges[2:]
    assert {
        (edge.source.label, edge.source.key, edge.edge_type, edge.target.label, edge.target.key)
        for edge in plan.edges
    } == {tuple(edge) for edge in expected_edges}
    assert len(plan.states) == (1 if case == 3 else 0)
