"""Health check port interface.

Uses typing.Protocol for structural subtyping.
Any adapter that can respond to a connectivity ping implements this.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class HealthCheckable(Protocol):
    """Protocol for services that support health-check pings."""

    async def health_ping(self) -> bool:
        """Return True if the service is reachable, False otherwise."""
        ...
