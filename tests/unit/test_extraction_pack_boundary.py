"""Optional user extraction must not disable core entities or request profiles."""

import json
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from context_graph.adapters.llm.client import LLMExtractionClient
from context_graph.settings import OntologySettings, Settings
from context_graph.worker import __main__ as runner
from context_graph.worker.extraction import ExtractionConsumer
from tests.fixtures.events import make_event


async def test_entity_only_client_controls_both_prompts_and_discards_user_output(monkeypatch):
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=json.dumps(
                        {
                            "entities": [
                                {
                                    "name": "Python",
                                    "entity_type": "tool",
                                    "confidence": 0.9,
                                    "source_quote": "We use Python for services",
                                }
                            ],
                            "persona": {
                                "name": "Unwanted",
                                "source_quote": "We use Python for services",
                            },
                            "preferences": [{"malformed": "must not parse"}],
                            "skills": [{"malformed": "must not parse"}],
                            "interests": [{"malformed": "must not parse"}],
                        }
                    )
                )
            )
        ]
    )
    call = AsyncMock(return_value=response)
    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(acompletion=call))
    event = make_event()
    result = await LLMExtractionClient(include_user=False).extract_from_session(
        [event],
        event.session_id,
        event.agent_id,
        [{"event_id": str(event.event_id), "payload": {"content": "We use Python for services"}}],
    )
    assert result["entities"][0]["name"] == "Python"
    assert result["persona"] is None
    assert result["preferences"] == result["skills"] == result["interests"] == []
    for message in call.call_args.kwargs["messages"]:
        assert "persona" not in message["content"]
        assert "preferences" not in message["content"]
        assert "entities" in message["content"].lower()


@pytest.mark.parametrize("builtins", [[], ["memory"]])
async def test_consumer_drops_unsolicited_user_results_but_writes_core_entities(builtins):
    graph, user = AsyncMock(), AsyncMock()
    graph.get_entities.return_value = []
    settings = Settings(ontology=OntologySettings(packs=["pdlc"], builtin_packs=builtins))
    consumer = ExtractionConsumer(
        subscription=AsyncMock(),
        event_log=AsyncMock(),
        llm_client=AsyncMock(),
        settings=settings,
        graph_store=graph,
        user_store=user,
    )
    await consumer._write_extraction_results(
        "session",
        "agent",
        {
            "entities": [{"name": "Python", "entity_type": "tool"}],
            "persona": {"name": "Unwanted"},
            "preferences": [{"key": "unwanted"}],
            "skills": [{"name": "unwanted"}],
            "interests": [{"entity_name": "unwanted"}],
        },
        ["event"],
    )
    graph.merge_entity_node_raw.assert_awaited_once()
    entity = graph.merge_entity_node_raw.call_args.kwargs
    assert entity["entity_id"] == "entity:Python" and entity["name"] == "Python"
    graph.merge_typed_edge.assert_awaited_once_with(
        source_id="event",
        target_id="entity:Python",
        edge_type="REFERENCES",
    )
    assert user.mock_calls == []


@pytest.mark.parametrize("builtins,enabled", [([], False), (["memory"], False), (["user"], True)])
async def test_factory_uses_same_capability_for_prompt_and_user_store(
    monkeypatch, builtins, enabled
):
    stores = SimpleNamespace(
        graph=AsyncMock(), event_log=AsyncMock(), subscription=lambda *_: AsyncMock()
    )
    monkeypatch.setattr(runner, "open_stores", AsyncMock(return_value=stores))
    monkeypatch.setattr(runner, "_open_embedding_service", lambda *_: None)
    settings = Settings(ontology=OntologySettings(packs=["pdlc"], builtin_packs=builtins))
    consumer, opened = await runner._build_consumer("extraction", settings)
    assert opened is stores
    assert consumer._llm_client._include_user is enabled
    assert (consumer._user_store is stores.graph) is enabled


async def test_invalid_composition_fails_before_opening_stores(monkeypatch):
    opened = AsyncMock()
    monkeypatch.setattr(runner, "open_stores", opened)
    settings = Settings(ontology=OntologySettings(packs=["nonexistent_pack"], builtin_packs=[]))
    with pytest.raises(Exception, match="nonexistent_pack"):
        await runner._build_consumer("extraction", settings)
    opened.assert_not_awaited()
