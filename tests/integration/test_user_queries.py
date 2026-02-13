"""Integration tests for user_queries against a real Neo4j instance.

Requires Neo4j running at bolt://localhost:7687 (docker-compose up).
"""

from __future__ import annotations

import pytest
from neo4j import AsyncGraphDatabase

from context_graph.adapters.neo4j import user_queries
from context_graph.settings import Neo4jSettings


@pytest.fixture
async def neo4j_driver():
    """Provide an async Neo4j driver, clean up all data after each test."""
    settings = Neo4jSettings()
    driver = AsyncGraphDatabase.driver(
        settings.uri,
        auth=(settings.username, settings.password),
    )

    # Create constraints for test stability
    async with driver.session(database=settings.database) as session:
        await session.run(
            "CREATE CONSTRAINT entity_pk IF NOT EXISTS "
            "FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE"
        )
        await session.run(
            "CREATE CONSTRAINT preference_pk IF NOT EXISTS "
            "FOR (p:Preference) REQUIRE p.preference_id IS UNIQUE"
        )
        await session.run(
            "CREATE CONSTRAINT skill_pk IF NOT EXISTS " "FOR (s:Skill) REQUIRE s.skill_id IS UNIQUE"
        )
        await session.run(
            "CREATE CONSTRAINT profile_pk IF NOT EXISTS "
            "FOR (p:UserProfile) REQUIRE p.profile_id IS UNIQUE"
        )
        await session.run(
            "CREATE CONSTRAINT event_pk IF NOT EXISTS " "FOR (e:Event) REQUIRE e.event_id IS UNIQUE"
        )

    yield driver, settings.database

    # Teardown: delete all test data
    async with driver.session(database=settings.database) as session:
        await session.run("MATCH (n) DETACH DELETE n")

    await driver.close()


# ---------------------------------------------------------------------------
# write_user_profile + get_user_profile
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestUserProfile:
    async def test_write_and_get_profile(self, neo4j_driver) -> None:
        driver, database = neo4j_driver
        profile_data = {
            "user_id": "user:alice",
            "profile_id": "profile:alice",
            "display_name": "Alice",
            "timezone": "US/Pacific",
            "language": "en",
            "communication_style": "concise",
            "technical_level": "expert",
        }
        await user_queries.write_user_profile(driver, database, profile_data)
        result = await user_queries.get_user_profile(driver, database, "user:alice")

        assert result is not None
        assert result["display_name"] == "Alice"
        assert result["timezone"] == "US/Pacific"
        assert result["language"] == "en"

    async def test_get_profile_not_found(self, neo4j_driver) -> None:
        driver, database = neo4j_driver
        result = await user_queries.get_user_profile(driver, database, "user:nonexistent")
        assert result is None

    async def test_write_profile_is_idempotent(self, neo4j_driver) -> None:
        driver, database = neo4j_driver
        profile_data = {
            "user_id": "user:bob",
            "profile_id": "profile:bob",
            "display_name": "Bob",
        }
        await user_queries.write_user_profile(driver, database, profile_data)
        await user_queries.write_user_profile(driver, database, profile_data)

        # Verify only one profile node
        async with driver.session(database=database) as session:
            result = await session.run(
                "MATCH (p:UserProfile {profile_id: 'profile:bob'}) " "RETURN count(p) AS cnt"
            )
            record = await result.single()

        assert record is not None
        assert record["cnt"] == 1


