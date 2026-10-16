"""Materialize deterministic, evidenced membership snapshots via existing graph ports."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

from context_graph.ports.pack_graph import EdgeWrite, NodeRef, NodeWrite

if TYPE_CHECKING:
    from context_graph.domain.models import SummaryNode
    from context_graph.ports.pack_graph import PackGraph


def episode_identity(session_id: str, event_ids: list[str]) -> str:
    """Identity is independent of arrival order and the position of other groups."""
    members = sorted(set(event_ids))
    digest = hashlib.sha256(
        json.dumps([session_id, members], separators=(",", ":")).encode()
    ).hexdigest()
    return "episode-" + digest


def summary_matches_snapshot(
    summary: dict[str, Any], identity: str, events: list[dict[str, Any]]
) -> bool:
    """Validate stored ownership and temporal bounds against actual source rows."""
    try:
        timestamps = [datetime.fromisoformat(str(event["occurred_at"])) for event in events]
        bounds = [datetime.fromisoformat(str(value)) for value in summary.get("time_range", [])]
        return (
            bool(timestamps)
            and summary.get("scope") == "episode"
            and summary.get("scope_id") == identity
            and summary.get("event_count") == len(events)
            and bounds == [min(timestamps), max(timestamps)]
        )
    except (KeyError, TypeError, ValueError):
        return False


async def materialize_episode_snapshot(
    graph: PackGraph, session_id: str, summary: SummaryNode, events: list[dict[str, Any]]
) -> str:
    members = sorted({str(event["event_id"]) for event in events})
    if not members or len(members) != len(events) or len(summary.time_range) != 2:
        raise ValueError("Episode requires unique source events and a bounded time range")
    refs = [NodeRef("Event", member, "event_id") for member in members]
    summary_ref = NodeRef("Summary", summary.summary_id, "summary_id")
    found = await graph.get_nodes([*refs, summary_ref])
    if summary_ref not in found or any(
        ref not in found or found[ref].get("session_id") != session_id for ref in refs
    ):
        raise ValueError("Episode source events and summary must exist in the same session")
    identity = episode_identity(session_id, members)
    if not summary_matches_snapshot(found[summary_ref], identity, [found[ref] for ref in refs]):
        raise ValueError("Episode summary ownership or temporal bounds are invalid")
    summary_sources = await graph.neighbors([summary_ref], ["SUMMARIZES"], "out", len(members) + 2)
    if (
        len(summary_sources) >= len(members) + 2
        or summary.scope != "episode"
        or summary.event_count != len(members)
        or {row["target_key"] for row in summary_sources if row["target_label"] == "Event"}
        != set(members)
    ):
        raise ValueError("Episode summary must summarize exactly its source events")
    episode = NodeRef("Episode", identity, "episode_id")
    properties = {
        "session_id": session_id,
        "start_time": found[summary_ref]["time_range"][0],
        "end_time": found[summary_ref]["time_range"][-1],
        "event_count": len(members),
        "episode_type": "temporal",
        "summary_id": summary.summary_id,
        "source_event_ids": members,
        "snapshot_kind": "membership",
    }
    evidence = {"method": "temporal_consolidation", "session_id": session_id}
    existing = (await graph.get_nodes([episode])).get(episode)
    if (
        existing is not None
        and existing.get("episode_id") == identity
        and existing.get("complete") is True
        and all(existing.get(key) == value for key, value in properties.items())
    ):
        # Routine Summary refresh must not deactivate an immutable published Episode.
        # Overflow rows make the shortcut fail rather than hide extra links.
        membership = await graph.neighbors(
            [episode], ["CONTAINS", "DERIVED_FROM"], "out", 2 * len(members) + 1
        )
        summarized_by = await graph.neighbors([episode], ["SUMMARIZES"], "in", 2)
        expected = {(kind, member) for kind in ("CONTAINS", "DERIVED_FROM") for member in members}
        if (
            len(membership) == len(expected)
            and {(r["edge_type"], r["target_key"]) for r in membership} == expected
            and all(
                r["source_label"] == "Episode"
                and r["source_key"] == identity
                and r["target_label"] == "Event"
                and r.get("properties", {}) == evidence
                for r in membership
            )
            and len(summarized_by) == 1
            and summarized_by[0]["source_label"] == "Summary"
            and summarized_by[0]["source_key"] == summary_ref.key
            and summarized_by[0]["target_label"] == "Episode"
            and summarized_by[0]["target_key"] == identity
            and summarized_by[0].get("properties", {}) == {}
        ):
            return identity
    await graph.upsert_nodes([NodeWrite(episode, {**properties, "complete": False})])
    links = [
        EdgeWrite(kind, episode, ref, evidence)
        for ref in refs
        for kind in ("CONTAINS", "DERIVED_FROM")
    ]
    links.append(EdgeWrite("SUMMARIZES", summary_ref, episode))
    if await graph.upsert_edges(links) != len(links):
        raise ValueError("Episode evidence is incomplete; retry after source projection")
    await graph.upsert_nodes([NodeWrite(episode, {"complete": True})])
    return identity
