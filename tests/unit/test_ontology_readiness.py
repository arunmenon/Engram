"""Ontology status must describe the same blocked state as reconciliation."""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.api.routes.ontology import router
from context_graph.domain.pack_projection import PackProjector
from context_graph.ontology.versioning import OntologyChangeRefusedError, reconcile, record_state
from context_graph.ports.errors import RuntimeFencedError
from context_graph.settings import Settings
from tests.unit.test_pack_versioning import BASE, OPTIONS, _ledger


async def test_reverted_configuration_still_reports_unfinished_replay() -> None:
    graph = MemoryGraphStore()
    await record_state(
        graph,
        BASE,
        applied="initial",
        extra={
            "replay_incomplete": True,
            "replay_target_version": "unfinished-target",
            "replay_failures": ["1-0"],
        },
    )
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    app.state.graph_store, app.state.ontology, app.state.settings = graph, BASE, Settings()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/ontology")
    assert response.status_code == 200
    body = response.json()
    assert body["change"]["kind"] == "none"
    assert body["readiness"]["processing_ready"] is False
    assert "unfinished" in body["readiness"]["next_action"].lower()
    assert body["graph"]["replay_target_version"] == "unfinished-target"
    with pytest.raises(OntologyChangeRefusedError, match="replay incomplete"):
        await reconcile(graph, await _ledger(), PackProjector(BASE, frozenset()), **OPTIONS)


async def test_status_command_and_api_describe_same_failed_build(monkeypatch, capsys) -> None:
    import json
    from types import SimpleNamespace

    from context_graph.ontology import __main__ as cli
    from context_graph.ontology import load_registry

    registry, graph, settings = load_registry(["pdlc"]), MemoryGraphStore(), Settings()
    await record_state(graph, registry, applied="rebuild", extra={"gate_passed": False})

    async def close():
        pass

    async def open_stores(_settings):
        return SimpleNamespace(graph=graph, close=close)

    monkeypatch.setattr(cli, "open_stores", open_stores)
    assert await cli.run_status(settings) == 0
    output = capsys.readouterr().out
    command = json.loads(output[output.index("{\n") :])
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    app.state.graph_store, app.state.ontology, app.state.settings = graph, registry, settings
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        body = (await client.get("/v1/ontology")).json()
    assert command["readiness"] == body["readiness"]
    assert not command["readiness"]["processing_ready"]
    assert not command["readiness"]["evaluation_ready"]
    assert "rebuild" in command["readiness"]["next_action"]


@pytest.mark.parametrize("skipped", [False, True])
async def test_reevaluation_cannot_clear_failed_rebuild_but_can_finish_diagnostic_build(
    tmp_path, skipped
) -> None:
    from context_graph.ontology.__main__ import evaluate_graph
    from context_graph.ontology.rebuild import rebuild
    from context_graph.ontology.versioning import EvalPending, read_state
    from tests.unit.test_pack_versioning import DEMO_INTENTS, _eval_set, _registry

    registry, log, graph = _registry(**DEMO_INTENTS), await _ledger(), MemoryGraphStore()
    failed, passed = tmp_path / "failed", tmp_path / "passed"
    failed.mkdir()
    passed.mkdir()
    _eval_set(failed, ["Ticket:t|2"])
    _eval_set(passed, ["Ticket:t|1"])
    await rebuild(
        log,
        graph,
        PackProjector(registry, frozenset()),
        Settings(),
        eval_dirs=[failed],
        skip_gate=skipped,
    )
    assert await EvalPending(graph, registry, ttl_s=0).packs() == frozenset({"demo"})
    reports = await evaluate_graph(Settings(), graph, registry, [passed], record=True)
    assert reports and all(r.passed for r in reports)
    state = await read_state(graph)
    assert state is not None
    if skipped:
        assert await EvalPending(graph, registry, ttl_s=0).packs() == frozenset()
        assert not state.properties["gate_skipped"]
        await reconcile(graph, log, PackProjector(registry, frozenset()), **OPTIONS)
    else:
        assert state.failed_gate
        assert await EvalPending(graph, registry, ttl_s=0).packs() == frozenset({"demo"})
        with pytest.raises(OntologyChangeRefusedError, match="evaluation gate failed"):
            await reconcile(graph, log, PackProjector(registry, frozenset()), **OPTIONS)


