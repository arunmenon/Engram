"""A removed assignment cannot leave old values through an unnoticed replay."""

import pytest

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.domain.pack_projection import PackProjector
from context_graph.domain.pack_versioning import classify_change
from context_graph.ontology.rebuild import rebuild
from context_graph.ontology.versioning import (
    OntologyChangeRefusedError,
    read_state,
    reconcile,
    record_state,
)
from context_graph.settings import Settings
from tests.unit.test_pack_versioning import BASE, TICKET, _ledger, _project_all, _registry


async def test_removed_node_assignment_replay_differs_from_fresh_and_normal_update_must_refuse():
    old = BASE
    new = _registry(**{"version: 1.0.0": "version: 2.0.0", "set: {title: $.title}": "set: {}"})
    log = await _ledger()
    event_ids = [entry.event_id for entry in await log.read_after(None, 100)]
    documents_before = await log.get_documents(event_ids)
    original, diagnostic, fresh = MemoryGraphStore(), MemoryGraphStore(), MemoryGraphStore()
    await _project_all(log, original, old)
    await record_state(original, old, applied="initial")
    state_before = await read_state(original)
    record_before = await original.get_nodes([TICKET])
    assert record_before[TICKET]["title"] == "A"

    # Direct replay on a disposable graph establishes the unsafe update mode;
    # this is not adoption of the new pack on the original graph.
    await _project_all(log, diagnostic, old)
    await _project_all(log, diagnostic, new)
    assert (await diagnostic.get_nodes([TICKET]))[TICKET]["title"] == "A"
    report = await rebuild(log, fresh, PackProjector(new, frozenset()), Settings(), eval_dirs=[])
    assert report.passed and report.events == 3
    assert "title" not in (await fresh.get_nodes([TICKET]))[TICKET]

    plan = classify_change(old, new)
    assert plan.kind == "breaking"
    assert not plan.replay_event_types
    assert not plan.version_problems
    assert any("property assignment" in reason and "title" in reason for reason in plan.reasons)
    with pytest.raises(OntologyChangeRefusedError, match="property assignment"):
        await reconcile(
            original,
            log,
            PackProjector(new, frozenset()),
            allow_breaking=False,
            batch_size=2,
            lookup_limit=100,
        )
    assert await read_state(original) == state_before
    assert await original.get_nodes([TICKET]) == record_before
    assert await log.get_documents(event_ids) == documents_before


@pytest.mark.parametrize(
    "old_version,new_version,permitted",
    [
        ("1.0.0", "1.1.0", False),
        ("1.0.0", "2.0.0", True),
        ("0.1.0", "0.1.1", False),
        ("0.1.0", "0.2.0", True),
    ],
)
def test_removed_assignment_enforces_normal_and_pre_one_versions(
    old_version, new_version, permitted
):
    old = _registry(**{"version: 1.0.0": "version: " + old_version})
    new = _registry(
        **{
            "version: 1.0.0": "version: " + new_version,
            "set: {title: $.title}": "set: {}",
        }
    )
    plan = classify_change(old, new)
    assert plan.kind == "breaking"
    assert bool(plan.version_problems) is not permitted


def test_added_assignment_and_changed_expression_remain_mapping_updates():
    added = _registry(
        **{
            "version: 1.0.0": "version: 1.1.0",
            "title: string}": "title: string, summary: string}",
            "set: {title: $.title}": "set: {title: $.title, summary: $.summary}",
        }
    )
    changed = _registry(
        **{
            "version: 1.0.0": "version: 1.1.0",
            "set: {title: $.title}": "set: {title: $.summary}",
        }
    )
    for new in (added, changed):
        plan = classify_change(BASE, new)
        assert plan.kind == "mapping"
        assert plan.replay_event_types == {"demo.ticket.opened"}
        assert not plan.version_problems
    assert classify_change(BASE, BASE).kind == "none"


async def test_explicit_clear_remains_supported_in_place():
    new = _registry(
        **{
            "version: 1.0.0": "version: 1.1.0",
            "set: {title: $.title}": "set: {title: {value: null, on_null: clear}}",
            "projection:": "processing: {requires: [pack.properties.v1]}\nprojection:",
        }
    )
    log, graph = await _ledger(), MemoryGraphStore()
    await _project_all(log, graph, BASE)
    await record_state(graph, BASE, applied="initial")
    assert (await graph.get_nodes([TICKET]))[TICKET]["title"] == "A"
    plan = await reconcile(
        graph,
        log,
        PackProjector(new, frozenset()),
        allow_breaking=False,
        batch_size=2,
        lookup_limit=100,
    )
    assert plan.kind == "mapping"
    assert "title" not in (await graph.get_nodes([TICKET]))[TICKET]