# ---------------------------------------------------------------------------
# write_preference_with_edges + get_user_preferences
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestUserPreferences:
    async def test_write_and_get_preference(self, neo4j_driver) -> None:
        driver, database = neo4j_driver
        pref_data = {
            "preference_id": "pref:vim-001",
            "category": "tool",
            "key": "editor-vim",
            "polarity": "positive",
            "strength": 0.9,
            "confidence": 0.8,
            "source": "explicit",
        }
        await user_queries.write_preference_with_edges(
            driver=driver,
            database=database,
            user_entity_id="user:test-pref",
            preference_data=pref_data,
            source_event_ids=[],
            derivation_info={"method": "stated", "session_id": "s1"},
        )

        prefs = await user_queries.get_user_preferences(driver, database, "user:test-pref")
        assert len(prefs) == 1
        assert prefs[0]["key"] == "editor-vim"
        assert prefs[0]["polarity"] == "positive"

    async def test_active_only_filter(self, neo4j_driver) -> None:
        driver, database = neo4j_driver

        # Write active preference
        await user_queries.write_preference_with_edges(
            driver=driver,
            database=database,
            user_entity_id="user:test-filter",
            preference_data={
                "preference_id": "pref:active",
                "category": "tool",
                "key": "active-pref",
                "polarity": "positive",
                "strength": 0.8,
                "confidence": 0.7,
                "source": "explicit",
            },
            source_event_ids=[],
            derivation_info={"method": "stated"},
        )

        # Write superseded preference
        await user_queries.write_preference_with_edges(
            driver=driver,
            database=database,
            user_entity_id="user:test-filter",
            preference_data={
                "preference_id": "pref:old",
                "category": "tool",
                "key": "old-pref",
                "polarity": "positive",
                "strength": 0.5,
                "confidence": 0.6,
                "source": "explicit",
                "superseded_by": "pref:active",
            },
            source_event_ids=[],
            derivation_info={"method": "stated"},
        )

        # Active only should return 1
        active_prefs = await user_queries.get_user_preferences(
            driver, database, "user:test-filter", active_only=True
        )
        assert len(active_prefs) == 1
        assert active_prefs[0]["preference_id"] == "pref:active"

        # All preferences should return 2
        all_prefs = await user_queries.get_user_preferences(
            driver, database, "user:test-filter", active_only=False
        )
        assert len(all_prefs) == 2

    async def test_preference_creates_has_preference_edge(self, neo4j_driver) -> None:
        driver, database = neo4j_driver
        await user_queries.write_preference_with_edges(
            driver=driver,
            database=database,
            user_entity_id="user:test-edge",
            preference_data={
                "preference_id": "pref:edge-test",
                "category": "workflow",
                "key": "agile",
                "polarity": "positive",
                "strength": 0.7,
                "confidence": 0.6,
                "source": "implicit_intentional",
            },
            source_event_ids=[],
            derivation_info={"method": "llm_extraction"},
        )

        # Verify HAS_PREFERENCE edge exists
        async with driver.session(database=database) as session:
            result = await session.run(
                "MATCH (e:Entity {entity_id: 'user:test-edge'})"
                "-[:HAS_PREFERENCE]->"
                "(p:Preference {preference_id: 'pref:edge-test'}) "
                "RETURN count(*) AS cnt"
            )
            record = await result.single()

        assert record is not None
        assert record["cnt"] == 1

    async def test_preference_with_about_entity(self, neo4j_driver) -> None:
        driver, database = neo4j_driver
        await user_queries.write_preference_with_edges(
            driver=driver,
            database=database,
            user_entity_id="user:about-test",
            preference_data={
                "preference_id": "pref:about-test",
                "category": "tool",
                "key": "python-preference",
                "polarity": "positive",
                "strength": 0.9,
                "confidence": 0.8,
                "source": "explicit",
                "about_entity": "python",
            },
            source_event_ids=[],
            derivation_info={"method": "stated"},
        )

        # Verify ABOUT edge
        async with driver.session(database=database) as session:
            result = await session.run(
                "MATCH (p:Preference {preference_id: 'pref:about-test'})"
                "-[:ABOUT]->"
                "(t:Entity) "
                "RETURN t.name AS name"
            )
            record = await result.single()

        assert record is not None
        assert record["name"] == "python"


