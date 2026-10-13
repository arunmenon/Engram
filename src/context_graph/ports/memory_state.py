"""Atomic Memory state/evidence boundary used by the shared projection worker."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from context_graph.domain.memory_actions import MemoryAction


@runtime_checkable
class MemoryStateStore(Protocol):
    async def apply_memory_action(self, action: MemoryAction) -> str:
        """Apply owner/revision checks, state and distinct evidence in one transaction.

        Returns applied/duplicate. Domain conflicts or missing references leave
        state and evidence unchanged. Driver outages use normal storage errors.
        """
        ...
