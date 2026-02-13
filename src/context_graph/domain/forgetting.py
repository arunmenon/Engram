"""Retention tier enforcement and pruning rules (ADR-0008).

Pure domain module — ZERO framework imports.

Implements the Ebbinghaus-inspired forgetting curve tier system:
- HOT: recent events, full fidelity
- WARM: older events, prune low-similarity edges
- COLD: old events, prune low-importance/low-access nodes
- ARCHIVE: beyond retention ceiling, remove from graph entirely

Source: ADR-0008
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from context_graph.domain.models import RetentionTier


@dataclass
class PruningActions:
    """Aggregated pruning decisions for a batch of events."""

    delete_edges: list[str] = field(default_factory=list)
    delete_nodes: list[str] = field(default_factory=list)
    archive_event_ids: list[str] = field(default_factory=list)


def classify_retention_tier(
    occurred_at: datetime,
    now: datetime | None = None,
    hot_hours: int = 24,
    warm_hours: int = 168,
    cold_hours: int = 720,
) -> RetentionTier:
    """Classify an event into a retention tier based on its age.

    Tier boundaries (from ADR-0008):
    - HOT:     age < hot_hours  (default 24h)
    - WARM:    hot_hours <= age < warm_hours  (default 7 days)
    - COLD:    warm_hours <= age < cold_hours  (default 30 days)
    - ARCHIVE: age >= cold_hours
    """
    if now is None:
        now = datetime.now(UTC)

    age_hours = (now - occurred_at).total_seconds() / 3600.0

    if age_hours < hot_hours:
        return RetentionTier.HOT
    if age_hours < warm_hours:
        return RetentionTier.WARM
    if age_hours < cold_hours:
        return RetentionTier.COLD
    return RetentionTier.ARCHIVE


def should_prune_warm(
    event_data: dict[str, Any],
    warm_min_similarity: float = 0.7,
) -> bool:
    """Check if an event's SIMILAR_TO edge should be pruned in the warm tier.

    In the warm tier, SIMILAR_TO edges with a similarity score below
    the threshold are candidates for removal to reduce graph noise.

    The event_data dict is expected to have a ``similarity_score`` key
    (the score on the SIMILAR_TO edge, not the event itself).
    """
    similarity: float = event_data.get("similarity_score", 1.0)
    return bool(similarity < warm_min_similarity)


def should_prune_cold(
    event_data: dict[str, Any],
    cold_min_importance: int = 5,
    cold_min_access_count: int = 3,
) -> bool:
    """Check if a cold-tier event should be pruned from the graph.

    In the cold tier, events that fail BOTH thresholds are pruned:
    - importance_score < cold_min_importance AND
    - access_count < cold_min_access_count

    Meeting either threshold is enough to survive.
    """
    importance = event_data.get("importance_score") or 0
    access_count = event_data.get("access_count", 0)
    return importance < cold_min_importance and access_count < cold_min_access_count


def get_pruning_actions(
    events: list[dict[str, Any]],
    hot_hours: int = 24,
    warm_hours: int = 168,
    cold_hours: int = 720,
    warm_min_similarity: float = 0.7,
    cold_min_importance: int = 5,
    cold_min_access_count: int = 3,
    now: datetime | None = None,
) -> PruningActions:
    """Compute pruning actions for a batch of events.

    For each event, classifies its retention tier and applies the
    corresponding pruning rules:
    - HOT: no action
    - WARM: mark low-similarity edges for deletion
    - COLD: mark low-importance/low-access nodes for deletion
    - ARCHIVE: mark event for archival (remove from graph entirely)

    Returns a PruningActions with lists of IDs to delete/archive.
    """
    if now is None:
        now = datetime.now(UTC)

    actions = PruningActions()

    for event in events:
        occurred_at_raw = event.get("occurred_at")
        if occurred_at_raw is None:
            continue

        if isinstance(occurred_at_raw, str):
            occurred_at = datetime.fromisoformat(occurred_at_raw)
        else:
            occurred_at = occurred_at_raw

        tier = classify_retention_tier(
            occurred_at=occurred_at,
            now=now,
            hot_hours=hot_hours,
            warm_hours=warm_hours,
            cold_hours=cold_hours,
        )

        event_id = event.get("event_id", "")
        if not event_id:
            continue

        if tier == RetentionTier.HOT:
            continue

        if tier == RetentionTier.WARM:
            if should_prune_warm(event, warm_min_similarity=warm_min_similarity):
                actions.delete_edges.append(event_id)

        elif tier == RetentionTier.COLD:
            if should_prune_cold(
                event,
                cold_min_importance=cold_min_importance,
                cold_min_access_count=cold_min_access_count,
            ):
                actions.delete_nodes.append(event_id)

        elif tier == RetentionTier.ARCHIVE:
            actions.archive_event_ids.append(event_id)

    return actions