@pytest.mark.parametrize("allow_breaking", [False, True])
async def test_known_missing_history_is_disclosed_without_new_worker_policy(allow_breaking) -> None:
    from context_graph.ontology.versioning import EvalPending

    graph, settings = MemoryGraphStore(), Settings(ontology={"allow_breaking": allow_breaking})
    await record_state(
        graph, BASE, applied="rebuild", extra={"gate_passed": True, "missing_documents": 1}
    )
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    app.state.graph_store, app.state.ontology, app.state.settings = graph, BASE, settings
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        readiness = (await client.get("/v1/ontology")).json()["readiness"]
    assert readiness["processing_ready"]
    assert not readiness["evaluation_ready"]
    assert readiness["recorded_history_incomplete"]
    assert readiness["diagnostic_only"]
    assert await EvalPending(graph, BASE, ttl_s=0).packs() == frozenset({"demo"})
    await reconcile(
        graph,
        await _ledger(),
        PackProjector(BASE, frozenset()),
        **(OPTIONS | {"allow_breaking": allow_breaking}),
    )


async def test_recorded_passing_questions_do_not_report_failed_build_as_ready(
    tmp_path, monkeypatch, capsys
) -> None:
    from types import SimpleNamespace

    from context_graph.ontology import __main__ as cli
    from tests.unit.test_pack_versioning import DEMO_INTENTS, _eval_set, _registry

    registry, graph = _registry(**DEMO_INTENTS), MemoryGraphStore()
    (tmp_path / "demo.pack.yaml").write_text(registry.pack("demo").canonical_json())
    _eval_set(tmp_path, ["Ticket:t|1"])
    settings = Settings(
        ontology={"packs": ["demo"], "builtin_packs": [], "pack_dirs": [str(tmp_path)]}
    )
    from tests.unit.test_pack_versioning import _project_all

    await _project_all(await _ledger(), graph, registry)
    await record_state(graph, registry, applied="rebuild", extra={"gate_passed": False})

    async def close():
        pass

    async def open_stores(_settings):
        return SimpleNamespace(graph=graph, close=close)

    monkeypatch.setattr(cli, "open_stores", open_stores)
    assert await cli.run_evaluate(settings, [], record=True) == 1
    captured = capsys.readouterr()
    assert '"passed": true' in captured.out
    assert '"evaluation_ready": false' in captured.out
    assert "rebuild" in captured.err


@pytest.mark.parametrize("skipped", [False, True])
async def test_artifact_query_explains_actual_blocker(skipped) -> None:
    from context_graph.api.routes.artifacts import router as artifact_router
    from context_graph.ontology.__main__ import _retriever
    from context_graph.ontology.versioning import EvalPending
    from tests.unit.test_pack_versioning import DEMO_INTENTS, _registry

    registry, graph, settings = _registry(**DEMO_INTENTS), MemoryGraphStore(), Settings()
    await record_state(
        graph, registry, applied="rebuild", extra={"gate_passed": skipped, "gate_skipped": skipped}
    )
    app = FastAPI()
    app.include_router(artifact_router, prefix="/v1")
    app.state.ontology, app.state.settings = registry, settings
    app.state.artifacts = _retriever(settings, graph, registry)
    app.state.eval_pending = EvalPending(graph, registry, ttl_s=0)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/query/artifacts", json={"query": "fix ticket", "intent": "fixes"}
        )
    assert response.status_code == 409
    assert ("evaluation" if skipped else "rebuild") in response.json()["detail"]


