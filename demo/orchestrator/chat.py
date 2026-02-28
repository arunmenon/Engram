import logging
import uuid
from datetime import datetime, timezone

from .context_client import ContextGraphClient
from .llm import chat_completion
from .models import ChatResponse
from .scenarios import get_scenario

logger = logging.getLogger(__name__)

cg_client = ContextGraphClient()


def build_event(
    event_type: str,
    session_id: str,
    agent_id: str,
    payload: dict,
    parent_event_id: str | None = None,
) -> dict:
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "agent_id": agent_id,
        "trace_id": str(uuid.uuid4()),
        "payload_ref": f"inline:{event_type}",
        "payload": payload,
        "parent_event_id": parent_event_id,
    }


async def handle_chat(
    session_id: str,
    user_message: str,
    scenario_id: str,
    conversation_history: list[dict] | None = None,
) -> ChatResponse:
    scenario = get_scenario(scenario_id)
    if not scenario:
        return ChatResponse(
            agent_message="Unknown scenario", context_used=0, events_ingested=0
        )

    # 1. Ingest user event
    user_event = build_event(
        "observation.input",
        session_id,
        scenario["persona"]["name"],
        {"content": user_message, "role": "user"},
    )
    try:
        await cg_client.ingest_event(user_event)
    except Exception:
        logger.warning("Failed to ingest user event to CG API", exc_info=True)

    # 2. Query context
    atlas = {}
    try:
        atlas = await cg_client.get_session_context(
            session_id, query=user_message
        )
    except Exception:
        logger.warning("Failed to fetch session context from CG API", exc_info=True)

    # 3. Build messages for LLM
    context_text = ""
    node_count = 0
    intents = {}
    if atlas and "nodes" in atlas:
        node_count = len(atlas["nodes"])
        intents = atlas.get("meta", {}).get("inferred_intents", {})
        context_text = format_context(atlas)

    messages = [
        {"role": "system", "content": scenario["agent_system_prompt"]},
    ]
    if context_text:
        messages.append(
            {
                "role": "system",
                "content": f"Relevant context from the knowledge graph:\n{context_text}",
            }
        )
    if conversation_history:
        messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})

    # 4. Call LLM
    try:
        agent_reply = await chat_completion(messages)
    except Exception as e:
        agent_reply = (
            f"I'm having trouble connecting to the AI service. Error: {e!s}"
        )

    # 5. Ingest agent event
    agent_event = build_event(
        "agent.invoke",
        session_id,
        "support-agent",
        {"content": agent_reply, "role": "agent"},
        parent_event_id=user_event["event_id"],
    )
    try:
        await cg_client.ingest_event(agent_event)
    except Exception:
        logger.warning("Failed to ingest agent event to CG API", exc_info=True)

    return ChatResponse(
        agent_message=agent_reply,
        context_used=node_count,
        events_ingested=2,
        inferred_intents=intents,
    )


def format_context(atlas: dict) -> str:
    lines = []
    for node_id, node in atlas.get("nodes", {}).items():
        attrs = node.get("attributes", {})
        lines.append(
            f"- [{node.get('node_type')}] {attrs.get('label', node_id)}: {attrs}"
        )
    return "\n".join(lines[:20])
