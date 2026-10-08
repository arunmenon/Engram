"""Composition boundaries: mandatory core, optional built-ins, explicit dependencies."""

import hashlib
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from context_graph.domain.ontology import (
    EventDef,
    OntologyError,
    OntologyRegistry,
    Pack,
    ProcessingSection,
)
from context_graph.domain.pack_bundle import PROCESSING_PROVIDERS, resolve_bundle
from context_graph.domain.pack_versioning import classify_change
from context_graph.ontology.loader import load_registry, parse_pack
from context_graph.ontology.runtime import configured_bundle
from context_graph.settings import OntologySettings


def test_legacy_default_preserves_existing_builtin_schema() -> None:
    registry = load_registry([])
    assert {pack.name for pack in registry.packs} == {"core", "memory", "user"}
    assert {"Belief", "UserProfile", "Event"} <= registry.node_types.keys()


@pytest.mark.parametrize(
    ("selected", "types"),
    [
        ([], {"Event", "Entity", "Summary"}),
        (["memory"], {"Event", "Entity", "Summary", "Belief", "Goal", "Episode"}),
        (
            ["user"],
            {
                "Event",
                "Entity",
                "Summary",
                "UserProfile",
                "Preference",
                "Skill",
                "Workflow",
                "BehavioralPattern",
            },
        ),
    ],
)
def test_selected_builtins_do_not_pull_in_unrelated_types(
    selected: list[str], types: set[str]
) -> None:
    registry = load_registry([], builtin_packs=selected)
    assert set(registry.node_types) == types
    assert "core" in {pack.name for pack in registry.packs}


def test_domain_only_includes_core_but_not_optional_builtins() -> None:
    registry = load_registry(["pdlc"], builtin_packs=[])
    assert {pack.name for pack in registry.packs} == {"core", "pdlc"}
    assert {"Event", "Change", "Requirement", "DesignElement"} <= registry.node_types.keys()
    assert not {"Belief", "UserProfile", "Preference"} & registry.node_types.keys()
    assert registry.edge_type("DERIVED_FROM").to_types == {"Event"}


def test_named_dependency_can_require_an_optional_builtin(tmp_path: Path) -> None:
    (tmp_path / "lab.pack.yaml").write_text(
        "pack:\n  name: lab\n  version: 1.0.0\n  requires: [memory>=1.0]\n"
    )
    registry = load_registry(["lab"], [tmp_path], builtin_packs=[])
    assert {pack.name for pack in registry.packs} == {"core", "memory", "lab"}
    assert "Belief" in registry.node_types and "UserProfile" not in registry.node_types


def test_order_and_duplicate_selection_do_not_change_composed_identity() -> None:
    first = load_registry(["pdlc"], builtin_packs=["user", "memory"])
    second = load_registry(["pdlc", "core", "pdlc"], builtin_packs=["memory", "user", "user"])
    assert first.version == second.version


def test_invalid_builtin_selection_fails_instead_of_becoming_domain_selection() -> None:
    with pytest.raises(OntologyError, match="unknown built-in pack 'pdlc'"):
        load_registry([], builtin_packs=["pdlc"])


def test_required_core_cannot_be_shadowed_even_with_no_optional_packs(tmp_path: Path) -> None:
    (tmp_path / "core.pack.yaml").write_text("pack: {name: core, version: 99.0.0}\n")
    with pytest.raises(OntologyError, match="base pack 'core' cannot be replaced"):
        load_registry([], [tmp_path], builtin_packs=[])


def test_incompatible_required_version_is_not_silently_loaded(tmp_path: Path) -> None:
    (tmp_path / "lab.pack.yaml").write_text(
        "pack:\n  name: lab\n  version: 1.0.0\n  requires: [core>=99.0]\n"
    )
    with pytest.raises(OntologyError, match="requires"):
        load_registry(["lab"], [tmp_path], builtin_packs=[])


def test_legacy_core_identity_survives_absent_processing_section() -> None:
    registry = load_registry([], builtin_packs=[])
    assert registry.version == "sha256:7aa9c7d4db1d5a24"
    assert hashlib.sha256(registry.pack("core").canonical_json().encode()).hexdigest() == (
        "7aa9c7d4db1d5a2479197eaf47e33eb752cec6bed4b07e6d92dc648c28f59048"
    )
    snapshot = registry.pack("core").canonical_json()
    assert "processing" not in snapshot
    assert Pack.model_validate_json(snapshot).canonical_json() == snapshot


def test_bundle_enables_user_only_from_selected_owner() -> None:
    domain = resolve_bundle(load_registry(["pdlc"], builtin_packs=[]))
    user = resolve_bundle(load_registry([], builtin_packs=["user"]))
    memory = resolve_bundle(load_registry([], builtin_packs=["memory"]))
    assert domain.enables("pack.project.v1") and domain.enables("pack.extract.v1")
    assert not domain.enables("user.extract.v1")
    assert user.enables("user.extract.v1")
    assert not memory.enables("user.extract.v1")
    assert memory.enables("summary.consolidate.v1")
    assert not any("belief" in handler or "episode" in handler for _, handler in memory.processing)


