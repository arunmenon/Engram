"""Atomic publication plan for an extracted Entity and its source references.

Projection dependencies are required before any mutation. Existing Entity origin
and counts survive publication; retrying the same result does not add support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context_graph.ports.errors import UnavailableError
from context_graph.ports.pack_graph import EdgeWrite, NodeRef, NodeWrite

if TYPE_CHECKING:
    from context_graph.domain.models import Edge, EntityNode


def publication_refs(
    entity_id: str, source_event_ids: list[str], resolution: Edge | None = None
) -> tuple[NodeRef, ...]:
    if (
        not entity_id
        or not source_event_ids
        or any(not isinstance(eid, str) or not eid for eid in source_event_ids)
    ):
        raise ValueError("Entity publication requires an identity and source Events")
    refs = [
        NodeRef("Entity", entity_id, "entity_id"),
        *[NodeRef("Event", eid, "event_id") for eid in sorted(set(source_event_ids))],
    ]
    if resolution is not None:
        if resolution.source != entity_id or str(resolution.edge_type) not in {
            "SAME_AS",
            "RELATED_TO",
        }:
            raise ValueError("Unsupported Entity resolution publication")
        refs.append(NodeRef("Entity", resolution.target, "entity_id"))
    return tuple(dict.fromkeys(refs))


def publication_edge_keys(
    entity_id: str, source_event_ids: list[str], resolution: Edge | None = None
) -> tuple[tuple[NodeRef, str, NodeRef], ...]:
    target = NodeRef("Entity", entity_id, "entity_id")
    edges = [
        (NodeRef("Event", eid, "event_id"), "REFERENCES", target)
        for eid in sorted(set(source_event_ids))
    ]
    if resolution is not None:
        edges.append(
            (target, str(resolution.edge_type), NodeRef("Entity", resolution.target, "entity_id"))
        )
    return tuple(edges)


def plan_entity_publication(
    entity_id: str,
    source_event_ids: list[str],
    node: EntityNode | None,
    resolution: Edge | None,
    stored: dict[NodeRef, dict[str, Any]],
    existing_edges: dict[tuple[NodeRef, str, NodeRef], dict[str, Any]],
) -> tuple[tuple[NodeWrite, ...], tuple[EdgeWrite, ...]]:
    refs = publication_refs(entity_id, source_event_ids, resolution)
    entity = refs[0]
    for ref in refs[1:]:
        if ref not in stored:
            raise UnavailableError("Entity publication dependency is not projected")
        if stored[ref].get(ref.key_property) != ref.key:
            raise ValueError("Entity publication dependency identity is invalid")
    old = stored.get(entity)
    if old is not None and old.get("entity_id") != entity_id:
        raise ValueError("Existing Entity identity is invalid")
    if node is None and old is None:
        raise UnavailableError("Resolved Entity is no longer available")
    writes: tuple[NodeWrite, ...] = ()
    if node is not None:
        if node.entity_id != entity_id:
            raise ValueError("Publication Entity identity disagrees")
        props = (
            dict(old)
            if old is not None
            else dict(
                entity_id=entity_id,
                name=node.name,
                entity_type=str(node.entity_type),
                first_seen=node.first_seen.isoformat(),
                mention_count=node.mention_count,
            )
        )
        props.update(last_seen=node.last_seen.isoformat(), embedding=list(node.embedding))
        writes = (NodeWrite(entity, props),)
    edges = []
    for source, kind, target in publication_edge_keys(entity_id, source_event_ids, resolution):
        key = (source, kind, target)
        if kind == "REFERENCES" and key in existing_edges:
            continue
        props = dict(existing_edges.get(key, {}))
        if resolution is not None and kind == str(resolution.edge_type):
            props.update(resolution.properties)
        edges.append(EdgeWrite(kind, source, target, props))
    return writes, tuple(edges)
