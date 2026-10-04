"""UserStore conformance suite (ADR-0012, ADR-0019 §5).

Pins the personalization round trips the extraction worker and the
users API rely on, including GDPR export and delete.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.conformance.graph_fixtures import event_node

if TYPE_CHECKING:
    from context_graph.ports.graph_backend import GraphBackend

USER = "user:alice"
DERIVATION = {"method": "llm_extraction", "session_id": "s1", "model_id": "m1"}


async def _seed_events(graph: GraphBackend) -> None:
    await graph.merge_event_nodes_batch([event_node("evt-1"), event_node("evt-2")])


class TestProfile:
    async def test_profile_round_trip(self, graph: GraphBackend) -> None:
        assert await graph.get_user_profile(USER) is None
        await graph.write_user_profile(
            {"user_id": USER, "display_name": "Alice", "timezone": "UTC"}
        )
        await graph.write_user_profile({"user_id": USER, "display_name": "Alice B"})

        profile = await graph.get_user_profile(USER)
        assert profile is not None
        assert profile["display_name"] == "Alice B"
        assert profile["user_id"] == USER
        assert "timezone" not in profile  # rewritten without it
        assert profile["created_at"] <= profile["updated_at"]


class TestPreferences:
    async def test_preferences_and_supersession(self, graph: GraphBackend) -> None:
        await _seed_events(graph)
        await graph.write_preference_with_edges(
            USER,
            {"preference_id": "pref-old", "key": "editor", "polarity": "positive"},
            ["evt-1"],
            DERIVATION,
        )
        await graph.write_preference_with_edges(
            USER,
            {"preference_id": "pref-new", "key": "editor", "about_entity": "vim"},
            ["evt-2", "missing-event"],
            DERIVATION,
        )
        await graph.set_preference_superseded("pref-old", "pref-new")

        active = await graph.get_user_preferences(USER)
        assert [p["preference_id"] for p in active] == ["pref-new"]
        everything = await graph.get_user_preferences(USER, active_only=False)
        assert {p["preference_id"] for p in everything} == {"pref-old", "pref-new"}
        assert everything[0]["preference_id"] == "pref-new"  # newest confirmation first

    async def test_reobservation_counts(self, graph: GraphBackend) -> None:
        for _ in range(2):
            await graph.write_preference_with_edges(
                USER, {"preference_id": "pref-1", "key": "tabs"}, [], DERIVATION
            )
        (preference,) = await graph.get_user_preferences(USER)
        assert preference["observation_count"] == 2
        assert preference["scope"] == "global"


class TestSkillsAndInterests:
    async def test_skills_sorted_by_name(self, graph: GraphBackend) -> None:
        await _seed_events(graph)
        for skill_id, name in (("s-py", "python"), ("s-go", "go")):
            await graph.write_skill_with_edges(
                USER, {"skill_id": skill_id, "name": name}, ["evt-1"], DERIVATION
            )
        assert [s["name"] for s in await graph.get_user_skills(USER)] == ["go", "python"]

    async def test_interests_by_weight(self, graph: GraphBackend) -> None:
        await graph.write_interest_edge(USER, "kafka", "tool", 0.4, "inferred")
        await graph.write_interest_edge(USER, "rust", "concept", 0.9, "stated")
        interests = await graph.get_user_interests(USER)
        assert [i["name"] for i in interests] == ["rust", "kafka"]
        assert interests[0]["entity_id"] == "entity:rust"
        assert interests[0]["source"] == "stated"

    async def test_derived_from_allowlist(self, graph: GraphBackend) -> None:
        with pytest.raises(ValueError, match="Unknown source_id_field"):
            await graph.write_derived_from_edge("x", "event_id", "evt-1", "manual", "s1")


class TestGdpr:
    async def test_export_includes_provenance(self, graph: GraphBackend) -> None:
        await _seed_events(graph)
        await graph.write_user_profile({"user_id": USER, "display_name": "Alice"})
        await graph.write_preference_with_edges(
            USER, {"preference_id": "pref-1", "key": "editor"}, ["evt-1"], DERIVATION
        )
        await graph.write_skill_with_edges(
            USER, {"skill_id": "skill-1", "name": "python"}, ["evt-2"], DERIVATION
        )
        await graph.write_interest_edge(USER, "rust", "concept", 0.9, "stated")

        export = await graph.export_user_data(USER)

        assert export["user_id"] == USER
        assert export["profile"]["display_name"] == "Alice"
        assert [p["preference_id"] for p in export["preferences"]] == ["pref-1"]
        assert [s["skill_id"] for s in export["skills"]] == ["skill-1"]
        assert [i["name"] for i in export["interests"]] == ["rust"]
        chains = {
            (c["source_type"], c["source_id"], c["event_id"]) for c in export["provenance_chains"]
        }
        assert chains == {("Preference", "pref-1", "evt-1"), ("Skill", "skill-1", "evt-2")}

    async def test_delete_user_data(self, graph: GraphBackend) -> None:
        await _seed_events(graph)
        await graph.write_user_profile({"user_id": USER, "display_name": "Alice"})
        await graph.write_preference_with_edges(
            USER, {"preference_id": "pref-1", "key": "editor"}, ["evt-1"], DERIVATION
        )
        await graph.write_skill_with_edges(
            USER, {"skill_id": "skill-1", "name": "python"}, [], DERIVATION
        )
        await graph.write_interest_edge(USER, "rust", "concept", 0.9, "stated")

        assert await graph.delete_user_data(USER) == 1
        assert await graph.get_user_profile(USER) is None
        assert await graph.get_user_preferences(USER, active_only=False) == []
        assert await graph.get_user_skills(USER) == []
        assert await graph.get_user_interests(USER) == []
        entity = await graph.get_entity(USER)
        assert entity is not None
        assert entity["entity"]["name"] == "REDACTED"
        assert await graph.delete_user_data("user:nobody") == 0
