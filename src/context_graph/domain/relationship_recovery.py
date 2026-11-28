"""Pure compaction of deferred edge effects; never store payload/property values."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from context_graph.ports.errors import RuntimeFencedError


def recovery_digest(value: Any) -> str:
    def normalize(item: Any) -> Any:
        if isinstance(item, dict):
            return {key: normalize(v) for key, v in item.items() if v is not None}
        if isinstance(item, list | tuple):
            return [normalize(v) for v in item]
        return item

    encoded = json.dumps(normalize(value), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def intent_generation(record: dict[str, Any]) -> str:
    return recovery_digest(
        [
            record["edge_type"],
            record["source"],
            record["target"],
            record["required"],
            record["effects"],
        ]
    )


def merge_relationship_intent(
    before: dict[str, Any] | None, incoming: dict[str, Any], *, reinterpret: bool = False
) -> dict[str, Any] | None:
    """Keep only event references needed for the last write to each property.

    A later event may omit a property: dropping the earlier effect would lose it.
    Metadata size/effect bounds refuse work explicitly, never silently evict it.
    """
    if incoming.get("kind") == "blocked_lookup":
        return None if before is not None else dict(incoming)
    if reinterpret and before and before.get("bundle") != incoming.get("bundle"):
        before = None
    if before and before.get("status") in {"recovered", "existing_relationship_kept"}:
        if incoming["order_key"] <= before["order_key"]:
            return None
        # Completed fields are already in the graph. A genuinely new event
        # need not retain/refetch their source documents after retention.
        before = None
    pointer_keys = (
        "event_id",
        "bundle",
        "authority",
        "effect_digest",
        "selector_digest",
        "position",
        "order_key",
        "required",
        "writes",
        "plan_digest",
        "source_id",
        "source_digest",
    )
    entry = {key: incoming.get(key) for key in pointer_keys}
    entry["writes"] = incoming.get("writes") or ["__edge__"]
    entry["event_generation"] = incoming["generation"]
    entries = list(before.get("effects", [])) if before else []
    for prior in entries:
        if prior["order_key"] == entry["order_key"]:
            if prior != entry:
                raise RuntimeFencedError("Conflicting deferred effects at one log position")
            break
    else:
        entries.append(entry)
    entries.sort(key=lambda p: p["order_key"])
    winner: dict[str, str] = {}
    for effect in entries:
        for name in effect["writes"]:
            winner[name] = effect["order_key"]
    retained = [effect for effect in entries if effect["order_key"] in set(winner.values())]
    latest = before if before and before["order_key"] > incoming["order_key"] else incoming
    record = {
        key: value
        for key, value in latest.items()
        if key not in {"effects", "generation", "status"}
    }
    record["effects"] = retained
    record["required"] = bool(incoming["required"] or (before and before["required"]))
    record["generation"] = intent_generation(record)
    if before and record["generation"] == before["generation"]:
        return None
    record["status"] = "endpoint_missing"
    if len(retained) > 1024 or len(json.dumps(record)) > 131_072:
        raise ValueError("relationship_recovery_metadata_budget_exceeded")
    return record
