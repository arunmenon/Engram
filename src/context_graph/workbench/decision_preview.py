"""Transient candidate checks through the real planner; never writes graph or draft state."""

import copy
import json
from typing import Any, Literal

from pydantic import Field

from context_graph.workbench.authoring import samples
from context_graph.workbench.engine import validate
from context_graph.workbench.models import Content, Strict


class CandidateEdit(Strict):
    path: list[str | int] = Field(min_length=1, max_length=8)
    value: Any


class DecisionOption(Strict):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,50}$")
    label: str = Field(min_length=1, max_length=120)
    explanation: str = Field(min_length=1, max_length=800)
    evidence: list[str] = Field(min_length=1, max_length=8)
    kind: Literal["identity", "lifecycle"]
    node_type: str = Field(min_length=1, max_length=100)
    edits: list[CandidateEdit] = Field(default_factory=list, max_length=20)


def candidate_pack(raw: dict[str, Any], option: DecisionOption) -> dict[str, Any]:
    candidate = copy.deepcopy(raw)
    node = candidate.get("types", {}).get("nodes", {}).get(option.node_type)
    if not isinstance(node, dict):
        raise ValueError("The selected record type is absent from this pack")
    if option.kind == "lifecycle" and not node.get("lifecycle"):
        raise ValueError("This record type has no lifecycle states")
    if len(json.dumps([edit.model_dump() for edit in option.edits])) > 8000:
        raise ValueError("This option exceeds the bounded preview size")
    if len({tuple(edit.path) for edit in option.edits}) != len(option.edits):
        raise ValueError("An option cannot replace the same rule twice")
    for edit in option.edits:
        path = edit.path
        parent: Any = candidate
        for part in path[:-1]:
            if (
                isinstance(parent, list)
                and type(part) is int
                and 0 <= part < len(parent)
                or isinstance(parent, dict)
                and isinstance(part, str)
                and part in parent
            ):
                if isinstance(parent, list):
                    assert isinstance(part, int)
                    parent = parent[part]
                else:
                    parent = parent[part]
            else:
                raise ValueError("The proposed rule path is not in the current pack")
        allowed = False
        if option.kind == "identity":
            allowed = path == ["types", "nodes", option.node_type, "key"] or (
                path[0] == "projection"
                and path[-1] == "key"
                and isinstance(parent, dict)
                and parent.get("type") == option.node_type
            )
        else:
            allowed = (
                len(path) == 4
                and path[0] == "projection"
                and path[2] == "transition"
                and path[3] in {"to", "only_from"}
                and isinstance(parent, dict)
                and parent.get("type") == option.node_type
            )
        if not allowed or not isinstance(parent, dict):
            raise ValueError(
                "This preview supports identity keys or existing transition guards/targets only"
            )
        parent[str(path[-1])] = copy.deepcopy(edit.value)
    return candidate


def summarize(check: dict[str, Any], node_type: str, key_fields: list[str]) -> dict[str, Any]:
    records: dict[str, list[int]] = {}
    identities: dict[str, dict[str, Any]] = {}
    event_names: dict[str, set[str]] = {}
    transitions = []
    edges: set[tuple[str, str, str]] = set()
    provenance: set[tuple[str, str, str]] = set()
    for sample in check["samples"]:
        plan = sample.get("planned") or {}
        for node in plan.get("nodes", []):
            if node["ref"]["label"] == node_type:
                key = node["ref"]["key"]
                records.setdefault(key, []).append(sample["index"] + 1)
                identities[key] = {
                    field: node["properties"][field]
                    for field in key_fields
                    if field in node["properties"]
                }
                event_names.setdefault(key, set()).add(sample["event_type"])
        for state in plan.get("states", []):
            if state["ref"]["label"] == node_type:
                transitions.append(
                    {
                        "sample": sample["index"] + 1,
                        "event": sample["event_type"],
                        "record": state["ref"]["key"],
                        "to": state["to_state"],
                        "only_from": state["only_from"],
                    }
                )
        for edge in plan.get("edges", []):
            if node_type in {edge["source"]["label"], edge["target"]["label"]}:
                # DERIVED_FROM is the engine's event-provenance link, not a business relation.
                target = provenance if edge["edge_type"] == "DERIVED_FROM" else edges
                target.add((edge["source"]["key"], edge["edge_type"], edge["target"]["key"]))
    return {
        "record_count": len(records),
        "records": [
            {
                "id": key,
                "samples": sorted(set(indices)),
                "identity": identities[key],
                "events": sorted(event_names[key]),
            }
            for key, indices in records.items()
        ],
        "relationships": [list(edge) for edge in sorted(edges)],
        "provenance_relationships": [list(edge) for edge in sorted(provenance)],
        "transitions": transitions,
    }


def preview_options(record: dict[str, Any], options: list[DecisionOption]) -> list[dict[str, Any]]:
    if not options:
        return []
    content = Content.model_validate(record["content"])
    raw = record["proposal"]["pack"]
    results = []
    for option in options:
        result: dict[str, Any] = {
            "id": option.id,
            "available": False,
            "label": "Planned, not executed",
            "reason": None,
        }
        try:
            if len(samples(content)) > 20:
                raise ValueError("Use at most 20 representative events for a decision preview")
            candidate = candidate_pack(raw, option)
            before, after = validate(content, raw), validate(content, candidate)
            if not before["passed"] or not after["passed"]:
                raise ValueError(
                    "The current or candidate pack did not pass composition and sample checks"
                )
            baseline, planned = (
                summarize(before, option.node_type, raw["types"]["nodes"][option.node_type]["key"]),
                summarize(
                    after, option.node_type, candidate["types"]["nodes"][option.node_type]["key"]
                ),
            )
            if option.kind == "identity" and not planned["records"]:
                raise ValueError("Cannot be planned from these samples: no matching record updates")
            if option.kind == "lifecycle":
                exercised = {transition["event"] for transition in planned["transitions"]}
                edited_events = {
                    candidate["projection"][edit.path[1]]["event"] for edit in option.edits
                }
                if not exercised or not edited_events.issubset(exercised):
                    raise ValueError(
                        "Cannot be planned from these samples: the selected transitions are "
                        "not covered"
                    )
            result.update(available=True, before=baseline, after=planned)
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            result["reason"] = (
                "This option is unavailable; its rules or sample coverage need review."
            )
            if str(exc).startswith("Cannot be planned from these samples"):
                result["reason"] = (
                    "This choice cannot be planned from these samples. Add events that exercise "
                    "the affected records or state changes, or leave the decision unresolved."
                )
            result["detail"] = str(exc)[:1500]
        results.append(result)
    return results