@pytest.mark.parametrize("failure", [OSError, RuntimeFencedError])
async def test_status_read_error_is_not_ready_or_an_authority_bypass(monkeypatch, failure) -> None:
    from context_graph.ports.errors import RuntimeFencedError

    graph = MemoryGraphStore()

    async def failed_read(_refs):
        raise failure("state unavailable")

    monkeypatch.setattr(graph, "get_nodes", failed_read)
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    app.state.graph_store, app.state.ontology, app.state.settings = graph, BASE, Settings()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        if failure is RuntimeFencedError:
            with pytest.raises(RuntimeFencedError):
                await client.get("/v1/ontology")
        else:
            response = await client.get("/v1/ontology")
            assert not response.json()["readiness"]["processing_ready"]


@pytest.mark.parametrize(
    ("applied", "extra", "override", "processing", "evaluated", "diagnostic"),
    [
        ("initial", {}, False, True, True, False),
        ("initial", {"eval_pending": ["demo"]}, False, True, False, False),
        ("rebuild", {"gate_passed": True}, False, True, True, False),
        ("rebuild", {"gate_passed": False}, False, False, False, False),
        ("rebuild", {"gate_passed": False, "gate_skipped": True}, False, False, False, True),
        ("rebuild", {"gate_passed": False}, True, True, False, True),
        ("rebuild", {"gate_passed": True, "gate_skipped": True}, False, True, False, True),
    ],
)
async def test_status_distinguishes_processing_from_evaluated_readiness(
    applied, extra, override, processing, evaluated, diagnostic
):
    graph, settings = MemoryGraphStore(), Settings(ontology={"allow_breaking": override})
    await record_state(graph, BASE, applied=applied, extra=extra)
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    app.state.graph_store, app.state.ontology, app.state.settings = graph, BASE, settings
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        readiness = (await client.get("/v1/ontology")).json()["readiness"]
    assert readiness["processing_ready"] is processing
    assert readiness["evaluation_ready"] is evaluated
    assert readiness["diagnostic_only"] is diagnostic
    if processing:
        await reconcile(
            graph,
            await _ledger(),
            PackProjector(BASE, frozenset()),
            **(OPTIONS | {"allow_breaking": override}),
        )
    else:
        with pytest.raises(OntologyChangeRefusedError):
            await reconcile(graph, await _ledger(), PackProjector(BASE, frozenset()), **OPTIONS)


async def test_matching_version_label_cannot_hide_different_recorded_pack_definitions() -> None:
    from context_graph.ontology.versioning import STATE_REF
    from context_graph.ports.pack_graph import NodeWrite
    from tests.unit.test_pack_versioning import _registry

    graph = MemoryGraphStore()
    different = _registry(**{"version: 1.0.0": "version: 2.0.0", "number: int": "number: string"})
    await record_state(graph, different, applied="initial")
    # A corrupt metadata label is not proof its saved definitions match.
    await graph.upsert_nodes([NodeWrite(STATE_REF, {"version": BASE.version})])
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    app.state.graph_store, app.state.ontology, app.state.settings = graph, BASE, Settings()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        body = (await client.get("/v1/ontology")).json()
    assert body["change"]["kind"] == "breaking"
    assert not body["readiness"]["processing_ready"]
    assert not body["readiness"]["evaluation_ready"]
    assert body["readiness"]["pending_packs"] == ["demo"]
    with pytest.raises(OntologyChangeRefusedError):
        await reconcile(graph, await _ledger(), PackProjector(BASE, frozenset()), **OPTIONS)