def test_support_requirement_does_not_enable_handler() -> None:
    registry = load_registry([], builtin_packs=[])
    lab = parse_pack(
        "pack: {name: lab, version: 1.0.0, requires: [core>=1.0]}\n"
        "processing: {requires: [user.extract.v1]}\n"
    )
    bundle = resolve_bundle(OntologyRegistry([*registry.packs, lab]))
    assert not bundle.enables("user.extract.v1")


@pytest.mark.parametrize("field", ["enabled", "requires"])
def test_unsupported_processing_is_refused(field: str) -> None:
    registry = load_registry([], builtin_packs=[])
    lab = parse_pack(
        "pack: {name: lab, version: 1.0.0, requires: [core>=1.0]}\n"
        f"processing: {{{field}: [unknown.handler.v99]}}\n"
    )
    with pytest.raises(OntologyError, match="unsupported processing handler"):
        resolve_bundle(OntologyRegistry([*registry.packs, lab]))


def test_domain_cannot_impersonate_specialized_user_handler() -> None:
    registry = load_registry([], builtin_packs=["user"])
    lab = parse_pack(
        "pack: {name: lab, version: 1.0.0, requires: [core>=1.0]}\n"
        "processing: {enabled: [user.extract.v1]}\n"
    )
    with pytest.raises(OntologyError, match="cannot enable 'user.extract.v1'"):
        resolve_bundle(OntologyRegistry([*registry.packs, lab]))


def test_missing_core_provider_is_refused() -> None:
    providers = dict(PROCESSING_PROVIDERS)
    del providers["event.project.v1"]
    with pytest.raises(OntologyError, match="unavailable processing handler"):
        resolve_bundle(load_registry([], builtin_packs=[]), providers)


def test_bundle_snapshot_does_not_borrow_mutable_registry_state() -> None:
    registry = load_registry(["pdlc"], builtin_packs=[])
    bundle = resolve_bundle(registry)
    identity = bundle.identity
    registry.node_types.clear()
    reconstructed = bundle.registry
    assert "Change" in reconstructed.node_types
    reconstructed.node_types.clear()
    assert "Change" in bundle.registry.node_types
    assert bundle.identity == identity
    with pytest.raises(FrozenInstanceError):
        bundle.identity = "changed"  # type: ignore[misc]


def test_bundle_recomposes_when_manifest_changed_before_resolution() -> None:
    registry = load_registry([], builtin_packs=[])
    before = resolve_bundle(registry)
    registry.pack("core").events["tool.review_probe"] = EventDef()
    after = resolve_bundle(registry)
    assert before.identity != after.identity
    assert after.schema_version == after.registry.version
    assert "tool.review_probe" in after.registry.pack("core").events


def test_core_handlers_reject_foreign_owned_core_types() -> None:
    core = parse_pack("pack: {name: core, version: 1.0.0}\n")
    lab = parse_pack(
        "pack: {name: lab, version: 1.0.0, requires: [core>=1.0]}\n"
        "types:\n  nodes:\n"
        + "".join(
            f"    {name}: {{key: [id], properties: {{id: string}}}}\n"
            for name in ("Event", "Entity", "Summary")
        )
    )
    with pytest.raises(OntologyError, match="core-owned schema type"):
        resolve_bundle(OntologyRegistry([core, lab]))


def test_processing_change_is_versioned_and_removal_breaking() -> None:
    old = load_registry([], builtin_packs=["user"])
    user = old.pack("user")
    disabled = user.model_copy(
        update={
            "pack": user.pack.model_copy(update={"version": "2.0.0"}),
            "processing": ProcessingSection(),
        }
    )
    new = OntologyRegistry([old.pack("core"), disabled])
    plan = classify_change(old, new)
    assert plan.kind == "breaking" and not plan.version_problems
    assert not plan.replay_event_types  # Removing a writer is not a generic replay recipe.
    reenabled = disabled.model_copy(
        update={
            "pack": disabled.pack.model_copy(update={"version": "2.1.0"}),
            "processing": user.processing,
        }
    )
    plan = classify_change(new, OntologyRegistry([old.pack("core"), reenabled]))
    assert plan.kind == "additive" and not plan.version_problems


def test_explicit_empty_environment_does_not_reenable_default_builtins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CG_ONTOLOGY_BUILTIN_PACKS", "")
    monkeypatch.setenv("CG_ONTOLOGY_PACKS", "pdlc")
    settings = OntologySettings()
    assert settings.builtin_packs == []
    bundle = configured_bundle(settings)
    assert {name for name, _version in bundle.pack_identities} == {"core", "pdlc"}


def test_cache_separates_optional_selection_and_canonicalizes_order() -> None:
    core = configured_bundle(OntologySettings(packs=[], builtin_packs=[]))
    user = configured_bundle(OntologySettings(packs=[], builtin_packs=["user"]))
    both = configured_bundle(OntologySettings(packs=[], builtin_packs=["memory", "user"]))
    reordered = configured_bundle(OntologySettings(packs=[], builtin_packs=["user", "memory"]))
    assert core.identity != user.identity
    assert both is reordered
