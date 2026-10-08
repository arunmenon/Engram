"""Validate explicit pack removals before a public write batch performs I/O.

Ordinary None properties retain their existing skip semantics. Registry-specific
requiredness and writer permissions are checked by the pack planner, not inferred
from field names here. This boundary protects identity and engine metadata.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context_graph.domain.ontology import PROPERTY_NAME, SYSTEM_PROPERTIES

if TYPE_CHECKING:
    from context_graph.ports.pack_graph import EdgeWrite, NodeWrite

PROTECTED_REMOVALS = SYSTEM_PROPERTIES | {"source_trust", "status", "event_id"}


def _validate(names: tuple[str, ...], properties: dict[str, Any], protected: set[str]) -> None:
    if not isinstance(names, tuple) or any(
        not isinstance(name, str) or PROPERTY_NAME.fullmatch(name) is None for name in names
    ):
        raise ValueError("Invalid property removal names")
    if len(set(names)) != len(names):
        raise ValueError("Duplicate property removal")
    if set(names) & (set(properties) | protected | PROTECTED_REMOVALS):
        raise ValueError("Conflicting or protected property removal")


def validate_node_removals(writes: list[NodeWrite]) -> None:
    for write in writes:
        _validate(write.remove_properties, write.properties, {write.ref.key_property})


def validate_edge_removals(writes: list[EdgeWrite]) -> None:
    for write in writes:
        _validate(write.remove_properties, write.properties, set())
        if write.create_only and write.remove_properties:
            raise ValueError("Property removal with create_only is unsupported")
