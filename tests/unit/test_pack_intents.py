"""Intents, weights and seed strategies from the registry (ADR-0018 phase 2)."""

from __future__ import annotations

import pytest

from context_graph.domain.intent import classify_intent, get_edge_weights, select_seed_strategy
from context_graph.domain.pack_intents import RegistryIntents
from context_graph.ontology import load_registry
from context_graph.settings import INTENT_WEIGHTS

QUERIES = [
    "why did the build fail because of the timeout",
    "when was it deployed, before or after the release",
    "who is the author of this change",
    "how does the workflow process run",
    "what do I prefer for my style",
    "describe what happened",
    "similar related events compared",
    "an unrelated sentence",
    "",
]


@pytest.mark.parametrize("query", QUERIES)
def test_base_packs_equal_todays_tables(query: str) -> None:
    intents = RegistryIntents.for_events(load_registry([]))
    fixed = {str(k): v for k, v in classify_intent(query).items()}
    assert intents.classify(query) == fixed
    weights = {
        str(k): v for k, v in get_edge_weights(classify_intent(query), INTENT_WEIGHTS).items()
    }
    assert intents.edge_weights(fixed) == weights
    assert intents.seed_strategy(fixed) == select_seed_strategy(classify_intent(query))


def test_pdlc_adds_artifact_intents_without_changing_event_intents() -> None:
    registry = load_registry(["pdlc"])
    events = RegistryIntents.for_events(registry)
    artifacts = RegistryIntents.for_artifacts(registry)
    assert events.names == [
        "why", "when", "what", "related", "general", "who_is", "how_does", "personalize"
    ]  # fmt: skip
    assert artifacts.names == [
        "why",
        "who_is",
        "trace",
        "completeness",
        "status",
        "impact",
        "preflight",
    ]
    assert events.classify("why did it fail") == {"why": 1.0}
    assert events.edge_weights({"why": 1.0})["IMPLEMENTS"] == 4  # PDLC's addition to why
    assert artifacts.classify("which requirements have no tests") == {"completeness": 1.0}
    assert artifacts.classify("nothing matches here") == {}


async def test_engine_takes_intents_from_the_registry() -> None:
    from unittest.mock import AsyncMock

    from context_graph.domain.models import SubgraphQuery
    from context_graph.retrieval.engine import RetrievalEngine
    from context_graph.settings import DecaySettings

    reads = AsyncMock()
    reads.seed_events.return_value = []
    engine = RetrievalEngine(
        reads, decay=DecaySettings(), intents=RegistryIntents.for_events(load_registry(["pdlc"]))
    )
    response = await engine.get_subgraph(
        SubgraphQuery(query="why did it fail", session_id="s", agent_id="a")
    )
    assert response.meta.inferred_intents == {"why": 1.0}
    assert response.meta.seed_strategy == "causal_roots"
