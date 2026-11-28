"""Atomic, tenant-local relationship recovery over existing graph storage.

Intents contain references and digests, never event payload/property copies.
Storage keys identify an edge; generation identifies its latest deferred event.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from context_graph.ports.pack_graph import EdgeWrite

RECOVERY_LABEL = "ProjectionRecovery"
CURSOR_LABEL = "ProjectionRecoveryCursor"


class RelationshipRecoveryStore(Protocol):
    async def put_relationship_intent(self, record: dict[str, Any]) -> None:
        """Atomically retain the greatest log-order candidate; same generation is a no-op.

        Equal order with conflicting generation is refused. Existing terminal state
        never regresses on redelivery. Ordering tokens are supplied by the log adapter.
        """
        ...

    async def get_relationship_intents(self, keys: list[str]) -> dict[str, dict[str, Any]]:
        """Bounded point reads for redelivery fencing; keys are exact edge identities."""
        ...

    async def relationship_intents(self, after: str | None, limit: int) -> list[dict[str, Any]]:
        """At most limit rows, strictly after node_id, ordered by node_id in storage."""
        ...

    async def settle_relationship_intent(
        self,
        key: str,
        generation: str,
        status: str,
        edge: EdgeWrite | None = None,
    ) -> str:
        """CAS the generation and optionally create an edge in the same atomic unit.

        Return superseded, endpoint_missing, recovered or existing_relationship_kept.
        Existing relationships are NEVER changed. Endpoint checks, insert and terminal
        status must be atomic; an exception/fence leaves the transaction unchanged.
        """
        ...
