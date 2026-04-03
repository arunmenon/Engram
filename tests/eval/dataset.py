"""Evaluation dataset for autoresearch scoring optimization.

Three PayPal domain scenarios with deterministic graphs and 24 labeled
queries across all 8 intent types. Ground truth is derived from graph
structure (Approach A) with invariant violations (Approach D).

This module has ZERO framework dependencies — pure Python + stdlib.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any

# Base timestamp for all scenarios (UTC)
_BASE_TIME = datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc)


class IntentType(str, Enum):
    """Intent types for evaluation queries."""

    WHY = "why"
    WHEN = "when"
    WHAT = "what"
    RELATED = "related"
    GENERAL = "general"
    WHO_IS = "who_is"
    HOW_DOES = "how_does"
    PERSONALIZE = "personalize"


class DatasetMode(str, Enum):
    """Dataset loading mode."""

    ORIGINAL = "original"
    EXTENDED = "extended"
    GENERATED_ONLY = "generated-only"


_ACTIVE_MODE: DatasetMode = DatasetMode.ORIGINAL


def set_dataset_mode(mode: DatasetMode) -> None:
    """Set the active dataset mode. Call before load_eval_dataset()."""
    global _ACTIVE_MODE  # noqa: PLW0603
    _ACTIVE_MODE = mode


@dataclass(frozen=True)
class EvalNode:
    """A node in the evaluation graph."""

    node_id: str
    node_type: str  # "Event", "Entity", "UserProfile", "Preference", "Skill"
    attributes: dict[str, Any]  # All properties needed for scoring


@dataclass(frozen=True)
class EvalEdge:
    """An edge in the evaluation graph."""

    source: str
    target: str
    edge_type: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RelevanceJudgment:
    """A single node's relevance grade for a query."""

    node_id: str
    grade: int  # 3=highly relevant, 2=relevant, 1=marginally relevant


@dataclass(frozen=True)
class EvalQuery:
    """A single evaluation query with ground truth."""

    query_id: str
    query: str
    intent: str  # IntentType value
    scenario: str  # session ID
    expected_top_nodes: list[RelevanceJudgment]
    must_not_appear: list[str]
    rationale: str


@dataclass
class EvalScenario:
    """A complete scenario with graph + queries."""

    scenario_id: str
    description: str
    nodes: list[EvalNode]
    edges: list[EvalEdge]
    queries: list[EvalQuery]


def _deterministic_embedding(seed: str, scenario_offset: int = 0, dim: int = 8) -> list[float]:
    """Generate deterministic 8D embeddings using hash-based seeding.

    Args:
        seed: String to seed the embedding (node_id, scenario, etc.)
        scenario_offset: Integer offset for scenario separation
        dim: Embedding dimensionality (default 8)

    Returns:
        List of floats in [-1, 1] that is deterministic and reproducible.
    """
    # Create a deterministic hash
    hash_input = f"{seed}:offset={scenario_offset}"
    hash_bytes = hashlib.sha256(hash_input.encode()).digest()

    # Convert bytes to floats in [-1, 1] range
    embedding = []
    for i in range(dim):
        byte_val = hash_bytes[i % len(hash_bytes)]
        # Map 0-255 to [-1, 1]
        normalized = (byte_val / 127.5) - 1.0
        embedding.append(normalized)

    return embedding


def _event_node(
    event_id: str,
    event_type: str,
    description: str,
    occurred_at: datetime,
    importance_hint: int | None = None,
    status: str = "success",
    scenario_offset: int = 0,
) -> EvalNode:
    """Create an Event node with full attributes."""
    return EvalNode(
        node_id=event_id,
        node_type="Event",
        attributes={
            "event_type": event_type,
            "description": description,
            "occurred_at": occurred_at.isoformat(),
            "access_count": 0,
            "importance_score": importance_hint,
            "embedding": _deterministic_embedding(event_id, scenario_offset),
            "in_degree": 0,  # Will be updated after building edges
            "user_affinity": 0.0,
            "status": status,
        },
    )


def _entity_node(
    entity_id: str,
    entity_type: str,
    name: str,
    mention_count: int = 1,
    scenario_offset: int = 0,
) -> EvalNode:
    """Create an Entity node with full attributes."""
    return EvalNode(
        node_id=entity_id,
        node_type="Entity",
        attributes={
            "entity_type": entity_type,
            "name": name,
            "last_seen": _BASE_TIME.isoformat(),
            "mention_count": mention_count,
            "embedding": _deterministic_embedding(entity_id, scenario_offset),
        },
    )


def _user_profile_node(profile_id: str, name: str) -> EvalNode:
    """Create a UserProfile node.

    UserProfile nodes are scored like entities (via score_entity_node)
    so they need last_seen and mention_count for scoring compatibility.
    """
    return EvalNode(
        node_id=profile_id,
        node_type="UserProfile",
        attributes={
            "name": name,
            "embedding": _deterministic_embedding(profile_id),
            "last_seen": (_BASE_TIME + timedelta(hours=2, seconds=11)).isoformat(),
            "mention_count": 5,
        },
    )


def _preference_node(
    pref_id: str,
    description: str,
    category: str = "workflow",
    polarity: str = "positive",
) -> EvalNode:
    """Create a Preference node.

    Preference nodes need last_seen/mention_count for scoring compatibility
    since they are scored like entities in retrieval.
    """
    return EvalNode(
        node_id=pref_id,
        node_type="Preference",
        attributes={
            "description": description,
            "category": category,
            "polarity": polarity,
            "embedding": _deterministic_embedding(pref_id),
            "last_seen": (_BASE_TIME + timedelta(hours=2, seconds=11)).isoformat(),
            "mention_count": 2,
        },
    )


def _skill_node(skill_id: str, name: str, proficiency: float = 0.85) -> EvalNode:
    """Create a Skill node.

    Skill nodes need last_seen/mention_count for scoring compatibility
    since they are scored like entities in retrieval.
    """
    return EvalNode(
        node_id=skill_id,
        node_type="Skill",
        attributes={
            "name": name,
            "proficiency": proficiency,
            "embedding": _deterministic_embedding(skill_id),
            "last_seen": (_BASE_TIME + timedelta(hours=2, seconds=11)).isoformat(),
            "mention_count": 3,
        },
    )


