"""The built-in packs restate today's schema exactly (ADR-0018 phase 0 exit checks).

``core``, ``memory`` and ``user`` must equal the enums and node models in
``domain/models.py``, the intent tables in ``settings.py`` and
``domain/intent.py``, and ``docker/neo4j/constraints.cypher``. The PDLC
pack must load on top of them.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from context_graph.adapters.neo4j.ontology_schema import schema_statements
from context_graph.domain import intent as intent_module
from context_graph.domain import models
from context_graph.ontology import BUILTIN_PACK_DIR, load_registry
from context_graph.settings import INTENT_WEIGHTS, OTEL_TO_EVENT_TYPE, Settings

if TYPE_CHECKING:
    from context_graph.domain.ontology import OntologyRegistry

REPO = Path(__file__).resolve().parents[2]

NODE_MODELS = {
    "Event": models.EventNode,
    "Entity": models.EntityNode,
    "Summary": models.SummaryNode,
    "UserProfile": models.UserProfileNode,
    "Preference": models.PreferenceNode,
    "Skill": models.SkillNode,
    "Workflow": models.WorkflowNode,
    "BehavioralPattern": models.BehavioralPatternNode,
    "Belief": models.BeliefNode,
    "Goal": models.GoalNode,
    "Episode": models.EpisodeNode,
}


@pytest.fixture(scope="module")
def registry() -> OntologyRegistry:
    """The base packs alone: today's schema."""
    return load_registry([])


def test_configured_packs() -> None:
    configured = load_registry(Settings().ontology.packs)
    assert [pack.name for pack in configured.packs] == ["core", "memory", "user", "pdlc"]


class TestTodaysSchema:
    def test_base_packs(self, registry: OntologyRegistry) -> None:
        assert [pack.name for pack in registry.packs] == ["core", "memory", "user"]

    def test_node_types_equal_the_enum(self, registry: OntologyRegistry) -> None:
        assert set(registry.node_types) == {t.value for t in models.NodeType}

    def test_edge_types_equal_the_enum(self, registry: OntologyRegistry) -> None:
        assert set(registry.edge_types) == {t.value for t in models.EdgeType}

    def test_event_types_equal_the_enum(self, registry: OntologyRegistry) -> None:
        assert set(registry.event_types) == {t.value for t in models.EventType}

    def test_otel_aliases_equal_the_mapping(self, registry: OntologyRegistry) -> None:
        aliases = {
            declared.definition.aliases["otel"]: name
            for name, declared in registry.event_types.items()
            if "otel" in declared.definition.aliases
        }
        assert aliases == OTEL_TO_EVENT_TYPE

    def test_intents_equal_the_enum(self, registry: OntologyRegistry) -> None:
        assert set(registry.intents) == {t.value for t in models.IntentType}
        assert registry.fallback_intent == models.IntentType.GENERAL

    @pytest.mark.parametrize("type_name", sorted(NODE_MODELS))
    def test_properties_equal_the_node_model(
        self, registry: OntologyRegistry, type_name: str
    ) -> None:
        assert set(registry.node_type(type_name).properties) == set(
            NODE_MODELS[type_name].model_fields
        )

    def test_entity_types_equal_the_enum(self, registry: OntologyRegistry) -> None:
        spec = registry.node_type("Entity").properties["entity_type"]
        assert spec.enum == [t.value for t in models.EntityType]  # type: ignore[union-attr]

    def test_intent_weights_equal_settings(self, registry: OntologyRegistry) -> None:
        expected = {
            str(intent): {str(edge): weight for edge, weight in weights.items()}
            for intent, weights in INTENT_WEIGHTS.items()
        }
        assert registry.intent_weights() == expected

    def test_intent_keywords_and_seeds_equal_the_classifier(
        self, registry: OntologyRegistry
    ) -> None:
        keywords = {str(k): v for k, v in intent_module._INTENT_KEYWORDS.items()}
        seeds = {str(k): v for k, v in intent_module._SEED_STRATEGIES.items()}
        assert registry.intent_keywords() == keywords
        assert registry.seed_strategies() == seeds

    def test_edge_endpoints(self, registry: OntologyRegistry) -> None:
        def endpoints(name: str) -> tuple[set[str], set[str]]:
            edge = registry.edge_type(name)
            return edge.from_types, edge.to_types

        assert endpoints("FOLLOWS") == ({"Event"}, {"Event"})
        assert endpoints("REFERENCES") == ({"Event"}, {"Entity"})
        assert endpoints("SUMMARIZES") == ({"Summary"}, {"Event", "Summary"})
        assert endpoints("SUPERSEDES") == ({"Belief"}, {"Belief"})
        assert endpoints("CONTAINS") == ({"Episode"}, {"Event"})
        assert endpoints("DERIVED_FROM") == (
            {"Preference", "BehavioralPattern", "Skill", "Workflow"},
            {"Event"},
        )
        assert endpoints("HAS_PROFILE") == ({"Entity"}, {"UserProfile"})


