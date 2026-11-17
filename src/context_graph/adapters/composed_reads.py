"""Read-only pack selection over the complete Memory/Spanner primitives.

Filter before shared retrieval operations count, rank or limit rows. The
original graph remains available for writes and privacy maintenance; this view
never changes its configuration. Other adapter implementations need their own
pre-limit read scope and are not covered by this adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from context_graph.adapters.graph_ops import EdgeKey, EdgeRow, GraphOperations, NodeKey

if TYPE_CHECKING:
    from context_graph.domain.pack_bundle import ActiveBundle


@dataclass(frozen=True)
class ReadScope:
    identity: str
    node_types: frozenset[str]
    edges: frozenset[tuple[str, str, str]]
    key_fields: tuple[tuple[str, str], ...]

    @classmethod
    def from_bundle(cls, bundle: ActiveBundle) -> ReadScope:
        registry = bundle.registry
        return cls(
            bundle.identity,
            bundle.node_types,
            frozenset(
                (source, edge, target)
                for edge in registry.edge_types
                for source in registry.node_types
                for target in registry.node_types
                if registry.allows(edge, source, target)
            ),
            tuple((name, node.key_property) for name, node in registry.node_types.items()),
        )

    def key_field(self, label: str) -> str:
        return dict(self.key_fields)[label]


class ComposedReadView(GraphOperations):
    """Shared retrieval algorithms over active, immutable graph vocabulary."""

    def __init__(self, graph: GraphOperations, scope: ReadScope) -> None:
        super().__init__()
        self._graph = graph
        self.scope = scope

    async def _get_nodes(self, keys: list[NodeKey]) -> dict[NodeKey, dict[str, Any]]:
        wanted = {key for key in keys if key[0] in self.scope.node_types}
        if not wanted:
            return {}
        return {
            key: dict(props)
            for key, props in (await self._graph.read_keyed_nodes(sorted(wanted))).items()
            if key in wanted and str(props.get(self.scope.key_field(key[0]), "")) == key[1]
        }

    async def _find_nodes(
        self, label: str, where: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        if label not in self.scope.node_types:
            return []
        field = self.scope.key_field(label)
        rows = await self._graph.read_label_nodes(label, where)
        keys = [(label, str(row[field])) for row in rows if row.get(field) is not None]
        canonical = await self._get_nodes(keys)
        return [
            props
            for props in canonical.values()
            if all(props.get(name) == value for name, value in (where or {}).items())
        ]

    async def _edges(
        self,
        *,
        sources: list[NodeKey] | None = None,
        targets: list[NodeKey] | None = None,
        edge_type: str | None = None,
    ) -> list[EdgeRow]:
        if sources is not None:
            sources = [key for key in sources if key[0] in self.scope.node_types]
            if not sources:
                return []
        if targets is not None:
            targets = [key for key in targets if key[0] in self.scope.node_types]
            if not targets:
                return []
        if edge_type is not None and not any(edge == edge_type for _, edge, _ in self.scope.edges):
            return []
        rows = await self._graph.read_matching_edges(
            sources=sources, targets=targets, edge_type=edge_type
        )
        source_set = set(sources) if sources is not None else None
        target_set = set(targets) if targets is not None else None
        filtered = [
            (key, dict(props))
            for key, props in rows
            if (key[0][0], key[1], key[2][0]) in self.scope.edges
            and props.get("link_status", "confirmed") != "rejected"
            and (source_set is None or key[0] in source_set)
            and (target_set is None or key[2] in target_set)
            and (edge_type is None or key[1] == edge_type)
        ]
        endpoints = {key[0] for key, _props in filtered} | {key[2] for key, _props in filtered}
        existing = await self._get_nodes(sorted(endpoints))
        return [
            (key, props) for key, props in filtered if key[0] in existing and key[2] in existing
        ]

    async def _upsert_nodes(self, items: list[tuple[NodeKey, dict[str, Any]]]) -> None:
        raise PermissionError("Composed graph view is read-only")

    async def _delete_nodes(self, keys: list[NodeKey]) -> int:
        raise PermissionError("Composed graph view is read-only")

    async def _upsert_edges(self, items: list[tuple[EdgeKey, dict[str, Any]]]) -> int:
        raise PermissionError("Composed graph view is read-only")

    async def _delete_edges(self, keys: list[EdgeKey]) -> None:
        raise PermissionError("Composed graph view is read-only")

    async def _clear(self) -> None:
        raise PermissionError("Composed graph view is read-only")


class ComposedGraphReads:
    """Expose GraphReads only, forwarding the one intentional access write."""

    def __init__(self, view: ComposedReadView) -> None:
        self._view = view

    def __getattr__(self, name: str) -> Any:
        # GraphOperationReads methods operate entirely on the scoped view.
        return getattr(self._view.reads, name)

    async def record_access(self, event_ids: list[str], accessed_at: str) -> None:
        nodes = await self._view._get_nodes([("Event", eid) for eid in event_ids])
        valid = [eid for eid in event_ids if ("Event", eid) in nodes]
        if valid:
            await self._view._graph.record_event_access(valid, accessed_at)