# ---------------------------------------------------------------------------
# write_skill_with_edges + get_user_skills
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestUserSkills:
    async def test_write_and_get_skill(self, neo4j_driver) -> None:
        driver, database = neo4j_driver
        skill_data = {
            "skill_id": "skill:python-001",
            "name": "Python",
            "category": "programming_language",
            "description": "Python programming",
            "proficiency": 0.85,
            "confidence": 0.9,
            "source": "observed",
        }
        await user_queries.write_skill_with_edges(
            driver=driver,
            database=database,
            user_entity_id="user:skill-test",
            skill_data=skill_data,
            source_event_ids=[],
            derivation_info={"method": "llm_extraction", "session_id": "s1"},
        )

        skills = await user_queries.get_user_skills(driver, database, "user:skill-test")
        assert len(skills) == 1
        assert skills[0]["name"] == "Python"
        assert skills[0]["category"] == "programming_language"

    async def test_skill_creates_has_skill_edge(self, neo4j_driver) -> None:
        driver, database = neo4j_driver
        await user_queries.write_skill_with_edges(
            driver=driver,
            database=database,
            user_entity_id="user:skill-edge",
            skill_data={
                "skill_id": "skill:go-001",
                "name": "Go",
                "category": "programming_language",
            },
            source_event_ids=[],
            derivation_info={"method": "observed"},
        )

        async with driver.session(database=database) as session:
            result = await session.run(
                "MATCH (e:Entity {entity_id: 'user:skill-edge'})"
                "-[r:HAS_SKILL]->"
                "(s:Skill {skill_id: 'skill:go-001'}) "
                "RETURN r.proficiency AS proficiency"
            )
            record = await result.single()

        assert record is not None
        assert record["proficiency"] == 0.5  # default

    async def test_skill_with_derived_from(self, neo4j_driver) -> None:
        driver, database = neo4j_driver

        # Create source event first
        async with driver.session(database=database) as session:
            await session.run(
                "CREATE (:Event {event_id: 'evt-source-001', "
                "event_type: 'tool.execute', "
                "occurred_at: '2024-02-11T12:00:00Z', "
                "session_id: 'sess-1', agent_id: 'a1', "
                "trace_id: 't1', global_position: '1-0'})"
            )

        await user_queries.write_skill_with_edges(
            driver=driver,
            database=database,
            user_entity_id="user:derived-test",
            skill_data={
                "skill_id": "skill:derived-001",
                "name": "Docker",
                "category": "tool_proficiency",
            },
            source_event_ids=["evt-source-001"],
            derivation_info={
                "method": "llm_extraction",
                "session_id": "sess-1",
            },
        )

        # Verify DERIVED_FROM edge
        async with driver.session(database=database) as session:
            result = await session.run(
                "MATCH (s:Skill {skill_id: 'skill:derived-001'})"
                "-[r:DERIVED_FROM]->"
                "(e:Event {event_id: 'evt-source-001'}) "
                "RETURN r.method AS method"
            )
            record = await result.single()

        assert record is not None
        assert record["method"] == "llm_extraction"


# ---------------------------------------------------------------------------
# write_interest_edge + get_user_interests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestUserInterests:
    async def test_write_and_get_interest(self, neo4j_driver) -> None:
        driver, database = neo4j_driver
        await user_queries.write_interest_edge(
            driver=driver,
            database=database,
            user_entity_id="user:interest-test",
            entity_name="kubernetes",
            entity_type="tool",
            weight=0.8,
            source="explicit",
        )

        interests = await user_queries.get_user_interests(driver, database, "user:interest-test")
        assert len(interests) == 1
        assert interests[0]["name"] == "kubernetes"
        assert interests[0]["weight"] == 0.8
        assert interests[0]["source"] == "explicit"

    async def test_multiple_interests(self, neo4j_driver) -> None:
        driver, database = neo4j_driver
        for name, weight in [("python", 0.9), ("rust", 0.6), ("go", 0.4)]:
            await user_queries.write_interest_edge(
                driver=driver,
                database=database,
                user_entity_id="user:multi-interest",
                entity_name=name,
                entity_type="concept",
                weight=weight,
                source="inferred",
            )

        interests = await user_queries.get_user_interests(driver, database, "user:multi-interest")
        assert len(interests) == 3
        # Should be sorted by weight DESC
        assert interests[0]["name"] == "python"
        assert interests[2]["name"] == "go"


