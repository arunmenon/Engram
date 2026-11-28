"""Composed definitions retain the version responsibility of their contributor."""

import pytest

from context_graph.domain.ontology import OntologyRegistry, Pack
from context_graph.domain.pack_versioning import classify_change
from tests.unit.test_pack_versioning import CORE


def bundle(*, extension=True, rule=True, version="1.0.0", expression="$.label"):
    owner = Pack.model_validate(
        {
            "pack": {"name": "aa", "version": "1.0.0", "requires": ["core>=1.1"]},
            "types": {
                "nodes": {"Thing": {"key": ["id"], "properties": {"id": "string"}}},
                "edges": {"RELATES": {"from": ["Thing"], "to": ["Thing"]}},
            },
            "events": {
                "aa.observed": {
                    "payload_contract": {
                        "properties": {
                            "id": {"type": "string", "required": True},
                            "label": {"type": "string"},
                            "new_label": {"type": "string"},
                        }
                    }
                }
            },
            "projection": [
                {"event": "aa.observed", "upsert": [{"type": "Thing", "key": {"id": "$.id"}}]}
            ],
        }
    )
    contributor = Pack.model_validate(
        {
            "pack": {"name": "bb", "version": version, "requires": ["core>=1.1", "aa>=1.0"]},
            "types": {
                "nodes": {
                    "Other": {"key": ["id"], "properties": {"id": "string", "label": "string"}}
                },
                "extends_core_edges": {"RELATES": {"from": ["Other"], "to": ["Other"]}}
                if extension
                else {},
            },
            "projection": [
                {
                    "event": "aa:aa.observed",
                    "upsert": [
                        {
                            "type": "Other",
                            "key": {"id": "$.id"},
                            "set": {"label": expression},
                        }
                    ],
                }
            ]
            if rule
            else [],
        }
    )
    return OntologyRegistry([CORE, owner, contributor])


def test_removed_foreign_edge_extension_requires_contributor_major_not_unchanged_owner():
    old, new = bundle(), bundle(extension=False, version="1.1.0")
    assert old.pack("aa").canonical_json() == new.pack("aa").canonical_json()
    plan = classify_change(old, new)
    assert plan.kind == "breaking"
    assert plan.pack_changes.get("bb") == "breaking"
    assert "aa" not in plan.pack_changes
    assert any(p.startswith("bb:") and "major version" in p for p in plan.version_problems)


def test_foreign_event_rule_edit_requires_contributor_minor_not_owner_version():
    old, new = bundle(), bundle(expression="$.new_label", version="1.0.1")
    plan = classify_change(old, new)
    assert plan.kind == "mapping"
    assert plan.pack_changes.get("bb") == "mapping"
    assert "aa" not in plan.pack_changes
    assert plan.replay_event_types == {"aa.observed"}
    assert any(p.startswith("bb:") and "minor version" in p for p in plan.version_problems)


def test_foreign_rule_removal_requires_contributor_major_even_with_owner_rule_remaining():
    old, new = bundle(), bundle(rule=False, version="1.1.0")
    plan = classify_change(old, new)
    assert plan.kind == "breaking"
    assert plan.pack_changes.get("bb") == "breaking"
    assert "aa" not in plan.pack_changes
    assert any(p.startswith("bb:") and "major version" in p for p in plan.version_problems)


def test_new_foreign_event_rule_requires_its_contributor_minor_version():
    old, new = bundle(rule=False), bundle(version="1.0.1")
    plan = classify_change(old, new)
    assert plan.kind == "mapping"
    assert plan.pack_changes.get("bb") == "mapping"
    assert "aa" not in plan.pack_changes
    assert any(p.startswith("bb:") and "minor version" in p for p in plan.version_problems)


def test_static_field_removal_keeps_s1_gate_and_charges_the_contributor():
    old, parent = bundle(), bundle(version="1.1.0")
    data = parent.pack("bb").model_dump(by_alias=True)
    data["projection"][0]["upsert"][0]["set"] = {}
    new = OntologyRegistry([CORE, parent.pack("aa"), Pack.model_validate(data)])
    plan = classify_change(old, new)
    assert plan.kind == "breaking"
    assert plan.pack_changes.get("bb") == "breaking"
    assert "aa" not in plan.pack_changes
    assert any(p.startswith("bb:") and "major version" in p for p in plan.version_problems)


