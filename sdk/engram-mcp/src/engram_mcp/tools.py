"""Seven MCP tool definitions for the Engram context graph."""

from __future__ import annotations

import asyncio
import json as _json
import re
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from mcp.types import TextContent, Tool

from engram import Event, SubgraphQuery
from engram.models import AtlasResponse

if TYPE_CHECKING:
    from mcp.server import Server

    from engram_mcp.server import EngramMCPServer

# Validation constants
MAX_CONTENT_SIZE = 1_000_000  # 1MB
MAX_METADATA_SIZE = 100_000  # 100KB
MAX_NODES_LIMIT = 500
MAX_DEPTH_LIMIT = 10
VALID_ENTITY_TYPES = {"agent", "user", "service", "tool", "resource", "concept"}

# Error sanitization patterns
_SENSITIVE_PATTERNS = [
    re.compile(r"/(?:Users|home|var|opt|src)/[^\s]+", re.IGNORECASE),
    re.compile(
        r"(?:api[_-]?key|admin[_-]?key|password|secret|token)"
        r'["\s:=]+["\']?[\w\-\.]+',
        re.IGNORECASE,
    ),
    re.compile(r"(?:redis|neo4j|postgres)://[^\s]+", re.IGNORECASE),
    re.compile(r'File "[^"]+", line \d+', re.IGNORECASE),
    re.compile(r"Traceback \(most recent call last\):", re.IGNORECASE),
]

_MAX_ERROR_LENGTH = 500


def _sanitize_error(exc: Exception) -> str:
    """Sanitize exception message for safe display to users."""
    message = str(exc)
    for pattern in _SENSITIVE_PATTERNS:
        message = pattern.sub("[REDACTED]", message)
    if len(message) > _MAX_ERROR_LENGTH:
        message = message[:_MAX_ERROR_LENGTH] + "..."
    return message


def _validate_entity_type(entity_type: str) -> str:
    """Validate entity_type against allowlist."""
    normalized = entity_type.strip().lower()
    if normalized not in VALID_ENTITY_TYPES:
        raise ValueError(
            f"Invalid entity_type: {entity_type!r}. "
            f"Must be one of: {', '.join(sorted(VALID_ENTITY_TYPES))}"
        )
    return normalized


def _safe_int(value: Any, name: str, default: int, min_val: int, max_val: int) -> int:
    """Safely convert a value to int with bounds checking."""
    if value is None:
        return default
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer, got {type(value).__name__}") from exc
    return max(min_val, min(result, max_val))


TOOL_DEFINITIONS: list[Tool] = [
    Tool(
        name="engram_record",
        description="Record an observation or event in the Engram context graph",
        inputSchema={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The content/observation to record",
                },
                "event_type": {
                    "type": "string",
                    "description": (
                        "Event type (e.g., 'observation.output', 'tool.execute'). "
                        "Defaults to 'observation.output'."
                    ),
                    "default": "observation.output",
                },
                "importance": {
                    "type": "integer",
                    "description": "Importance hint from 1-10",
                    "minimum": 1,
                    "maximum": 10,
                },
                "metadata": {
                    "type": "object",
                    "description": "Additional metadata to include in the event payload",
                },
            },
            "required": ["content"],
        },
    ),
    Tool(
        name="engram_recall",
        description="Retrieve context for the current session or a specific session",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query to filter context",
                },
                "session_id": {
                    "type": "string",
                    "description": (
                        "Session ID to retrieve context for. Uses current session if not provided."
                    ),
                },
                "max_nodes": {
                    "type": "integer",
                    "description": "Maximum number of nodes to return",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 500,
                },
            },
        },
    ),
    Tool(
        name="engram_search",
        description="Search across all sessions and entities in the context graph",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
                "max_nodes": {
                    "type": "integer",
                    "description": "Maximum nodes to return",
                    "default": 50,
                },
                "intents": {
                    "type": "string",
                    "description": (
                        "Intent type filter "
                        "(why, when, what, related, general, who_is, how_does, personalize)"
                    ),
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="engram_trace",
        description=("Get provenance/lineage chain for a specific node — shows causal origins"),
        inputSchema={
            "type": "object",
            "properties": {
                "node_id": {
                    "type": "string",
                    "description": "The node ID to trace lineage from",
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum traversal depth",
                    "default": 3,
                    "minimum": 1,
                    "maximum": 10,
                },
                "intent": {
                    "type": "string",
                    "description": "Intent for traversal weighting",
                    "default": "why",
                },
            },
            "required": ["node_id"],
        },
    ),
    Tool(
        name="engram_profile",
        description="View user profile, preferences, and skills",
        inputSchema={
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "User ID to look up",
                },
            },
            "required": ["user_id"],
        },
    ),
    Tool(
        name="engram_entities",
        description="List known entities with their relationships",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum entities to return",
                    "default": 20,
                },
                "entity_type": {
                    "type": "string",
                    "description": (
                        "Filter by entity type (agent, user, service, tool, resource, concept)"
                    ),
                },
            },
        },
    ),
    Tool(
        name="engram_forget",
        description="Request GDPR data deletion for a user",
        inputSchema={
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "User ID whose data should be deleted",
                },
            },
            "required": ["user_id"],
        },
    ),
]


