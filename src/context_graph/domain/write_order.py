"""Pure, explicit business-order decisions over a native transaction snapshot."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import asdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from context_graph.domain.relationship_recovery import recovery_digest, semantic_digest

if TYPE_CHECKING:
    from context_graph.ports.pack_graph import (
        EdgeWrite,
        NodeRef,
        NodeWrite,
        StateChange,
        WriteOrder,
    )

ORDER_LABEL = "ProjectionOrder"
NodeKey = tuple[str, str]
EdgeKey = tuple[NodeKey, str, NodeKey]


def ordering_value(value: Any, kind: str) -> str:
    if kind == "sequence":
        if type(value) is not int or not 0 <= value <= 2**63 - 1:
            raise ValueError("write_order_requires_nonnegative_int64_sequence")
        return f"{value:020d}"
    if not isinstance(value, str) or not re.search(r"(Z|[+-]\d\d:\d\d)$", value):
        raise ValueError("write_order_requires_explicit_timezone_timestamp")
    fraction = re.search(r"[.,](\d+)", value)
    if fraction and len(fraction[1]) > 6:
        raise ValueError("write_order_timestamp_precision_exceeds_microseconds")
    try:
        stamp = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("write_order_invalid_timestamp") from exc
    return stamp.astimezone(UTC).isoformat(timespec="microseconds")


def node_key(ref: NodeRef) -> NodeKey:
    return ref.label, ref.key


def edge_key(edge: EdgeWrite) -> EdgeKey:
    return node_key(edge.source), edge.edge_type, node_key(edge.target)


def clock_key(kind: str, key: NodeKey | EdgeKey) -> NodeKey:
    return ORDER_LABEL, recovery_digest([kind, key])


def authority_claims(
    nodes: list[NodeWrite], states: list[StateChange], edges: list[EdgeWrite]
) -> dict[NodeKey, dict[str, Any]]:
    """Immutable identities for observed authority values, even after field supersession.

    One compact row per record/authority value, not a retained payload/history
    queue. Reusing a sequence for a different event remains detectable forever.
    """
    claims: dict[NodeKey, dict[str, Any]] = {}
    candidates: list[tuple[str, NodeKey | EdgeKey, WriteOrder | None]] = [
        ("node", node_key(w.ref), w.order) for w in nodes if not w.placeholder
    ]
    candidates += [("node", node_key(w.ref), w.order) for w in states]
    for edge in edges:
        candidates.extend(
            ("edge", edge_key(edge), token)
            for token in [edge.order, *(edge.property_orders or {}).values()]
        )
    for kind, key, token in candidates:
        if token is None or not token.value:
            continue
        if not re.fullmatch(r"[0-9a-f]{64}", token.effect_digest):
            raise ValueError("write_order_requires_semantic_receipt")
        ckey = (ORDER_LABEL, recovery_digest(["claim", kind, key, token.contract, token.value]))
        claim = {
            "node_id": ckey[1],
            "kind": "authority_claim",
            "contract": token.contract,
            "source": token.source,
            "value": token.value,
            "event_id": token.event_id,
            "source_digest": token.source_digest,
            "effect_digest": token.effect_digest,
            "bundle": token.bundle,
        }
        if ckey in claims and claims[ckey] != claim:
            raise ValueError("write_order_equal_authority_conflict")
        claims[ckey] = claim
    return claims


def snapshot_keys(
    nodes: list[NodeWrite], states: list[StateChange], edges: list[EdgeWrite]
) -> tuple[set[NodeKey], set[EdgeKey]]:
    keys = {node_key(w.ref) for w in nodes} | {node_key(w.ref) for w in states}
    edge_keys = {edge_key(w) for w in edges}
    clocks = {clock_key("node", key) for key in keys}
    clocks |= {clock_key("edge", key) for key in edge_keys}
    keys |= {node_key(ref) for edge in edges for ref in (edge.source, edge.target)}
    return keys | clocks | set(authority_claims(nodes, states, edges)), edge_keys


def decide(
    nodes: list[NodeWrite],
    states: list[StateChange],
    edges: list[EdgeWrite],
    stored_nodes: dict[NodeKey, dict[str, Any]],
    stored_edges: dict[EdgeKey, dict[str, Any]],
    *,
    reinterpret: bool = False,
) -> tuple[dict[NodeKey, dict[str, Any]], dict[EdgeKey, dict[str, Any]], dict[str, int]]:
    """Return changed rows only; caller commits all rows atomically or none.

    There is no I/O, inferred authority, retained payload or hidden arrival clock.
    An absent legacy clock cannot be initialized over an existing real record.
    """
    current_nodes, current_edges = deepcopy(stored_nodes), deepcopy(stored_edges)
    changed_nodes: set[NodeKey] = set()
    changed_edges: set[EdgeKey] = set()
    counts = {"stale_fields": 0, "duplicate_fields": 0, "written_fields": 0, "edges": 0}

    duplicates: set[NodeKey] = set()
    identity_fields = (
        "node_id",
        "kind",
        "contract",
        "source",
        "value",
        "event_id",
        "source_digest",
    )
    available = set(current_nodes) | {node_key(write.ref) for write in nodes}
    ready_edges = [
        edge
        for edge in edges
        if node_key(edge.source) in available and node_key(edge.target) in available
    ]
    for ckey, claim in authority_claims(nodes, states, ready_edges).items():
        previous = current_nodes.get(ckey)
        if previous is not None:
            if any(previous.get(name) != claim[name] for name in identity_fields):
                raise ValueError("write_order_equal_authority_conflict")
            if previous.get("effect_digest") == claim["effect_digest"]:
                duplicates.add(ckey)
                continue
            if not (reinterpret and previous.get("bundle") != claim["bundle"]):
                raise ValueError("write_order_changed_effect_without_explicit_replay")
        current_nodes[ckey] = claim
        changed_nodes.add(ckey)

    def duplicate(kind: str, key: NodeKey | EdgeKey, token: WriteOrder) -> bool:
        ckey = (ORDER_LABEL, recovery_digest(["claim", kind, key, token.contract, token.value]))
        return ckey in duplicates

    def require_record(kind: str, key: NodeKey | EdgeKey, present: bool) -> None:
        previous = current_nodes.get(clock_key(kind, key))
        if not present and previous is not None and not previous.get("placeholder"):
            raise ValueError(f"write_order_{kind}_missing_but_clock_survives")

    def clock(
        kind: str, key: NodeKey | EdgeKey, token: WriteOrder, existing: bool
    ) -> dict[str, Any]:
        ckey = clock_key(kind, key)
        previous = current_nodes.get(ckey)
        if previous is None:
            if existing:
                raise ValueError("write_order_existing_data_needs_explicit_rebuild")
            previous = {
                "node_id": ckey[1],
                "contract": token.contract,
                "source": token.source,
                "fields": {},
                "placeholder": True,
            }
            current_nodes[ckey] = previous
        if previous["contract"] != token.contract or previous["source"] != token.source:
            raise ValueError("write_order_policy_or_source_conflict")
        changed_nodes.add(ckey)
        return previous

    def permitted(meta: dict[str, Any], name: str, value: Any, token: WriteOrder) -> bool:
        if not token.value or not token.event_id or not token.source_digest:
            raise ValueError("write_order_missing_authority")
        fields = meta["fields"]
        prior = fields.get(name)
        new = {**asdict(token), "mutation": semantic_digest(value)}
        for observed in fields.values():
            if observed["value"] == token.value and (
                observed["event_id"] != token.event_id
                or observed["source_digest"] != token.source_digest
            ):
                raise ValueError("write_order_equal_authority_conflict")
        if prior is not None:
            if token.value < prior["value"]:
                counts["stale_fields"] += 1
                return False
            if token.value == prior["value"]:
                if (
                    token.event_id != prior["event_id"]
                    or token.source_digest != prior["source_digest"]
                ):
                    raise ValueError("write_order_equal_authority_conflict")
                reinterpreted = reinterpret and token.bundle != prior["bundle"]
                if not reinterpreted:
                    if token.ordinal < prior.get("ordinal", 0):
                        counts["stale_fields"] += 1
                        return False
                    if token.ordinal == prior.get("ordinal", 0):
                        if new["mutation"] == prior["mutation"] and token.bundle == prior["bundle"]:
                            counts["duplicate_fields"] += 1
                            return False
                        raise ValueError("write_order_changed_effect_without_explicit_replay")
        fields[name] = new
        meta["placeholder"] = False
        if len(json.dumps(meta)) > 131_072:
            raise ValueError("write_order_metadata_budget_exceeded")
        counts["written_fields"] += 1
        return True

    for write in nodes:
        token = write.order
        if token is None:
            raise ValueError("write_order_port_requires_ordered_mutation")
        key = node_key(write.ref)
        require_record("node", key, key in current_nodes)
        if not write.placeholder and duplicate("node", key, token):
            counts["duplicate_fields"] += len(write.properties) + len(write.remove_properties)
            continue
        meta = clock("node", key, token, key in current_nodes)
        if write.placeholder:
            if key not in current_nodes:
                current_nodes[key] = {
                    **write.defaults,
                    **write.properties,
                    write.ref.key_property: write.ref.key,
                }
                changed_nodes.add(key)
            continue
        props = current_nodes.get(key, {})
        if meta["placeholder"]:
            props = {**props, **write.defaults, write.ref.key_property: write.ref.key}
        for name, value in write.properties.items():
            if value is not None and permitted(meta, name, ["set", value], token):
                props[name] = value
        for name in write.remove_properties:
            if permitted(meta, name, ["clear"], token):
                props.pop(name, None)
        current_nodes[key] = props
        changed_nodes.add(key)

    for state in states:
        token = state.order
        if token is None:
            raise ValueError("write_order_port_requires_ordered_mutation")
        key = node_key(state.ref)
        if key not in current_nodes:
            raise ValueError("write_order_state_record_missing")
        if duplicate("node", key, token):
            counts["duplicate_fields"] += 1
            continue
        meta = clock("node", key, token, True)
        props = current_nodes[key]
        if permitted(meta, "status", ["state", state.to_state, state.only_from], token):
            if props.get("status") == state.to_state:
                continue
            if state.only_from and props.get("status") not in state.only_from:
                raise ValueError("write_order_state_prerequisite_missing")
            props.update(status=state.to_state, status_changed_at=state.changed_at)
            changed_nodes.add(key)

    for edge in edges:
        token = edge.order
        if token is None:
            raise ValueError("write_order_port_requires_ordered_mutation")
        ekey = edge_key(edge)
        if ekey[0] not in current_nodes or ekey[2] not in current_nodes:
            # S2 journals missing endpoints separately; no clock is advanced.
            continue
        require_record("edge", ekey, ekey in current_edges)
        if edge.create_only and ekey in current_edges:
            continue
        orders = [token, *(edge.property_orders or {}).values()]
        if all(duplicate("edge", ekey, order) for order in orders):
            counts["duplicate_fields"] += len(edge.properties) + len(edge.remove_properties)
            continue
        meta = clock("edge", ekey, token, ekey in current_edges)
        props = current_edges.get(ekey, {})
        for name, value in edge.properties.items():
            field_order = (edge.property_orders or {}).get(name, token)
            if duplicate("edge", ekey, field_order):
                counts["duplicate_fields"] += 1
                continue
            if value is not None and permitted(meta, name, ["set", value], field_order):
                props[name] = value
        for name in edge.remove_properties:
            field_order = (edge.property_orders or {}).get(name, token)
            if duplicate("edge", ekey, field_order):
                counts["duplicate_fields"] += 1
                continue
            if permitted(meta, name, ["clear"], field_order):
                props.pop(name, None)
        current_edges[ekey] = props
        changed_edges.add(ekey)
        counts["edges"] += 1

    return (
        {k: current_nodes[k] for k in changed_nodes},
        {k: current_edges[k] for k in changed_edges},
        counts,
    )