@pytest.mark.parametrize(
    "before,after,allowed",
    [
        ("1.0.0", "1.1.0", False),
        ("1.0.0", "2.0.0", True),
        ("0.1.0", "0.1.1", False),
        ("0.1.0", "0.2.0", True),
    ],
)
def test_extension_removal_preserves_contributor_version_rules(before, after, allowed):
    plan = classify_change(bundle(version=before), bundle(extension=False, version=after))
    assert plan.pack_changes["bb"] == "breaking"
    assert bool(plan.version_problems) is not allowed
    assert all(p.startswith("bb:") for p in plan.version_problems)


def test_pre_one_mapping_still_accepts_a_patch_on_the_changed_contributor():
    plan = classify_change(
        bundle(version="0.1.0"), bundle(expression="$.new_label", version="0.1.1")
    )
    assert plan.kind == "mapping"
    assert plan.pack_changes == {"bb": "mapping"}
    assert not plan.version_problems


def third(*, extension=False, expression="$.label", version="1.0.0"):
    return Pack.model_validate(
        {
            "pack": {"name": "cc", "version": version, "requires": ["core>=1.1", "aa>=1.0"]},
            "types": {
                "nodes": {
                    "Third": {"key": ["id"], "properties": {"id": "string", "label": "string"}}
                },
                "extends_core_edges": {"RELATES": {"from": ["Third"], "to": ["Third"]}}
                if extension
                else {},
            },
            "projection": [
                {
                    "event": "aa:aa.observed",
                    "upsert": [
                        {
                            "type": "Third",
                            "key": {"id": "$.id"},
                            "set": {"label": expression},
                        }
                    ],
                }
            ],
        }
    )


def test_multiple_contributors_keep_their_own_rule_severity():
    base, updated = bundle(), bundle(rule=False, version="1.1.0")
    old = OntologyRegistry([*base.packs, third()])
    new = OntologyRegistry([*updated.packs, third(expression="$.new_label", version="1.1.0")])
    plan = classify_change(old, new)
    assert plan.kind == "breaking"
    assert plan.pack_changes == {"bb": "breaking", "cc": "mapping"}
    assert any(p.startswith("bb:") and "major version" in p for p in plan.version_problems)
    assert not any(p.startswith("aa:") or p.startswith("cc:") for p in plan.version_problems)


def test_removed_and_added_extension_charge_different_contributors():
    base, updated = bundle(), bundle(extension=False, version="1.1.0")
    old = OntologyRegistry([*base.packs, third()])
    new = OntologyRegistry([*updated.packs, third(extension=True, version="1.0.1")])
    plan = classify_change(old, new)
    assert plan.kind == "breaking"
    assert plan.pack_changes == {"bb": "breaking", "cc": "additive"}
    assert any(p.startswith("bb:") and "major version" in p for p in plan.version_problems)
    assert any(p.startswith("cc:") and "minor version" in p for p in plan.version_problems)


def test_owner_documentation_edit_does_not_inherit_contributor_breaking_requirement():
    base, updated = bundle(), bundle(extension=False, version="2.0.0")
    data = updated.pack("aa").model_dump(by_alias=True)
    data["pack"].update(version="1.1.0", description="Clarified owner documentation")
    new = OntologyRegistry([CORE, Pack.model_validate(data), updated.pack("bb")])
    plan = classify_change(base, new)
    assert plan.kind == "breaking"
    assert plan.pack_changes == {"bb": "breaking"}
    assert not plan.version_problems


def test_wildcard_endpoint_changes_charge_the_pack_whose_types_changed():
    original = bundle()
    old_data = original.pack("bb").model_dump(by_alias=True)
    old_data["types"]["extends_core_edges"]["RELATES"] = {"from": "*", "to": "*"}
    old = OntologyRegistry([CORE, original.pack("aa"), Pack.model_validate(old_data)])
    new_data = original.pack("bb").model_dump(by_alias=True)
    new_data["pack"]["version"] = "1.1.0"
    new_data["types"]["extends_core_edges"]["RELATES"] = {"from": "*", "to": "*"}
    new_data["types"]["nodes"]["Replacement"] = new_data["types"]["nodes"].pop("Other")
    new_data["projection"][0]["upsert"][0]["type"] = "Replacement"
    new = OntologyRegistry([CORE, original.pack("aa"), Pack.model_validate(new_data)])
    plan = classify_change(old, new)
    assert plan.kind == "breaking"
    assert plan.pack_changes == {"bb": "breaking"}
    assert any(p.startswith("bb:") and "major version" in p for p in plan.version_problems)
    assert not any(p.startswith("aa:") or p.startswith("core:") for p in plan.version_problems)