def _build_payment_scenario() -> EvalScenario:
    """Build payment decline & recovery scenario (pay-decline-001).

    Timeline: 2026-03-15 10:00:00 UTC + 0 seconds per event
    """
    scenario_id = "pay-decline-001"
    base_time = _BASE_TIME

    # Events
    events = [
        _event_node(
            "evt-pay-010",
            "system.session_start",
            "Payment session initiated for order #9827",
            base_time + timedelta(seconds=0),
            scenario_offset=0,
        ),
        _event_node(
            "evt-pay-011",
            "tool.execute",
            "Velocity check on card ending 4242",
            base_time + timedelta(seconds=1),
            importance_hint=7,
            scenario_offset=0,
        ),
        _event_node(
            "evt-pay-012",
            "agent.invoke",
            "Submit authorization request to Visa network",
            base_time + timedelta(seconds=2),
            importance_hint=8,
            scenario_offset=0,
        ),
        _event_node(
            "evt-pay-013",
            "observation.output",
            "Authorization declined: insufficient_funds",
            base_time + timedelta(seconds=3),
            importance_hint=9,
            status="failed",
            scenario_offset=0,
        ),
        _event_node(
            "evt-pay-014",
            "agent.invoke",
            "Initiate 3DS step-up authentication",
            base_time + timedelta(seconds=4),
            importance_hint=7,
            scenario_offset=0,
        ),
        _event_node(
            "evt-pay-015",
            "tool.execute",
            "3DS challenge sent to cardholder",
            base_time + timedelta(seconds=5),
            importance_hint=6,
            scenario_offset=0,
        ),
        _event_node(
            "evt-pay-016",
            "observation.input",
            "Cardholder completed 3DS challenge",
            base_time + timedelta(seconds=6),
            importance_hint=6,
            scenario_offset=0,
        ),
        _event_node(
            "evt-pay-017",
            "agent.invoke",
            "Retry authorization with 3DS proof",
            base_time + timedelta(seconds=7),
            importance_hint=8,
            scenario_offset=0,
        ),
        _event_node(
            "evt-pay-018",
            "observation.output",
            "Authorization approved, auth_code=A8F29D",
            base_time + timedelta(seconds=8),
            importance_hint=9,
            scenario_offset=0,
        ),
        _event_node(
            "evt-pay-019",
            "tool.execute",
            "Payment captured: $450.00",
            base_time + timedelta(seconds=9),
            importance_hint=10,
            scenario_offset=0,
        ),
    ]

    # Entities
    entities = [
        _entity_node("ent-pay-card", "resource", "card-ending-4242", 5, scenario_offset=0),
        _entity_node("ent-pay-visa", "service", "visa-network", 3, scenario_offset=0),
        _entity_node("ent-pay-risk", "service", "risk-engine", 2, scenario_offset=0),
        _entity_node("ent-pay-3ds", "service", "3ds-service", 3, scenario_offset=0),
        _entity_node("ent-pay-merchant", "agent", "merchant-checkout", 2, scenario_offset=0),
        _entity_node("ent-pay-order", "resource", "order-9827", 4, scenario_offset=0),
    ]

    nodes = events + entities

    # Edges: FOLLOWS chain
    edges = [
        EvalEdge("evt-pay-010", "evt-pay-011", "FOLLOWS"),
        EvalEdge("evt-pay-011", "evt-pay-012", "FOLLOWS"),
        EvalEdge("evt-pay-012", "evt-pay-013", "FOLLOWS"),
        EvalEdge("evt-pay-013", "evt-pay-014", "FOLLOWS"),
        EvalEdge("evt-pay-014", "evt-pay-015", "FOLLOWS"),
        EvalEdge("evt-pay-015", "evt-pay-016", "FOLLOWS"),
        EvalEdge("evt-pay-016", "evt-pay-017", "FOLLOWS"),
        EvalEdge("evt-pay-017", "evt-pay-018", "FOLLOWS"),
        EvalEdge("evt-pay-018", "evt-pay-019", "FOLLOWS"),
        # CAUSED_BY edges: causal relationships
        EvalEdge("evt-pay-013", "evt-pay-012", "CAUSED_BY"),
        EvalEdge("evt-pay-014", "evt-pay-013", "CAUSED_BY"),
        EvalEdge("evt-pay-018", "evt-pay-017", "CAUSED_BY"),
        EvalEdge("evt-pay-017", "evt-pay-016", "CAUSED_BY"),
        EvalEdge("evt-pay-019", "evt-pay-018", "CAUSED_BY"),
        # REFERENCES edges: events to entities
        EvalEdge("evt-pay-011", "ent-pay-risk", "REFERENCES"),
        EvalEdge("evt-pay-011", "ent-pay-card", "REFERENCES"),
        EvalEdge("evt-pay-012", "ent-pay-visa", "REFERENCES"),
        EvalEdge("evt-pay-012", "ent-pay-card", "REFERENCES"),
        EvalEdge("evt-pay-013", "ent-pay-visa", "REFERENCES"),
        EvalEdge("evt-pay-013", "ent-pay-card", "REFERENCES"),
        EvalEdge("evt-pay-014", "ent-pay-3ds", "REFERENCES"),
        EvalEdge("evt-pay-015", "ent-pay-3ds", "REFERENCES"),
        EvalEdge("evt-pay-015", "ent-pay-card", "REFERENCES"),
        EvalEdge("evt-pay-017", "ent-pay-visa", "REFERENCES"),
        EvalEdge("evt-pay-017", "ent-pay-3ds", "REFERENCES"),
        EvalEdge("evt-pay-018", "ent-pay-visa", "REFERENCES"),
        EvalEdge("evt-pay-019", "ent-pay-order", "REFERENCES"),
        EvalEdge("evt-pay-019", "ent-pay-merchant", "REFERENCES"),
    ]

    # Payment scenario queries
    queries = [
        # WHY queries
        EvalQuery(
            query_id="pay-why-01",
            query="Why was the payment initially declined?",
            intent=IntentType.WHY,
            scenario=scenario_id,
            expected_top_nodes=[
                RelevanceJudgment("evt-pay-013", 3),
                RelevanceJudgment("evt-pay-012", 3),
                RelevanceJudgment("ent-pay-visa", 2),
                RelevanceJudgment("evt-pay-011", 2),
                RelevanceJudgment("ent-pay-card", 1),
            ],
            must_not_appear=["evt-mo-040", "evt-fr-020", "evt-pay-019"],
            rationale="CAUSED_BY chain from evt-pay-013 → evt-pay-012 is the causal answer. "
            "Visa network is the declining party. Risk engine ran before auth but did not cause the decline.",
        ),
        # WHEN queries
        EvalQuery(
            query_id="pay-when-01",
            query="When did the 3DS authentication happen in the payment flow?",
            intent=IntentType.WHEN,
            scenario=scenario_id,
            expected_top_nodes=[
                RelevanceJudgment("evt-pay-014", 3),
                RelevanceJudgment("evt-pay-015", 3),
                RelevanceJudgment("evt-pay-016", 3),
                RelevanceJudgment("evt-pay-013", 2),
                RelevanceJudgment("evt-pay-017", 2),
            ],
            must_not_appear=["evt-fr-020", "evt-mo-040"],
            rationale="Temporal query — FOLLOWS edges around the 3DS events. "
            "The surrounding events give temporal context.",
        ),
        # WHAT queries
        EvalQuery(
            query_id="pay-what-01",
            query="What is the risk engine's role in the payment flow?",
            intent=IntentType.WHAT,
            scenario=scenario_id,
            expected_top_nodes=[
                RelevanceJudgment("ent-pay-risk", 3),
                RelevanceJudgment("evt-pay-011", 3),
                RelevanceJudgment("ent-pay-card", 2),
                RelevanceJudgment("evt-pay-012", 1),
            ],
            must_not_appear=["evt-fr-020", "evt-mo-040"],
            rationale="Entity-centric query — the risk engine entity and events that REFERENCE it "
            "define its role.",
        ),
        # RELATED queries
        EvalQuery(
            query_id="pay-related-01",
            query="What entities are associated with card-ending-4242?",
            intent=IntentType.RELATED,
            scenario=scenario_id,
            expected_top_nodes=[
                RelevanceJudgment("ent-pay-card", 3),
                RelevanceJudgment("ent-pay-visa", 3),
                RelevanceJudgment("ent-pay-risk", 2),
                RelevanceJudgment("ent-pay-3ds", 2),
                RelevanceJudgment("evt-pay-011", 1),
            ],
            must_not_appear=["ent-fr-compliance", "ent-mo-merchant"],
            rationale="Entities co-referenced with the card entity via shared REFERENCES edges from events.",
        ),
        # GENERAL queries
        EvalQuery(
            query_id="pay-general-01",
            query="Summarize the payment session",
            intent=IntentType.GENERAL,
            scenario=scenario_id,
            expected_top_nodes=[
                RelevanceJudgment("evt-pay-019", 3),
                RelevanceJudgment("evt-pay-013", 3),
                RelevanceJudgment("evt-pay-018", 2),
                RelevanceJudgment("evt-pay-010", 2),
                RelevanceJudgment("ent-pay-order", 2),
            ],
            must_not_appear=["evt-fr-020", "evt-mo-040"],
            rationale="General summary — high-importance events (start, failure, resolution, outcome) "
            "plus key entity.",
        ),
        # WHO_IS queries
        EvalQuery(
            query_id="pay-who-01",
            query="Who is involved in the payment transaction?",
            intent=IntentType.WHO_IS,
            scenario=scenario_id,
            expected_top_nodes=[
                RelevanceJudgment("ent-pay-merchant", 3),
                RelevanceJudgment("ent-pay-visa", 3),
                RelevanceJudgment("ent-pay-risk", 2),
                RelevanceJudgment("ent-pay-3ds", 2),
                RelevanceJudgment("ent-pay-card", 2),
            ],
            must_not_appear=["ent-fr-acc", "ent-mo-merchant"],
            rationale="All entities referenced by events in the payment session — they are the 'who' "
            "(agents and services).",
        ),
        # HOW_DOES queries
        EvalQuery(
            query_id="pay-how-01",
            query="How does 3DS verification work in the payment flow?",
            intent=IntentType.HOW_DOES,
            scenario=scenario_id,
            expected_top_nodes=[
                RelevanceJudgment("evt-pay-014", 3),
                RelevanceJudgment("evt-pay-015", 3),
                RelevanceJudgment("evt-pay-016", 3),
                RelevanceJudgment("evt-pay-017", 2),
                RelevanceJudgment("ent-pay-3ds", 2),
            ],
            must_not_appear=["evt-fr-020", "evt-mo-040"],
            rationale="Process/workflow query — the sequential events involving 3DS describe 'how' it works.",
        ),
    ]

    return EvalScenario(
        scenario_id=scenario_id,
        description="Payment decline & recovery with 3DS verification",
        nodes=nodes,
        edges=edges,
        queries=queries,
    )


