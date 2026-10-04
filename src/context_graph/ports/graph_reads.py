"""Graph read operations used by the retrieval engine (ADR-0019 C3, C6).

Named, bounded reads that replace the query text the retrieval pipeline
used to run directly against Neo4j. Every read takes an optional
``timeout_s`` bound. Rows are plain dicts of node or edge properties: no
driver types cross this port.

Uses typing.Protocol for structural subtyping (not ABCs).

Source: ADR-0019
"""

from __future__ import annotations

from typing import Any, Protocol

# Seed strategies a backend must answer (domain.intent.select_seed_strategy).
# Unknown names fall back to "general" (most recent events).
SEED_STRATEGIES = (
    "causal_roots",
    "entity_hubs",
    "temporal_anchors",
    "user_profile",
    "similar_cluster",
    "workflow_pattern",
    "general",
)

# Keys of a row returned by ``event_neighbors``.
NEIGHBOR_ROW_KEYS = (
    "seed_event_id",
    "rel_type",
    "rel_props",
    "neighbor_labels",
    "neighbor_props",
    "neighbor_event_id",
    "neighbor_entity_id",
    "neighbor_summary_id",
)


class GraphReads(Protocol):
    """Bounded reads the retrieval engine composes."""

    async def seed_events(
        self,
        strategy: str,
        session_id: str | None,
        limit: int,
        *,
        timeout_s: float | None = None,
    ) -> list[dict[str, Any]]:
        """Return event properties chosen by a seed strategy, best first."""
        ...

    async def get_event_nodes(
        self, event_ids: list[str], *, timeout_s: float | None = None
    ) -> list[dict[str, Any]]:
        """Return the properties of the given events that exist (any order)."""
        ...

    async def cross_session_entity_events(
        self, session_id: str | None, limit: int, *, timeout_s: float | None = None
    ) -> list[dict[str, Any]]:
        """Return other sessions' events referencing this session's entities, newest first."""
        ...

    async def event_neighbors(
        self, event_ids: list[str], neighbor_limit: int, *, timeout_s: float | None = None
    ) -> list[dict[str, Any]]:
        """Return one row per outgoing edge of the given events (keys: NEIGHBOR_ROW_KEYS).

        An event with no outgoing edges yields a row with ``rel_type`` None.
        """
        ...

    async def session_events_page(
        self,
        session_id: str,
        limit: int,
        *,
        after: tuple[str, str] | None = None,
        timeout_s: float | None = None,
    ) -> list[dict[str, Any]]:
        """Return a page of a session's events.

        Without ``after``: the newest ``limit`` events, newest first. With
        ``after=(occurred_at, event_id)``: the next ``limit`` events after
        that key, oldest first (keyset pagination).
        """
        ...

    async def session_edges(
        self, session_id: str, event_ids: list[str], *, timeout_s: float | None = None
    ) -> list[dict[str, Any]]:
        """Return edges among the given events of a session.

        Rows: ``source``, ``target``, ``edge_type``, ``props`` (a dict, empty if none).
        """
        ...

    async def lineage_chains(
        self,
        node_id: str,
        max_depth: int,
        max_nodes: int,
        *,
        timeout_s: float | None = None,
    ) -> list[dict[str, Any]]:
        """Return CAUSED_BY chains from an event, at most ``max_nodes`` chains.

        Each chain: ``nodes`` (event property dicts along the path) and
        ``edges`` (dicts with ``source``, ``target`` event ids and ``properties``).
        """
        ...

    async def record_access(self, event_ids: list[str], accessed_at: str) -> None:
        """Increment access counts and set last-accessed time (ISO 8601) on events."""
        ...
