"""In-memory graph backend (ADR-0019 §6).

Supplies the storage primitives of ``adapters.graph_ops.GraphOperations``
over plain dicts; every ``GraphBackend`` method comes from that shared
layer, which the conformance suite checks against Neo4j.

Single-process and not durable: for tests and the reference backend.

Source: ADR-0019
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context_graph.adapters.graph_ops import (
    EdgeKey,
    EdgeRow,
    GraphOperations,
    NodeKey,
    apply_set,
    key_property,
)

if TYPE_CHECKING:
    from context_graph.domain.memory_actions import MemoryAction
    from context_graph.domain.models import Edge, EntityNode
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

    async def get_user_extraction(self, trigger: Any) -> dict[str, Any] | None:
        from context_graph.domain.user_extraction import event_ref, receipt_from_event

        ref = event_ref(trigger)
        return receipt_from_event(trigger, self.nodes.get((ref.label, ref.key)))

    async def prepare_user_extraction(
        self, trigger: Any, candidate: dict[str, Any]
    ) -> dict[str, Any]:
        from context_graph.domain.user_extraction import (
            OWNER_FIELD,
            RECEIPT_FIELD,
            event_ref,
            select_prepared_receipt,
        )

        ref = event_ref(trigger)
        key = (ref.label, ref.key)
        winner = select_prepared_receipt(trigger, self.nodes.get(key), candidate)
        # No await between selection and mutation: reference-event-loop atomic.
        self.nodes[key] = {**self.nodes[key], RECEIPT_FIELD: winner, OWNER_FIELD: winner["owner"]}
        from context_graph.domain.user_extraction import receipt_from_event

        result = receipt_from_event(trigger, self.nodes[key])
        assert result is not None
        return result

    async def apply_user_extraction(self, trigger: Any) -> str:
        from context_graph.domain.user_extraction import (
            event_ref,
            extraction_refs,
            plan_user_extraction,
            receipt_from_event,
        )

        ref = event_ref(trigger)
        receipt = receipt_from_event(trigger, self.nodes.get((ref.label, ref.key)))
        if receipt is None:
            raise ValueError("User extraction was not prepared")
        refs = [ref, *extraction_refs(receipt)]
        stored = {
            ref: dict(self.nodes[(ref.label, ref.key)])
            for ref in refs
            if (ref.label, ref.key) in self.nodes
        }
        plan = plan_user_extraction(trigger, stored)
        updated = {(write.ref.label, write.ref.key): dict(write.properties) for write in plan.nodes}
        edge_updates = {
            (
                (write.source.label, write.source.key),
                write.edge_type,
                (write.target.label, write.target.key),
            ): dict(write.properties)
            for write in plan.edges
        }
        for key in edge_updates:
            if any(
                endpoint not in self.nodes and endpoint not in updated
                for endpoint in (key[0], key[2])
            ):
                raise ValueError("User extraction edge endpoint is missing")
        self.nodes.update(updated)
        for key, props in edge_updates.items():
            self.edges.setdefault(key, {}).update(props)
        return plan.outcome

    async def apply_memory_action(self, action: MemoryAction) -> str:
        """Reference atomic action: no await or mutation before the whole plan validates."""
        from context_graph.domain.memory_actions import plan_memory_action

        refs = action.read_refs()
        stored = {
            ref: dict(self.nodes[(ref.label, ref.key)])
            for ref in refs
            if (ref.label, ref.key) in self.nodes
        }
        plan = plan_memory_action(action, stored)
        nodes = {(write.ref.label, write.ref.key): dict(write.properties) for write in plan.nodes}
        edges = {}
        available = self.nodes.keys() | nodes.keys()
        for write in plan.edges:
            source = (write.source.label, write.source.key)
            target = (write.target.label, write.target.key)
            if source not in available or target not in available:
                raise ValueError("Memory evidence endpoint is absent")
            edges[(source, write.edge_type, target)] = dict(write.properties)
        self.nodes.update(nodes)
        self.edges.update(edges)
        return plan.outcome

    async def publish_extracted_entity(
        self,
        entity_id: str,
        source_event_ids: list[str],
        *,
        node: EntityNode | None = None,
        resolution: Edge | None = None,
    ) -> None:
        from context_graph.domain.entity_publication import (
            plan_entity_publication,
            publication_edge_keys,
            publication_refs,
        )

        refs = publication_refs(entity_id, source_event_ids, resolution)
        stored = {
            ref: dict(self.nodes[(ref.label, ref.key)])
            for ref in refs
            if (ref.label, ref.key) in self.nodes
        }
        edges = {
            key: dict(self.edges[((key[0].label, key[0].key), key[1], (key[2].label, key[2].key))])
            for key in publication_edge_keys(entity_id, source_event_ids, resolution)
            if ((key[0].label, key[0].key), key[1], (key[2].label, key[2].key)) in self.edges
        }
        nodes, writes = plan_entity_publication(
            entity_id, source_event_ids, node, resolution, stored, edges
        )
        # No await between validation and mutation: reference-event-loop atomic.
        self.nodes.update({(n.ref.label, n.ref.key): dict(n.properties) for n in nodes})
        self.edges.update(
            {
                ((e.source.label, e.source.key), e.edge_type, (e.target.label, e.target.key)): dict(
                    e.properties
                )
                for e in writes
            }
        )

    async def _delete_orphan_candidates(self, keys: list[NodeKey]) -> list[NodeKey]:
        # Recheck at mutation time; never detach a newly linked node.
        connected = {node for edge in self.edges for node in (edge[0], edge[2])}
        deleted = [key for key in keys if key in self.nodes and key not in connected]
        for key in deleted:
            del self.nodes[key]
        return deleted

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
            props = self.nodes.setdefault((label, node_id), {key_property(label): node_id})
            apply_set(props, updates)

    async def _delete_nodes(self, keys: list[NodeKey]) -> int:
        doomed = {key for key in keys if key in self.nodes}
        for edge_key in [k for k in self.edges if k[0] in doomed or k[2] in doomed]:
            del self.edges[edge_key]
        for key in doomed:
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