def _build_fraud_scenario() -> EvalScenario:
    """Build fraud investigation scenario (fraud-inv-002).

    Timeline: 2026-03-15 12:00:00 UTC (base + 2h)
    """
    scenario_id = "fraud-inv-002"
    base_time = _BASE_TIME + timedelta(hours=2)

    # Events
    events = [
        _event_node(
            "evt-fr-020",
            "system.session_start",
            "Fraud investigation: account ACC-7731",
            base_time + timedelta(seconds=0),
            scenario_offset=1,
        ),
        _event_node(
            "evt-fr-021",
            "tool.execute",
            "Fetch account profile ACC-7731",
            base_time + timedelta(seconds=1),
            importance_hint=5,
            scenario_offset=1,
        ),
        _event_node(
            "evt-fr-022",
            "tool.execute",
            "Pull login history last 48h",
            base_time + timedelta(seconds=2),
            importance_hint=7,
            scenario_offset=1,
        ),
        _event_node(
            "evt-fr-023",
            "observation.output",
            "5 failed logins from IP 198.51.100.42, new device fingerprint D-9X2F",
            base_time + timedelta(seconds=3),
            importance_hint=9,
            scenario_offset=1,
        ),
        _event_node(
            "evt-fr-024",
            "tool.execute",
            "Check device D-9X2F associations",
            base_time + timedelta(seconds=4),
            importance_hint=8,
            scenario_offset=1,
        ),
        _event_node(
            "evt-fr-025",
            "observation.output",
            "Device D-9X2F linked to 3 previously banned accounts",
            base_time + timedelta(seconds=5),
            importance_hint=10,
            scenario_offset=1,
        ),
        _event_node(
            "evt-fr-026",
            "llm.chat",
            "Analyze pattern: multiple failed logins, new device, rapid transactions",
            base_time + timedelta(seconds=6),
            importance_hint=7,
            scenario_offset=1,
        ),
        _event_node(
            "evt-fr-027",
            "observation.output",
            "LLM assessment: high-confidence account takeover (ATO) pattern",
            base_time + timedelta(seconds=7),
            importance_hint=9,
            scenario_offset=1,
        ),
        _event_node(
            "evt-fr-028",
            "tool.execute",
            "Pull transactions last 24h",
            base_time + timedelta(seconds=8),
            importance_hint=7,
            scenario_offset=1,
        ),
        _event_node(
            "evt-fr-029",
            "observation.output",
            "3 transactions totaling $8,200 to new payees in last 6h",
            base_time + timedelta(seconds=9),
            importance_hint=9,
            scenario_offset=1,
        ),
        _event_node(
            "evt-fr-030",
            "agent.invoke",
            "Flag account ACC-7731, initiate hold, notify compliance",
            base_time + timedelta(seconds=10),
            importance_hint=10,
            scenario_offset=1,
        ),
        _event_node(
            "evt-fr-031",
            "tool.execute",
            "Account ACC-7731 placed on hold",
            base_time + timedelta(seconds=11),
            importance_hint=10,
            scenario_offset=1,
        ),
    ]

    # Entities
    entities = [
        _entity_node("ent-fr-acc", "user", "account-ACC-7731", 6, scenario_offset=1),
        _entity_node("ent-fr-device", "resource", "device-D-9X2F", 4, scenario_offset=1),
        _entity_node("ent-fr-ip", "resource", "ip-198.51.100.42", 3, scenario_offset=1),
        _entity_node("ent-fr-txn-svc", "service", "transaction-service", 2, scenario_offset=1),
        _entity_node("ent-fr-id-svc", "service", "identity-service", 2, scenario_offset=1),
        _entity_node("ent-fr-device-graph", "service", "device-graph", 2, scenario_offset=1),
        _entity_node("ent-fr-compliance", "agent", "compliance-team", 1, scenario_offset=1),
        _entity_node("ent-fr-banned", "concept", "banned-account-cluster", 2, scenario_offset=1),
    ]

    # User profile nodes for personalization
    user_profile = [
        _user_profile_node("user-profile-analyst", "Fraud Analyst Maya"),
        _preference_node(
            "pref-analyst-01",
            "Prefers device-first investigation approach",
            category="workflow",
        ),
        _preference_node(
            "pref-analyst-02",
            "Wants transaction summaries grouped by payee",
            category="style",
        ),
        _skill_node("skill-analyst-01", "Account takeover investigation", 0.9),
        _skill_node("skill-analyst-02", "Device fingerprint analysis", 0.85),
    ]

    nodes = events + entities + user_profile

    # Edges: FOLLOWS chain
    edges = [
        EvalEdge("evt-fr-020", "evt-fr-021", "FOLLOWS"),
        EvalEdge("evt-fr-021", "evt-fr-022", "FOLLOWS"),
        EvalEdge("evt-fr-022", "evt-fr-023", "FOLLOWS"),
        EvalEdge("evt-fr-023", "evt-fr-024", "FOLLOWS"),
        EvalEdge("evt-fr-024", "evt-fr-025", "FOLLOWS"),
        EvalEdge("evt-fr-025", "evt-fr-026", "FOLLOWS"),
        EvalEdge("evt-fr-026", "evt-fr-027", "FOLLOWS"),
        EvalEdge("evt-fr-027", "evt-fr-028", "FOLLOWS"),
        EvalEdge("evt-fr-028", "evt-fr-029", "FOLLOWS"),
        EvalEdge("evt-fr-029", "evt-fr-030", "FOLLOWS"),
        EvalEdge("evt-fr-030", "evt-fr-031", "FOLLOWS"),
        # CAUSED_BY edges
        EvalEdge("evt-fr-024", "evt-fr-023", "CAUSED_BY"),
        EvalEdge("evt-fr-026", "evt-fr-025", "CAUSED_BY"),
        EvalEdge("evt-fr-027", "evt-fr-026", "CAUSED_BY"),
        EvalEdge("evt-fr-030", "evt-fr-027", "CAUSED_BY"),
        EvalEdge("evt-fr-030", "evt-fr-029", "CAUSED_BY"),
        EvalEdge("evt-fr-031", "evt-fr-030", "CAUSED_BY"),
        # REFERENCES edges
        EvalEdge("evt-fr-021", "ent-fr-acc", "REFERENCES"),
        EvalEdge("evt-fr-021", "ent-fr-id-svc", "REFERENCES"),
        EvalEdge("evt-fr-022", "ent-fr-acc", "REFERENCES"),
        EvalEdge("evt-fr-023", "ent-fr-ip", "REFERENCES"),
        EvalEdge("evt-fr-023", "ent-fr-device", "REFERENCES"),
        EvalEdge("evt-fr-023", "ent-fr-acc", "REFERENCES"),
        EvalEdge("evt-fr-024", "ent-fr-device", "REFERENCES"),
        EvalEdge("evt-fr-024", "ent-fr-device-graph", "REFERENCES"),
        EvalEdge("evt-fr-025", "ent-fr-device", "REFERENCES"),
        EvalEdge("evt-fr-025", "ent-fr-banned", "REFERENCES"),
        EvalEdge("evt-fr-028", "ent-fr-txn-svc", "REFERENCES"),
        EvalEdge("evt-fr-028", "ent-fr-acc", "REFERENCES"),
        EvalEdge("evt-fr-029", "ent-fr-acc", "REFERENCES"),
        EvalEdge("evt-fr-030", "ent-fr-acc", "REFERENCES"),
        EvalEdge("evt-fr-030", "ent-fr-compliance", "REFERENCES"),
        EvalEdge("evt-fr-031", "ent-fr-acc", "REFERENCES"),
        # Entity relationships
        EvalEdge("ent-fr-device", "ent-fr-ip", "RELATED_TO", {"relationship": "same_session_origin"}),
        EvalEdge("ent-fr-device", "ent-fr-banned", "RELATED_TO", {"relationship": "linked_in_graph"}),
        # User profile relationships
        EvalEdge("ent-fr-acc", "user-profile-analyst", "HAS_PROFILE"),
        EvalEdge("user-profile-analyst", "pref-analyst-01", "HAS_PREFERENCE"),
        EvalEdge("user-profile-analyst", "pref-analyst-02", "HAS_PREFERENCE"),
        EvalEdge("user-profile-analyst", "skill-analyst-01", "HAS_SKILL"),
        EvalEdge("user-profile-analyst", "skill-analyst-02", "HAS_SKILL"),
        # Derivation edges
        EvalEdge("pref-analyst-01", "evt-fr-024", "DERIVED_FROM"),
        EvalEdge("skill-analyst-01", "evt-fr-027", "DERIVED_FROM"),
    ]

    # Fraud scenario queries
    queries = [
        # WHY queries
        EvalQuery(
            query_id="fr-why-01",
            query="Why was the merchant account flagged?",
            intent=IntentType.WHY,
            scenario=scenario_id,
            expected_top_nodes=[
                RelevanceJudgment("evt-fr-030", 3),
                RelevanceJudgment("evt-fr-027", 3),
                RelevanceJudgment("evt-fr-029", 3),
                RelevanceJudgment("evt-fr-025", 2),
                RelevanceJudgment("evt-fr-023", 2),
            ],
            must_not_appear=["evt-pay-010", "evt-mo-040"],
            rationale="evt-fr-030 has two CAUSED_BY edges — to evt-fr-027 (ATO pattern) and evt-fr-029 (rapid txns). "
            "Both causal chains should surface.",
        ),
        # WHEN queries
        EvalQuery(
            query_id="fr-when-01",
            query="What was the sequence of events leading to the account hold?",
            intent=IntentType.WHEN,
            scenario=scenario_id,
            expected_top_nodes=[
                RelevanceJudgment("evt-fr-031", 3),
                RelevanceJudgment("evt-fr-030", 3),
                RelevanceJudgment("evt-fr-029", 2),
                RelevanceJudgment("evt-fr-027", 2),
                RelevanceJudgment("evt-fr-025", 2),
                RelevanceJudgment("evt-fr-023", 2),
            ],
            must_not_appear=["evt-pay-010", "evt-mo-040"],
            rationale="Full FOLLOWS chain traced backward from evt-fr-031. All temporal predecessors are relevant.",
        ),
        # WHAT queries
        EvalQuery(
            query_id="fr-what-01",
            query="What transactions occurred on the flagged account?",
            intent=IntentType.WHAT,
            scenario=scenario_id,
            expected_top_nodes=[
                RelevanceJudgment("evt-fr-029", 3),
                RelevanceJudgment("evt-fr-028", 3),
                RelevanceJudgment("ent-fr-acc", 2),
                RelevanceJudgment("ent-fr-txn-svc", 2),
            ],
            must_not_appear=["evt-pay-010", "evt-mo-040"],
            rationale="REFERENCES edges from transaction events to account entity.",
        ),
        # RELATED queries
        EvalQuery(
            query_id="fr-related-01",
            query="What other services are similar to the risk engine?",
            intent=IntentType.RELATED,
            scenario=scenario_id,
            expected_top_nodes=[
                RelevanceJudgment("ent-fr-device-graph", 3),
                RelevanceJudgment("ent-fr-id-svc", 2),
                RelevanceJudgment("ent-fr-txn-svc", 2),
            ],
            must_not_appear=["ent-mo-mcc", "ent-pay-order"],
            rationale="Cross-scenario comparison via entity type similarity. "
            "Device-graph and risk-engine are both risk assessment services.",
        ),
        # GENERAL queries
        EvalQuery(
            query_id="fr-general-01",
            query="Give me an overview of the fraud investigation",
            intent=IntentType.GENERAL,
            scenario=scenario_id,
            expected_top_nodes=[
                RelevanceJudgment("evt-fr-031", 3),
                RelevanceJudgment("evt-fr-030", 3),
                RelevanceJudgment("evt-fr-027", 2),
                RelevanceJudgment("evt-fr-025", 2),
                RelevanceJudgment("ent-fr-acc", 2),
                RelevanceJudgment("evt-fr-020", 1),
            ],
            must_not_appear=["evt-pay-010", "evt-mo-040"],
            rationale="General — high-importance events that capture the story arc.",
        ),
        # WHO_IS queries
        EvalQuery(
            query_id="fr-who-01",
            query="Who is the fraud analyst investigating this account?",
            intent=IntentType.WHO_IS,
            scenario=scenario_id,
            expected_top_nodes=[
                RelevanceJudgment("user-profile-analyst", 3),
                RelevanceJudgment("skill-analyst-01", 3),
                RelevanceJudgment("skill-analyst-02", 2),
                RelevanceJudgment("pref-analyst-01", 2),
            ],
            must_not_appear=["evt-pay-010", "ent-mo-merchant"],
            rationale="HAS_PROFILE, HAS_SKILL, HAS_PREFERENCE edges from user profile node.",
        ),
        # HOW_DOES queries
        EvalQuery(
            query_id="fr-how-01",
            query="How does the device fingerprint investigation process work?",
            intent=IntentType.HOW_DOES,
            scenario=scenario_id,
            expected_top_nodes=[
                RelevanceJudgment("evt-fr-024", 3),
                RelevanceJudgment("evt-fr-025", 3),
                RelevanceJudgment("ent-fr-device", 3),
                RelevanceJudgment("ent-fr-device-graph", 2),
                RelevanceJudgment("evt-fr-023", 2),
            ],
            must_not_appear=["evt-pay-010", "evt-mo-040"],
            rationale="Workflow/process focused on device investigation steps.",
        ),
        # PERSONALIZE queries
        EvalQuery(
            query_id="fr-personalize-01",
            query="How should I customize the fraud investigation workflow for this analyst?",
            intent=IntentType.PERSONALIZE,
            scenario=scenario_id,
            expected_top_nodes=[
                RelevanceJudgment("pref-analyst-01", 3),
                RelevanceJudgment("pref-analyst-02", 3),
                RelevanceJudgment("user-profile-analyst", 2),
                RelevanceJudgment("skill-analyst-01", 2),
                RelevanceJudgment("skill-analyst-02", 2),
            ],
            must_not_appear=["evt-pay-010", "ent-mo-merchant"],
            rationale="PERSONALIZE intent surfaces preferences and skills via HAS_PREFERENCE, HAS_SKILL edges.",
        ),
        EvalQuery(
            query_id="fr-personalize-02",
            query="What are this user's preferred investigation methods?",
            intent=IntentType.PERSONALIZE,
            scenario=scenario_id,
            expected_top_nodes=[
                RelevanceJudgment("pref-analyst-01", 3),
                RelevanceJudgment("skill-analyst-01", 2),
                RelevanceJudgment("skill-analyst-02", 2),
                RelevanceJudgment("user-profile-analyst", 2),
                RelevanceJudgment("evt-fr-024", 1),
            ],
            must_not_appear=["evt-pay-010", "ent-mo-merchant"],
            rationale="Preference + skill nodes with DERIVED_FROM edges back to source events.",
        ),
    ]

    return EvalScenario(
        scenario_id=scenario_id,
        description="Fraud investigation with account takeover detection",
        nodes=nodes,
        edges=edges,
        queries=queries,
    )