def register_tools(server: Server, mcp_server: EngramMCPServer) -> None:
    """Register all 7 Engram tools with the MCP server."""

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return TOOL_DEFINITIONS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Dispatch tool calls to the appropriate handler."""
        handlers = {
            "engram_record": _handle_record,
            "engram_recall": _handle_recall,
            "engram_search": _handle_search,
            "engram_trace": _handle_trace,
            "engram_profile": _handle_profile,
            "engram_entities": _handle_entities,
            "engram_forget": _handle_forget,
        }
        handler = handlers.get(name)
        if handler is None:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
        return await handler(mcp_server, arguments)


# --- Tool handlers ---


async def _handle_record(
    mcp_server: EngramMCPServer, arguments: dict[str, Any]
) -> list[TextContent]:
    """Record an event in the context graph."""
    content = arguments.get("content", "")
    if not isinstance(content, str):
        return [TextContent(type="text", text="Error: content must be a string")]
    if len(content) > MAX_CONTENT_SIZE:
        return [
            TextContent(
                type="text",
                text=f"Error: content exceeds maximum size of {MAX_CONTENT_SIZE} bytes",
            )
        ]

    event_type = arguments.get("event_type", "observation.output")
    importance = arguments.get("importance")
    metadata = arguments.get("metadata")

    # Validate importance if provided
    if importance is not None:
        try:
            importance = _safe_int(importance, "importance", 5, 1, 10)
        except ValueError as exc:
            return [TextContent(type="text", text=f"Error: {exc}")]

    # Validate metadata size if provided
    if metadata is not None:
        if not isinstance(metadata, dict):
            return [TextContent(type="text", text="Error: metadata must be an object")]
        try:
            metadata_size = len(_json.dumps(metadata))
        except (TypeError, ValueError):
            return [TextContent(type="text", text="Error: metadata is not JSON-serializable")]
        if metadata_size > MAX_METADATA_SIZE:
            return [
                TextContent(
                    type="text",
                    text=f"Error: metadata exceeds maximum size of {MAX_METADATA_SIZE} bytes",
                )
            ]

    event_id = uuid.uuid4()
    parent_id = uuid.UUID(mcp_server.last_event_id) if mcp_server.last_event_id else None

    event = Event(
        event_id=event_id,
        event_type=event_type,
        occurred_at=datetime.now(timezone.utc),
        session_id=mcp_server.session_id,
        agent_id=mcp_server.agent_id,
        trace_id=mcp_server.trace_id,
        payload_ref=content,
        parent_event_id=parent_id,
        importance_hint=importance,
        payload=metadata,
    )

    try:
        result = await mcp_server.client.ingest(event)
    except Exception:
        return [TextContent(type="text", text="Error recording event: ingestion failed")]

    await mcp_server.update_last_event_id(str(event_id))

    text = (
        f"# Event Recorded\n\n"
        f"- **Event ID**: {result.event_id}\n"
        f"- **Position**: {result.global_position}\n"
        f"- **Type**: {event_type}\n"
        f"- **Session**: {mcp_server.session_id}\n"
    )
    if importance:
        text += f"- **Importance**: {importance}/10\n"

    return [TextContent(type="text", text=text)]


async def _handle_recall(
    mcp_server: EngramMCPServer, arguments: dict[str, Any]
) -> list[TextContent]:
    """Retrieve context for a session."""
    session_id = arguments.get("session_id", mcp_server.session_id)
    query = arguments.get("query")

    try:
        max_nodes = _safe_int(arguments.get("max_nodes"), "max_nodes", 50, 1, MAX_NODES_LIMIT)
    except ValueError as exc:
        return [TextContent(type="text", text=f"Error: {exc}")]

    try:
        response = await mcp_server.client.get_context(session_id, query=query, max_nodes=max_nodes)
    except ValueError as exc:
        return [TextContent(type="text", text=f"Error: {exc}")]
    except Exception:
        return [TextContent(type="text", text="Error retrieving context: request failed")]

    text = _format_atlas_response(response, title="Session Context")
    return [TextContent(type="text", text=text)]


async def _handle_search(
    mcp_server: EngramMCPServer, arguments: dict[str, Any]
) -> list[TextContent]:
    """Search across sessions and entities."""
    query_text = arguments["query"]
    intent = arguments.get("intents")

    try:
        max_nodes = _safe_int(arguments.get("max_nodes"), "max_nodes", 50, 1, MAX_NODES_LIMIT)
    except ValueError as exc:
        return [TextContent(type="text", text=f"Error: {exc}")]

    subgraph_query = SubgraphQuery(
        query=query_text,
        session_id=mcp_server.session_id,
        agent_id=mcp_server.agent_id,
        max_nodes=max_nodes,
        intent=intent,
    )

    try:
        response = await mcp_server.client.query_subgraph(subgraph_query)
    except Exception:
        return [TextContent(type="text", text="Error searching: request failed")]

    text = _format_atlas_response(response, title="Search Results")
    return [TextContent(type="text", text=text)]


async def _handle_trace(
    mcp_server: EngramMCPServer, arguments: dict[str, Any]
) -> list[TextContent]:
    """Get lineage for a node."""
    node_id = arguments["node_id"]
    intent = arguments.get("intent", "why")

    try:
        max_depth = _safe_int(arguments.get("max_depth"), "max_depth", 3, 1, MAX_DEPTH_LIMIT)
    except ValueError as exc:
        return [TextContent(type="text", text=f"Error: {exc}")]

    try:
        response = await mcp_server.client.get_lineage(node_id, max_depth=max_depth, intent=intent)
    except ValueError as exc:
        return [TextContent(type="text", text=f"Error: {exc}")]
    except Exception:
        return [TextContent(type="text", text="Error tracing lineage: request failed")]

    text = _format_atlas_response(response, title=f"Lineage for {node_id}")
    return [TextContent(type="text", text=text)]


async def _handle_profile(
    mcp_server: EngramMCPServer, arguments: dict[str, Any]
) -> list[TextContent]:
    """Fetch user profile with preferences, skills, patterns, and interests."""
    user_id = arguments["user_id"]

    try:
        results = await asyncio.gather(
            mcp_server.client.get_user_profile(user_id),
            mcp_server.client.get_user_preferences(user_id),
            mcp_server.client.get_user_skills(user_id),
            mcp_server.client.get_user_patterns(user_id),
            mcp_server.client.get_user_interests(user_id),
            return_exceptions=True,
        )
    except ValueError as exc:
        return [TextContent(type="text", text=f"Error: {exc}")]
    except Exception:
        return [TextContent(type="text", text="Error fetching user profile: request failed")]

    profile = results[0] if not isinstance(results[0], BaseException) else None
    preferences = results[1] if not isinstance(results[1], BaseException) else []
    skills = results[2] if not isinstance(results[2], BaseException) else []
    patterns = results[3] if not isinstance(results[3], BaseException) else []
    interests = results[4] if not isinstance(results[4], BaseException) else []

    lines = [f"# User Profile: {user_id}\n"]

    if profile is not None:
        lines.append("## Profile")
        if profile.display_name:
            lines.append(f"- **Name**: {profile.display_name}")
        if profile.timezone:
            lines.append(f"- **Timezone**: {profile.timezone}")
        if profile.language:
            lines.append(f"- **Language**: {profile.language}")
        if profile.communication_style:
            lines.append(f"- **Communication Style**: {profile.communication_style}")
        if profile.technical_level:
            lines.append(f"- **Technical Level**: {profile.technical_level}")
        lines.append("")

    if preferences:
        lines.append("## Preferences")
        for pref in preferences:
            name = pref.get("name", "unknown")
            value = pref.get("value", "")
            lines.append(f"- **{name}**: {value}")
        lines.append("")

    if skills:
        lines.append("## Skills")
        for skill in skills:
            name = skill.get("name", "unknown")
            level = skill.get("level", "")
            lines.append(f"- **{name}** ({level})" if level else f"- **{name}**")
        lines.append("")

    if patterns:
        lines.append("## Behavioral Patterns")
        for pattern in patterns:
            name = pattern.get("name", "unknown")
            lines.append(f"- {name}")
        lines.append("")

    if interests:
        lines.append("## Interests")
        for interest in interests:
            name = interest.get("name", "unknown")
            lines.append(f"- {name}")
        lines.append("")

    text = "\n".join(lines)
    return [TextContent(type="text", text=text)]


async def _handle_entities(
    mcp_server: EngramMCPServer, arguments: dict[str, Any]
) -> list[TextContent]:
    """List entities via subgraph search.

    The server does not expose a list-all-entities endpoint, so we use
    the subgraph query with an entity-focused search.
    """
    try:
        limit = _safe_int(arguments.get("limit"), "limit", 20, 1, MAX_NODES_LIMIT)
    except ValueError as exc:
        return [TextContent(type="text", text=f"Error: {exc}")]

    entity_type = arguments.get("entity_type")
    if entity_type is not None:
        try:
            entity_type = _validate_entity_type(entity_type)
        except ValueError as exc:
            return [TextContent(type="text", text=f"Error: {exc}")]

    query_text = f"entities type:{entity_type}" if entity_type else "entities"
    subgraph_query = SubgraphQuery(
        query=query_text,
        session_id=mcp_server.session_id,
        agent_id=mcp_server.agent_id,
        max_nodes=limit,
        intent="related",
    )

    try:
        response = await mcp_server.client.query_subgraph(subgraph_query)
    except Exception:
        return [TextContent(type="text", text="Error listing entities: request failed")]

    lines = ["# Entities\n"]
    entity_count = 0
    for node_id, node in response.nodes.items():
        if node.node_type == "Entity":
            entity_count += 1
            name = node.attributes.get("name", node_id)
            etype = node.attributes.get("entity_type", "unknown")
            lines.append(f"- **{name}** (type: {etype}, id: {node_id})")

    if entity_count == 0:
        lines.append("No entities found. Try using `engram_search` with a specific query.")

    lines.append(f"\n*{entity_count} entities returned*")
    text = "\n".join(lines)
    return [TextContent(type="text", text=text)]


async def _handle_forget(
    mcp_server: EngramMCPServer, arguments: dict[str, Any]
) -> list[TextContent]:
    """GDPR data deletion for a user."""
    user_id = arguments["user_id"]
    if not user_id or not isinstance(user_id, str) or not user_id.strip():
        return [TextContent(type="text", text="Error: user_id must not be empty")]
    try:
        result = await mcp_server.client.delete_user(user_id)
    except ValueError as exc:
        return [TextContent(type="text", text=f"Error: {exc}")]
    except Exception:
        return [TextContent(type="text", text="Error deleting user data: request failed")]

    deleted_count = result.get("deleted_count", 0)
    text = (
        f"# GDPR Deletion Complete\n\n"
        f"- **User ID**: {user_id}\n"
        f"- **Deleted nodes**: {deleted_count}\n"
        f"- **Status**: All user data has been erased\n"
    )
    return [TextContent(type="text", text=text)]


# --- Formatting helpers ---


def _format_atlas_response(response: AtlasResponse, title: str) -> str:
    """Format an AtlasResponse as LLM-readable markdown text."""
    lines = [f"# {title}\n"]

    if not response.nodes:
        lines.append("No results found.\n")
        return "\n".join(lines)

    # Summary
    meta = response.meta
    lines.append(
        f"*{meta.nodes_returned} nodes, "
        f"query took {meta.query_ms}ms"
        f"{', truncated' if meta.truncated else ''}*\n"
    )

    # Inferred intents
    if meta.inferred_intents:
        intent_parts = [f"{k}: {v:.1f}" for k, v in meta.inferred_intents.items()]
        lines.append(f"**Intents**: {', '.join(intent_parts)}\n")

    # Nodes grouped by type
    nodes_by_type: dict[str, list[tuple[str, Any]]] = {}
    for node_id, node in response.nodes.items():
        nodes_by_type.setdefault(node.node_type, []).append((node_id, node))

    for node_type, nodes in nodes_by_type.items():
        lines.append(f"## {node_type}s ({len(nodes)})\n")
        for node_id, node in nodes:
            score_text = ""
            if node.scores.relevance_score > 0 or node.scores.decay_score > 0:
                score_text = (
                    f" [relevance={node.scores.relevance_score:.2f}, "
                    f"decay={node.scores.decay_score:.2f}]"
                )

            payload = node.attributes.get("payload_ref", "")
            if payload:
                display = payload[:120] + ("..." if len(payload) > 120 else "")
                lines.append(f"- **{node_id}**{score_text}: {display}")
            else:
                name = node.attributes.get("name", node_id)
                lines.append(f"- **{name}** ({node_id}){score_text}")

            if node.provenance:
                lines.append(
                    f"  - Source: session={node.provenance.session_id}, "
                    f"agent={node.provenance.agent_id}"
                )
        lines.append("")

    # Edges summary
    if response.edges:
        lines.append(f"## Relationships ({len(response.edges)})\n")
        for edge in response.edges[:20]:
            lines.append(f"- {edge.source} --[{edge.edge_type}]--> {edge.target}")
        if len(response.edges) > 20:
            lines.append(f"  ... and {len(response.edges) - 20} more")
        lines.append("")

    # Pagination
    if response.pagination.has_more:
        lines.append(f"*More results available (cursor: {response.pagination.cursor})*\n")

    return "\n".join(lines)
