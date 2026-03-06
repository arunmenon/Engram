"""MCP server setup with session-per-connection management."""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server

from engram import EngramClient, EngramConfig, Event
from engram_mcp.tools import register_tools


class EngramMCPServer:
    """MCP server that wraps the Engram SDK with session-per-connection."""

    def __init__(self, config: EngramConfig | None = None) -> None:
        self._config = config or EngramConfig()
        self._client: EngramClient | None = None
        self._session_id: str = str(uuid.uuid4())
        self._trace_id: str = str(uuid.uuid4())
        self._agent_id: str = os.environ.get("ENGRAM_AGENT_ID", "mcp-agent")
        self._last_event_id: str | None = None
        self._event_lock = asyncio.Lock()
        self._started: bool = False
        self._server = Server("engram-mcp")

    @property
    def client(self) -> EngramClient:
        """Return the underlying EngramClient. Raises if not started."""
        if self._client is None:
            raise RuntimeError("EngramMCPServer not started — call start() first")
        return self._client

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def trace_id(self) -> str:
        return self._trace_id

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def last_event_id(self) -> str | None:
        return self._last_event_id

    @last_event_id.setter
    def last_event_id(self, value: str | None) -> None:
        self._last_event_id = value

    async def update_last_event_id(self, value: str | None) -> None:
        """Update last_event_id under the event lock for concurrent safety."""
        async with self._event_lock:
            self._last_event_id = value

    async def start(self) -> None:
        """Initialize client and register tools. Idempotent."""
        if self._started:
            return
        self._started = True
        self._client = EngramClient(config=self._config)
        register_tools(self._server, self)

        # Send session_start event
        event = Event(
            event_id=uuid.uuid4(),
            event_type="system.session_start",
            occurred_at=datetime.now(timezone.utc),
            session_id=self._session_id,
            agent_id=self._agent_id,
            trace_id=self._trace_id,
            payload_ref="MCP session started",
        )
        try:
            await self._client.ingest(event)
            self._last_event_id = str(event.event_id)
        except Exception:
            # Don't fail startup if the server is not yet available
            pass

    async def shutdown(self) -> None:
        """Send session_end event and close client."""
        if self._client is None:
            return
        self._started = False

        # Send session_end event
        parent_id = uuid.UUID(self._last_event_id) if self._last_event_id else None
        event = Event(
            event_id=uuid.uuid4(),
            event_type="system.session_end",
            occurred_at=datetime.now(timezone.utc),
            session_id=self._session_id,
            agent_id=self._agent_id,
            trace_id=self._trace_id,
            payload_ref="MCP session ended",
            parent_event_id=parent_id,
        )
        import contextlib

        with contextlib.suppress(Exception):
            await self._client.ingest(event)

        await self._client.close()
        self._client = None

    async def run(self) -> None:
        """Run the MCP server over stdio."""
        await self.start()
        try:
            async with stdio_server() as (read_stream, write_stream):
                init_options = self._server.create_initialization_options()
                await self._server.run(read_stream, write_stream, init_options)
        finally:
            await self.shutdown()


def main() -> None:
    """Entry point for `engram-mcp` CLI command."""
    config_kwargs: dict[str, Any] = {}
    base_url = os.environ.get("ENGRAM_BASE_URL")
    if base_url:
        config_kwargs["base_url"] = base_url
    api_key = os.environ.get("ENGRAM_API_KEY")
    if api_key:
        config_kwargs["api_key"] = api_key

    config = EngramConfig(**config_kwargs) if config_kwargs else None
    mcp_server = EngramMCPServer(config=config)
    asyncio.run(mcp_server.run())
