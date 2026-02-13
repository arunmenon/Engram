"""Re-consolidation logic (ADR-0008 Stage 3).

Pure domain module — ZERO framework imports.

Handles:
- Reconsolidation threshold checks
- Temporal episode grouping
- Deterministic summary creation (LLM path is Phase 5)
- Event pruning selection based on retention tier rules

Source: ADR-0008
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from context_graph.domain.models import RetentionTier, SummaryNode

if TYPE_CHECKING:
    from context_graph.settings import RetentionSettings


def should_reconsolidate(event_count: int, threshold: int = 150) -> bool:
    """Check whether a session's event count exceeds the reflection threshold.

    Returns True when the session has accumulated enough events to warrant
    a re-consolidation pass (creating summaries and pruning).
    """
    return event_count >= threshold


def group_events_into_episodes(
    events: list[dict[str, Any]],
    gap_minutes: int = 30,
) -> list[list[dict[str, Any]]]:
    """Split an event stream into episodes by temporal gaps.

    Events must have an ``occurred_at`` key (ISO string or datetime).
    A gap greater than ``gap_minutes`` between consecutive events starts a
    new episode. Events are sorted by occurred_at before grouping.

    Returns a list of episodes, each a list of event dicts.
    """
    if not events:
        return []

    def _parse_dt(raw: str | datetime) -> datetime:
        if isinstance(raw, datetime):
            return raw
        return datetime.fromisoformat(raw)

    sorted_events = sorted(events, key=lambda e: _parse_dt(e["occurred_at"]))
    gap_seconds = gap_minutes * 60

    episodes: list[list[dict[str, Any]]] = [[sorted_events[0]]]

    for event in sorted_events[1:]:
        prev_dt = _parse_dt(episodes[-1][-1]["occurred_at"])
        curr_dt = _parse_dt(event["occurred_at"])
        delta = (curr_dt - prev_dt).total_seconds()

        if delta > gap_seconds:
            episodes.append([event])
        else:
            episodes[-1].append(event)

    return episodes


def create_summary_from_events(
    events: list[dict[str, Any]],
    scope: str,
    scope_id: str,
) -> SummaryNode:
    """Create a deterministic summary node without LLM.

    Summarizes event count, distinct types, and time range. Generates a
    stable summary_id from scope_id and a hash of the event IDs.
    """
    if not events:
        msg = "Cannot create summary from empty event list"
        raise ValueError(msg)

    def _parse_dt(raw: str | datetime) -> datetime:
        if isinstance(raw, datetime):
            return raw
        return datetime.fromisoformat(raw)

    event_ids = sorted(e.get("event_id", "") for e in events)
    id_hash = hashlib.sha256("|".join(event_ids).encode()).hexdigest()[:12]
    summary_id = f"summary-{scope_id}-{id_hash}"

    event_types = sorted({e.get("event_type", "unknown") for e in events})
    timestamps = [_parse_dt(e["occurred_at"]) for e in events if "occurred_at" in e]
    timestamps.sort()

    time_range: list[datetime] = []
    if timestamps:
        time_range = [timestamps[0], timestamps[-1]]

    start_str = timestamps[0].isoformat() if timestamps else "?"
    end_str = timestamps[-1].isoformat() if timestamps else "?"
    content = f"{len(events)} events ({', '.join(event_types)}) " f"from {start_str} to {end_str}"

    return SummaryNode(
        summary_id=summary_id,
        scope=scope,
        scope_id=scope_id,
        content=content,
        created_at=datetime.now(UTC),
        event_count=len(events),
        time_range=time_range,
    )


def build_summary_prompt(episode_events: list[dict[str, Any]]) -> str:
    """Build an LLM prompt for summarizing an episode.

    Returns a prompt string for future LLM use (Phase 5). The prompt
    includes structured event data for the model to summarize.
    """

    def _parse_dt(raw: str | datetime) -> datetime:
        if isinstance(raw, datetime):
            return raw
        return datetime.fromisoformat(raw)

    sorted_events = sorted(
        episode_events,
        key=lambda e: _parse_dt(e.get("occurred_at", "1970-01-01T00:00:00+00:00")),
    )

    lines = [
        "Summarize the following sequence of agent events into a concise "
        "episode description. Focus on what actions were taken, what tools "
        "were used, and what the outcome was.",
        "",
        "Events:",
    ]

    for event in sorted_events:
        event_type = event.get("event_type", "unknown")
        tool_name = event.get("tool_name", "")
        occurred_at = event.get("occurred_at", "")
        status = event.get("status", "")
        tool_str = f" [{tool_name}]" if tool_name else ""
        status_str = f" ({status})" if status else ""
        lines.append(f"- {occurred_at}: {event_type}{tool_str}{status_str}")

    lines.append("")
    lines.append("Episode summary:")

    return "\n".join(lines)


def select_events_for_pruning(
    events: list[dict[str, Any]],
    tier: RetentionTier,
    retention: RetentionSettings,
) -> list[str]:
    """Return event_ids that should be pruned based on tier rules.

    - HOT tier: nothing is pruned.
    - WARM tier: events with low similarity scores are candidates
      (SIMILAR_TO edges below warm_min_similarity_score).
    - COLD tier: events below cold_min_importance AND cold_min_access_count.
    - ARCHIVE tier: all events are candidates for pruning.
    """
    if tier == RetentionTier.HOT:
        return []

    prune_ids: list[str] = []

    for event in events:
        event_id = event.get("event_id", "")
        if not event_id:
            continue

        if tier == RetentionTier.WARM:
            # In warm tier, we prune events that have low-quality
            # SIMILAR_TO connections (the similarity score is on the edge,
            # but for event-level pruning we check importance/access).
            # Events with very low importance and no access get pruned.
            importance = event.get("importance_score") or 0
            access_count = event.get("access_count", 0)
            if importance < retention.cold_min_importance and access_count == 0:
                prune_ids.append(event_id)

        elif tier == RetentionTier.COLD:
            importance = event.get("importance_score") or 0
            access_count = event.get("access_count", 0)
            if (
                importance < retention.cold_min_importance
                and access_count < retention.cold_min_access_count
            ):
                prune_ids.append(event_id)

        elif tier == RetentionTier.ARCHIVE:
            prune_ids.append(event_id)

    return prune_ids