def _build_merchant_scenario() -> EvalScenario:
    """Build merchant onboarding scenario (merch-onb-003).

    Timeline: 2026-03-15 14:00:00 UTC (base + 4h)
    """
    scenario_id = "merch-onb-003"
    base_time = _BASE_TIME + timedelta(hours=4)

    # Events
    events = [
        _event_node(
            "evt-mo-040",
            "system.session_start",
            "Merchant onboarding: Sunrise Coffee LLC",
            base_time + timedelta(seconds=0),
            scenario_offset=2,
        ),
        _event_node(
            "evt-mo-041",
            "tool.execute",
            "Process application for Sunrise Coffee LLC, MCC 5814",
            base_time + timedelta(seconds=1),
            importance_hint=6,
            scenario_offset=2,
        ),
        _event_node(
            "evt-mo-042",
            "agent.invoke",
            "Initiate KYB verification for EIN 84-2918374",
            base_time + timedelta(seconds=2),
            importance_hint=7,
            scenario_offset=2,
        ),
        _event_node(
            "evt-mo-043",
            "tool.execute",
            "Run business verification: secretary of state, OFAC, adverse media",
            base_time + timedelta(seconds=3),
            importance_hint=8,
            scenario_offset=2,
        ),
        _event_node(
            "evt-mo-044",
            "observation.output",
            "KYB passed: entity verified, no OFAC hits, clean adverse media",
            base_time + timedelta(seconds=4),
            importance_hint=7,
            scenario_offset=2,
        ),
        _event_node(
            "evt-mo-045",
            "tool.execute",
            "Verify uploaded business license",
            base_time + timedelta(seconds=5),
            importance_hint=7,
            scenario_offset=2,
        ),
        _event_node(
            "evt-mo-046",
            "observation.output",
            "Document verification FAILED: business license expired 2025-12-31",
            base_time + timedelta(seconds=6),
            importance_hint=9,
            status="failed",
            scenario_offset=2,
        ),
        _event_node(
            "evt-mo-047",
            "observation.input",
            "Merchant uploaded renewed business license (valid through 2027-12-31)",
            base_time + timedelta(seconds=7),
            importance_hint=6,
            scenario_offset=2,
        ),
        _event_node(
            "evt-mo-048",
            "tool.execute",
            "Re-verify renewed business license",
            base_time + timedelta(seconds=8),
            importance_hint=7,
            scenario_offset=2,
        ),
        _event_node(
            "evt-mo-049",
            "observation.output",
            "Document verification PASSED: license valid",
            base_time + timedelta(seconds=9),
            importance_hint=8,
            scenario_offset=2,
        ),
        _event_node(
            "evt-mo-050",
            "agent.invoke",
            "Approve merchant, set tier=standard, daily_limit=$10,000",
            base_time + timedelta(seconds=10),
            importance_hint=10,
            scenario_offset=2,
        ),
    ]

    # Entities
    entities = [
        _entity_node("ent-mo-merchant", "agent", "sunrise-coffee-llc", 6, scenario_offset=2),
        _entity_node("ent-mo-ein", "resource", "ein-84-2918374", 3, scenario_offset=2),
        _entity_node("ent-mo-kyb", "service", "kyb-service", 2, scenario_offset=2),
        _entity_node("ent-mo-docver", "service", "doc-verification-service", 3, scenario_offset=2),
        _entity_node("ent-mo-license", "resource", "business-license", 4, scenario_offset=2),
        _entity_node("ent-mo-mcc", "concept", "mcc-5814-eating-places", 1, scenario_offset=2),
        _entity_node("ent-mo-ofac", "service", "ofac-screening", 1, scenario_offset=2),
    ]

    nodes = events + entities

    # Edges: FOLLOWS chain
    edges = [
        EvalEdge("evt-mo-040", "evt-mo-041", "FOLLOWS"),
        EvalEdge("evt-mo-041", "evt-mo-042", "FOLLOWS"),
        EvalEdge("evt-mo-042", "evt-mo-043", "FOLLOWS"),
        EvalEdge("evt-mo-043", "evt-mo-044", "FOLLOWS"),
        EvalEdge("evt-mo-044", "evt-mo-045", "FOLLOWS"),
        EvalEdge("evt-mo-045", "evt-mo-046", "FOLLOWS"),
        EvalEdge("evt-mo-046", "evt-mo-047", "FOLLOWS"),
        EvalEdge("evt-mo-047", "evt-mo-048", "FOLLOWS"),
        EvalEdge("evt-mo-048", "evt-mo-049", "FOLLOWS"),
        EvalEdge("evt-mo-049", "evt-mo-050", "FOLLOWS"),
        # CAUSED_BY edges
        EvalEdge("evt-mo-043", "evt-mo-042", "CAUSED_BY"),
        EvalEdge("evt-mo-046", "evt-mo-045", "CAUSED_BY"),
        EvalEdge("evt-mo-048", "evt-mo-047", "CAUSED_BY"),
        EvalEdge("evt-mo-049", "evt-mo-048", "CAUSED_BY"),
        EvalEdge("evt-mo-050", "evt-mo-049", "CAUSED_BY"),
        EvalEdge("evt-mo-050", "evt-mo-044", "CAUSED_BY"),
        # REFERENCES edges
        EvalEdge("evt-mo-041", "ent-mo-merchant", "REFERENCES"),
        EvalEdge("evt-mo-041", "ent-mo-mcc", "REFERENCES"),
        EvalEdge("evt-mo-042", "ent-mo-ein", "REFERENCES"),
        EvalEdge("evt-mo-042", "ent-mo-merchant", "REFERENCES"),
        EvalEdge("evt-mo-043", "ent-mo-kyb", "REFERENCES"),
        EvalEdge("evt-mo-043", "ent-mo-ein", "REFERENCES"),
        EvalEdge("evt-mo-043", "ent-mo-ofac", "REFERENCES"),
        EvalEdge("evt-mo-045", "ent-mo-docver", "REFERENCES"),
        EvalEdge("evt-mo-045", "ent-mo-license", "REFERENCES"),
        EvalEdge("evt-mo-046", "ent-mo-license", "REFERENCES"),
        EvalEdge("evt-mo-046", "ent-mo-docver", "REFERENCES"),
        EvalEdge("evt-mo-047", "ent-mo-license", "REFERENCES"),
        EvalEdge("evt-mo-047", "ent-mo-merchant", "REFERENCES"),
        EvalEdge("evt-mo-048", "ent-mo-docver", "REFERENCES"),
        EvalEdge("evt-mo-048", "ent-mo-license", "REFERENCES"),
        EvalEdge("evt-mo-049", "ent-mo-license", "REFERENCES"),
        EvalEdge("evt-mo-050", "ent-mo-merchant", "REFERENCES"),
    ]

    # Merchant scenario queries
    queries = [
        # WHY queries
        EvalQuery(
            query_id="mo-why-01",
            query="Why did document verification fail?",
            intent=IntentType.WHY,
            scenario=scenario_id,
            expected_top_nodes=[
                RelevanceJudgment("evt-mo-046", 3),
                RelevanceJudgment("evt-mo-045", 3),
                RelevanceJudgment("ent-mo-license", 2),
                RelevanceJudgment("ent-mo-docver", 2),
            ],
            must_not_appear=["evt-pay-010", "evt-fr-020", "evt-mo-049"],
            rationale="CAUSED_BY: evt-mo-046 ← evt-mo-045. License entity explains what was expired.",
        ),
        # WHEN queries
        EvalQuery(
            query_id="mo-when-01",
            query="When did the KYB check complete relative to document verification?",
            intent=IntentType.WHEN,
            scenario=scenario_id,
            expected_top_nodes=[
                RelevanceJudgment("evt-mo-044", 3),
                RelevanceJudgment("evt-mo-045", 3),
                RelevanceJudgment("evt-mo-043", 2),
                RelevanceJudgment("evt-mo-046", 2),
            ],
            must_not_appear=["evt-pay-010", "evt-fr-020"],
            rationale="Temporal comparison — the two parallel verification processes and their relationship.",
        ),
        # WHAT queries
        EvalQuery(
            query_id="mo-what-01",
            query="What does the onboarding process involve for a new merchant?",
            intent=IntentType.WHAT,
            scenario=scenario_id,
            expected_top_nodes=[
                RelevanceJudgment("evt-mo-041", 3),
                RelevanceJudgment("evt-mo-042", 2),
                RelevanceJudgment("evt-mo-043", 2),
                RelevanceJudgment("evt-mo-045", 2),
                RelevanceJudgment("evt-mo-050", 2),
                RelevanceJudgment("ent-mo-merchant", 2),
            ],
            must_not_appear=["evt-pay-010", "evt-fr-020"],
            rationale="Broad 'what' query — the full event chain describes the process.",
        ),
        # RELATED queries
        EvalQuery(
            query_id="mo-related-01",
            query="Are there similar verification patterns across merchant onboarding and payments?",
            intent=IntentType.RELATED,
            scenario=scenario_id,
            expected_top_nodes=[
                RelevanceJudgment("ent-mo-docver", 3),
                RelevanceJudgment("ent-mo-kyb", 2),
                RelevanceJudgment("ent-pay-3ds", 2),
                RelevanceJudgment("evt-mo-046", 2),
                RelevanceJudgment("evt-pay-013", 1),
            ],
            must_not_appear=["evt-fr-020"],
            rationale="Cross-scenario comparison via entity type similarity and pattern matching.",
        ),
        # GENERAL queries
        EvalQuery(
            query_id="mo-general-01",
            query="What happened in the merchant onboarding?",
            intent=IntentType.GENERAL,
            scenario=scenario_id,
            expected_top_nodes=[
                RelevanceJudgment("evt-mo-050", 3),
                RelevanceJudgment("evt-mo-046", 3),
                RelevanceJudgment("evt-mo-049", 2),
                RelevanceJudgment("evt-mo-041", 2),
                RelevanceJudgment("ent-mo-merchant", 2),
            ],
            must_not_appear=["evt-pay-010", "evt-fr-020"],
            rationale="General overview — dramatic arc: start, failure, resolution, success.",
        ),
        # WHO_IS queries
        EvalQuery(
            query_id="mo-who-01",
            query="Who is the merchant applying for onboarding?",
            intent=IntentType.WHO_IS,
            scenario=scenario_id,
            expected_top_nodes=[
                RelevanceJudgment("ent-mo-merchant", 3),
                RelevanceJudgment("ent-mo-ein", 2),
                RelevanceJudgment("ent-mo-mcc", 2),
                RelevanceJudgment("evt-mo-041", 1),
            ],
            must_not_appear=["ent-fr-acc", "ent-pay-merchant"],
            rationale="Entity hub query — merchant entity and its directly connected identifiers.",
        ),
        # HOW_DOES queries
        EvalQuery(
            query_id="mo-how-01",
            query="How does KYB verification work for new merchants?",
            intent=IntentType.HOW_DOES,
            scenario=scenario_id,
            expected_top_nodes=[
                RelevanceJudgment("evt-mo-042", 3),
                RelevanceJudgment("evt-mo-043", 3),
                RelevanceJudgment("evt-mo-044", 3),
                RelevanceJudgment("ent-mo-kyb", 2),
                RelevanceJudgment("ent-mo-ofac", 2),
                RelevanceJudgment("ent-mo-ein", 1),
            ],
            must_not_appear=["evt-pay-010", "evt-fr-020"],
            rationale="Process query — the KYB event chain describes the workflow.",
        ),
        # PERSONALIZE queries
        EvalQuery(
            query_id="mo-personalize-01",
            query="Personalize the merchant onboarding experience based on this application",
            intent=IntentType.PERSONALIZE,
            scenario=scenario_id,
            expected_top_nodes=[
                RelevanceJudgment("ent-mo-merchant", 3),
                RelevanceJudgment("ent-mo-mcc", 2),
                RelevanceJudgment("evt-mo-050", 2),
                RelevanceJudgment("evt-mo-041", 1),
            ],
            must_not_appear=["evt-fr-020", "user-profile-analyst"],
            rationale="No user profile exists for merchant scenario, so personalization "
            "falls back to entity-centric data.",
        ),
    ]

    return EvalScenario(
        scenario_id=scenario_id,
        description="Merchant onboarding with KYC/KYB and document verification",
        nodes=nodes,
        edges=edges,
        queries=queries,
    )