def _normalise(statement: str) -> str:
    """One statement, whitespace collapsed and the node variable renamed to ``n``."""
    text = " ".join(statement.split()).rstrip(";")
    text = text.replace("{ ", "{").replace(" }", "}")
    variable = re.search(r"FOR \((\w+):", text)
    if variable:
        text = re.sub(rf"\b{variable.group(1)}\b(?=[.:])", "n", text)
    return text


def _cypher_file_statements() -> set[str]:
    text = (REPO / "docker" / "neo4j" / "constraints.cypher").read_text()
    body = "\n".join(line for line in text.splitlines() if not line.strip().startswith("//"))
    return {_normalise(s) for s in body.split(";") if s.strip()}


def test_generated_neo4j_schema_equals_constraints_file(registry: OntologyRegistry) -> None:
    generated = {_normalise(s) for s in schema_statements(registry, embedding_dimensions=384)}
    # The recorded-ontology node's constraint is generated only (the file is frozen)
    state = _normalise(
        "CREATE CONSTRAINT ontologystate_pk IF NOT EXISTS FOR (n:OntologyState) "
        "REQUIRE n.node_id IS UNIQUE"
    )
    assert state in generated
    assert generated - {state} == _cypher_file_statements()


class TestPdlcPack:
    def test_loads_with_its_requirements(self) -> None:
        registry = load_registry(["pdlc"])
        assert [pack.name for pack in registry.packs] == ["core", "memory", "user", "pdlc"]
        assert registry.pack("pdlc").version == "1.6.0"
        # 16 in the design note; Release was added by the real-project mapping (v0.4)
        assert len([t for t in registry.node_types.values() if t.pack == "pdlc"]) == 17
        assert set(registry.rules_for("pdlc.change.merged")[0][1].model_dump()) >= {"event"}

    def test_pdlc_types_are_identified_by_node_id(self) -> None:
        registry = load_registry(["pdlc"])
        statements = schema_statements(registry, embedding_dimensions=384)
        assert (
            "CREATE CONSTRAINT change_pk IF NOT EXISTS FOR (n:Change) REQUIRE n.node_id IS UNIQUE"
        ) in statements

    def test_docs_copy_is_identical(self) -> None:
        packaged = (BUILTIN_PACK_DIR / "pdlc.pack.yaml").read_text()
        documented = (REPO / "docs/research/2026-10/ontology/pdlc.pack.yaml").read_text()
        assert packaged == documented

    def test_all_packs_together(self) -> None:
        registry = load_registry(["memory", "user", "pdlc"])
        supersedes = registry.edge_type("SUPERSEDES")
        assert {"Belief", "Decision", "Spec", "DesignElement"} <= supersedes.from_types
        assert registry.intent_weights()["why"]["IMPLEMENTS"] == 4
        assert registry.intent_weights()["why"]["CAUSED_BY"] == 5.0
