"""Graph maintenance port interface.

Uses typing.Protocol for structural subtyping.
Covers batch maintenance operations used by admin routes and consolidation worker.

Source: ADR-0008
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class GraphMaintenance(Protocol):
    """Protocol for graph maintenance operations."""

    async def get_session_event_counts(
        self,
    ) -> dict[str, int]:
        """Count events per session in the graph.

        Returns a dict of {session_id: event_count}.
        """
        ...

    async def get_graph_stats(self) -> dict[str, Any]:
        """Get node and edge counts by type for admin/monitoring."""
        ...

    async def write_summary_with_edges(
        self,
        summary_id: str,
        scope: str,
        scope_id: str,
        content: str,
        created_at: str,
        event_count: int,
        time_range: list[str],
        event_ids: list[str],
    ) -> None:
        """Write a summary node and SUMMARIZES edges to the covered events."""
        ...

    async def count_edges_by_type_and_age(self, min_score: float, max_age_hours: int) -> int:
        """Count edges matching delete_edges_by_type_and_age without mutation.

        This is an estimate from the current graph; concurrent writes may change
        the subsequent live deletion count.
        """
        ...

    async def delete_edges_by_type_and_age(
        self,
        min_score: float,
        max_age_hours: int,
    ) -> int:
        """Delete SIMILAR_TO edges below a score threshold and older than max_age_hours."""
        ...

    async def delete_cold_events(
        self,
        max_age_hours: int,
        min_importance: int,
        min_access_count: int,
    ) -> int:
        """Delete cold-tier event nodes that don't meet retention criteria."""
        ...

    async def delete_archive_events(self, event_ids: list[str]) -> int:
        """Delete archived event nodes by their IDs."""
        ...

    async def get_archive_event_ids(self, max_age_hours: int) -> list[str]:
        """Get event IDs older than the specified age for archive-tier pruning."""
        ...

    async def delete_orphan_nodes(self, batch_size: int = 500) -> tuple[dict[str, int], list[str]]:
        """Delete orphaned nodes (no relationships) and return counts + deleted entity IDs."""
        ...

    async def update_importance_from_centrality(self) -> int:
        """Recompute importance scores based on in-degree centrality."""
        ...

    async def run_session_query(self, cypher: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Run an arbitrary read query and return records as dicts.

        Deprecated (ADR-0019): query text must not cross a port. Use the
        named operations below; kept only because this port is frozen.
        """
        ...

    # -- Named operations (ADR-0019 C6) -----------------------------------

    async def session_agent_id(self, session_id: str) -> str | None:
        """Return the agent id recorded on a session's events, or None if none exist."""
        ...

    async def session_events(self, session_id: str, limit: int) -> list[dict[str, Any]]:
        """Return a session's event node properties ordered by occurred_at."""
        ...

    async def session_event_timeline(self, session_id: str) -> list[dict[str, Any]]:
        """Return event_id, event_type, occurred_at, tool_name and status, in time order."""
        ...

    async def events_for_pruning(self, limit: int) -> list[dict[str, Any]]:
        """Return the oldest ``limit`` events with event_id, occurred_at,
        importance_score, access_count (0 if unset) and similarity_score."""
        ...

    async def delete_all(self, *, confirm: bool = False) -> None:
        """Delete every node and edge. Admin-only; raises InvalidRequest unless confirm."""
        ...