def _build_cross_scenario_edges() -> list[EvalEdge]:
    """Build edges that connect entities across scenarios.

    These edges enable cross-scenario relevance queries.
    """
    return [
        # Card and account have similar semantics (financial instruments)
        EvalEdge(
            "ent-pay-card",
            "ent-fr-acc",
            "SIMILAR_TO",
            {"similarity": 0.65, "reason": "both_financial_accounts"},
        ),
        # Risk engine and device graph are both risk assessment services
        EvalEdge(
            "ent-pay-risk",
            "ent-fr-device-graph",
            "SIMILAR_TO",
            {"similarity": 0.78, "reason": "risk_assessment_services"},
        ),
        # 3DS and KYB are both verification services
        EvalEdge(
            "ent-pay-3ds",
            "ent-mo-kyb",
            "SIMILAR_TO",
            {"similarity": 0.65, "reason": "verification_services"},
        ),
    ]


def _load_generated_scenarios() -> list[EvalScenario]:
    """Load generated scenarios from frozen JSON artifact."""
    json_path = Path(__file__).parent / "dataset_generated.json"
    if not json_path.exists():
        msg = (
            f"Generated dataset not found: {json_path}. "
            "Run generate_dataset.py first."
        )
        raise FileNotFoundError(msg)

    with open(json_path) as f:
        data = json.load(f)

    scenarios = []
    for s in data["scenarios"]:
        nodes = [
            EvalNode(n["node_id"], n["node_type"], n["attributes"])
            for n in s["nodes"]
        ]
        edges = [
            EvalEdge(e["source"], e["target"], e["edge_type"], e.get("properties", {}))
            for e in s["edges"]
        ]
        queries = [
            EvalQuery(
                query_id=q["query_id"],
                query=q["query"],
                intent=q["intent"],
                scenario=q["scenario"],
                expected_top_nodes=[
                    RelevanceJudgment(j["node_id"], j["grade"])
                    for j in q["expected_top_nodes"]
                ],
                must_not_appear=q["must_not_appear"],
                rationale=q["rationale"],
            )
            for q in s["queries"]
        ]
        scenarios.append(
            EvalScenario(s["scenario_id"], s["description"], nodes, edges, queries)
        )

    # Add cross-scenario edges to the first scenario (they'll be merged later)
    cross_edges = [
        EvalEdge(e["source"], e["target"], e["edge_type"], e.get("properties", {}))
        for e in data.get("cross_scenario_edges", [])
    ]
    if cross_edges and scenarios:
        scenarios[0].edges = list(scenarios[0].edges) + cross_edges

    return scenarios


