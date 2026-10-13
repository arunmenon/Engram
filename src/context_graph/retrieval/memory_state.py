"""Bounded, owner-scoped Belief and Goal recall with actual graph evidence."""

from __future__ import annotations

import math
from datetime import datetime
from typing import TYPE_CHECKING, Any

from context_graph.domain.memory_actions import MEMORY_EVENT_HANDLERS, memory_identity
from context_graph.domain.models import AtlasEdge, AtlasNode, NodeScores
from context_graph.ports.pack_graph import NodeRef
from context_graph.retrieval.atlas import build_atlas_node

if TYPE_CHECKING:
    from context_graph.domain.models import SubgraphQuery
    from context_graph.ports.pack_graph import PackGraph


def _owned(props: dict[str, Any], query: SubgraphQuery) -> bool:
    return props.get("agent_id") == query.agent_id and (
        props.get("scope") == "agent"
        or (props.get("scope") == "session" and props.get("session_id") == query.session_id)
    )


def _time(value: Any) -> datetime:
    timestamp = datetime.fromisoformat(str(value))
    if timestamp.utcoffset() is None:
        raise ValueError("Memory evidence timestamp must be timezone aware")
    return timestamp


def _valid_state(
    label: str,
    props: dict[str, Any],
    sources: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    query: SubgraphQuery,
) -> dict[str, Any] | None:
    """Return the actual creation Event only when counters and state are evidenced."""
    try:
        members = props["evidence_event_ids"]
        if (
            type(props.get("state_revision")) is not int
            or props["state_revision"] != len(members) - 1
        ):
            return None
        evidence = [
            row
            for row in rows
            if row["source_label"] == label
            and row["source_key"] == props[label.lower() + "_id"]
            and row["edge_type"] == "DERIVED_FROM"
        ]
        if {(row["target_label"], row["target_key"]) for row in evidence} != {
            ("Event", member) for member in members
        }:
            return None
        roles = {
            row["target_key"]: row.get("properties", {}).get("evidence_role") for row in evidence
        }
        creation = []
        support = set()
        terminals = []
        corrections = []
        for source in sources:
            if source.get("agent_id") != query.agent_id or (
                props["scope"] == "session" and source.get("session_id") != props["session_id"]
            ):
                return None
            if (
                source.get("memory_subject_id") != props[label.lower() + "_id"]
                or source.get("memory_subject_label") != label
            ):
                return None
            event_type = source["event_type"]
            if MEMORY_EVENT_HANDLERS.get(event_type) != "memory." + label.lower() + ".v1":
                return None
            action = event_type.rsplit(".", 1)[1]
            if label == "Belief":
                role = (
                    "inference"
                    if action == "inferred"
                    else "correction"
                    if action == "corrected"
                    else "support"
                )
                if action in ("stated", "inferred"):
                    creation.append(source)
                if action in ("stated", "confirmed"):
                    support.add(source["event_id"])
                if action == "corrected":
                    corrections.append(source)
            else:
                role = "lifecycle"
                if action == "created":
                    creation.append(source)
                else:
                    terminals.append(source)
            if roles[source["event_id"]] != role:
                return None
        if sorted(
            s["memory_expected_revision"]
            for s in sources
            if s.get("memory_expected_revision") is not None
        ) != list(range(len(members) - 1)):
            return None
        if len(creation) != 1 or _time(props["created_at"]) != _time(creation[0]["occurred_at"]):
            return None
        if creation[0].get("session_id") != props["session_id"]:
            return None
        if label == "Belief":
            if props.get("origin") != creation[0]["event_type"].rsplit(".", 1)[1]:
                return None
            if (
                type(props.get("confirmation_count")) is not int
                or props["confirmation_count"] != len(support)
                or len(props.get("supporting_event_ids", [])) != len(support)
                or set(props.get("supporting_event_ids", [])) != support
            ):
                return None
            confidence = props["confidence"]
            if (
                isinstance(confidence, bool)
                or not isinstance(confidence, (int, float))
                or not math.isfinite(confidence)
                or not 0 <= confidence <= 1
                or (props["origin"] == "inferred" and confidence > 0.8)
            ):
                return None
            if support:
                if _time(props["last_confirmed_at"]) != max(
                    _time(s["occurred_at"]) for s in sources if s["event_id"] in support
                ):
                    return None
            elif props.get("last_confirmed_at") is not None:
                return None
            if len(corrections) != int(bool(props.get("superseded_by"))):
                return None
        else:
            if len(terminals) > 1 or props.get("evidence_count") != len(members):
                return None
            expected = terminals[0]["event_type"].rsplit(".", 1)[1] if terminals else "active"
            if props.get("status") != expected or bool(props.get("superseded_by")) != (
                expected == "superseded"
            ):
                return None
            changed = terminals[0] if terminals else creation[0]
            if _time(props.get("status_changed_at")) != _time(changed["occurred_at"]) or _time(
                props["last_active_at"]
            ) != max(_time(s["occurred_at"]) for s in sources):
                return None
        return creation[0]
    except (KeyError, TypeError, ValueError):
        return None


