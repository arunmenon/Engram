"""In-memory graph backend (ADR-0019 §6).

Supplies the storage primitives of ``adapters.graph_ops.GraphOperations``
over plain dicts; every ``GraphBackend`` method comes from that shared
layer, which the conformance suite checks against Neo4j.

Single-process and not durable: for tests and the reference backend.

Source: ADR-0019
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right, insort
from copy import deepcopy
from typing import TYPE_CHECKING, Any

from context_graph.adapters.graph_ops import (
    EdgeKey,
    EdgeRow,
    GraphOperations,
    NodeKey,
    apply_set,
    key_property,
)
from context_graph.domain.relationship_recovery import merge_relationship_intent
from context_graph.ports.errors import RuntimeFencedError
from context_graph.ports.relationship_recovery import RECOVERY_LABEL

if TYPE_CHECKING:
    from context_graph.ports.pack_graph import EdgeWrite
    from context_graph.settings import DecaySettings, PPRSettings


class MemoryGraphStore(GraphOperations):
    """``GraphBackend`` held in process memory."""

    def __init__(
        self,
        *,
        decay_settings: DecaySettings | None = None,
        ppr_settings: PPRSettings | None = None,
    ) -> None:
        super().__init__(
            decay_settings=decay_settings,
            ppr_settings=ppr_settings,
            provenance_source="memory",
        )
        self.nodes: dict[NodeKey, dict[str, Any]] = {}
        self.edges: dict[EdgeKey, dict[str, Any]] = {}
        self._recovery_keys: list[str] = []

    async def _get_nodes(self, keys: list[NodeKey]) -> dict[NodeKey, dict[str, Any]]:
        return {key: dict(self.nodes[key]) for key in keys if key in self.nodes}

    async def _find_nodes(
        self, label: str, where: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        return [
            dict(props)
            for (node_label, _id), props in self.nodes.items()
            if node_label == label
            and all(props.get(name) == value for name, value in (where or {}).items())
        ]

    async def _upsert_nodes(self, items: list[tuple[NodeKey, dict[str, Any]]]) -> None:
        for (label, node_id), updates in items:
            if label == RECOVERY_LABEL and (label, node_id) not in self.nodes:
                insort(self._recovery_keys, node_id)
            props = self.nodes.setdefault((label, node_id), {key_property(label): node_id})
            apply_set(props, updates)

    async def _delete_nodes(self, keys: list[NodeKey]) -> int:
        doomed = {key for key in keys if key in self.nodes}
        for edge_key in [k for k in self.edges if k[0] in doomed or k[2] in doomed]:
            del self.edges[edge_key]
        for key in doomed:
            if key[0] == RECOVERY_LABEL:
                self._recovery_keys.pop(bisect_left(self._recovery_keys, key[1]))
            del self.nodes[key]
        return len(doomed)

    async def _edges(
        self,
        *,
        sources: list[NodeKey] | None = None,
        targets: list[NodeKey] | None = None,
        edge_type: str | None = None,
    ) -> list[EdgeRow]:
        source_set = set(sources) if sources is not None else None
        target_set = set(targets) if targets is not None else None
        return [
            (key, dict(props))
            for key, props in self.edges.items()
            if (source_set is None or key[0] in source_set)
            and (target_set is None or key[2] in target_set)
            and (edge_type is None or key[1] == edge_type)
        ]

    async def _upsert_edges(self, items: list[tuple[EdgeKey, dict[str, Any]]]) -> int:
        written = 0
        for key, updates in items:
            if key[0] not in self.nodes or key[2] not in self.nodes:
                continue
            apply_set(self.edges.setdefault(key, {}), updates)
            written += 1
        return written

    async def _delete_edges(self, keys: list[EdgeKey]) -> None:
        for key in keys:
            self.edges.pop(key, None)

    async def _clear(self) -> None:
        self.nodes = {}
        self.edges = {}
        self._recovery_keys = []

    async def put_relationship_intent(
        self, record: dict[str, Any], *, reinterpret: bool = False
    ) -> None:
        key = (RECOVERY_LABEL, record["node_id"])
        before = self.nodes.get(key)
        merged = merge_relationship_intent(before, record, reinterpret=reinterpret)
        if merged is not None:
            if before is None:
                insort(self._recovery_keys, key[1])
            self.nodes[key] = deepcopy(merged)

    async def get_relationship_intents(self, keys: list[str]) -> dict[str, dict[str, Any]]:
        return {
            key: deepcopy(self.nodes[(RECOVERY_LABEL, key)])
            for key in keys
            if (RECOVERY_LABEL, key) in self.nodes
        }

    async def relationship_intents(self, after: str | None, limit: int) -> list[dict[str, Any]]:
        if not 0 < limit <= 1000:
            raise ValueError("Recovery page limit outside 1..1000")
        start = bisect_right(self._recovery_keys, after) if after is not None else 0
        keys = self._recovery_keys[start : start + limit]
        return [deepcopy(self.nodes[(RECOVERY_LABEL, key)]) for key in keys]

    async def settle_relationship_intent(
        self,
        key: str,
        generation: str,
        status: str,
        edge: EdgeWrite | None = None,
    ) -> str:
        # No await between the check and mutation: one event-loop atomic unit.
        record = self.nodes.get((RECOVERY_LABEL, key))
        if record is None or record["generation"] != generation:
            return "superseded"
        if edge is not None:
            from dataclasses import asdict

            if [edge.edge_type, asdict(edge.source), asdict(edge.target)] != [
                record["edge_type"],
                record["source"],
                record["target"],
            ]:
                raise RuntimeFencedError("Recovery endpoint identity changed")
            source, target = self._ref_key(edge.source), self._ref_key(edge.target)
            if source not in self.nodes or target not in self.nodes:
                status = "endpoint_missing"
            elif (source, edge.edge_type, target) in self.edges:
                status = "existing_relationship_kept"
            else:
                self.edges[(source, edge.edge_type, target)] = deepcopy(edge.properties)
                status = "recovered"
        record["status"] = status
        return status