def load_eval_dataset() -> dict[str, Any]:
    """Load the complete evaluation dataset.

    Respects _ACTIVE_MODE:
    - ORIGINAL: 3 hand-crafted scenarios (59 nodes, default)
    - EXTENDED: 3 original + 7 generated (merged)
    - GENERATED_ONLY: 7 generated scenarios only

    Returns:
        {
            "scenarios": [EvalScenario, ...],
            "cross_edges": [EvalEdge, ...],
            "all_nodes": {node_id: EvalNode},
            "all_edges": [EvalEdge, ...],
            "queries": [EvalQuery, ...],
            "intent_distribution": {intent: count},
            "metadata": {
                "base_time": datetime,
                "total_events": int,
                "total_entities": int,
                "total_edges": int,
                "total_queries": int,
            }
        }
    """
    # Build original scenarios (unless generated-only mode)
    if _ACTIVE_MODE == DatasetMode.GENERATED_ONLY:
        scenarios: list[EvalScenario] = []
        cross_edges: list[EvalEdge] = []
    else:
        pay_scenario = _build_payment_scenario()
        fraud_scenario = _build_fraud_scenario()
        merchant_scenario = _build_merchant_scenario()
        scenarios = [pay_scenario, fraud_scenario, merchant_scenario]
        cross_edges = _build_cross_scenario_edges()

    # Append generated scenarios if extended or generated-only mode
    if _ACTIVE_MODE in (DatasetMode.EXTENDED, DatasetMode.GENERATED_ONLY):
        generated_scenarios = _load_generated_scenarios()
        scenarios.extend(generated_scenarios)

    # Merge all nodes
    all_nodes = {}
    for scenario in scenarios:
        for node in scenario.nodes:
            all_nodes[node.node_id] = node

    # Merge all edges
    all_edges = []
    for scenario in scenarios:
        all_edges.extend(scenario.edges)
    if cross_edges:
        all_edges.extend(cross_edges)

    # Merge all queries
    all_queries = []
    for scenario in scenarios:
        all_queries.extend(scenario.queries)

    # Calculate intent distribution
    intent_distribution = {}
    for query in all_queries:
        intent = query.intent
        intent_distribution[intent] = intent_distribution.get(intent, 0) + 1

    # Collect metadata
    total_events = sum(1 for node in all_nodes.values() if node.node_type == "Event")
    total_entities = sum(
        1
        for node in all_nodes.values()
        if node.node_type in ("Entity", "UserProfile", "Preference", "Skill")
    )

    return {
        "scenarios": scenarios,
        "cross_edges": cross_edges,
        "all_nodes": all_nodes,
        "all_edges": all_edges,
        "queries": all_queries,
        "intent_distribution": intent_distribution,
        "metadata": {
            "base_time": _BASE_TIME.isoformat(),
            "total_events": total_events,
            "total_entities": total_entities,
            "total_edges": len(all_edges),
            "total_queries": len(all_queries),
            "intent_types": list(IntentType),
            "queries_per_intent": {intent: intent_distribution[intent] for intent in IntentType},
        },
    }


