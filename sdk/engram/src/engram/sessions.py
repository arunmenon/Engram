from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from engram.client import EngramClient
    from engram.models import AtlasResponse, IngestResult

from engram.models import Event, EventStatus


class SessionManager:
    """Manages a session lifecycle with auto-generated IDs and event chaining."""

    def __init__(self, client: EngramClient, agent_id: str) -> None:
        self._client = client
        self._agent_id = agent_id
        self._session_id = str(uuid.uuid4())
        self._trace_id = str(uuid.uuid4())
        self._last_event_id: str | None = None
        self._event_count: int = 0
        self._started: bool = False
        self._ended: bool = False
        self._lock = asyncio.Lock()

    @property
    def id(self) -> str:
        """The session ID."""
        return self._session_id

    @property
    def trace_id(self) -> str:
        """The trace ID shared by all events in this session."""
        return self._trace_id

    @property
    def event_count(self) -> int:
        """Number of events recorded in this session."""
        return self._event_count

    async def record(
        self,
        content: str,
        *,
        event_type: str = "observation.output",
        importance: int | None = None,
        tool_name: str | None = None,
        status: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> IngestResult:
        """Record an event in this session with auto-generated fields."""
        async with self._lock:
            return await self._record_unlocked(
                content,
                event_type=event_type,
                importance=importance,
                tool_name=tool_name,
                status=status,
                payload=payload,
            )

    async def _record_unlocked(
        self,
        content: str,
        *,
        event_type: str = "observation.output",
        importance: int | None = None,
        tool_name: str | None = None,
        status: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> IngestResult:
        """Internal record without lock -- caller must hold self._lock."""
        event_id = uuid.uuid4()
        parent_id = uuid.UUID(self._last_event_id) if self._last_event_id else None
        event_status = EventStatus(status) if status else None

        event = Event(
            event_id=event_id,
            event_type=event_type,
            occurred_at=datetime.now(timezone.utc),
            session_id=self._session_id,
            agent_id=self._agent_id,
            trace_id=self._trace_id,
            payload_ref=content,
            parent_event_id=parent_id,
            tool_name=tool_name,
            importance_hint=importance,
            status=event_status,
            payload=payload,
        )

        result = await self._client.ingest(event)
        self._last_event_id = str(event_id)
        self._event_count += 1
        return result

    async def context(
        self,
        *,
        query: str | None = None,
        max_nodes: int = 100,
        max_depth: int = 3,
    ) -> AtlasResponse:
        """Retrieve context for this session."""
        return await self._client.get_context(
            self._session_id, query=query, max_nodes=max_nodes, max_depth=max_depth
        )

    async def end(self) -> IngestResult | None:
        """Explicitly end this session by sending system.session_end event.

        Idempotent: calling end() multiple times only sends one event.
        The ended flag is set before the send to prevent duplicate session_end
        events if the first attempt partially succeeds then raises.
        """
        async with self._lock:
            if not self._started or self._ended:
                return None
            self._ended = True
            return await self._record_unlocked(
                "Session ended", event_type="system.session_end"
            )

    async def __aenter__(self) -> SessionManager:
        """Start the session. Sends system.session_start event."""
        self._started = True
        await self.record("Session started", event_type="system.session_start")
        return self

    async def __aexit__(self, *exc: Any) -> None:
        """End the session. Sends system.session_end event."""
        await self.end()
