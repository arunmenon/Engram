"""Required source gaps must not pass a replacement-graph build."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.adapters.memory.log import MemoryEventLog
from context_graph.domain.pack_projection import PackProjector
from context_graph.ontology.rebuild import rebuild
from context_graph.ports.errors import RuntimeFencedError
from context_graph.settings import Settings
from tests.unit.test_pack_versioning import DEMO_INTENTS, _eval_set, _event, _registry


async def retained_history() -> MemoryEventLog:
    now = datetime(2026, 11, 26, tzinfo=UTC)
    log = MemoryEventLog(clock=lambda: now.timestamp())
    for number, days in [(1, 0), (2, 3)]:
        event, payload = _event(
            "demo.ticket.opened",
            {"tracker": "t", "number": number, "title": f"Ticket {number}"},
            number,
        )
        await log.append(
            event.model_copy(update={"occurred_at": now - timedelta(days=days)}), payload
        )
    return log


@pytest.mark.parametrize("skip_gate", [False, True])
async def test_expired_required_document_cannot_pass_even_when_questions_pass(tmp_path, skip_gate):
    log, graph = await retained_history(), MemoryGraphStore()
    registry = _registry(**DEMO_INTENTS)
    _eval_set(tmp_path, ["Ticket:t|1"])
    assert await log.expire(max_age_days=1) == (0, 1)
    report = await rebuild(
        log,
        graph,
        PackProjector(registry, frozenset()),
        Settings(),
        eval_dirs=[tmp_path],
        skip_gate=skip_gate,
    )
    assert report.events == 2 and report.missing_documents == 1
    assert report.gate_skipped if skip_gate else all(r.passed for r in report.gate)
    assert not report.passed


@pytest.mark.parametrize("allow_breaking", [False, True])
async def test_incomplete_target_cannot_start_even_with_processing_override(
    tmp_path, allow_breaking
):
    from context_graph.ontology.versioning import OntologyChangeRefusedError, read_state, reconcile
    from tests.unit.test_pack_versioning import OPTIONS

    log, graph = await retained_history(), MemoryGraphStore()
    registry = _registry(**DEMO_INTENTS)
    _eval_set(tmp_path, ["Ticket:t|1"])
    await log.expire(max_age_days=1)
    await rebuild(
        log, graph, PackProjector(registry, frozenset()), Settings(), eval_dirs=[tmp_path]
    )
    with pytest.raises(OntologyChangeRefusedError, match="incomplete"):
        await reconcile(
            graph,
            log,
            PackProjector(registry, frozenset()),
            **(OPTIONS | {"allow_breaking": allow_breaking}),
        )
    state = await read_state(graph)
    assert state is not None and state.properties["rebuild_complete"] is False


async def test_status_never_calls_an_incomplete_build_processing_ready(tmp_path):
    from context_graph.ontology.versioning import read_state, status_for_state

    log, graph = await retained_history(), MemoryGraphStore()
    registry = _registry(**DEMO_INTENTS)
    await log.expire(max_age_days=1)
    await rebuild(
        log, graph, PackProjector(registry, frozenset()), Settings(), eval_dirs=[], skip_gate=True
    )
    status = status_for_state(await read_state(graph), registry, allow_breaking=True)
    assert not status["readiness"]["processing_ready"]
    assert not status["readiness"]["evaluation_ready"]
    assert status["graph"]["rebuild_complete"] is False


@pytest.mark.parametrize("failure", [OSError, asyncio.CancelledError, RuntimeFencedError])
async def test_interrupted_build_stays_blocked_and_recovers_on_fresh_target(monkeypatch, failure):
    from context_graph.ontology.versioning import OntologyChangeRefusedError, read_state, reconcile
    from tests.unit.test_pack_versioning import BASE, OPTIONS

    log, graph = await retained_history(), MemoryGraphStore()
    settings = Settings(consumer={"projection_batch_size": 1}, ontology={"replay_batch_size": 1})
    original = log.read_after

    async def interrupted(position, limit):
        if position is not None:
            raise failure("source read interrupted")
        return await original(position, limit)

    monkeypatch.setattr(log, "read_after", interrupted)
    with pytest.raises(failure):
        await rebuild(
            log, graph, PackProjector(BASE, frozenset()), settings, eval_dirs=[], skip_gate=True
        )
    state = await read_state(graph)
    assert state is not None and state.properties["rebuild_in_progress"] is True
    with pytest.raises(OntologyChangeRefusedError, match="incomplete"):
        await reconcile(
            graph, log, PackProjector(BASE, frozenset()), **(OPTIONS | {"allow_breaking": True})
        )
    monkeypatch.setattr(log, "read_after", original)
    from context_graph.ontology.rebuild import RebuildRefusedError

    with pytest.raises(RebuildRefusedError, match="fresh"):
        await rebuild(
            log, graph, PackProjector(BASE, frozenset()), settings, eval_dirs=[], skip_gate=True
        )
    replacement = MemoryGraphStore()
    report = await rebuild(
        log, replacement, PackProjector(BASE, frozenset()), settings, eval_dirs=[], skip_gate=True
    )
    assert report.passed
    assert (await read_state(graph)).incomplete_rebuild
    assert not (await read_state(replacement)).incomplete_rebuild
    await reconcile(replacement, log, PackProjector(BASE, frozenset()), **OPTIONS)


async def test_document_lost_between_ledger_scan_and_projection_cannot_pass(monkeypatch):
    from tests.unit.test_pack_versioning import BASE

    log, graph = await retained_history(), MemoryGraphStore()
    missing_id = (await log.read_after(None, 10))[1].event_id
    original = log.get_documents

    async def lost_during_fetch(ids):
        docs = await original(ids)
        return [
            None if event_id == missing_id else doc for event_id, doc in zip(ids, docs, strict=True)
        ]

    monkeypatch.setattr(log, "get_documents", lost_during_fetch)
    report = await rebuild(
        log, graph, PackProjector(BASE, frozenset()), Settings(), eval_dirs=[], skip_gate=True
    )
    assert not report.passed
    assert report.missing_documents == 1


async def test_original_archived_event_can_rebuild_a_fresh_complete_target(tmp_path):
    from context_graph.adapters.fs.archive import FilesystemArchiveStore
    from context_graph.ontology.versioning import read_state, reconcile
    from context_graph.ports.event_log import ImportedEvent
    from context_graph.ports.pack_graph import NodeRef
    from tests.unit.test_pack_versioning import OPTIONS

    log, graph = await retained_history(), MemoryGraphStore()
    registry = _registry(**DEMO_INTENTS)
    _eval_set(tmp_path, ["Ticket:t|1"])
    original_entries = await log.read_after(None, 10)
    archive = FilesystemArchiveStore(tmp_path / "archive")
    assert await log.expire(max_age_days=1, archive_store=archive) == (1, 1)
    assert not (
        await rebuild(
            log, graph, PackProjector(registry, frozenset()), Settings(), eval_dirs=[tmp_path]
        )
    ).passed
    saved = await archive.list_archives()
    restored = await archive.restore_archive(saved[0]["archive_id"])
    by_id = {str(doc["event_id"]): doc for doc in restored}
    by_id.update(
        {
            entry.event_id: entry.document
            for entry in await log.read_after(None, 10)
            if entry.document
        }
    )
    recovered, replacement = MemoryEventLog(), MemoryGraphStore()
    await recovered.append_imported(
        [ImportedEvent(by_id[e.event_id], e.position) for e in original_entries]
    )
    report = await rebuild(
        recovered,
        replacement,
        PackProjector(registry, frozenset()),
        Settings(),
        eval_dirs=[tmp_path],
    )
    assert report.passed and report.projection_complete and report.evaluation_passed
    assert report.events == 2 and report.missing_documents == 0
    assert not (await read_state(replacement)).incomplete_rebuild
    assert (await replacement.get_nodes([NodeRef("Ticket", "Ticket:t|2")]))[
        NodeRef("Ticket", "Ticket:t|2")
    ]["title"] == "Ticket 2"
    recovered_entries = await recovered.read_after(None, 10)
    assert [e.event_id for e in recovered_entries] == [e.event_id for e in original_entries]
    assert [e.document["payload"] for e in recovered_entries] == [
        e.document["payload"] for e in original_entries
    ]
    assert (await log.read_after(None, 10))[1].document is None
    await reconcile(replacement, recovered, PackProjector(registry, frozenset()), **OPTIONS)


@pytest.mark.parametrize("skip_gate", [False, True])
async def test_command_fails_and_separates_history_from_question_results(
    tmp_path, monkeypatch, capsys, skip_gate
):
    import json
    from types import SimpleNamespace

    from context_graph.ontology import __main__ as cli

    log, graph = await retained_history(), MemoryGraphStore()
    registry = _registry(**DEMO_INTENTS)
    (tmp_path / "demo.pack.yaml").write_text(registry.pack("demo").canonical_json())
    _eval_set(tmp_path, ["Ticket:t|1"])
    await log.expire(max_age_days=1)
    settings = Settings(
        ontology={"packs": ["demo"], "builtin_packs": [], "pack_dirs": [str(tmp_path)]}
    )
    target = Settings(
        storage={"graph": "memory", "event_log": "memory"}, ontology=settings.ontology
    )

    async def close():
        pass

    async def opened(configuration):
        return SimpleNamespace(event_log=log, graph=graph, close=close)

    monkeypatch.setattr(cli, "open_stores", opened)
    assert await cli.run_rebuild(settings, target, [], skip_gate=skip_gate, force=False) == 1
    output = capsys.readouterr().out
    body = json.loads(output[output.index("{\n") :])
    assert not body["passed"] and not body["projection_complete"]
    assert body["evaluation_passed"] is (None if skip_gate else True)
    assert body["missing_documents"] == 1
    assert not body["readiness"]["processing_ready"]


async def test_authority_precheck_makes_no_target_writes(monkeypatch):
    from context_graph.ontology.versioning import read_state
    from context_graph.ports.errors import RuntimeFencedError
    from tests.unit.test_pack_versioning import BASE

    log, graph = await retained_history(), MemoryGraphStore()
    monkeypatch.setattr(log, "requires_source_provenance", True, raising=False)
    with pytest.raises(RuntimeFencedError):
        await rebuild(
            log, graph, PackProjector(BASE, frozenset()), Settings(), eval_dirs=[], skip_gate=True
        )
    assert await read_state(graph) is None
    assert (await graph.get_graph_stats())["total_nodes"] == 0


@pytest.mark.parametrize("force", [False, True])
async def test_trimming_source_cannot_make_failed_target_look_recovered(tmp_path, force):
    from context_graph.ontology.rebuild import RebuildRefusedError
    from context_graph.ontology.versioning import read_state

    clock = [datetime(2026, 11, 26, tzinfo=UTC)]
    log, graph = MemoryEventLog(clock=lambda: clock[0].timestamp()), MemoryGraphStore()
    registry = _registry(**DEMO_INTENTS)
    for number, days in [(1, 0), (2, 3)]:
        event, payload = _event(
            "demo.ticket.opened", {"tracker": "t", "number": number, "title": str(number)}, number
        )
        await log.append(
            event.model_copy(update={"occurred_at": clock[0] - timedelta(days=days)}), payload
        )
    await log.expire(1)
    _eval_set(tmp_path, ["Ticket:t|1"])
    first = await rebuild(
        log, graph, PackProjector(registry, frozenset()), Settings(), eval_dirs=[tmp_path]
    )
    assert not first.passed and first.missing_documents == 1
    failed_state = await read_state(graph)
    clock[0] += timedelta(days=8)
    assert await log.trim(7, []) == 2
    with pytest.raises(RebuildRefusedError, match="fresh"):
        await rebuild(
            log,
            graph,
            PackProjector(registry, frozenset()),
            Settings(),
            eval_dirs=[tmp_path],
            force=force,
        )
    assert await read_state(graph) == failed_state


@pytest.mark.parametrize("allow_breaking", [False, True])
async def test_legacy_failed_diagnostic_is_known_incomplete(allow_breaking):
    from context_graph.ontology.versioning import (
        OntologyChangeRefusedError,
        reconcile,
        record_state,
    )
    from tests.unit.test_pack_versioning import BASE, OPTIONS

    log, graph = await retained_history(), MemoryGraphStore()
    await record_state(
        graph, BASE, applied="rebuild", extra={"gate_skipped": True, "gate_passed": False}
    )
    with pytest.raises(OntologyChangeRefusedError, match="incomplete"):
        await reconcile(
            graph,
            log,
            PackProjector(BASE, frozenset()),
            **(OPTIONS | {"allow_breaking": allow_breaking}),
        )


async def test_evaluation_status_is_current_after_skip_and_recorded_evaluation(tmp_path):
    from context_graph.ontology.__main__ import evaluate_graph
    from context_graph.ontology.versioning import read_state, status_for_state

    registry, log, graph = _registry(**DEMO_INTENTS), await retained_history(), MemoryGraphStore()
    _eval_set(tmp_path, ["Ticket:t|1"])
    projector = PackProjector(registry, frozenset())
    await rebuild(log, graph, projector, Settings(), eval_dirs=[tmp_path])
    await rebuild(log, graph, projector, Settings(), eval_dirs=[], skip_gate=True)
    status = status_for_state(await read_state(graph), registry)
    assert status["graph"]["evaluation_passed"] is None
    assert status["graph"]["evaluation_status"] == "skipped"
    failed = tmp_path / "failed"
    failed.mkdir()
    _eval_set(failed, ["Ticket:t|2"])
    await evaluate_graph(Settings(), graph, registry, [failed], record=True)
    status = status_for_state(await read_state(graph), registry)
    assert status["graph"]["evaluation_passed"] is False
    assert status["graph"]["evaluation_status"] == "failed"
    await evaluate_graph(Settings(), graph, registry, [tmp_path], record=True)
    status = status_for_state(await read_state(graph), registry)
    assert status["graph"]["evaluation_passed"] is True
    assert status["graph"]["evaluation_status"] == "passed"


async def test_write_failure_stays_incomplete_and_recovers_on_fresh_target(monkeypatch):
    from context_graph.ontology.rebuild import RebuildRefusedError
    from context_graph.ontology.versioning import OntologyChangeRefusedError, read_state, reconcile
    from tests.unit.test_pack_versioning import BASE, OPTIONS

    log, graph = await retained_history(), MemoryGraphStore()
    second = (await log.read_after(None, 10))[1]
    original = graph.merge_event_nodes_batch

    async def failing(nodes):
        if any(str(node.event_id) == second.event_id for node in nodes):
            raise RuntimeError("required write failed")
        return await original(nodes)

    monkeypatch.setattr(graph, "merge_event_nodes_batch", failing)
    report = await rebuild(
        log, graph, PackProjector(BASE, frozenset()), Settings(), eval_dirs=[], skip_gate=True
    )
    assert not report.passed and report.failed_events == 1 and not report.projection_complete
    assert (await read_state(graph)).properties["rebuild_failure_count"] == 1
    with pytest.raises(OntologyChangeRefusedError, match="incomplete"):
        await reconcile(
            graph, log, PackProjector(BASE, frozenset()), **(OPTIONS | {"allow_breaking": True})
        )
    monkeypatch.setattr(graph, "merge_event_nodes_batch", original)
    with pytest.raises(RebuildRefusedError, match="fresh"):
        await rebuild(
            log,
            graph,
            PackProjector(BASE, frozenset()),
            Settings(),
            eval_dirs=[],
            skip_gate=True,
            force=True,
        )
    replacement = MemoryGraphStore()
    assert (
        await rebuild(
            log,
            replacement,
            PackProjector(BASE, frozenset()),
            Settings(),
            eval_dirs=[],
            skip_gate=True,
        )
    ).passed


async def test_missing_count_is_full_while_position_examples_are_bounded():
    from tests.unit.test_pack_versioning import BASE

    log = MemoryEventLog()
    for number in range(105):
        event, payload = _event(
            "demo.ticket.opened", {"tracker": "t", "number": number, "title": "old"}, number
        )
        await log.append(event, payload)
    assert await log.expire(max_age_days=0) == (0, 105)
    report = await rebuild(
        log,
        MemoryGraphStore(),
        PackProjector(BASE, frozenset()),
        Settings(),
        eval_dirs=[],
        skip_gate=True,
    )
    assert report.missing_documents == 105
    assert len(report.missing_positions) == 100
    assert len(set(report.missing_positions)) == 100
    assert not report.passed
