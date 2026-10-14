"""Core Entity resolution must retain stored IDs through public worker/graph seams."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.adapters.memory.log import MemoryEventLog
from context_graph.adapters.memory.subscription import MemorySubscription
from context_graph.domain.models import Event
from context_graph.domain.projection import event_to_node
from context_graph.ports.pack_graph import NodeRef
from context_graph.settings import OntologySettings, Settings
from context_graph.worker.extraction import ExtractionConsumer


class Provider:
    def __init__(self, first, second):
        self.names = iter([first, second])

    async def extract_from_session(self, **kwargs):
        name = next(self.names)
        return {
            "entities": [
                {"name": name, "entity_type": "tool", "confidence": 1.0, "source_quote": name}
            ]
        }


@pytest.mark.parametrize("user", [False, True])
@pytest.mark.parametrize("first,second", [("ResetToken", "ResetToken"), ("JavaScript", "JS")])
async def test_repeated_entity_resolution_retains_id_and_all_session_references(
    user, first, second
):
    graph, ledger = MemoryGraphStore(), MemoryEventLog()
    settings = Settings(ontology=OntologySettings(builtin_packs=["user"] if user else []))
    subscription = MemorySubscription(ledger.stream, "extraction", "identity-test")
    await subscription.ensure_group()
    worker = ExtractionConsumer(
        subscription, ledger, Provider(first, second), settings, graph_store=graph, user_store=graph
    )
    ids = []
    for index, (kind, name) in enumerate(
        [
            ("observation.input", first),
            ("system.session_end", ""),
            ("observation.input", second),
            ("system.session_end", ""),
        ]
    ):
        event = Event(
            event_id=UUID(int=9000 + index),
            event_type=kind,
            occurred_at=datetime(2026, 10, 14, tzinfo=UTC) + timedelta(seconds=index),
            session_id="identity-session",
            agent_id="alice",
            trace_id="identity",
            payload_ref="identity:" + str(index),
        )
        position = await ledger.append(event, {"content": name} if name else {})
        await graph.merge_event_node(
            event_to_node(event.model_copy(update={"global_position": position}))
        )
        ids.append(str(event.event_id))
        if kind == "system.session_end":
            await worker.process_message(position, {"event_id": str(event.event_id)})
    entity = NodeRef("Entity", "entity:" + first, "entity_id")
    assert entity in await graph.get_nodes([entity])
    links = await graph.neighbors([entity], ["REFERENCES"], "in", 20)
    assert {row["source_key"] for row in links} == set(ids)
    entities = await graph.get_entities()
    assert {e["entity_id"] for e in entities if e["entity_type"] == "tool"} == {entity.key}


@pytest.mark.parametrize("tier", ["exact", "same-name-other-type", "fuzzy", "semantic"])
def test_resolution_keeps_authoritative_storage_id_instead_of_reconstructing_name(tier):
    from context_graph.domain.entity_resolution import (
        SemanticCandidate,
        resolve_close_match,
        resolve_exact_match,
        resolve_semantic_match,
    )

    stored = {"name": "ResetToken", "entity_type": "tool", "entity_id": "entity:stable-key"}
    if tier == "exact":
        result = resolve_exact_match("resettoken", "tool", [stored])
    elif tier == "same-name-other-type":
        result = resolve_exact_match("resettoken", "concept", [stored])
    elif tier == "fuzzy":
        result = resolve_close_match("ResetTokens", "tool", [stored])
    else:
        result = resolve_semantic_match(
            "expiry", "tool", [SemanticCandidate("ResetToken", "tool", "entity:stable-key", 0.95)]
        )
    assert result is not None
    assert result.canonical_entity_id == "entity:stable-key"


@pytest.mark.parametrize("matched_id", [None, "", 42])
@pytest.mark.parametrize("name", ["ResetToken", "ResetTokens"])
async def test_worker_rejects_matched_candidate_without_valid_storage_identity(matched_id, name):
    from unittest.mock import AsyncMock

    graph, ledger = MemoryGraphStore(), MemoryEventLog()
    now = datetime(2026, 10, 14, tzinfo=UTC).isoformat()
    await graph.merge_entity_node_raw(
        entity_id="entity:stable",
        name="ResetToken",
        entity_type="tool",
        first_seen=now,
        last_seen=now,
        mention_count=1,
    )

    class InvalidCandidateStore:
        """Invalid external storage result; all graph writes still delegate to the real port."""

        def __getattr__(self, attribute):
            return getattr(graph, attribute)

        async def get_entities(self, limit=1000):
            return [dict(row, entity_id=matched_id) for row in await graph.get_entities(limit)]

    provider = AsyncMock()
    provider.extract_from_session.return_value = {
        "entities": [{"name": name, "entity_type": "tool", "confidence": 1.0, "source_quote": name}]
    }
    event = Event(
        event_id=UUID(int=9100),
        event_type="system.session_end",
        occurred_at=datetime(2026, 10, 14, tzinfo=UTC),
        session_id="bad-id",
        agent_id="alice",
        trace_id="t",
        payload_ref="bad-id",
    )
    position = await ledger.append(event, {"content": name})
    await graph.merge_event_node(
        event_to_node(event.model_copy(update={"global_position": position}))
    )
    subscription = MemorySubscription(ledger.stream, "extraction", "bad-id")
    await subscription.ensure_group()
    worker = ExtractionConsumer(
        subscription,
        ledger,
        provider,
        Settings(ontology=OntologySettings(builtin_packs=[])),
        graph_store=InvalidCandidateStore(),
    )
    with pytest.raises(ValueError, match="storage identity"):
        await worker.process_message(position, {"event_id": str(event.event_id)})
    assert {row["entity_id"] for row in await graph.get_entities()} == {"entity:stable"}
    assert (
        await graph.neighbors(
            [NodeRef("Event", str(event.event_id), "event_id")], ["REFERENCES"], "out", 10
        )
        == []
    )
