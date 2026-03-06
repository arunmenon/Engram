"""User store port interface.

Uses typing.Protocol for structural subtyping.
Covers user profile, preferences, skills, patterns, interests,
and GDPR operations.

Source: ADR-0012
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class UserStore(Protocol):
    """Protocol for user-specific graph operations."""

    async def get_user_profile(self, user_id: str) -> dict[str, Any] | None:
        """Fetch a user's profile node. Returns None if not found."""
        ...

    async def get_user_preferences(
        self, user_id: str, active_only: bool = True
    ) -> list[dict[str, Any]]:
        """Fetch a user's preferences."""
        ...

    async def get_user_skills(self, user_id: str) -> list[dict[str, Any]]:
        """Fetch a user's skills."""
        ...

    async def get_user_patterns(self, user_id: str) -> list[dict[str, Any]]:
        """Fetch a user's behavioral patterns."""
        ...

    async def get_user_interests(self, user_id: str) -> list[dict[str, Any]]:
        """Fetch a user's interests."""
        ...

    async def delete_user_data(self, user_id: str) -> int:
        """GDPR cascade delete. Returns the number of affected entities."""
        ...

    async def export_user_data(self, user_id: str) -> dict[str, Any]:
        """GDPR export: return all data associated with a user."""
        ...

    async def write_user_profile(self, profile_data: dict[str, Any]) -> None:
        """Create or update a user profile with HAS_PROFILE edge."""
        ...

    async def write_preference_with_edges(
        self,
        user_entity_id: str,
        preference_data: dict[str, Any],
        source_event_ids: list[str],
        derivation_info: dict[str, Any],
    ) -> None:
        """Write a Preference node with HAS_PREFERENCE, ABOUT, and DERIVED_FROM edges."""
        ...

    async def write_skill_with_edges(
        self,
        user_entity_id: str,
        skill_data: dict[str, Any],
        source_event_ids: list[str],
        derivation_info: dict[str, Any],
    ) -> None:
        """Write a Skill node with HAS_SKILL and DERIVED_FROM edges."""
        ...

    async def write_interest_edge(
        self,
        user_entity_id: str,
        entity_name: str,
        entity_type: str,
        weight: float,
        source: str,
    ) -> None:
        """Create an INTERESTED_IN edge from user to a target entity."""
        ...

    async def write_derived_from_edge(
        self,
        source_node_id: str,
        source_id_field: str,
        event_id: str,
        method: str,
        session_id: str,
    ) -> None:
        """Write a single DERIVED_FROM edge from a source node to an event."""
        ...

    async def set_preference_superseded(
        self,
        preference_id: str,
        superseded_by: str,
    ) -> None:
        """Mark a preference as superseded by another preference."""
        ...
