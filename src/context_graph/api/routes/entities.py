"""Entity endpoint.

GET /v1/entities/{entity_id} — retrieve an entity and its connected events.

Source: ADR-0009, ADR-0011
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from context_graph.api.dependencies import get_graph_store
from context_graph.ports.graph_store import GraphStore  # noqa: TCH001 — runtime: Depends()

router = APIRouter(tags=["entities"])

GraphStoreDep = Annotated[GraphStore, Depends(get_graph_store)]


@router.get("/entities/{entity_id}")
async def get_entity(
    entity_id: str,
    graph_store: GraphStoreDep,
) -> dict[str, Any]:
    """Retrieve an entity and its connected events."""
    result = await graph_store.get_entity(entity_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return result
