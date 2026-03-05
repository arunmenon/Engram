from __future__ import annotations

import asyncio
import warnings
from typing import Any

from engram.config import configure as _configure_config
from engram.config import get_config
from engram.models import AtlasResponse, IngestResult, Memory, SubgraphQuery

_init_lock = asyncio.Lock()
_default_client: Any = None
_default_session: Any = None

# Canonical text-extraction key order — must match AtlasResponse._TEXT_KEYS
_TEXT_KEYS = (
    "content",
    "payload_ref",
    "summary",
    "text",
    "belief_text",
    "description",
    "name",
)


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


async def add(
    text: str,
    *,
    agent_id: str = "default",
    importance: int | None = None,
) -> IngestResult:
    """Simple add — wraps record() with event_type='observation.output'."""
    session = await _get_session(agent_id)
    return await session.record(
        text,
        event_type="observation.output",
        importance=importance,
    )


async def search(
    query: str,
    *,
    top_k: int = 10,
) -> list[Memory]:
    """Simple search — wraps query_subgraph(), returns flat Memory list."""
    client = _get_client()
    # Build a SubgraphQuery using session context when available
    session_id = _default_session.id if _default_session is not None else "default"
    agent_id = getattr(_default_session, "_agent_id", "default")
    subgraph_query = SubgraphQuery(
        query=query,
        session_id=session_id,
        agent_id=agent_id,
        max_nodes=top_k,
    )
    atlas = await client.query_subgraph(subgraph_query)
    memories: list[Memory] = []
    for node_id, node in atlas.nodes.items():
        text = ""
        for key in _TEXT_KEYS:
            val = node.attributes.get(key)
            if val and isinstance(val, str):
                text = val
                break
        if text:
            score = node.scores.decay_score
            source_session = ""
            if node.provenance is not None:
                source_session = node.provenance.session_id
            memories.append(
                Memory(
                    text=text,
                    memory_id=node_id,
                    node_type=node.node_type,
                    score=score,
                    source_session=source_session,
                )
            )
    memories.sort(key=lambda m: m.score, reverse=True)
    return memories


async def aclose() -> None:
    """Gracefully end session and close client."""
    global _default_session, _default_client  # noqa: PLW0603
    if _default_session is not None:
        try:
            await _default_session.end()
        except Exception:  # noqa: BLE001
            pass
        _default_session = None
    if _default_client is not None:
        try:
            await _default_client.close()
        except Exception:  # noqa: BLE001
            pass
        _default_client = None


def configure(
    base_url: str | None = None,
    api_key: str | None = None,
    **kwargs: Any,
) -> None:
    """Configure the module-level client. Resets existing client/session.

    Note: This is a synchronous function. If a session is active, it will be
    discarded without sending session_end. Call aclose() first to avoid
    session leak.
    """
    global _default_client, _default_session  # noqa: PLW0603
    if _default_session is not None:
        warnings.warn(
            "configure() called with active session. Call aclose() first to avoid session leak.",
            ResourceWarning,
            stacklevel=2,
        )
    _configure_config(base_url=base_url, api_key=api_key, **kwargs)
    _default_client = None
    _default_session = None
