"""Simulate endpoint — stateless LLM proxy for dynamic two-agent conversations.

Receives a persona spec + conversation history, streams the LLM response
back as SSE tokens. Completely stateless — the frontend manages turn-taking.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Literal

import litellm
import orjson
import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/simulate", tags=["simulate"])


class PersonaSpec(BaseModel):
    """Persona definition for a simulated agent."""

    name: str = Field(..., max_length=100)
    role: Literal["customer", "support"]
    system_prompt: str = Field(..., max_length=4000)
    model_id: str | None = None
    temperature: float | None = None


class ConversationMessage(BaseModel):
    """A single message in the conversation history."""

    role: Literal["user", "assistant", "system"]
    content: str = Field(..., max_length=8000)


class SimulateTurnRequest(BaseModel):
    """Request body for a single conversation turn."""

    persona: PersonaSpec
    conversation_history: list[ConversationMessage] = Field(default_factory=list, max_length=100)
    session_context: str | None = None
    max_tokens: int = Field(default=512, ge=50, le=2048)
    stream: bool = True


class TurnResult(BaseModel):
    """Non-streaming response for a completed turn."""

    content: str
    turn_id: str
    model_id: str
    tokens_used: int


@router.post("/turn")
async def simulate_turn(
    body: SimulateTurnRequest, request: Request
) -> TurnResult | JSONResponse | EventSourceResponse:
    """Generate a single conversation turn via LLM.

    Streams SSE tokens when stream=True, returns JSON otherwise.
    Uses litellm.acompletion for model-agnostic LLM access.
    """
    settings = request.app.state.settings.simulation
    model_id = body.persona.model_id or settings.default_model_id
    temperature = (
        body.persona.temperature
        if body.persona.temperature is not None
        else settings.default_temperature
    )

    # Validate model
    if model_id not in settings.allowed_models:
        return JSONResponse(
            status_code=422,
            content={
                "detail": f"Model '{model_id}' not allowed. Allowed: {settings.allowed_models}"
            },
        )

    # Build messages for the LLM
    messages = _build_messages(body)
    turn_id = str(uuid.uuid4())

    logger.info(
        "simulate_turn_start",
        persona=body.persona.name,
        role=body.persona.role,
        model=model_id,
        history_len=len(body.conversation_history),
        stream=body.stream,
    )

    if body.stream:
        return EventSourceResponse(
            _stream_response(messages, model_id, temperature, body.max_tokens, turn_id),
            media_type="text/event-stream",
        )

    # Non-streaming response
    try:
        response = await litellm.acompletion(
            model=model_id,
            messages=messages,
            temperature=temperature,
            max_tokens=body.max_tokens,
            stream=False,
        )
        content = response.choices[0].message.content or ""
        tokens_used = response.usage.completion_tokens if response.usage else 0

        logger.info(
            "simulate_turn_complete",
            turn_id=turn_id,
            tokens=tokens_used,
        )

        return TurnResult(
            content=content,
            turn_id=turn_id,
            model_id=model_id,
            tokens_used=tokens_used,
        )
    except Exception as exc:
        logger.error("simulate_turn_error", error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal error generating response"},
        )


def _build_messages(body: SimulateTurnRequest) -> list[dict[str, Any]]:
    """Build the LLM message array from persona + history."""
    messages: list[dict[str, Any]] = [{"role": "system", "content": body.persona.system_prompt}]

    # Add session context as a system message on first turn
    if body.session_context and not body.conversation_history:
        messages.append(
            {
                "role": "system",
                "content": f"Topic: {body.session_context}. Begin the conversation naturally.",
            }
        )

    # Add conversation history
    for msg in body.conversation_history:
        messages.append({"role": msg.role, "content": msg.content})

    # Truncate history to prevent exceeding model context limits.
    # Keep system messages + last N conversation turns.
    max_history_messages = 40  # ~20 turns of back-and-forth
    system_msgs = [m for m in messages if m["role"] == "system"]
    conv_msgs = [m for m in messages if m["role"] != "system"]
    if len(conv_msgs) > max_history_messages:
        conv_msgs = conv_msgs[-max_history_messages:]
    messages = system_msgs + conv_msgs

    return messages


async def _stream_response(
    messages: list[dict[str, Any]],
    model_id: str,
    temperature: float,
    max_tokens: int,
    turn_id: str,
) -> AsyncGenerator[dict[str, str], None]:
    """Stream LLM response as SSE events."""
    full_content = ""
    token_index = 0
    tokens_used = 0

    try:
        response = await litellm.acompletion(
            model=model_id,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                content = delta.content
                full_content += content
                yield {
                    "event": "token",
                    "data": orjson.dumps({"content": content, "index": token_index}).decode(),
                }
                token_index += 1

            # Track usage if provided in final chunk
            if hasattr(chunk, "usage") and chunk.usage:
                tokens_used = chunk.usage.completion_tokens or token_index

        # Send done event
        if not tokens_used:
            tokens_used = token_index

        yield {
            "event": "done",
            "data": orjson.dumps(
                {
                    "content": full_content,
                    "turn_id": turn_id,
                    "model_id": model_id,
                    "tokens_used": tokens_used,
                }
            ).decode(),
        }

        logger.info(
            "simulate_turn_stream_complete",
            turn_id=turn_id,
            tokens=tokens_used,
        )

    except Exception as exc:
        logger.error("simulate_turn_stream_error", error=str(exc))
        yield {
            "event": "error",
            "data": orjson.dumps({"error": "Internal error generating response"}).decode(),
        }