async def add_memory_state_context(
    graph: PackGraph,
    query: SubgraphQuery,
    families: list[str],
    nodes: dict[str, AtlasNode],
    edges: list[AtlasEdge],
    seen: set[tuple[str, str, str]],
    provenance_source: str,
    *,
    include_history: bool = False,
) -> bool:
    limit = min(query.max_nodes, 10)
    candidates: list[tuple[str, dict[str, Any]]] = []
    truncated = False
    for family in families:
        for scope in ("session", "agent"):
            where = {"agent_id": query.agent_id, "scope": scope, "complete": True}
            if scope == "session":
                where["session_id"] = query.session_id
            matches = await graph.find_nodes(family, where, limit + 1)
            truncated |= len(matches) > limit
            candidates.extend((family, props) for props in matches[:limit])
    refs: set[NodeRef] = set()
    chosen = []
    for family, props in candidates:
        members = props.get("evidence_event_ids", [])
        if (
            not isinstance(members, list)
            or not members
            or not all(isinstance(m, str) for m in members)
            or len(set(members)) != len(members)
            or not isinstance(props.get("local_key"), str)
        ):
            truncated = True
            continue
        if props.get(family.lower() + "_id") != memory_identity(
            family, query.agent_id, props["scope"], props["session_id"], props["local_key"]
        ):
            truncated = True
            continue
        event_refs = {NodeRef("Event", member, "event_id") for member in members}
        if props.get("superseded_by"):
            event_refs.add(NodeRef(family, props["superseded_by"], family.lower() + "_id"))
        if len(refs | event_refs) > 1024:
            truncated = True
            continue
        refs |= event_refs
        chosen.append((family, props))
    if not chosen:
        return truncated
    found = await graph.get_nodes(sorted(refs, key=lambda ref: (ref.label, ref.key)))
    state_refs = [
        NodeRef(family, p[family.lower() + "_id"], family.lower() + "_id") for family, p in chosen
    ]
    row_limit = sum(len(p["evidence_event_ids"]) for _, p in chosen) + 4 * len(chosen) + 1
    rows = await graph.neighbors(
        state_refs, ["DERIVED_FROM", "SUPERSEDES", "CONTRADICTS"], "both", row_limit
    )
    if len(rows) >= row_limit:
        return True
    history = include_history
    authorized: set[tuple[str, str, str]] = set()
    valid = {}
    for family, props in chosen:
        possible_sources = [
            found.get(NodeRef("Event", member, "event_id"))
            for member in props["evidence_event_ids"]
        ]
        if any(source is None for source in possible_sources):
            truncated = True
            continue
        sources = [source for source in possible_sources if source is not None]
        anchor = _valid_state(family, props, sources, rows, query)
        identity = props[family.lower() + "_id"]
        if anchor is None:
            truncated = True
            continue
        if props.get("superseded_by"):
            replacement = found.get(NodeRef(family, props["superseded_by"], family.lower() + "_id"))
            history_sources = [
                s
                for s in sources
                if s["event_type"] in ("memory.belief.corrected", "memory.goal.superseded")
            ]
            required = {"SUPERSEDES"} | (
                {"CONTRADICTS"} if props.get("contradiction_declared") else set()
            )
            actual = {
                row["edge_type"]
                for row in rows
                if row["source_label"] == family
                and row["source_key"] == props["superseded_by"]
                and row["target_label"] == family
                and row["target_key"] == identity
                and row["edge_type"] in ("SUPERSEDES", "CONTRADICTS")
                and row.get("properties", {}).get("source_event_id")
                in {s["event_id"] for s in history_sources}
            }
            if (
                not replacement
                or not _owned(replacement, query)
                or not replacement.get("complete")
                or actual != required
            ):
                truncated = True
                continue
            authorized.update((props["superseded_by"], kind, identity) for kind in required)
            if not history:
                continue
        for source in sources:
            nodes.setdefault(
                source["event_id"],
                build_atlas_node(source, NodeScores(), provenance_source=provenance_source),
            )
        nodes[identity] = AtlasNode(
            node_id=identity,
            node_type=family,
            attributes=props,
            provenance=build_atlas_node(
                anchor, NodeScores(), provenance_source=provenance_source
            ).provenance,
            scores=NodeScores(decay_score=1, relevance_score=1, importance_score=5),
            retrieval_reason="memory_context",
        )
        valid[identity] = family
    for row in rows:
        source, target, kind = row["source_key"], row["target_key"], row["edge_type"]
        if kind in ("SUPERSEDES", "CONTRADICTS") and (source, kind, target) not in authorized:
            truncated = True
            continue
        if source in valid and target in nodes and (kind == "DERIVED_FROM" or target in valid):
            key = (source, kind, target)
            if key not in seen:
                seen.add(key)
                edges.append(
                    AtlasEdge(
                        source=source,
                        target=target,
                        edge_type=kind,
                        properties=row.get("properties", {}),
                    )
                )
    return truncated
