"""LangChain chat history backed by the Engram context graph."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

if TYPE_CHECKING:
    from engram.client import EngramClient

from engram.models import Event


class EngramChatMessageHistory(BaseChatMessageHistory):
    """Chat message history stored in Engram.

    Since Engram's API is async, the synchronous ``messages`` property raises
    ``NotImplementedError``. Use ``aget_messages()`` for async access.
    """

    def __init__(
        self,
        client: EngramClient,
        session_id: str,
        agent_id: str = "langchain",
        trace_id: str | None = None,
    ) -> None:
        self.client = client
        self.session_id = session_id
        self.agent_id = agent_id
        self.trace_id = trace_id or str(uuid.uuid4())

    @property
    def messages(self) -> list[BaseMessage]:
        """Sync access is not supported. Use ``aget_messages()`` instead."""
        raise NotImplementedError(
            "EngramChatMessageHistory requires async access. "
            "Use `await history.aget_messages()` instead."
        )

    async def aget_messages(self) -> list[BaseMessage]:
        """Retrieve chat messages from Engram for this session."""
        response = await self.client.get_context(self.session_id, max_nodes=1000, max_depth=1)
        messages: list[BaseMessage] = []
        sorted_nodes = sorted(
            response.nodes.values(),
            key=lambda n: (
                n.provenance.occurred_at if n.provenance else datetime.min.replace(tzinfo=UTC)
            ),
        )
        for node in sorted_nodes:
            message = _node_to_message(node)
            if message is not None:
                messages.append(message)
        return messages

    def add_message(self, message: BaseMessage) -> None:
        """Sync add is not supported. Use ``aadd_messages()`` instead."""
        raise NotImplementedError(
            "EngramChatMessageHistory requires async access. "
            "Use `await history.aadd_messages([message])` instead."
        )

    async def aadd_messages(self, messages: list[BaseMessage]) -> None:
        """Ingest chat messages into Engram as events."""
        events: list[Event] = []
        for message in messages:
            event_type = _message_type_to_event_type(message)
            content = message.content if isinstance(message.content, str) else str(message.content)
            event = Event(
                event_id=uuid.uuid4(),
                event_type=event_type,
                occurred_at=datetime.now(UTC),
                session_id=self.session_id,
                agent_id=self.agent_id,
                trace_id=self.trace_id,
                payload_ref=content,
                payload={"role": message.type, "content": content},
            )
            events.append(event)
        if events:
            await self.client.ingest_batch(events)

    async def aclear(self) -> None:
        """No-op: Engram events are immutable and cannot be cleared."""

    def clear(self) -> None:
        """No-op: Engram events are immutable and cannot be cleared."""


def _node_to_message(node: Any) -> BaseMessage | None:
    """Convert an AtlasNode to a LangChain message, or None if not a message."""
    attributes = node.attributes
    role = attributes.get("role")
    content = attributes.get("content") or attributes.get("payload_ref", "")

    if not content and not role:
        return None

    if role == "human" or node.node_type == "HumanMessage":
        return HumanMessage(content=content)
    if role == "ai" or node.node_type == "AIMessage":
        return AIMessage(content=content)
    if role == "system" or node.node_type == "SystemMessage":
        return SystemMessage(content=content)

    event_type = ""
    if node.provenance:
        event_type = getattr(node, "event_type", "")
    if not event_type:
        event_type = attributes.get("event_type", "")

    if "human" in event_type or "user" in event_type:
        return HumanMessage(content=content)
    if "ai" in event_type or "llm" in event_type or "agent" in event_type:
        return AIMessage(content=content)

    if content:
        return HumanMessage(content=content)
    return None


def _message_type_to_event_type(message: BaseMessage) -> str:
    """Map a LangChain message type to an Engram event type."""
    type_map = {
        "human": "chat.human",
        "ai": "chat.ai",
        "system": "chat.system",
        "function": "chat.function",
        "tool": "chat.tool",
    }
    return type_map.get(message.type, "chat.message")