async def test_normal_reconcile_refuses_contributor_minor_before_changing_recorded_state():
    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.domain.pack_projection import PackProjector
    from context_graph.ontology.versioning import (
        OntologyChangeRefusedError,
        read_state,
        reconcile,
        record_state,
    )
    from context_graph.ports.pack_graph import NodeRef, NodeWrite

    old, new = bundle(), bundle(extension=False, version="1.1.0")
    graph, ledger = MemoryGraphStore(), MemoryEventLog()
    ref = NodeRef("Other", "Other:kept")
    await graph.upsert_nodes([NodeWrite(ref, {"id": "kept", "label": "original"})])
    await record_state(graph, old, applied="initial")
    before, nodes = await read_state(graph), await graph.get_nodes([ref])
    with pytest.raises(OntologyChangeRefusedError, match="bb:.*major version"):
        await reconcile(
            graph,
            ledger,
            PackProjector(new, frozenset()),
            allow_breaking=False,
            batch_size=2,
            lookup_limit=100,
        )
    assert await read_state(graph) == before
    assert await graph.get_nodes([ref]) == nodes


def test_overlapping_extension_still_needs_contributor_version_without_forcing_rebuild():
    base, updated = bundle(rule=False), bundle(rule=False, extension=False, version="1.1.0")
    data = third().model_dump(by_alias=True)
    data["pack"]["requires"].append("bb>=1.0")
    data["types"]["extends_core_edges"] = {
        "RELATES": {
            "from": ["bb:Other"],
            "to": ["bb:Other"],
        }
    }
    shared = Pack.model_validate(data)
    old = OntologyRegistry([*base.packs, shared])
    new = OntologyRegistry([*updated.packs, shared])
    assert old.edge_type("RELATES").from_types == new.edge_type("RELATES").from_types
    assert old.edge_type("RELATES").to_types == new.edge_type("RELATES").to_types
    plan = classify_change(old, new)
    assert plan.kind == "additive" and not plan.replay_event_types
    assert any(p.startswith("bb:") and "major version" in p for p in plan.version_problems)


async def test_adequate_overlap_version_updates_metadata_without_replaying_data(monkeypatch):
    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.domain.pack_projection import PackProjector
    from context_graph.ontology.versioning import reconcile, record_state
    from context_graph.ports.pack_graph import NodeRef, NodeWrite

    base, updated = bundle(rule=False), bundle(rule=False, extension=False, version="2.0.0")
    data = third().model_dump(by_alias=True)
    data["pack"]["requires"].append("bb>=1.0")
    data["types"]["extends_core_edges"] = {
        "RELATES": {
            "from": ["bb:Other"],
            "to": ["bb:Other"],
        }
    }
    shared = Pack.model_validate(data)
    old, new = OntologyRegistry([*base.packs, shared]), OntologyRegistry([*updated.packs, shared])
    graph, ledger = MemoryGraphStore(), MemoryEventLog()
    ref = NodeRef("Other", "Other:kept")
    await graph.upsert_nodes([NodeWrite(ref, {"id": "kept", "label": "original"})])
    await record_state(graph, old, applied="initial")
    nodes_before = await graph.get_nodes([ref])

    async def unexpected_history_read(*args, **kwargs):
        raise AssertionError("metadata-only compatibility change must not replay history")

    monkeypatch.setattr(ledger, "read_after", unexpected_history_read)
    plan = await reconcile(
        graph,
        ledger,
        PackProjector(new, frozenset()),
        allow_breaking=False,
        batch_size=2,
        lookup_limit=100,
    )
    assert plan.kind == "additive" and not plan.version_problems
    assert plan.as_dict()["contributor_changes"] == {"bb": "breaking"}
    assert await graph.get_nodes([ref]) == nodes_before


def test_rule_transfer_checks_contracts_and_conservatively_replays_order_change():
    source = bundle()
    owner = source.pack("aa").model_dump(by_alias=True)
    contributor = source.pack("bb").model_dump(by_alias=True)
    owner["projection"][0]["event"] = "aa:aa.observed"
    owner["projection"][0]["upsert"][0]["type"] = "aa:Thing"
    old = OntologyRegistry([CORE, Pack.model_validate(owner), Pack.model_validate(contributor)])
    transferred = owner["projection"][0]
    owner["projection"] = []
    owner["pack"]["version"] = "1.1.0"
    contributor["projection"].append(transferred)
    contributor["pack"]["version"] = "1.1.0"
    new = OntologyRegistry([CORE, Pack.model_validate(owner), Pack.model_validate(contributor)])
    plan = classify_change(old, new)
    assert plan.kind == "mapping" and plan.replay_event_types == {"aa.observed"}
    assert plan.as_dict()["contributor_changes"] == {"aa": "breaking", "bb": "mapping"}
    assert any(p.startswith("aa:") and "major version" in p for p in plan.version_problems)
    assert not any(p.startswith("bb:") for p in plan.version_problems)


