"""Frozen User extraction output and transaction plans; no service/framework dependency.

The first prepared result wins for an accepted trigger. A prepared receipt is
not successful projection; User outputs and the applied marker commit together.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from context_graph.domain.extraction import SessionExtractionResult
from context_graph.ports.errors import UnavailableError
from context_graph.ports.pack_graph import EdgeWrite, NodeRef, NodeWrite

RECEIPT_FIELD = "user_extraction_receipt"
OWNER_FIELD = "user_extraction_owner"
PRIVATE_FIELDS = frozenset((RECEIPT_FIELD, OWNER_FIELD))
if TYPE_CHECKING:
    from collections.abc import Mapping

    from context_graph.domain.models import Event

MAX_INPUT_EVENTS = 200
MAX_USER_OUTPUTS = 40


class UserExtractionConflictError(ValueError):
    """An accepted trigger/receipt or correction has incompatible identity/state."""


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def artifact_identity(family: str, owner: str, item: dict[str, Any]) -> str:
    if family == "Preference":
        fields = ["category", "key", "scope", "scope_id", "context", "polarity", "about_entity"]
    else:
        fields = ["category", "name"]
    return family.lower() + ":" + _digest([owner, *[item.get(field) for field in fields]])


def _content(document: dict[str, Any]) -> str:
    payload = document.get("payload") or {}
    if not isinstance(payload, dict):
        return ""
    return " ".join(str(payload.get(key) or "") for key in ("content", "input", "output"))


def _normalize(value: str) -> str:
    return " ".join(value.lower().split())


def prepare_extraction_receipt(
    trigger: Event,
    events: list[Event],
    documents: list[dict[str, Any]],
    raw: dict[str, Any],
    *,
    applied_correction_sources: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Freeze validated output identities and exact quoted source membership."""
    if not events or len(events) > MAX_INPUT_EVENTS or not trigger.global_position:
        raise ValueError("User extraction requires a bounded accepted input window")
    ids = [str(event.event_id) for event in events]
    if len(set(ids)) != len(ids) or ids[-1] != str(trigger.event_id):
        raise ValueError("User input window must contain its distinct accepted trigger")
    if any(
        event.agent_id != trigger.agent_id or event.session_id != trigger.session_id
        for event in events
    ):
        raise UserExtractionConflictError("User extraction window crosses owner/session")
    by_id = {str(document["event_id"]): document for document in documents}
    if set(by_id) != set(ids):
        raise ValueError("User extraction documents do not match frozen inputs")
    result = SessionExtractionResult.model_validate(
        {**raw, "session_id": trigger.session_id, "agent_id": trigger.agent_id}
    ).model_dump(mode="json")
    owner = "user:" + trigger.agent_id
    outputs = [item for kind in ("preferences", "skills", "interests") for item in result[kind]]
    if result["persona"]:
        outputs.append(result["persona"])
    if len(outputs) > MAX_USER_OUTPUTS:
        raise ValueError("User extraction output exceeds the atomic bound")
    for item in outputs:
        quote = _normalize(item.get("source_quote", ""))
        supports = [
            event_id for event_id in ids if quote and quote in _normalize(_content(by_id[event_id]))
        ]
        if not supports:
            raise ValueError("User extraction quote has no exact accepted source")
        item["support_event_ids"] = supports
    preferences = result["preferences"]
    original_contexts = {id(item): item.get("context") for item in preferences}
    assignments: dict[int, tuple[str, str | None]] = {}
    selected_corrections = []
    for event_id in ids:
        if event_id in applied_correction_sources:
            continue
        declared = (by_id[event_id].get("payload") or {}).get("preference_corrections", [])
        if not isinstance(declared, list):
            raise ValueError("Preference corrections must be a list")
        for correction in declared:
            if not isinstance(correction, dict) or set(correction) != {
                "previous_preference_id",
                "replacement_key",
                "replacement_polarity",
                "context",
            }:
                raise ValueError(
                    "Correction needs an exact predecessor, replacement key, polarity and context"
                )
            if (
                not isinstance(correction["previous_preference_id"], str)
                or not correction["previous_preference_id"].strip()
                or not isinstance(correction["replacement_key"], str)
                or not correction["replacement_key"].strip()
                or correction["replacement_polarity"] not in ("positive", "negative", "neutral")
                or (
                    correction["context"] is not None and not isinstance(correction["context"], str)
                )
            ):
                raise ValueError("Correction identity metadata types differ")
            candidates = [
                item
                for item in preferences
                if item["key"] == correction["replacement_key"]
                and item["polarity"] == correction["replacement_polarity"]
                and event_id in item["support_event_ids"]
            ]
            exact = [
                item for item in candidates if original_contexts[id(item)] == correction["context"]
            ]
            targets = exact if exact else candidates
            if len(targets) != 1:
                raise ValueError("Correction must select exactly one supported replacement")
            target = targets[0]
            assignment = (correction["previous_preference_id"], correction["context"])
            if id(target) in assignments and assignments[id(target)] != assignment:
                raise ValueError("Conflicting correction declarations select the same replacement")
            assignments[id(target)] = assignment
            selected_corrections.append((assignment[0], target, event_id))
    # Explicit producer metadata owns canonical identity; model prose describes
    # the supported assertion. Resolve all selections before changing any context.
    for item in preferences:
        if id(item) in assignments:
            item["context"] = assignments[id(item)][1]
        item.update(scope="global", scope_id=None)
        item["preference_id"] = artifact_identity("Preference", owner, item)
    for item in result["skills"]:
        item["skill_id"] = artifact_identity("Skill", owner, item)
    corrections = [
        dict(
            previous_preference_id=previous,
            replacement_id=item["preference_id"],
            source_event_id=event_id,
        )
        for previous, item, event_id in selected_corrections
    ]
    receipt = dict(
        version="user-extraction-v1",
        owner=owner,
        session_id=trigger.session_id,
        trigger_event_id=str(trigger.event_id),
        source_position=trigger.global_position,
        input_event_ids=ids,
        input_hash=_digest([by_id[event_id] for event_id in ids]),
        effective_at=trigger.occurred_at.isoformat(),
        result=result,
        corrections=corrections,
        status="prepared",
    )
    receipt["result_hash"] = _digest([result, corrections, receipt["effective_at"]])
    return receipt


