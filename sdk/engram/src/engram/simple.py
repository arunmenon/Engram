from __future__ import annotations

import asyncio
from typing import Any

from engram.config import configure as _configure_config
from engram.config import get_config
from engram.models import AtlasResponse, IngestResult

_init_lock = asyncio.Lock()
_default_client: Any = None
_default_session: Any = None


def _get_client() -> Any:
    """Get or create the module-level default client."""
    global _default_client  # noqa: PLW0603
    if _default_client is None:
        from engram.client import EngramClient

        _default_client = EngramClient(config=get_config())
    return _default_client


async def _get_session(agent_id: str) -> Any:
    """Get or create the module-level default session."""
    global _default_session  # noqa: PLW0603
    async with _init_lock:
        if _default_session is None:
            client = _get_client()
            session = client.session(agent_id)
            await session.__aenter__()
            _default_session = session
    return _default_session


async def record(
    content: str,
    *,
    agent_id: str = "default",
    event_type: str = "observation.output",
    importance: int | None = None,
    tool_name: str | None = None,
    payload: dict[str, Any] | None = None,
) -> IngestResult:
    """Record an event. Auto-manages session and IDs.

    First call creates a session; subsequent calls reuse it.
    """
    session = await _get_session(agent_id)
    return await session.record(
        content,
        event_type=event_type,
        importance=importance,
        tool_name=tool_name,
        payload=payload,
    )


async def recall(
    query: str | None = None,
    *,
    session_id: str | None = None,
    max_nodes: int = 100,
) -> AtlasResponse:
    """Recall context. Uses current session if session_id not provided."""
    client = _get_client()
    if session_id is not None:
        return await client.get_context(session_id, max_nodes=max_nodes, query=query)
    if _default_session is not None:
        return await _default_session.context(query=query, max_nodes=max_nodes)
    # No session yet — use client directly with a placeholder
    return await client.get_context("default", max_nodes=max_nodes, query=query)


async def trace(
    node_id: str,
    *,
    max_depth: int = 3,
    intent: str | None = "why",
) -> AtlasResponse:
    """Trace provenance/lineage for a node."""
    client = _get_client()
    return await client.get_lineage(node_id, max_depth=max_depth, intent=intent)


def configure(
    base_url: str | None = None,
    api_key: str | None = None,
    **kwargs: Any,
) -> None:
    """Configure the module-level client. Resets existing client/session.

    Note: This is a synchronous function. If a session is active, it will be
    discarded without sending session_end. Use the full SessionManager API
    for proper lifecycle management.
    """
    global _default_client, _default_session  # noqa: PLW0603
    _configure_config(base_url=base_url, api_key=api_key, **kwargs)
    _default_client = None
    _default_session = None
