"""Validated Memory actions and backend-neutral atomic mutation plans.

State and its distinct evidence are one storage transaction, never separate
read-count-write calls. Structured producer assertions are not claims of truth.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from context_graph.domain.models import BeliefNode, GoalNode
from context_graph.ports.pack_graph import EdgeWrite, NodeRef, NodeWrite

if TYPE_CHECKING:
    from collections.abc import Mapping

    from context_graph.domain.models import Event


MEMORY_EVENT_HANDLERS = {
    **{
        f"memory.belief.{action}": "memory.belief.v1"
        for action in ("stated", "inferred", "confirmed", "corrected")
    },
    **{
        f"memory.goal.{action}": "memory.goal.v1"
        for action in ("created", "completed", "abandoned", "superseded")
    },
}


class MemoryActionConflictError(ValueError):
    """An action conflicts with the subject's owner, identity or revision."""


class MemoryReferenceMissingError(ValueError):
    """A required projected reference is not available; no partial state is written."""


def memory_identity(family: str, agent_id: str, scope: str, session_id: str, key: str) -> str:
    digest = hashlib.sha256(
        json.dumps(
            [family, agent_id, scope, session_id if scope == "session" else "", key],
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return family.lower() + "-" + digest


def _memory_ref(family: str, event: Event, scope: str, key: Any) -> NodeRef:
    if not isinstance(key, str) or not key.strip() or len(key) > 128:
        raise ValueError("Memory key must be a nonempty string of at most 128 characters")
    return NodeRef(
        family,
        memory_identity(family, event.agent_id, scope, event.session_id, key),
        family.lower() + "_id",
    )


@dataclass(frozen=True)
class MemoryAction:
    event: Event
    subject: NodeRef
    scope: str
    key: str
    properties: dict[str, Any]
    expected_revision: int | None = None
    replacement: NodeRef | None = None

    @classmethod
    def from_event(
        cls, event: Event, payload: dict[str, Any], *, trusted: bool = False
    ) -> MemoryAction:
        if event.event_type not in MEMORY_EVENT_HANDLERS:
            raise ValueError("Unsupported Memory action")
        key = payload.get("key")
        scope = payload.get("scope", "session")
        if not isinstance(key, str) or not key.strip() or len(key) > 128:
            raise ValueError("Memory key must be a nonempty string of at most 128 characters")
        if scope not in ("session", "agent"):
            raise ValueError("Memory scope must be session or agent")
        family = "Belief" if event.event_type.startswith("memory.belief.") else "Goal"
        subject = _memory_ref(family, event, scope, key)
        if event.event_type in {
            "memory.belief.confirmed",
            "memory.belief.corrected",
            "memory.goal.completed",
            "memory.goal.abandoned",
            "memory.goal.superseded",
        }:
            revision = payload.get("expected_revision")
            if type(revision) is not int or revision < 0:
                raise ValueError("Memory update requires a nonnegative expected_revision")
            if event.event_type in {"memory.belief.corrected", "memory.goal.superseded"}:
                replacement = _memory_ref(family, event, scope, payload.get("replacement_key"))
                contradicts = payload.get("contradicts", False)
                if replacement == subject or type(contradicts) is not bool:
                    raise ValueError(
                        "Correction needs another belief and an explicit boolean contradiction flag"
                    )
                return cls(
                    event, subject, scope, key, {"contradicts": contradicts}, revision, replacement
                )
            return cls(event, subject, scope, key, {}, revision)
        model: BeliefNode | GoalNode
        if family == "Belief":
            model = BeliefNode(
                belief_id=subject.key,
                belief_text=payload["belief_text"],
                confidence=payload["confidence"],
                category=payload["category"],
                created_at=event.occurred_at,
                last_confirmed_at=event.occurred_at,
                confirmation_count=0 if event.event_type.endswith(".inferred") else 1,
            )
            inferred = event.event_type.endswith(".inferred")
            if inferred and model.confidence > 0.8:
                raise ValueError("Inferred confidence cannot exceed 0.8")
            extra = {
                "origin": "inferred" if inferred else "stated",
                "supporting_event_ids": [] if inferred else [str(event.event_id)],
            }
        else:
            model = GoalNode(
                goal_id=subject.key,
                description=payload["description"],
                status="active",
                created_at=event.occurred_at,
                last_active_at=event.occurred_at,
                priority=payload.get("priority"),
            )
            extra = {"status_changed_at": event.occurred_at.isoformat()}
        properties = {
            **model.model_dump(mode="json"),
            "agent_id": event.agent_id,
            "session_id": event.session_id,
            "scope": scope,
            "local_key": key,
            "state_revision": 0,
            "evidence_event_ids": [str(event.event_id)],
            "complete": True,
            "source_trust": "trusted" if trusted else "untrusted",
            **extra,
        }
        if extra.get("origin") == "inferred":
            properties.pop("last_confirmed_at", None)
        return cls(event, subject, scope, key, properties)

    def read_refs(self) -> list[NodeRef]:
        return [
            self.subject,
            *([self.replacement] if self.replacement else []),
            NodeRef("Event", str(self.event.event_id), "event_id"),
        ]


@dataclass(frozen=True)
class MemoryMutation:
    nodes: tuple[NodeWrite, ...] = ()
    edges: tuple[EdgeWrite, ...] = ()
    outcome: str = "applied"


def _plan_memory_action(
    action: MemoryAction, stored: Mapping[NodeRef, dict[str, Any]]
) -> MemoryMutation:
    source = action.read_refs()[-1]
    event = stored.get(source)
    if event is None:
        raise MemoryReferenceMissingError("Memory source Event has not been projected")
    if (
        event.get("event_type") != action.event.event_type
        or event.get("agent_id") != action.event.agent_id
        or event.get("session_id") != action.event.session_id
    ):
        raise MemoryActionConflictError(
            "Memory source ownership differs from the accepted envelope"
        )
    current = stored.get(action.subject)
    if current is not None:
        if (
            current.get("agent_id") != action.event.agent_id
            or current.get("scope") != action.scope
            or current.get("local_key") != action.key
            or (action.scope == "session" and current.get("session_id") != action.event.session_id)
        ):
            raise MemoryActionConflictError("Memory subject ownership differs")
        if str(action.event.event_id) in current.get("evidence_event_ids", []):
            # Receipts prevent recounting; replay may restore missing evidence edges.
            kind = action.event.event_type
            role = (
                "lifecycle"
                if action.subject.label == "Goal"
                else (
                    "inference"
                    if kind.endswith(".inferred")
                    else "correction"
                    if kind.endswith(".corrected")
                    else "support"
                )
            )
            edges = [
                EdgeWrite(
                    "DERIVED_FROM", action.subject, source, {"evidence_role": role, "action": kind}
                )
            ]
            if action.replacement is not None:
                if action.replacement not in stored:
                    raise MemoryReferenceMissingError("Replacement for replay is absent")
                history = {"method": "declared", "source_event_id": str(action.event.event_id)}
                edges.append(EdgeWrite("SUPERSEDES", action.replacement, action.subject, history))
                if action.subject.label == "Belief" and action.properties.get("contradicts"):
                    edges.append(
                        EdgeWrite("CONTRADICTS", action.replacement, action.subject, history)
                    )
            return MemoryMutation(edges=tuple(edges), outcome="duplicate")
        if action.event.event_type == "memory.belief.confirmed":
            assert action.expected_revision is not None
            if current.get("state_revision") != action.expected_revision:
                raise MemoryActionConflictError(
                    "Memory expected revision conflicts with current state"
                )
            if current.get("superseded_by"):
                raise MemoryActionConflictError("Superseded Belief cannot receive confirmations")
            evidence = sorted({*current["evidence_event_ids"], str(action.event.event_id)})
            supports = sorted({*current["supporting_event_ids"], str(action.event.event_id)})
            if len(evidence) > 1024:
                raise ValueError("Memory evidence capacity exceeded")
            properties = {
                **current,
                "state_revision": action.expected_revision + 1,
                "evidence_event_ids": evidence,
                "supporting_event_ids": supports,
                "confirmation_count": len(supports),
                "last_confirmed_at": max(
                    datetime.fromisoformat(current["last_confirmed_at"])
                    if current.get("last_confirmed_at")
                    else action.event.occurred_at,
                    action.event.occurred_at,
                ).isoformat(),
            }
            return MemoryMutation(
                (NodeWrite(action.subject, properties),),
                (
                    EdgeWrite(
                        "DERIVED_FROM",
                        action.subject,
                        source,
                        {"evidence_role": "support", "action": action.event.event_type},
                    ),
                ),
            )
        if action.event.event_type in {"memory.goal.completed", "memory.goal.abandoned"}:
            assert action.expected_revision is not None
            if current.get("state_revision") != action.expected_revision:
                raise MemoryActionConflictError(
                    "Memory expected revision conflicts with current state"
                )
            if current.get("status") != "active":
                raise MemoryActionConflictError("Terminal Goal cannot be changed")
            evidence = sorted({*current["evidence_event_ids"], str(action.event.event_id)})
            if len(evidence) > 1024:
                raise ValueError("Memory evidence capacity exceeded")
            properties = {
                **current,
                "state_revision": action.expected_revision + 1,
                "status": action.event.event_type.rsplit(".", 1)[1],
                "status_changed_at": action.event.occurred_at.isoformat(),
                "evidence_event_ids": evidence,
                "evidence_count": len(evidence),
                "last_active_at": max(
                    datetime.fromisoformat(current["last_active_at"]), action.event.occurred_at
                ).isoformat(),
            }
            return MemoryMutation(
                (NodeWrite(action.subject, properties),),
                (
                    EdgeWrite(
                        "DERIVED_FROM",
                        action.subject,
                        source,
                        {"evidence_role": "lifecycle", "action": action.event.event_type},
                    ),
                ),
            )
        if action.event.event_type in {"memory.belief.corrected", "memory.goal.superseded"}:
            assert action.expected_revision is not None and action.replacement is not None
            if current.get("state_revision") != action.expected_revision:
                raise MemoryActionConflictError(
                    "Memory expected revision conflicts with current state"
                )
            if current.get("superseded_by"):
                raise MemoryActionConflictError("Superseded Belief cannot be corrected again")
            if action.subject.label == "Goal" and current.get("status") != "active":
                raise MemoryActionConflictError("Terminal Goal cannot be superseded")
            replacement = stored.get(action.replacement)
            if replacement is None:
                raise MemoryReferenceMissingError("Replacement Belief has not been projected")
            if (
                replacement.get("agent_id") != action.event.agent_id
                or replacement.get("scope") != action.scope
                or (
                    action.scope == "session"
                    and replacement.get("session_id") != action.event.session_id
                )
                or replacement.get("superseded_by")
                or (action.subject.label == "Goal" and replacement.get("status") != "active")
                or not replacement.get("complete")
            ):
                raise MemoryActionConflictError(
                    "Replacement Belief must be current and in the same owner/scope"
                )
            evidence = sorted({*current["evidence_event_ids"], str(action.event.event_id)})
            if len(evidence) > 1024:
                raise ValueError("Memory evidence capacity exceeded")
            properties = {
                **current,
                "state_revision": action.expected_revision + 1,
                "evidence_event_ids": evidence,
                "superseded_by": action.replacement.key,
                **(
                    {"contradiction_declared": action.properties["contradicts"]}
                    if action.subject.label == "Belief"
                    else {}
                ),
            }
            if action.subject.label == "Goal":
                properties.update(
                    status="superseded",
                    status_changed_at=action.event.occurred_at.isoformat(),
                    evidence_count=len(evidence),
                    last_active_at=max(
                        datetime.fromisoformat(current["last_active_at"]), action.event.occurred_at
                    ).isoformat(),
                )
            history = {"method": "declared", "source_event_id": str(action.event.event_id)}
            edges = [
                EdgeWrite(
                    "DERIVED_FROM",
                    action.subject,
                    source,
                    {
                        "evidence_role": "correction"
                        if action.subject.label == "Belief"
                        else "lifecycle",
                        "action": action.event.event_type,
                    },
                ),
                EdgeWrite("SUPERSEDES", action.replacement, action.subject, history),
            ]
            if action.subject.label == "Belief" and action.properties["contradicts"]:
                edges.append(EdgeWrite("CONTRADICTS", action.replacement, action.subject, history))
            return MemoryMutation((NodeWrite(action.subject, properties),), tuple(edges))
        raise MemoryActionConflictError(
            "Memory identity already exists; creation cannot overwrite it"
        )
    if action.expected_revision is not None:
        raise MemoryReferenceMissingError("Memory subject to update has not been projected")
    return MemoryMutation(
        (NodeWrite(action.subject, action.properties),),
        (
            EdgeWrite(
                "DERIVED_FROM",
                action.subject,
                source,
                {
                    "evidence_role": (
                        "inference" if action.properties.get("origin") == "inferred" else "support"
                    )
                    if action.subject.label == "Belief"
                    else "lifecycle",
                    "action": action.event.event_type,
                },
            ),
        ),
    )


def plan_memory_action(
    action: MemoryAction, stored: Mapping[NodeRef, dict[str, Any]]
) -> MemoryMutation:
    """Bind accepted action identity to its Event in the same state transaction."""
    plan = _plan_memory_action(action, stored)
    source = action.read_refs()[-1]
    receipt = {
        **stored[source],
        "memory_subject_id": action.subject.key,
        "memory_subject_label": action.subject.label,
        "memory_expected_revision": action.expected_revision,
    }
    return MemoryMutation((*plan.nodes, NodeWrite(source, receipt)), plan.edges, plan.outcome)