def event_ref(event: Event) -> NodeRef:
    return NodeRef("Event", str(event.event_id), "event_id")


def receipt_from_event(event: Event, props: dict[str, Any] | None) -> dict[str, Any] | None:
    if props is None:
        raise UnavailableError("User extraction awaits trigger projection")
    if (
        props.get("agent_id") != event.agent_id
        or props.get("session_id") != event.session_id
        or props.get("event_type") != event.event_type
    ):
        raise UserExtractionConflictError("User trigger projection identity differs")
    if props.get("user_extraction_status") == "redacted":
        raise UserExtractionConflictError("User extraction trigger was redacted")
    receipt = props.get(RECEIPT_FIELD)
    if isinstance(receipt, str):
        receipt = json.loads(receipt)
    if receipt is None:
        return None
    if (
        not isinstance(receipt, dict)
        or receipt.get("owner") != "user:" + event.agent_id
        or receipt.get("session_id") != event.session_id
        or receipt.get("trigger_event_id") != str(event.event_id)
        or receipt.get("source_position") != event.global_position
        or receipt.get("version") != "user-extraction-v1"
        or receipt.get("status") not in ("prepared", "applied")
    ):
        raise UserExtractionConflictError("Stored User extraction receipt identity differs")
    if receipt.get("result_hash") != _digest(
        [receipt["result"], receipt["corrections"], receipt["effective_at"]]
    ):
        raise UserExtractionConflictError("Stored User extraction result hash differs")
    return deepcopy(receipt)


def select_prepared_receipt(
    event: Event, props: dict[str, Any] | None, candidate: dict[str, Any]
) -> dict[str, Any]:
    existing = receipt_from_event(event, props)
    # Validate the proposed receipt through the same identity/hash checks.
    validated = receipt_from_event(event, {**(props or {}), RECEIPT_FIELD: candidate})
    if existing is not None:
        if (
            existing["input_hash"] != candidate["input_hash"]
            or existing["input_event_ids"] != candidate["input_event_ids"]
        ):
            raise UserExtractionConflictError("Trigger input window changed after preparation")
        return existing
    assert validated is not None
    return validated


def extraction_refs(receipt: dict[str, Any]) -> list[NodeRef]:
    """All existing or new endpoints to lock/read before one atomic apply."""
    owner = receipt["owner"]
    result = receipt["result"]
    refs = [
        NodeRef("Entity", owner, "entity_id"),
    ]
    if result["persona"]:
        refs.append(NodeRef("UserProfile", "profile:" + owner, "profile_id"))
    refs.extend(NodeRef("Event", event_id, "event_id") for event_id in receipt["input_event_ids"])
    refs.extend(
        NodeRef("Preference", item["preference_id"], "preference_id")
        for item in result["preferences"]
    )
    refs.extend(NodeRef("Skill", item["skill_id"], "skill_id") for item in result["skills"])
    refs.extend(
        NodeRef("Entity", "entity:" + item["entity_name"], "entity_id")
        for item in result["interests"]
    )
    refs.extend(
        NodeRef("Entity", "entity:" + item["about_entity"], "entity_id")
        for item in result["preferences"]
        if item.get("about_entity")
    )
    refs.extend(
        NodeRef("Preference", item["previous_preference_id"], "preference_id")
        for item in receipt["corrections"]
    )
    return sorted(set(refs), key=lambda ref: (ref.label, ref.key))


