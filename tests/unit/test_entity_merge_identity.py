"""A repeated name observation cannot rewrite the existing Entity's origin."""

from datetime import UTC, datetime, timedelta

import pytest

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.domain.models import EntityNode


@pytest.mark.asyncio
async def test_reobservation_preserves_first_seen_type_and_accumulated_mentions():
    graph = MemoryGraphStore()
    first = datetime(2026, 10, 15, tzinfo=UTC)
    original = EntityNode(
        entity_id="entity:Rust",
        name="Rust",
        entity_type="tool",
        first_seen=first,
        last_seen=first,
        mention_count=8,
    )
    await graph.merge_entity_node(original)
    later = first + timedelta(days=1)
    await graph.merge_entity_node(
        original.model_copy(
            update={
                "first_seen": later,
                "last_seen": later,
                "entity_type": "concept",
                "mention_count": 1,
            }
        )
    )
    stored = graph.nodes[("Entity", "entity:Rust")]
    assert stored["first_seen"] == first.isoformat()
    assert stored["entity_type"] == "tool"
    assert stored["mention_count"] == 8
    assert stored["last_seen"] == later.isoformat()
