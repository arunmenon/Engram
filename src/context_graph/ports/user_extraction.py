"""Atomic User extraction preparation and application on existing graph storage."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from context_graph.domain.models import Event


@runtime_checkable
class UserExtractionStore(Protocol):
    async def get_user_extraction(self, trigger: Event) -> dict[str, Any] | None:
        """Read a validated prepared/applied result; missing projection defers."""
        ...

    async def prepare_user_extraction(
        self, trigger: Event, candidate: dict[str, Any]
    ) -> dict[str, Any]:
        """First writer wins; return the stored winner before any User outputs."""
        ...

    async def apply_user_extraction(self, trigger: Event) -> str:
        """Atomically apply frozen User outputs/evidence and completion receipt."""
        ...
