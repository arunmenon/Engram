"""LangChain callback handler that captures chain/tool/LLM events into Engram."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from engram.models import Event
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

if TYPE_CHECKING:
    from uuid import UUID

    from engram.client import EngramClient


class EngramCallbackHandler(BaseCallbackHandler):
    """LangChain callback handler that buffers events for Engram ingestion.

    Since LangChain callbacks are synchronous but the Engram client is async,
    events are buffered in memory and flushed via the async ``flush()`` method.
    """

    def __init__(
        self,
        client: EngramClient,
        session_id: str,
        agent_id: str,
        *,
        trace_id: str | None = None,
    ) -> None:
        super().__init__()
        self.client = client
        self.session_id = session_id
        self.agent_id = agent_id
        self.trace_id = trace_id or str(uuid.uuid4())
        self._buffer: list[Event] = []

    @property
    def buffered_events(self) -> list[Event]:
        """Return a copy of the current event buffer."""
        return list(self._buffer)

    def _create_event(
        self,
        event_type: str,
        payload_ref: str,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tool_name: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Event:
        """Build an Engram Event and append it to the buffer."""
        parent_event_id = parent_run_id if parent_run_id else None
        event = Event(
            event_id=run_id,
            event_type=event_type,
            occurred_at=datetime.now(UTC),
            session_id=self.session_id,
            agent_id=self.agent_id,
            trace_id=self.trace_id,
            payload_ref=payload_ref,
            parent_event_id=parent_event_id,
            tool_name=tool_name,
            payload=payload,
        )
        self._buffer.append(event)
        return event

    # -- Chain callbacks --

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        chain_name = serialized.get("name") or serialized.get("id", ["unknown"])[-1]
        self._create_event(
            event_type="agent.invoke",
            payload_ref=f"Chain started: {chain_name}",
            run_id=run_id,
            parent_run_id=parent_run_id,
            payload={"chain_name": chain_name, "inputs": _safe_truncate(inputs)},
        )

    # -- Tool callbacks --

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        tool_name = serialized.get("name", "unknown_tool")
        self._create_event(
            event_type="tool.execute",
            payload_ref=f"Tool started: {tool_name}",
            run_id=run_id,
            parent_run_id=parent_run_id,
            tool_name=tool_name,
            payload={"input": _safe_truncate(input_str)},
        )

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        self._create_event(
            event_type="tool.result",
            payload_ref="Tool completed",
            run_id=uuid.uuid4(),
            parent_run_id=run_id,
            payload={"output": _safe_truncate(output)},
        )

    # -- LLM callbacks --

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        model_name = serialized.get("name") or serialized.get("id", ["unknown"])[-1]
        self._create_event(
            event_type="llm.invoke",
            payload_ref=f"LLM started: {model_name}",
            run_id=run_id,
            parent_run_id=parent_run_id,
            payload={
                "model": model_name,
                "prompt_count": len(prompts),
            },
        )

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        generation_count = sum(len(g) for g in response.generations)
        self._create_event(
            event_type="llm.result",
            payload_ref=f"LLM completed ({generation_count} generations)",
            run_id=uuid.uuid4(),
            parent_run_id=run_id,
            payload={"generation_count": generation_count},
        )

    # -- Flush --

    async def flush(self) -> int:
        """Send all buffered events to Engram. Returns the number of events flushed."""
        if not self._buffer:
            return 0
        events = self._buffer
        self._buffer = []
        await self.client.ingest_batch(events)
        return len(events)


def _safe_truncate(value: Any, max_length: int = 2000) -> Any:
    """Truncate large string values to avoid oversized payloads."""
    if isinstance(value, str) and len(value) > max_length:
        return value[:max_length] + "...[truncated]"
    if isinstance(value, dict):
        return {k: _safe_truncate(v, max_length) for k, v in value.items()}
    return value
