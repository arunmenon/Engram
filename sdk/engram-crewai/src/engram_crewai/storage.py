"""CrewAI storage backend powered by the Engram context graph.

Implements CrewAI's storage protocol methods without importing crewai
directly, to avoid pulling in the heavy dependency tree.
"""

from __future__ import annotations

import asyncio
import threading
import uuid
from datetime import UTC, datetime
from typing import Any

from engram.client import EngramClient
from engram.models import Event, SubgraphQuery


class EngramStorageBackend:
    """CrewAI-compatible storage backend that persists to Engram.

    Uses a background event loop thread (same pattern as EngramSyncClient)
    to bridge sync CrewAI calls to the async Engram client.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        agent_id: str = "crewai",
    ) -> None:
        self.agent_id = agent_id
        self._scopes: set[str] = set()

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._closed = False

        self._client = EngramClient(base_url=base_url, api_key=api_key)

    def _run_loop(self) -> None:
        """Run the event loop in the background thread."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run_sync(self, coro: Any) -> Any:
        """Run an async coroutine synchronously on the background loop."""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=30)

    def save(
        self,
        value: str,
        metadata: dict[str, Any] | None = None,
        scope: str = "default",
    ) -> str:
        """Save a value to Engram. Returns the event ID."""
        self._scopes.add(scope)
        event_id = uuid.uuid4()
        trace_id = str(uuid.uuid4())
        payload: dict[str, Any] = dict(metadata) if metadata else {}
        payload["content"] = value

        event = Event(
            event_id=event_id,
            event_type="observation.output",
            occurred_at=datetime.now(UTC),
            session_id=scope,
            agent_id=self.agent_id,
            trace_id=trace_id,
            payload_ref=value,
            payload=payload,
        )
        self._run_sync(self._client.ingest(event))
        return str(event_id)

    def search(
        self,
        query: str,
        limit: int = 10,
        scope: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search Engram for relevant context. Returns list of result dicts."""
        session_id = scope or "default"
        subgraph_query = SubgraphQuery(
            query=query,
            session_id=session_id,
            agent_id=self.agent_id,
            max_nodes=limit,
        )
        response = self._run_sync(self._client.query_subgraph(subgraph_query))
        results: list[dict[str, Any]] = []
        for node_id, node in response.nodes.items():
            content = _extract_content(node)
            result: dict[str, Any] = {
                "id": node_id,
                "content": content,
                "score": node.scores.relevance_score,
                "metadata": {
                    "node_type": node.node_type,
                    "retrieval_reason": node.retrieval_reason,
                    "decay_score": node.scores.decay_score,
                    "importance_score": node.scores.importance_score,
                },
            }
            if node.provenance:
                result["metadata"]["session_id"] = node.provenance.session_id
                result["metadata"]["agent_id"] = node.provenance.agent_id
                result["metadata"]["occurred_at"] = node.provenance.occurred_at.isoformat()
            results.append(result)
        return results

    def delete(self, item_id: str) -> bool:
        """No-op: Engram events are immutable. Always returns False."""
        return False

    def list_scopes(self) -> list[str]:
        """Return known session IDs (scopes) that have been used."""
        return sorted(self._scopes)

    # -- Async variants for direct async usage --

    async def asave(
        self,
        value: str,
        metadata: dict[str, Any] | None = None,
        scope: str = "default",
    ) -> str:
        """Async version of save()."""
        self._scopes.add(scope)
        event_id = uuid.uuid4()
        trace_id = str(uuid.uuid4())
        payload: dict[str, Any] = dict(metadata) if metadata else {}
        payload["content"] = value

        event = Event(
            event_id=event_id,
            event_type="observation.output",
            occurred_at=datetime.now(UTC),
            session_id=scope,
            agent_id=self.agent_id,
            trace_id=trace_id,
            payload_ref=value,
            payload=payload,
        )
        await self._client.ingest(event)
        return str(event_id)

    async def asearch(
        self,
        query: str,
        limit: int = 10,
        scope: str | None = None,
    ) -> list[dict[str, Any]]:
        """Async version of search()."""
        session_id = scope or "default"
        subgraph_query = SubgraphQuery(
            query=query,
            session_id=session_id,
            agent_id=self.agent_id,
            max_nodes=limit,
        )
        response = await self._client.query_subgraph(subgraph_query)
        results: list[dict[str, Any]] = []
        for node_id, node in response.nodes.items():
            content = _extract_content(node)
            result: dict[str, Any] = {
                "id": node_id,
                "content": content,
                "score": node.scores.relevance_score,
                "metadata": {
                    "node_type": node.node_type,
                    "retrieval_reason": node.retrieval_reason,
                    "decay_score": node.scores.decay_score,
                    "importance_score": node.scores.importance_score,
                },
            }
            if node.provenance:
                result["metadata"]["session_id"] = node.provenance.session_id
                result["metadata"]["agent_id"] = node.provenance.agent_id
                result["metadata"]["occurred_at"] = node.provenance.occurred_at.isoformat()
            results.append(result)
        return results

    def close(self) -> None:
        """Close the client and shut down the background loop."""
        if self._closed:
            return
        self._closed = True
        try:
            self._run_sync(self._client.close())
        finally:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=5)
            if not self._loop.is_closed():
                self._loop.close()

    def __enter__(self) -> EngramStorageBackend:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


def _extract_content(node: Any) -> str:
    """Extract text content from an AtlasNode's attributes."""
    attributes = node.attributes
    for key in ("content", "payload_ref", "summary", "text", "belief_text", "description", "name"):
        if key in attributes and isinstance(attributes[key], str):
            return attributes[key]
    if attributes:
        return str(attributes)
    return f"[{node.node_type}:{node.node_id}]"
