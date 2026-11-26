"""Changed relationship defaults must not look like a harmless hot update."""

from context_graph.domain.ontology import OntologyRegistry, Pack
from context_graph.domain.pack_versioning import classify_change
from tests.unit.test_pack_versioning import BASE, CORE


def registry(status="confirmed", *, version="1.0.0", defaults=True):
    data = BASE.pack("demo").model_dump(by_alias=True)
    data["pack"]["version"] = version
    edge = data["types"]["edges"]["RESOLVES"]
    edge["properties"]["link_status"] = {"enum": ["proposed", "confirmed", "rejected"]}
    edge["requires"] = ["link_status"] if defaults else []
    data["types"]["link_policy"] = (
        {"link_status": {"declared_links_start_as": status}} if status else None
    )
    data["projection"][0]["upsert"].append({"type": "Fix", "key": {"sha": "$.sha"}})
    data["projection"][0]["edges"] = [
        {
            "type": "RESOLVES",
            "from": {"type": "Fix", "key": {"sha": "$.sha"}},
            "to": {"type": "Ticket", "key": {"tracker": "$.tracker", "number": "$.number"}},
        }
    ]
    return OntologyRegistry([CORE, Pack.model_validate(data)])


def test_changed_effective_relationship_default_requires_rebuild_and_major_version():
    old, new = registry(), registry("proposed", version="1.1.0")
    assert old.edge_type("RESOLVES").link_defaults["link_status"] == "confirmed"
    assert new.edge_type("RESOLVES").link_defaults["link_status"] == "proposed"
    plan = classify_change(old, new)
    assert plan.kind == "breaking"
    assert plan.pack_changes["demo"] == "breaking"
    assert any("RESOLVES" in r and "defaults changed" in r and "rebuild" in r for r in plan.reasons)
    assert any("major version" in p for p in plan.version_problems)
    assert not plan.replay_event_types


def test_default_addition_and_removal_require_reconstruction_without_schema_changes():
    without, with_defaults = registry(defaults=False), registry(version="2.0.0")
    assert (
        without.edge_type("RESOLVES").properties == with_defaults.edge_type("RESOLVES").properties
    )
    for old, new in (
        (without, with_defaults),
        (registry(), registry(version="2.0.0", defaults=False)),
    ):
        plan = classify_change(old, new)
        assert plan.kind == "breaking"
        assert not plan.version_problems
        assert not plan.replay_event_types


def test_implicit_confirmed_and_explicit_confirmed_are_the_same_effective_default():
    old, new = registry(None), registry(version="1.1.0")
    assert old.edge_type("RESOLVES").link_defaults == new.edge_type("RESOLVES").link_defaults
    plan = classify_change(old, new)
    assert plan.kind == "additive"
    assert not plan.version_problems
    assert not any("defaults changed" in r for r in plan.reasons)
    assert not plan.replay_event_types


def test_default_changes_preserve_pre_one_version_requirements():
    old = registry(version="0.1.0")
    insufficient = classify_change(old, registry("proposed", version="0.1.1"))
    sufficient = classify_change(old, registry("proposed", version="0.2.0"))
    assert any("minor version" in p for p in insufficient.version_problems)
    assert not sufficient.version_problems


async def test_normal_update_refuses_changed_defaults_and_fresh_rebuild_reconstructs_links():
    import pytest

    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.domain.pack_projection import PackProjector
    from context_graph.ontology.rebuild import project_ledger, rebuild
    from context_graph.ontology.versioning import (
        OntologyChangeRefusedError,
        read_state,
        reconcile,
        record_state,
    )
    from context_graph.ports.pack_graph import NodeRef
    from context_graph.settings import Settings
    from tests.fixtures.events import make_event

    old, log, graph = registry(), MemoryEventLog(), MemoryGraphStore()
    event = make_event(event_type="demo.ticket.opened")
    payload = {"tracker": "t", "number": 1, "sha": "a", "title": "Retained source"}
    await log.append(event, payload)
    await project_ledger(log, graph, PackProjector(old, frozenset()), Settings(), batch_size=2)
    await record_state(graph, old, applied="initial")
    source_before = await log.get_documents([str(event.event_id)])
    state_before = await read_state(graph)
    ref = NodeRef("Fix", "Fix:a")
    old_links = await graph.neighbors([ref], ["RESOLVES"], "out", 10)
    assert len(old_links) == 1
    assert old_links[0]["properties"]["link_status"] == "confirmed"

    for new in (registry("proposed", version="2.0.0"), registry(version="2.0.0", defaults=False)):
        with pytest.raises(OntologyChangeRefusedError, match="defaults changed"):
            await reconcile(
                graph,
                log,
                PackProjector(new, frozenset()),
                allow_breaking=False,
                batch_size=2,
                lookup_limit=100,
            )
        assert await read_state(graph) == state_before
        assert await graph.neighbors([ref], ["RESOLVES"], "out", 10) == old_links
        target = MemoryGraphStore()
        report = await rebuild(
            log, target, PackProjector(new, frozenset()), Settings(), eval_dirs=[]
        )
        assert report.passed and report.events == 1
        links = await target.neighbors([ref], ["RESOLVES"], "out", 10)
        assert len(links) == 1
        expected = "proposed" if new.edge_type("RESOLVES").link_defaults else None
        assert links[0]["properties"].get("link_status") == expected
        assert await log.get_documents([str(event.event_id)]) == source_before
        assert await graph.neighbors([ref], ["RESOLVES"], "out", 10) == old_links