# ---------------------------------------------------------------------------
# delete_user_data (GDPR)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestDeleteUserData:
    async def test_cascade_deletes_user_data(self, neo4j_driver) -> None:
        driver, database = neo4j_driver

        # Set up user with profile, preference, skill
        await user_queries.write_user_profile(
            driver,
            database,
            {
                "user_id": "user:delete-test",
                "profile_id": "profile:delete-test",
                "display_name": "DeleteMe",
            },
        )
        await user_queries.write_preference_with_edges(
            driver=driver,
            database=database,
            user_entity_id="user:delete-test",
            preference_data={
                "preference_id": "pref:delete-test",
                "category": "tool",
                "key": "to-delete",
                "polarity": "positive",
                "strength": 0.5,
                "confidence": 0.5,
                "source": "explicit",
            },
            source_event_ids=[],
            derivation_info={"method": "stated"},
        )
        await user_queries.write_skill_with_edges(
            driver=driver,
            database=database,
            user_entity_id="user:delete-test",
            skill_data={"skill_id": "skill:delete-test", "name": "ToDelete"},
            source_event_ids=[],
            derivation_info={"method": "observed"},
        )

        affected = await user_queries.delete_user_data(driver, database, "user:delete-test")
        assert affected >= 1

        # Verify profile is gone
        profile = await user_queries.get_user_profile(driver, database, "user:delete-test")
        assert profile is None

        # Verify preferences are gone
        prefs = await user_queries.get_user_preferences(driver, database, "user:delete-test")
        assert len(prefs) == 0

        # Verify entity is anonymized
        async with driver.session(database=database) as session:
            result = await session.run(
                "MATCH (e:Entity {entity_id: 'user:delete-test'}) " "RETURN e.name AS name"
            )
            record = await result.single()

        assert record is not None
        assert record["name"] == "REDACTED"

    async def test_delete_nonexistent_user(self, neo4j_driver) -> None:
        driver, database = neo4j_driver
        affected = await user_queries.delete_user_data(driver, database, "user:ghost")
        assert affected == 0


# ---------------------------------------------------------------------------
# export_user_data (GDPR)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestExportUserData:
    async def test_export_returns_all_data(self, neo4j_driver) -> None:
        driver, database = neo4j_driver

        # Set up user data
        await user_queries.write_user_profile(
            driver,
            database,
            {
                "user_id": "user:export-test",
                "profile_id": "profile:export-test",
                "display_name": "Exporter",
                "timezone": "UTC",
            },
        )
        await user_queries.write_preference_with_edges(
            driver=driver,
            database=database,
            user_entity_id="user:export-test",
            preference_data={
                "preference_id": "pref:export-001",
                "category": "style",
                "key": "dark-mode",
                "polarity": "positive",
                "strength": 0.9,
                "confidence": 0.8,
                "source": "explicit",
            },
            source_event_ids=[],
            derivation_info={"method": "stated"},
        )
        await user_queries.write_skill_with_edges(
            driver=driver,
            database=database,
            user_entity_id="user:export-test",
            skill_data={
                "skill_id": "skill:export-001",
                "name": "TypeScript",
                "category": "programming_language",
            },
            source_event_ids=[],
            derivation_info={"method": "declared"},
        )
        await user_queries.write_interest_edge(
            driver=driver,
            database=database,
            user_entity_id="user:export-test",
            entity_name="graphql",
            entity_type="concept",
            weight=0.7,
            source="explicit",
        )

        export = await user_queries.export_user_data(driver, database, "user:export-test")

        assert export["user_id"] == "user:export-test"
        assert export["profile"] is not None
        assert export["profile"]["display_name"] == "Exporter"
        assert len(export["preferences"]) == 1
        assert export["preferences"][0]["key"] == "dark-mode"
        assert len(export["skills"]) == 1
        assert export["skills"][0]["name"] == "TypeScript"
        assert len(export["interests"]) == 1
        assert export["interests"][0]["name"] == "graphql"

    async def test_export_empty_user(self, neo4j_driver) -> None:
        driver, database = neo4j_driver
        export = await user_queries.export_user_data(driver, database, "user:no-data")
        assert export["user_id"] == "user:no-data"
        assert export["profile"] is None
        assert export["preferences"] == []
        assert export["skills"] == []
        assert export["patterns"] == []
        assert export["interests"] == []
