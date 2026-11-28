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
        if before is None or reinterpret:
            return dict(incoming)
        return None
    if reinterpret and before and before.get("bundle") != incoming.get("bundle"):
        before = None
    was_required = bool(before and before.get("required"))
    field_winners = dict(before.get("field_winners", {})) if before else {}
    if before:
        for effect in before.get("effects", []):
            for name in effect["writes"]:
                field_winners[name] = max(field_winners.get(name, ""), effect["order_key"])
    prior_order = before["order_key"] if before else ""
    patch_existing = False
    if before and before.get("status") in {"recovered", "existing_relationship_kept"}:
        if incoming["order_key"] <= before["order_key"]:
            uncovered = [name for name in incoming.get("writes", []) if name not in field_winners]
            if not uncovered:
                return None
            incoming = {**incoming, "writes": uncovered}
            patch_existing = True
        # Completed fields already exist. Keep only winner order metadata;
        # recovery never needs their retention-expired source documents again.
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
    entry: dict[str, Any] = {key: incoming.get(key) for key in pointer_keys}
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
    for name in entry["writes"]:
        field_winners[name] = max(field_winners.get(name, ""), entry["order_key"])
    record["field_winners"] = field_winners
    record["order_key"] = max(prior_order, incoming["order_key"])
    record["patch_existing"] = patch_existing or bool(before and before.get("patch_existing"))
    record["required"] = bool(incoming["required"] or was_required)
    record["generation"] = intent_generation(record)
    if before and record["generation"] == before["generation"]:
        return None
    record["status"] = "endpoint_missing"
    if len(retained) > 1024 or len(json.dumps(record)) > 131_072:
        raise ValueError("relationship_recovery_metadata_budget_exceeded")
    return record