async def test_corrected_rebuild_restores_eligibility_without_an_extra_evaluation(tmp_path):
    from context_graph.ontology.__main__ import evaluate_graph
    from context_graph.ontology.rebuild import rebuild
    from context_graph.ontology.versioning import EvalPending
    from tests.unit.test_pack_versioning import DEMO_INTENTS, _eval_set, _registry

    registry, graph, log = _registry(**DEMO_INTENTS), MemoryGraphStore(), await _ledger()
    bad, good = tmp_path / "bad", tmp_path / "good"
    bad.mkdir()
    good.mkdir()
    _eval_set(bad, ["Ticket:t|2"])
    _eval_set(good, ["Ticket:t|1"])
    projector = PackProjector(registry, frozenset())
    await rebuild(log, graph, projector, Settings(), eval_dirs=[bad])
    from context_graph.ontology.versioning import read_state

    failed_state = await read_state(graph)
    await evaluate_graph(Settings(), graph, registry, [good], record=True)
    assert await read_state(graph) == failed_state
    report = await rebuild(log, graph, projector, Settings(), eval_dirs=[good])
    assert report.passed
    assert await EvalPending(graph, registry, ttl_s=0).packs() == frozenset()


@pytest.mark.parametrize("newer_api", [False, True])
async def test_compatible_version_skew_preserves_existing_query_eligibility(newer_api):
    from context_graph.ontology.versioning import EvalPending
    from tests.unit.test_pack_versioning import DEMO_INTENTS, _registry

    old = _registry(**DEMO_INTENTS)
    new = _registry(
        **DEMO_INTENTS,
        **{"version: 1.0.0": "version: 1.1.0", "sha: string}": "sha: string, note: string}"},
    )
    graph = MemoryGraphStore()
    await record_state(graph, old if newer_api else new, applied="initial")
    assert await EvalPending(graph, new if newer_api else old, ttl_s=0).packs() == frozenset()


async def test_override_cannot_erase_failed_build_marker_on_pack_change():
    from context_graph.ontology.versioning import EvalPending, read_state
    from tests.unit.test_pack_versioning import DEMO_INTENTS, _registry

    old = _registry(**DEMO_INTENTS)
    new = _registry(
        **DEMO_INTENTS,
        **{"version: 1.0.0": "version: 1.1.0", "sha: string}": "sha: string, note: string}"},
    )
    graph, log = MemoryGraphStore(), await _ledger()
    await record_state(graph, old, applied="rebuild", extra={"gate_passed": False})
    await reconcile(
        graph, log, PackProjector(new, frozenset()), **(OPTIONS | {"allow_breaking": True})
    )
    assert (await read_state(graph)).failed_gate
    assert await EvalPending(graph, new, ttl_s=0).packs() == frozenset({"demo"})
    with pytest.raises(OntologyChangeRefusedError):
        await reconcile(graph, log, PackProjector(new, frozenset()), **OPTIONS)


async def test_passing_rebuild_clears_a_recorded_failed_evaluation(tmp_path) -> None:
    from context_graph.ontology.__main__ import evaluate_graph
    from context_graph.ontology.rebuild import rebuild
    from context_graph.ontology.versioning import EvalPending, read_state
    from tests.unit.test_pack_versioning import DEMO_INTENTS, _eval_set, _registry

    registry, graph, log = _registry(**DEMO_INTENTS), MemoryGraphStore(), await _ledger()
    bad, good = tmp_path / "bad", tmp_path / "good"
    bad.mkdir()
    good.mkdir()
    _eval_set(bad, ["Ticket:t|2"])
    _eval_set(good, ["Ticket:t|1"])
    projector = PackProjector(registry, frozenset())
    await rebuild(log, graph, projector, Settings(), eval_dirs=[], skip_gate=True)
    reports = await evaluate_graph(Settings(), graph, registry, [bad], record=True)
    assert reports and not all(r.passed for r in reports)
    assert (await read_state(graph)).properties["eval_pending"] == ["demo"]
    report = await rebuild(log, graph, projector, Settings(), eval_dirs=[good])
    assert report.passed
    assert (await read_state(graph)).properties["eval_pending"] == []
    assert await EvalPending(graph, registry, ttl_s=0).packs() == frozenset()