def test_core_provenance_retarget_does_not_charge_unchanged_domain_contributions():
    original = bundle()
    core = CORE.model_dump(by_alias=True)
    core["pack"]["version"] = "2.0.0"
    core["types"]["edges"]["DERIVED_FROM"]["to"] = ["Entity"]
    domain = original.pack("bb").model_dump(by_alias=True)
    domain["pack"].update(version="1.1.0", description="Doc-only change")
    new = OntologyRegistry(
        [Pack.model_validate(core), original.pack("aa"), Pack.model_validate(domain)]
    )
    plan = classify_change(original, new)
    assert plan.kind == "breaking"
    assert "aa" not in plan.pack_changes and "bb" not in plan.pack_changes
    assert "aa" not in plan.contributor_changes and "bb" not in plan.contributor_changes
    assert not plan.version_problems


def test_removed_edge_still_checks_the_withdrawn_extension_contract():
    original = bundle()
    owner = original.pack("aa").model_dump(by_alias=True)
    contributor = original.pack("bb").model_dump(by_alias=True)
    owner["types"]["edges"] = {}
    owner["pack"]["version"] = "2.0.0"
    contributor["types"]["extends_core_edges"] = {}
    contributor["pack"]["version"] = "1.1.0"
    new = OntologyRegistry([CORE, Pack.model_validate(owner), Pack.model_validate(contributor)])
    plan = classify_change(original, new)
    assert plan.kind == "breaking"
    assert plan.contributor_changes["bb"] == "breaking"
    assert any(p.startswith("bb:") and "major version" in p for p in plan.version_problems)


async def test_rule_transfer_replays_changed_write_order_to_match_a_fresh_graph():
    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.domain.pack_projection import PackProjector
    from context_graph.ontology.rebuild import project_ledger, rebuild
    from context_graph.ontology.versioning import reconcile, record_state
    from context_graph.ports.pack_graph import NodeRef
    from context_graph.settings import Settings
    from tests.fixtures.events import make_event

    source = bundle(rule=False)
    owner = source.pack("aa").model_dump(by_alias=True)
    contributor = source.pack("bb").model_dump(by_alias=True)
    owner["types"]["nodes"]["Thing"]["properties"]["label"] = "string"
    first = {
        "event": "aa:aa.observed",
        "upsert": [
            {
                "type": "aa:Thing",
                "key": {"id": "$.id"},
                "set": {"label": "L"},
            }
        ],
    }
    second = {
        "event": "aa:aa.observed",
        "upsert": [
            {
                "type": "aa:Thing",
                "key": {"id": "$.id"},
                "set": {"label": "N"},
            }
        ],
    }
    owner["projection"], contributor["projection"] = [first], [second]
    old = OntologyRegistry([CORE, Pack.model_validate(owner), Pack.model_validate(contributor)])
    owner["projection"], contributor["projection"] = [], [second, first]
    owner["pack"]["version"], contributor["pack"]["version"] = "2.0.0", "1.1.0"
    new = OntologyRegistry([CORE, Pack.model_validate(owner), Pack.model_validate(contributor)])
    log, live, fresh = MemoryEventLog(), MemoryGraphStore(), MemoryGraphStore()
    event = make_event(event_type="aa.observed")
    await log.append(event, {"id": "one"})
    await project_ledger(log, live, PackProjector(old, frozenset()), Settings(), batch_size=2)
    await record_state(live, old, applied="initial")
    ref = NodeRef("Thing", "Thing:one")
    assert (await live.get_nodes([ref]))[ref]["label"] == "N"
    report = await rebuild(log, fresh, PackProjector(new, frozenset()), Settings(), eval_dirs=[])
    assert report.passed and (await fresh.get_nodes([ref]))[ref]["label"] == "L"
    plan = await reconcile(
        live,
        log,
        PackProjector(new, frozenset()),
        allow_breaking=False,
        batch_size=2,
        lookup_limit=100,
    )
    assert plan.kind == "mapping"
    assert (await live.get_nodes([ref]))[ref]["label"] == "L"