@dataclass(frozen=True)
class UserExtractionMutation:
    nodes: tuple[NodeWrite, ...] = ()
    edges: tuple[EdgeWrite, ...] = ()
    outcome: str = "applied"


def plan_user_extraction(
    trigger: Event, stored: Mapping[NodeRef, dict[str, Any]]
) -> UserExtractionMutation:
    """Plan only the persisted winner; count distinct quoted Events, not calls."""
    trigger_ref = event_ref(trigger)
    receipt = receipt_from_event(trigger, stored.get(trigger_ref))
    if receipt is None:
        raise UserExtractionConflictError("User result was not prepared")
    if receipt["status"] == "applied":
        return UserExtractionMutation(outcome="duplicate")
    source_props = {}
    for event_id in receipt["input_event_ids"]:
        source = stored.get(NodeRef("Event", event_id, "event_id"))
        if source is None:
            raise UnavailableError("User extraction awaits source projection")
        if (
            source.get("agent_id") != trigger.agent_id
            or source.get("session_id") != trigger.session_id
        ):
            raise UserExtractionConflictError("User evidence projection crosses owner/session")
        source_props[event_id] = source
    owner = receipt["owner"]
    now = receipt["effective_at"]
    result = receipt["result"]
    user = NodeRef("Entity", owner, "entity_id")
    planned: dict[NodeRef, dict[str, Any]] = {}
    edges = []

    def existing(ref: NodeRef) -> dict[str, Any]:
        return planned.get(ref, stored.get(ref, {}))

    def latest_seen(ref: NodeRef) -> str:
        previous = existing(ref).get("last_seen")
        if previous and datetime.fromisoformat(previous) > datetime.fromisoformat(now):
            return str(previous)
        return str(now)

    def write(ref: NodeRef, values: dict[str, Any]) -> None:
        planned[ref] = {**existing(ref), ref.key_property: ref.key, **values}

    def supports(item: dict[str, Any]) -> list[str]:
        ids = item["support_event_ids"]
        if not isinstance(ids, list) or not ids or not set(ids) <= set(source_props):
            raise UserExtractionConflictError("Frozen output source membership differs")
        return sorted(set(ids))

    def derive(ref: NodeRef, item: dict[str, Any]) -> None:
        for event_id in supports(item):
            edges.append(
                EdgeWrite(
                    "DERIVED_FROM",
                    ref,
                    NodeRef("Event", event_id, "event_id"),
                    dict(
                        method="llm_extraction",
                        session_id=trigger.session_id,
                        extracted_at=now,
                        evidence_quote=item["source_quote"],
                        extraction_event_id=str(trigger.event_id),
                    ),
                )
            )

    persona = result["persona"]
    write(
        user,
        dict(
            entity_type="user",
            name=existing(user).get("name") or (persona or {}).get("name") or owner,
            first_seen=existing(user).get("first_seen", now),
            last_seen=latest_seen(user),
            mention_count=existing(user).get("mention_count", 1),
        ),
    )
    if persona:
        profile = NodeRef("UserProfile", "profile:" + owner, "profile_id")
        old = existing(profile)
        selected = supports(persona)
        known = set(old.get("support_event_ids", []))
        values = dict(
            user_id=owner,
            support_event_ids=sorted(known | set(selected)),
            created_at=old.get("created_at", now),
        )
        if set(selected) - known:
            name = persona.get("name") or trigger.agent_id
            if persona.get("role") and persona.get("name"):
                name += f" ({persona['role']})"
            values.update(
                display_name=name,
                communication_style=persona.get("communication_style"),
                technical_level=persona.get("tech_level"),
                updated_at=now,
            )
        write(profile, values)
        edges.append(EdgeWrite("HAS_PROFILE", user, profile))
        derive(profile, persona)
    for item in result["preferences"]:
        preference = NodeRef("Preference", item["preference_id"], "preference_id")
        old = existing(preference)
        if old and old.get("user_id") != owner:
            raise UserExtractionConflictError("Preference owner differs")
        selected = supports(item)
        known = set(old.get("support_event_ids", []))
        combined = known | set(selected)
        if len(combined) > 1024:
            raise ValueError("Preference support capacity exceeded")
        values = dict(
            user_id=owner, support_event_ids=sorted(combined), observation_count=len(combined)
        )
        if not old or set(selected) - known:
            times = [datetime.fromisoformat(source_props[key]["occurred_at"]) for key in selected]
            values.update(
                {
                    field: item.get(field)
                    for field in (
                        "category",
                        "key",
                        "polarity",
                        "strength",
                        "confidence",
                        "source",
                        "context",
                        "scope",
                        "scope_id",
                    )
                }
            )
            values.update(
                first_observed_at=min(
                    [
                        *times,
                        *(
                            [datetime.fromisoformat(old["first_observed_at"])]
                            if old.get("first_observed_at")
                            else []
                        ),
                    ]
                ).isoformat(),
                last_confirmed_at=max(
                    [
                        *times,
                        *(
                            [datetime.fromisoformat(old["last_confirmed_at"])]
                            if old.get("last_confirmed_at")
                            else []
                        ),
                    ]
                ).isoformat(),
            )
        write(preference, values)
        edges.append(EdgeWrite("HAS_PREFERENCE", user, preference))
        derive(preference, item)
        if item.get("about_entity"):
            about = NodeRef("Entity", "entity:" + item["about_entity"], "entity_id")
            write(
                about,
                dict(
                    name=item["about_entity"],
                    entity_type=existing(about).get("entity_type", "concept"),
                    first_seen=existing(about).get("first_seen", now),
                    last_seen=latest_seen(about),
                ),
            )
            edges.append(EdgeWrite("ABOUT", preference, about))
    for item in result["skills"]:
        skill = NodeRef("Skill", item["skill_id"], "skill_id")
        write(
            skill,
            dict(
                user_id=owner,
                name=item["name"],
                category=item["category"],
                created_at=existing(skill).get("created_at", now),
                support_event_ids=sorted(
                    set(existing(skill).get("support_event_ids", [])) | set(supports(item))
                ),
            ),
        )
        edges.append(
            EdgeWrite(
                "HAS_SKILL",
                user,
                skill,
                {field: item[field] for field in ("proficiency", "confidence", "source")},
            )
        )
        derive(skill, item)
    for item in result["interests"]:
        interest = NodeRef("Entity", "entity:" + item["entity_name"], "entity_id")
        write(
            interest,
            dict(
                name=item["entity_name"],
                entity_type=existing(interest).get("entity_type", item["entity_type"]),
                first_seen=existing(interest).get("first_seen", now),
                last_seen=latest_seen(interest),
            ),
        )
        edges.append(
            EdgeWrite(
                "INTERESTED_IN",
                user,
                interest,
                {field: item[field] for field in ("weight", "source")},
            )
        )
        derive(interest, item)
    for correction in receipt["corrections"]:
        previous = NodeRef("Preference", correction["previous_preference_id"], "preference_id")
        replacement = NodeRef("Preference", correction["replacement_id"], "preference_id")
        # A predecessor must predate this receipt; planned state catches two successors.
        old = existing(previous) if previous in stored else {}
        new = existing(replacement)
        if not old or not new:
            raise UserExtractionConflictError("User correction predecessor/replacement is missing")
        if (
            previous == replacement
            or old.get("user_id") != owner
            or new.get("user_id") != owner
            or any(
                old.get(field) != new.get(field)
                for field in ("category", "key", "scope", "scope_id", "context")
            )
        ):
            raise UserExtractionConflictError("Correction crosses preference owner or context")
        if old.get("superseded_by") not in (None, replacement.key) or new.get("superseded_by"):
            raise UserExtractionConflictError("Correction conflicts with current successor")
        correction_source = NodeRef("Event", correction["source_event_id"], "event_id")
        write(previous, dict(superseded_by=replacement.key))
        edges.append(
            EdgeWrite(
                "SUPERSEDES",
                replacement,
                previous,
                dict(method="declared", source_event_id=correction_source.key),
            )
        )
        edges.append(
            EdgeWrite(
                "DERIVED_FROM",
                previous,
                correction_source,
                dict(method="declared_correction", session_id=trigger.session_id, extracted_at=now),
            )
        )
    completed = deepcopy(receipt)
    completed["status"] = "applied"
    write(
        trigger_ref,
        {RECEIPT_FIELD: completed, OWNER_FIELD: owner, "user_extraction_status": "applied"},
    )
    return UserExtractionMutation(
        tuple(NodeWrite(ref, props) for ref, props in planned.items()), tuple(edges)
    )
