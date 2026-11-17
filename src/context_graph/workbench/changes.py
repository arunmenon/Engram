"""Reviewable omissions across assistant revisions, including repair attempts."""

from typing import Any


def _mapping(value: Any) -> dict[str, Any]:
    """Inspect partial model output without preempting the validator's repair loop."""
    return value if isinstance(value, dict) else {}


def pack_items(pack: dict[str, Any] | None) -> set[str]:
    if not pack:
        return set()
    items: set[str] = set()
    for kind in ("nodes", "edges"):
        for name, definition in _mapping(_mapping(pack.get("types")).get(kind)).items():
            items.add(f"{kind}.{name}")
            definition = _mapping(definition)
            for prop in _mapping(definition.get("properties")):
                items.add(f"{kind}.{name}.{prop}")
            states = _mapping(definition.get("lifecycle")).get("states", [])
            for state in states if isinstance(states, list) else []:
                items.add(f"{kind}.{name}.state:{state}")
    for name in _mapping(pack.get("events")):
        items.add(f"event:{name}")
    for name in _mapping(_mapping(pack.get("retrieval")).get("intents")):
        items.add(f"question intent:{name}")
    return items


def removed_items(before: dict[str, Any] | None, after: dict[str, Any] | None) -> list[str]:
    return sorted(pack_items(before) - pack_items(after))


def pack_changes(
    before: dict[str, Any] | None, after: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """Reviewable structural differences, not a claim of semantic equivalence.

    Keep identity lists together; show individual projection edits and ordering changes.
    IDs bind acknowledgement to the exact before/after values, not just a path.
    """
    import hashlib
    import json

    if before is None:
        return []  # Initial creation is reviewed as a whole pack.
    missing = object()
    changes: list[dict[str, Any]] = []

    def walk(old: Any, new: Any, path: list[str]) -> None:
        if (
            old is not missing
            and new is not missing
            and json.dumps(old, sort_keys=True) == json.dumps(new, sort_keys=True)
        ):
            return
        if isinstance(old, dict) and isinstance(new, dict):
            for key in sorted(old.keys() | new.keys()):
                if path == ["pack"] and key in {"version", "description", "owner"}:
                    continue
                walk(old.get(key, missing), new.get(key, missing), [*path, key])
            return
        if isinstance(old, list) and isinstance(new, list) and path == ["projection"]:
            # An event can have multiple rules; only use event keys when unambiguous.
            keyed = all(isinstance(v, dict) and isinstance(v.get("event"), str) for v in old + new)
            if (
                keyed
                and len({v["event"] for v in old}) == len(old)
                and len({v["event"] for v in new}) == len(new)
            ):
                old_map, new_map = {v["event"]: v for v in old}, {v["event"]: v for v in new}
                for event in sorted(old_map.keys() | new_map.keys()):
                    walk(old_map.get(event, missing), new_map.get(event, missing), [*path, event])
                old_order, new_order = [v["event"] for v in old], [v["event"] for v in new]
                if old_map.keys() == new_map.keys() and old_order != new_order:
                    walk(old_order, new_order, [*path, "rule order"])
            else:
                for i in range(max(len(old), len(new))):
                    walk(
                        old[i] if i < len(old) else missing,
                        new[i] if i < len(new) else missing,
                        [*path, str(i)],
                    )
            return
        category = {
            "projection": "Event mappings",
            "events": "Event contracts and handling",
            "retrieval": "Question retrieval",
            "processing": "Processing requirements",
            "pack": "Pack identity and dependencies",
        }.get(path[0] if path else "", "Pack definitions")
        if "key" in path or "id_property" in path:
            category = "Entity identity"
        elif "lifecycle" in path:
            category = "Lifecycle rules"
        change = {
            "path": path,
            "category": category,
            "kind": "added" if old is missing else "removed" if new is missing else "changed",
            "before": None if old is missing else old,
            "after": None if new is missing else new,
        }
        subject = " / ".join(path) or "Executable pack"
        if category == "Entity identity":

            def keys(value: Any) -> str:
                return " + ".join(map(str, value)) if isinstance(value, list) else str(value)

            change["summary"] = (
                f"{path[2] if len(path) > 2 else subject}: identity changes from "
                f"{keys(change['before'])} to {keys(change['after'])}. "
                "Check whether records that were separate could now be combined."
            )
        else:
            change["summary"] = (
                f"{subject} was {change['kind']}. Review the before and proposed rule."
            )
        change["id"] = hashlib.sha256(json.dumps(change, sort_keys=True).encode()).hexdigest()
        changes.append(change)

    walk(before, after, [])
    return changes
