from __future__ import annotations

import asyncio
import threading
from typing import Any

from engram.client import EngramClient
from engram.config import EngramConfig
from engram.models import (
    AtlasResponse,
    BatchResult,
    Event,
    HealthStatus,
    IngestResult,
    StatsResponse,
    SubgraphQuery,
    UserProfile,
)


class EngramSyncClient:
    """Synchronous wrapper around EngramClient using a background event loop thread."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        admin_key: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        config: EngramConfig | None = None,
    ) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._closed = False
        self._async_client = EngramClient(
            base_url=base_url,
            api_key=api_key,
            admin_key=admin_key,
            timeout=timeout,
            max_retries=max_retries,
            config=config,
        )

    def _run_loop(self) -> None:
        """Run the event loop in the background thread."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run(self, coro: Any) -> Any:
        """Run an async coroutine synchronously on the background loop."""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=self._async_client._config.timeout + 5)

    def ingest(self, event: Event) -> IngestResult:
        """Ingest a single event."""
        return self._run(self._async_client.ingest(event))

    def ingest_batch(self, events: list[Event]) -> BatchResult:
        """Ingest a batch of events."""
        return self._run(self._async_client.ingest_batch(events))

    def get_context(self, session_id: str, **kwargs: Any) -> AtlasResponse:
        """Get session context."""
        return self._run(self._async_client.get_context(session_id, **kwargs))

    def query_subgraph(self, query: SubgraphQuery) -> AtlasResponse:
        """Query subgraph."""
        return self._run(self._async_client.query_subgraph(query))

    def get_lineage(self, node_id: str, **kwargs: Any) -> AtlasResponse:
        """Get node lineage."""
        return self._run(self._async_client.get_lineage(node_id, **kwargs))

    def get_entity(self, entity_id: str) -> dict[str, Any]:
        """Get entity."""
        return self._run(self._async_client.get_entity(entity_id))

    def get_user_profile(self, user_id: str) -> UserProfile:
        """Get user profile."""
        return self._run(self._async_client.get_user_profile(user_id))

    def get_user_preferences(
        self, user_id: str, category: str | None = None
    ) -> list[dict[str, Any]]:
        """Get user preferences."""
        return self._run(self._async_client.get_user_preferences(user_id, category=category))

    def get_user_skills(self, user_id: str) -> list[dict[str, Any]]:
        """Get user skills."""
        return self._run(self._async_client.get_user_skills(user_id))

    def get_user_patterns(self, user_id: str) -> list[dict[str, Any]]:
        """Get user patterns."""
        return self._run(self._async_client.get_user_patterns(user_id))

    def get_user_interests(self, user_id: str) -> list[dict[str, Any]]:
        """Get user interests."""
        return self._run(self._async_client.get_user_interests(user_id))

    def export_user_data(self, user_id: str) -> dict[str, Any]:
        """Export user data (GDPR)."""
        return self._run(self._async_client.export_user_data(user_id))

    def delete_user(self, user_id: str) -> dict[str, Any]:
        """Delete user (GDPR)."""
        return self._run(self._async_client.delete_user(user_id))

    def health(self) -> HealthStatus:
        """Check health."""
        return self._run(self._async_client.health())

    def stats(self) -> StatsResponse:
        """Get admin stats."""
        return self._run(self._async_client.stats())

    def reconsolidate(self, session_id: str | None = None) -> dict[str, Any]:
        """Trigger reconsolidation."""
        return self._run(self._async_client.reconsolidate(session_id=session_id))

    def prune(self, tier: str, dry_run: bool = True) -> dict[str, Any]:
        """Prune events by tier."""
        return self._run(self._async_client.prune(tier, dry_run=dry_run))

    def health_detailed(self) -> dict[str, Any]:
        """Get detailed health."""
        return self._run(self._async_client.health_detailed())

    def close(self) -> None:
        """Close the client and shut down the background loop. Idempotent."""
        if self._closed:
            return
        self._closed = True
        try:
            self._run(self._async_client.close())
        finally:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=5)
            if not self._loop.is_closed():
                self._loop.close()

    def __enter__(self) -> EngramSyncClient:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()