if __name__ == "__main__":
    # Quick validation script
    dataset = load_eval_dataset()

    print("=" * 80)
    print("EVALUATION DATASET SUMMARY")
    print("=" * 80)
    print()

    metadata = dataset["metadata"]
    print(f"Base Time: {metadata['base_time']}")
    print(f"Total Events: {metadata['total_events']}")
    print(f"Total Entities: {metadata['total_entities']}")
    print(f"Total Edges: {metadata['total_edges']}")
    print(f"Total Queries: {metadata['total_queries']}")
    print()

    print("Intent Distribution:")
    for intent, count in sorted(dataset["intent_distribution"].items()):
        print(f"  {intent:15s}: {count:2d} queries")
    print()

    print("Scenarios:")
    for scenario in dataset["scenarios"]:
        print(f"  {scenario.scenario_id:20s}: {len(scenario.nodes):2d} nodes, "
              f"{len(scenario.edges):2d} edges, {len(scenario.queries):d} queries")
    print()

    print("Sample Query (WHY intent):")
    sample_query = dataset["queries"][0]
    print(f"  Query ID: {sample_query.query_id}")
    print(f"  Query: {sample_query.query}")
    print(f"  Intent: {sample_query.intent}")
    print(f"  Scenario: {sample_query.scenario}")
    print(f"  Expected Top Nodes: {len(sample_query.expected_top_nodes)}")
    print(f"  Must Not Appear: {len(sample_query.must_not_appear)}")
    print()

    print("✓ Dataset loaded successfully")
    print(f"✓ All {metadata['total_queries']} evaluation queries are defined")