async def test_removed_relationship_assignment_needs_rebuild_too():
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.domain.ontology import OntologyRegistry, Pack
    from context_graph.ports.pack_graph import NodeRef
    from tests.fixtures.events import make_event
    from tests.unit.test_link_default_impact import registry
    from tests.unit.test_pack_versioning import CORE

    data = registry(defaults=False).pack("demo").model_dump(by_alias=True)
    data["types"]["edges"]["RESOLVES"]["properties"]["reviewer"] = "string"
    data["projection"][0]["edges"][0]["set"] = {"reviewer": "$.reviewer"}
    old = OntologyRegistry([CORE, Pack.model_validate(data)])
    data["pack"]["version"] = "2.0.0"
    data["projection"][0]["edges"][0]["set"] = {}
    new = OntologyRegistry([CORE, Pack.model_validate(data)])
    assert old.edge_type("RESOLVES").properties == new.edge_type("RESOLVES").properties
    log = MemoryEventLog()
    event = make_event(event_type="demo.ticket.opened")
    payload = {"tracker": "t", "number": 1, "sha": "a", "reviewer": "Alex"}
    await log.append(event, payload)
    graph, fresh = MemoryGraphStore(), MemoryGraphStore()
    await _project_all(log, graph, old)
    await record_state(graph, old, applied="initial")
    ref = NodeRef("Fix", "Fix:a")
    links_before = await graph.neighbors([ref], ["RESOLVES"], "out", 10)
    assert links_before[0]["properties"]["reviewer"] == "Alex"
    diagnostic = MemoryGraphStore()
    await _project_all(log, diagnostic, old)
    await _project_all(log, diagnostic, new)
    replay_links = await diagnostic.neighbors([ref], ["RESOLVES"], "out", 10)
    assert replay_links[0]["properties"]["reviewer"] == "Alex"
    plan = classify_change(old, new)
    assert plan.kind == "breaking"
    assert any("reviewer" in r for r in plan.reasons)
    with pytest.raises(OntologyChangeRefusedError, match="property assignment"):
        await reconcile(
            graph,
            log,
            PackProjector(new, frozenset()),
            allow_breaking=False,
            batch_size=2,
            lookup_limit=100,
        )
    assert await graph.neighbors([ref], ["RESOLVES"], "out", 10) == links_before
    report = await rebuild(log, fresh, PackProjector(new, frozenset()), Settings(), eval_dirs=[])
    assert report.passed
    fresh_links = await fresh.neighbors([ref], ["RESOLVES"], "out", 10)
    assert len(fresh_links) == 1 and "reviewer" not in fresh_links[0]["properties"]


async def test_static_null_preserve_stops_writing_and_requires_reconstruction():
    capability = {"projection:": "processing: {requires: [pack.properties.v1]}\nprojection:"}
    old = _registry(
        **{
            **capability,
            "set: {title: $.title}": "set: {title: {value: $.title}}",
        }
    )
    new = _registry(
        **{
            **capability,
            "version: 1.0.0": "version: 2.0.0",
            "set: {title: $.title}": "set: {title: {value: null}}",
        }
    )
    log = await _ledger()
    event_ids = [entry.event_id for entry in await log.read_after(None, 100)]
    documents_before = await log.get_documents(event_ids)
    original, diagnostic, fresh = MemoryGraphStore(), MemoryGraphStore(), MemoryGraphStore()
    await _project_all(log, original, old)
    await record_state(original, old, applied="initial")
    state_before = await read_state(original)
    node_before = await original.get_nodes([TICKET])
    assert node_before[TICKET]["title"] == "A"
    await _project_all(log, diagnostic, old)
    await _project_all(log, diagnostic, new)
    assert (await diagnostic.get_nodes([TICKET]))[TICKET]["title"] == "A"
    report = await rebuild(log, fresh, PackProjector(new, frozenset()), Settings(), eval_dirs=[])
    assert report.passed and "title" not in (await fresh.get_nodes([TICKET]))[TICKET]
    plan = classify_change(old, new)
    assert plan.kind == "breaking" and not plan.version_problems
    with pytest.raises(OntologyChangeRefusedError, match="property assignment"):
        await reconcile(
            original,
            log,
            PackProjector(new, frozenset()),
            allow_breaking=False,
            batch_size=2,
            lookup_limit=100,
        )
    assert await read_state(original) == state_before
    assert await original.get_nodes([TICKET]) == node_before
    assert await log.get_documents(event_ids) == documents_before
