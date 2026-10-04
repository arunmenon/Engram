"""Graph operations for ontology packs (ADR-0018 decision 7).

Pack projection, pack retrieval and query plugins use only these
operations, never backend query text. They are written to the stricter of
Neo4j and Spanner Graph semantics: one label per node, an edge is
identified by (source, type, target), upserts are explicit, and edges are
readable in both directions.

A node is addressed by ``NodeRef(label, key, key_property)``: types from
today's schema keep their own unique property (``Event`` by ``event_id``);
types added by packs are identified by ``node_id`` (``<Type>:<key>``).

Labels, edge types and property names must already be validated against
the ontology registry, whose names have a fixed shape.

Source: ADR-0018
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, Protocol

if TYPE_CHECKING:
    from context_graph.domain.ontology import OntologyRegistry

Direction = Literal["out", "in", "both"]


@dataclass(frozen=True)
class NodeRef:
    label: str
    key: str
    key_property: str = "node_id"


@dataclass(frozen=True)
class NodeWrite:
    """MERGE a node by its key, then set ``properties``.

    ``defaults`` are set only when the node is created (a lifecycle's
    initial state). Properties whose value is None are not written.
    """

    ref: NodeRef
    properties: dict[str, Any] = field(default_factory=dict)
    defaults: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EdgeWrite:
    """MERGE one edge per (source, type, target), then set ``properties``.

    Nothing is written when either endpoint does not exist.
    """

    edge_type: str
    source: NodeRef
    target: NodeRef
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StateChange:
    """Move a node to ``to_state`` (``status``), recording when.

    Applied only when the node exists, is not already in ``to_state`` and,
    if ``only_from`` is given, is in one of those states.
    """

    ref: NodeRef
    to_state: str
    changed_at: str
    only_from: tuple[str, ...] = ()


class PackGraph(Protocol):
    """Generic node, edge and lifecycle operations every graph backend provides."""

    async def ensure_pack_schema(
        self, registry: OntologyRegistry, embedding_dimensions: int
    ) -> None:
        """Create what the backend needs for the registry's types (idempotent).

        Neo4j creates key constraints and indexes; schemaless backends do nothing.
        """
        ...

    async def upsert_nodes(self, writes: list[NodeWrite]) -> None:
        """MERGE the nodes and set their properties."""
        ...

    async def upsert_edges(self, writes: list[EdgeWrite]) -> int:
        """MERGE the edges whose endpoints exist; return how many were written."""
        ...

    async def change_states(self, changes: list[StateChange]) -> int:
        """Apply lifecycle transitions; return how many nodes changed state."""
        ...

    async def get_nodes(self, refs: list[NodeRef]) -> dict[NodeRef, dict[str, Any]]:
        """Properties of the nodes that exist."""
        ...

    async def find_nodes(
        self, label: str, equals: dict[str, Any], limit: int
    ) -> list[dict[str, Any]]:
        """Properties of up to ``limit`` nodes of ``label`` whose properties equal ``equals``."""
        ...

    async def neighbors(
        self,
        refs: list[NodeRef],
        edge_types: list[str] | None,
        direction: Direction,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Edges at the given nodes, with the node at the other end.

        Each row: ``edge_type``, ``properties``, ``source_label``,
        ``source_key``, ``target_label``, ``target_key``, ``node_label``
        and ``node`` (the other end's properties). Ordered by edge type,
        then source and target, and at most ``limit`` rows.
        """
        ...
