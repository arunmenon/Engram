"""Retrieval feedback endpoint.

POST /v1/feedback — submit feedback on retrieval quality

Stores feedback as a system event and adjusts importance scores
on helpful/irrelevant nodes.

Source: Product gap analysis — retrieval feedback loop
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import ORJSONResponse

from context_graph.api.dependencies import (
    TenantContext,
    get_event_store,
    get_graph_store,
    require_tenant,
)
from context_graph.domain.feedback import RetrievalFeedback  # noqa: TCH001 — runtime: Pydantic body
from context_graph.ports.event_store import EventStore  # noqa: TCH001 — runtime: Depends
from context_graph.ports.graph_store import GraphStore  # noqa: TCH001 — runtime: Depends

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])

EventStoreDep = Annotated[EventStore, Depends(get_event_store)]
GraphStoreDep = Annotated[GraphStore, Depends(get_graph_store)]
TenantDep = Annotated[TenantContext, Depends(require_tenant)]

# Importance adjustment constants
HELPFUL_IMPORTANCE_BUMP = 1
IRRELEVANT_IMPORTANCE_DECREMENT = 1
MIN_IMPORTANCE = 1
MAX_IMPORTANCE = 10


@router.post("")
async def submit_feedback(
    feedback: RetrievalFeedback,
    event_store: EventStoreDep,
    graph_store: GraphStoreDep,
    tenant: TenantDep,
) -> ORJSONResponse:
    """Submit retrieval feedback to adjust node importance scores.

    Bumps importance on helpful nodes and decrements on irrelevant ones.
    Also stores the feedback as a ``system.feedback`` event for audit.
    """
    from datetime import UTC, datetime

    from context_graph.domain.models import Event

    # Store feedback as an event for traceability
    feedback_event = Event.model_validate(
        {
            "event_id": str(uuid4()),
            "event_type": "system.feedback",
            "occurred_at": datetime.now(UTC).isoformat(),
            "session_id": feedback.session_id,
            "agent_id": "system",
            "trace_id": feedback.query_id,
            "payload_ref": f"feedback:{feedback.query_id}",
        },
        strict=False,
    )

    feedback_payload: dict[str, Any] = {
        "query_id": feedback.query_id,
        "helpful_node_ids": feedback.helpful_node_ids,
        "irrelevant_node_ids": feedback.irrelevant_node_ids,
    }

    global_position = await event_store.append(
        feedback_event,
        payload=feedback_payload,
        tenant_id=tenant.tenant_id,
    )

    # Adjust importance scores on the graph
    bumped = 0
    decremented = 0

    for node_id in feedback.helpful_node_ids:
        adjusted = await graph_store.adjust_node_importance(
            node_id=node_id,
            delta=HELPFUL_IMPORTANCE_BUMP,
            min_value=MIN_IMPORTANCE,
            max_value=MAX_IMPORTANCE,
            tenant_id=tenant.tenant_id,
        )
        if adjusted:
            bumped += 1

    for node_id in feedback.irrelevant_node_ids:
        adjusted = await graph_store.adjust_node_importance(
            node_id=node_id,
            delta=-IRRELEVANT_IMPORTANCE_DECREMENT,
            min_value=MIN_IMPORTANCE,
            max_value=MAX_IMPORTANCE,
            tenant_id=tenant.tenant_id,
        )
        if adjusted:
            decremented += 1

    logger.info(
        "feedback_submitted",
        query_id=feedback.query_id,
        session_id=feedback.session_id,
        helpful=len(feedback.helpful_node_ids),
        irrelevant=len(feedback.irrelevant_node_ids),
        bumped=bumped,
        decremented=decremented,
        global_position=global_position,
    )

    return ORJSONResponse(
        status_code=201,
        content={
            "query_id": feedback.query_id,
            "global_position": global_position,
            "bumped": bumped,
            "decremented": decremented,
        },
        headers={"X-Tenant-ID": tenant.tenant_id},
    )
