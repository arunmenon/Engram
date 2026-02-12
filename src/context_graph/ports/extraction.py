"""Knowledge extraction service port interface.

Source: ADR-0013
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from context_graph.domain.models import Event


class ExtractionService(Protocol):
    """Protocol for LLM-based knowledge extraction from sessions."""

    async def extract_from_session(
        self,
        events: list[Event],
        session_id: str,
        agent_id: str,
    ) -> dict[str, Any]:
        """Extract knowledge (entities, preferences, skills, interests) from a session.

        Returns a dict with keys: entities, preferences, skills, interests, patterns.
        Each value is a list of extracted items with confidence scores and
        provenance references back to source events.
        """
        ...
