"""Bounded session Episode context, returned only with actual complete evidence."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context_graph.domain.episodes import summary_matches_snapshot
from context_graph.domain.models import AtlasEdge, AtlasNode, NodeScores
from context_graph.ports.pack_graph import NodeRef
from context_graph.retrieval.atlas import build_atlas_node

if TYPE_CHECKING:
    from context_graph.domain.models import SubgraphQuery
    from context_graph.ports.pack_graph import PackGraph


async def add_episode_context(
    graph: PackGraph,
    query: SubgraphQuery,
    nodes: dict[str, AtlasNode],
    edges: list[AtlasEdge],
    seen: set[tuple[str, str, str]],
    provenance_source: str,
    *,
    owner_id: str | None = None,
) -> bool:
    """Add immutable membership snapshots; return whether the storage bound cut data.

    This supplies session context, not a latest partition or inferred domain links.
    Four bounded graph calls fetch candidates, their nodes and actual relationships.
    """
    limit = min(query.max_nodes, 10)
    candidates = await graph.find_nodes(
        "Episode", {"session_id": query.session_id, "complete": True}, limit + 1
    )
    truncated = len(candidates) > limit
    episodes = []
    refs: set[NodeRef] = set()
    member_count = 0
    for props in candidates[:limit]:
        members = props.get("source_event_ids", [])
        if (
            not isinstance(members, list)
            or not all(isinstance(member, str) for member in members)
            or not props.get("summary_id")
            or not props.get("episode_id")
            or not members
            or len(set(members)) != len(members)
            or props.get("event_count") != len(members)
        ):
            continue
        if member_count + len(members) > 500:
            truncated = True
            continue
        member_count += len(members)
        episodes.append(props)
        refs.add(NodeRef("Summary", props["summary_id"], "summary_id"))
        refs.update(NodeRef("Event", member, "event_id") for member in members)
    if not episodes:
        return truncated
    found = await graph.get_nodes(sorted(refs, key=lambda ref: (ref.label, ref.key)))
    episode_refs = [NodeRef("Episode", p["episode_id"], "episode_id") for p in episodes]
    row_limit = 2 * member_count + len(episodes) + 1
    rows = await graph.neighbors(
        episode_refs, ["CONTAINS", "DERIVED_FROM", "SUMMARIZES"], "both", row_limit
    )
    summary_refs = [NodeRef("Summary", p["summary_id"], "summary_id") for p in episodes]
    summary_limit = member_count + len(episodes) + 1
    summary_rows = await graph.neighbors(summary_refs, ["SUMMARIZES"], "out", summary_limit)
    if len(rows) >= row_limit or len(summary_rows) >= summary_limit:
        # A bounded read cannot establish exact evidence when unseen edges may remain.
        return True
    for props in episodes:
        identity = props["episode_id"]
        members = set(props["source_event_ids"])
        contained: set[str] = set()
        derived: set[str] = set()
        valid_edges = []
        summary_link = False
        for row in rows:
            edge = row["edge_type"]
            if (row["source_label"], row["source_key"], row["target_label"]) == (
                "Episode",
                identity,
                "Event",
            ):
                target = row["target_key"]
                if edge in {"CONTAINS", "DERIVED_FROM"}:
                    (contained if edge == "CONTAINS" else derived).add(target)
                    valid_edges.append((identity, edge, target, row.get("properties", {})))
            if (
                row["source_label"],
                row["source_key"],
                edge,
                row["target_label"],
                row["target_key"],
            ) == ("Summary", props["summary_id"], "SUMMARIZES", "Episode", identity):
                summary_link = True
                valid_edges.append((props["summary_id"], edge, identity, row.get("properties", {})))
        sources = [found.get(NodeRef("Event", member, "event_id")) for member in sorted(members)]
        summary = found.get(NodeRef("Summary", props["summary_id"], "summary_id"))
        if (
            contained != members
            or derived != members
            or not summary_link
            or not summary
            or any(not source or source.get("session_id") != query.session_id for source in sources)
        ):
            continue
        valid_sources = [source for source in sources if source is not None]
        if owner_id is not None and any(
            source.get("agent_id") != owner_id for source in valid_sources
        ):
            # The Summary represents the entire snapshot; do not filter its
            # members and present a different, apparently complete Episode.
            continue
        if not summary_matches_snapshot(summary, identity, valid_sources) or [
            props.get("start_time"),
            props.get("end_time"),
        ] != summary.get("time_range"):
            continue
        summary_sources = [
            row
            for row in summary_rows
            if row["source_key"] == props["summary_id"] and row["target_label"] == "Event"
        ]
        if {row["target_key"] for row in summary_sources} != members:
            continue
        valid_edges.extend(
            (props["summary_id"], "SUMMARIZES", row["target_key"], row.get("properties", {}))
            for row in summary_sources
        )
        anchor = min(
            valid_sources, key=lambda source: (source.get("occurred_at", ""), source["event_id"])
        )
        evidence = build_atlas_node(
            anchor, NodeScores(), provenance_source=provenance_source
        ).provenance
        for source in valid_sources:
            nodes.setdefault(
                source["event_id"],
                build_atlas_node(source, NodeScores(), provenance_source=provenance_source),
            )
        for key, label, attrs in [
            (identity, "Episode", props),
            (props["summary_id"], "Summary", summary),
        ]:
            nodes[key] = AtlasNode(
                node_id=key,
                node_type=label,
                attributes=attrs,
                provenance=evidence,
                scores=NodeScores(decay_score=0.9, relevance_score=1.0, importance_score=5),
                retrieval_reason="episode",
            )
        for source, edge, target, attributes in valid_edges:
            if (source, edge, target) not in seen:
                seen.add((source, edge, target))
                edges.append(
                    AtlasEdge(source=source, target=target, edge_type=edge, properties=attributes)
                )
    return truncated
