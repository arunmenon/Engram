"""Pure, immutable executable selection alongside the composed schema registry.

This validates declared engine support, not external service readiness or tenant
authorization. Production factories must enforce this selection at their boundaries.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

from context_graph.domain.ontology import OntologyError, OntologyRegistry, Pack

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True)
class ProcessingProvider:
    owner: str | None
    required_types: frozenset[str] = frozenset()
    required_type_owners: tuple[tuple[str, str], ...] = ()


PROCESSING_PROVIDERS: Mapping[str, ProcessingProvider] = MappingProxyType(
    {
        "event.project.v1": ProcessingProvider("core", frozenset({"Event"})),
        "event.enrich.v1": ProcessingProvider("core", frozenset({"Event"})),
        "entity.extract.v1": ProcessingProvider("core", frozenset({"Event", "Entity"})),
        "summary.consolidate.v1": ProcessingProvider("core", frozenset({"Event", "Summary"})),
        "event.retain.v1": ProcessingProvider("core", frozenset({"Event"})),
        "user.extract.v1": ProcessingProvider(
            "user",
            frozenset({"Event", "Entity", "UserProfile", "Preference", "Skill"}),
            (("Event", "core"), ("Entity", "core")),
        ),
        "pack.project.v1": ProcessingProvider(None),
        "pack.properties.v1": ProcessingProvider(None),
        "pack.extract.v1": ProcessingProvider(None),
    }
)
CORE_PROCESSING = (
    "event.project.v1",
    "event.enrich.v1",
    "entity.extract.v1",
    "summary.consolidate.v1",
    "event.retain.v1",
)


@dataclass(frozen=True)
class ActiveBundle:
    """Value snapshot: never borrow mutable registry dictionaries from a caller.

    ``registry`` reconstructs an independent schema view. The processing bindings,
    identity and allowed vocabulary cannot change if that view is mutated.
    """

    schema_version: str
    identity: str
    pack_identities: tuple[tuple[str, str], ...]
    processing: tuple[tuple[str, str], ...]
    node_types: frozenset[str]
    edge_types: frozenset[str]
    declared_intents: frozenset[str]
    _pack_snapshots: tuple[str, ...]

    @property
    def registry(self) -> OntologyRegistry:
        return OntologyRegistry([Pack.model_validate_json(text) for text in self._pack_snapshots])

    def enables(self, handler: str) -> bool:
        return any(selected == handler for _owner, selected in self.processing)


def resolve_bundle(
    registry: OntologyRegistry,
    provider_catalog: Mapping[str, ProcessingProvider] = PROCESSING_PROVIDERS,
) -> ActiveBundle:
    """Resolve exact handlers once; no store/provider construction or pack-pair branches."""
    # Recompose from the exact snapshots we retain. A caller may have mutated a
    # Pack since its registry cached the schema and identity.
    snapshots = tuple(pack.canonical_json() for pack in registry.packs)
    registry = OntologyRegistry([Pack.model_validate_json(text) for text in snapshots])
    bindings: set[tuple[str, str]] = set()
    problems: list[str] = []
    # These existing facilities implement core. Memory has no implicit producer.
    for handler in CORE_PROCESSING:
        bindings.add(("core", handler))

    for pack in registry.packs:
        for handler in {*pack.processing.requires, *pack.processing.enabled}:
            if handler not in provider_catalog:
                problems.append(f"{pack.name}: unsupported processing handler {handler!r}")
        for handler in pack.processing.enabled:
            provider = provider_catalog.get(handler)
            if provider is None:
                continue
            if provider.owner != pack.name:
                problems.append(
                    f"{pack.name}: cannot enable {handler!r}; owned by "
                    f"{provider.owner or 'the projection/extraction declarations'}"
                )
            else:
                bindings.add((pack.name, handler))
        if pack.projection:
            bindings.add((pack.name, "pack.project.v1"))
        if pack.extraction.sources and pack.extraction.propose:
            bindings.add((pack.name, "pack.extract.v1"))

    for owner, handler in sorted(bindings):
        provider = provider_catalog.get(handler)
        if provider is None:
            problems.append(f"{owner}: unavailable processing handler {handler!r}")
            continue
        missing = provider.required_types - registry.node_types.keys()
        if missing:
            problems.append(f"{owner}: {handler!r} requires schema types {sorted(missing)}")
        expected_owners = dict(provider.required_type_owners)
        for type_name in provider.required_types:
            expected_owner = expected_owners.get(type_name, provider.owner)
            node = registry.node_types.get(type_name)
            if node is not None and expected_owner is not None and node.pack != expected_owner:
                problems.append(
                    f"{owner}: {handler!r} requires {expected_owner}-owned schema type "
                    f"{type_name!r}; supplied by {node.pack!r}"
                )
    if problems:
        raise OntologyError(problems)

    processing = tuple(sorted(bindings))
    identity_data = {"schema": registry.version, "processing": processing}
    digest = hashlib.sha256(
        json.dumps(identity_data, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return ActiveBundle(
        schema_version=registry.version,
        identity=f"sha256:{digest}",
        pack_identities=tuple((pack.name, pack.version) for pack in registry.packs),
        processing=processing,
        node_types=frozenset(registry.node_types),
        edge_types=frozenset(registry.edge_types),
        declared_intents=frozenset(registry.intents),
        _pack_snapshots=snapshots,
    )
