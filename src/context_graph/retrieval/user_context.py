"""Bounded owned User context for personalization, with stored source evidence."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context_graph.domain.models import AtlasEdge, AtlasNode, NodeScores
from context_graph.ports.pack_graph import NodeRef
from context_graph.retrieval.atlas import build_atlas_node

if TYPE_CHECKING:
    from context_graph.domain.models import SubgraphQuery
    from context_graph.ports.pack_graph import PackGraph


async def add_user_context(
    graph: PackGraph,
    query: SubgraphQuery,
    nodes: dict[str, AtlasNode],
    edges: list[AtlasEdge],
    seen: set[tuple[str, str, str]],
    provenance_source: str,
) -> bool:
    """Follow the canonical owner, never an LLM-named Entity or another owner.

    Only supported owned profiles, active preferences and Skills with complete
    evidence are returned. The caller gates this helper on the selected User pack.
    This is logical owner selection, not tenant authorization.
    """
    owner = NodeRef("Entity", "user:" + query.agent_id, "entity_id")
    families = {
        "HAS_PROFILE": ("UserProfile", "profile_id"),
        "HAS_PREFERENCE": ("Preference", "preference_id"),
        "HAS_SKILL": ("Skill", "skill_id"),
    }
    limit = min(query.max_nodes, 30)
    links = await graph.neighbors([owner], list(families), "out", limit + 1)
    truncated = len(links) > limit
    selected = []
    for row in links[:limit]:
        family = families.get(row["edge_type"])
        if family and (row["source_label"], row["source_key"], row["target_label"]) == (
            owner.label,
            owner.key,
            family[0],
        ):
            selected.append((row, NodeRef(family[0], row["target_key"], family[1])))
    found = await graph.get_nodes([owner, *[ref for _, ref in selected]])
    owner_props = found.get(owner)
    if not owner_props or owner_props.get("entity_id") != owner.key:
        return truncated
    source_ids: set[str]
    candidates, source_ids = [], set()
    for row, ref in selected:
        props = found.get(ref)
        if (
            not props
            or props.get("user_id") != owner.key
            or props.get(ref.key_property) != ref.key
            or (ref.label == "UserProfile" and ref.key != "profile:" + owner.key)
        ):
            truncated = True
            continue
        if ref.label == "Preference" and props.get("superseded_by"):
            continue
        supports = props.get("support_event_ids")
        if (
            not isinstance(supports, list)
            or not supports
            or any(not isinstance(key, str) for key in supports)
            or len(set(supports)) != len(supports)
            or len(source_ids | set(supports)) > 500
        ):
            truncated = True
            continue
        source_ids.update(supports)
        candidates.append((row, ref, props, set(supports)))
    if not candidates:
        return truncated
    sources = await graph.get_nodes(
        [NodeRef("Event", key, "event_id") for key in sorted(source_ids)]
    )
    edge_limit = sum(len(supports) for _, _, _, supports in candidates) + 1
    evidence = await graph.neighbors(
        [ref for _, ref, _, _ in candidates], ["DERIVED_FROM"], "out", edge_limit
    )
    if len(evidence) >= edge_limit:
        return True
    for link, ref, props, supports in candidates:
        actual = [
            r for r in evidence if (r["source_label"], r["source_key"]) == (ref.label, ref.key)
        ]
        if (
            {(r["target_label"], r["target_key"]) for r in actual}
            != {("Event", key) for key in supports}
            or any(
                sources.get(NodeRef("Event", key, "event_id"), {}).get("agent_id") != query.agent_id
                for key in supports
            )
            or (ref.label == "Preference" and props.get("observation_count") != len(supports))
        ):
            truncated = True
            continue
        anchor = sources[NodeRef("Event", min(supports), "event_id")]
        nodes[owner.key] = AtlasNode(
            node_id=owner.key,
            node_type="Entity",
            attributes=owner_props,
            scores=NodeScores(decay_score=1),
            retrieval_reason="user_context",
        )
        nodes[ref.key] = AtlasNode(
            node_id=ref.key,
            node_type=ref.label,
            attributes=props,
            provenance=build_atlas_node(
                anchor, NodeScores(), provenance_source=provenance_source
            ).provenance,
            scores=NodeScores(decay_score=1, relevance_score=1),
            retrieval_reason="user_context",
        )
        for key in supports:
            nodes.setdefault(
                key,
                build_atlas_node(
                    sources[NodeRef("Event", key, "event_id")],
                    NodeScores(),
                    provenance_source=provenance_source,
                ),
            )
        for row in [link, *actual]:
            identity = (row["source_key"], row["edge_type"], row["target_key"])
            if identity not in seen:
                seen.add(identity)
                edges.append(
                    AtlasEdge(
                        source=identity[0],
                        edge_type=identity[1],
                        target=identity[2],
                        properties=row.get("properties", {}),
                    )
                )
    return truncated
