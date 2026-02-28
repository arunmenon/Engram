"""E2E tests for User Personalization and GDPR endpoints.

Exercises the full user personalization pipeline against the running stack:
1. Create test user data directly in Neo4j (Entity, UserProfile, Preference, etc.)
2. Retrieve data via the /v1/users/ API endpoints
3. Verify GDPR data-export includes all stored data
4. Verify GDPR cascade deletion removes all user-related nodes and edges
5. Verify post-deletion returns 404 / empty results

Prerequisites:
    - docker-compose up (redis, neo4j, api)
    - pip install -e ".[dev]"

Usage:
    python -m pytest tests/e2e/test_e2e_users.py -v
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx
import pytest
from neo4j import AsyncGraphDatabase

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_URL = "http://127.0.0.1:8000"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "engram-dev-password"
NEO4J_DATABASE = "neo4j"

# All test IDs use this prefix for isolation and cleanup
PREFIX = "e2e-users-"

CLEANUP_QUERY = """
MATCH (n)
WHERE n.entity_id STARTS WITH 'e2e-users-'
   OR n.user_id STARTS WITH 'e2e-users-'
   OR n.preference_id STARTS WITH 'e2e-users-'
   OR n.skill_id STARTS WITH 'e2e-users-'
   OR n.pattern_id STARTS WITH 'e2e-users-'
   OR n.profile_id STARTS WITH 'e2e-users-'
DETACH DELETE n
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def neo4j_driver():
    """Function-scoped async Neo4j driver."""
    driver = AsyncGraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD),
    )
    # Cleanup before test
    async with driver.session(database=NEO4J_DATABASE) as session:
        await session.run(CLEANUP_QUERY)
    try:
        yield driver
    finally:
        # Cleanup after test
        async with driver.session(database=NEO4J_DATABASE) as session:
            await session.run(CLEANUP_QUERY)
        await driver.close()


@pytest.fixture
async def http_client():
    """Function-scoped async HTTP client."""
    async with httpx.AsyncClient(base_url=API_URL, timeout=15.0, trust_env=False) as client:
        yield client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def create_user_entity(driver, user_id: str, name: str) -> None:
    """Create an Entity node for a user."""
    now = datetime.now(UTC).isoformat()
    query = """
    CREATE (u:Entity {
        entity_id: $user_id,
        name: $name,
        entity_type: 'user',
        first_seen: $now,
        last_seen: $now,
        mention_count: 1
    })
    """
    async with driver.session(database=NEO4J_DATABASE) as session:
        await session.run(query, {"user_id": user_id, "name": name, "now": now})


async def create_user_profile(
    driver,
    user_id: str,
    display_name: str,
    profile_id: str | None = None,
) -> str:
    """Create a UserProfile node and link it to the Entity. Returns profile_id."""
    if profile_id is None:
        profile_id = f"{PREFIX}profile-{uuid.uuid4().hex[:8]}"
    now = datetime.now(UTC).isoformat()
    query = """
    MATCH (u:Entity {entity_id: $user_id})
    CREATE (p:UserProfile {
        profile_id: $profile_id,
        user_id: $user_id,
        display_name: $display_name,
        timezone: 'UTC',
        language: 'en',
        created_at: $now,
        updated_at: $now
    })
    CREATE (u)-[:HAS_PROFILE]->(p)
    """
    async with driver.session(database=NEO4J_DATABASE) as session:
        await session.run(
            query,
            {
                "user_id": user_id,
                "display_name": display_name,
                "profile_id": profile_id,
                "now": now,
            },
        )
    return profile_id


async def create_preference(
    driver,
    user_id: str,
    pref_id: str,
    category: str = "tool",
    key: str = "vim",
    polarity: str = "positive",
    strength: float = 0.8,
    source: str = "explicit",
) -> None:
    """Create a Preference node and link it to the user Entity."""
    now = datetime.now(UTC).isoformat()
    query = """
    MATCH (u:Entity {entity_id: $user_id})
    CREATE (pref:Preference {
        preference_id: $pref_id,
        category: $category,
        key: $key,
        polarity: $polarity,
        strength: $strength,
        source: $source,
        confidence: 0.9,
        scope: 'global',
        observation_count: 3,
        first_observed_at: $now,
        last_confirmed_at: $now
    })
    CREATE (u)-[:HAS_PREFERENCE]->(pref)
    """
    async with driver.session(database=NEO4J_DATABASE) as session:
        await session.run(
            query,
            {
                "user_id": user_id,
                "pref_id": pref_id,
                "category": category,
                "key": key,
                "polarity": polarity,
                "strength": strength,
                "source": source,
                "now": now,
            },
        )


async def create_skill(
    driver,
    user_id: str,
    skill_id: str,
    name: str = "Python",
    category: str = "programming",
    description: str = "General Python programming",
) -> None:
    """Create a Skill node and link it to the user Entity."""
    now = datetime.now(UTC).isoformat()
    query = """
    MATCH (u:Entity {entity_id: $user_id})
    CREATE (s:Skill {
        skill_id: $skill_id,
        name: $name,
        category: $category,
        description: $description,
        created_at: $now
    })
    CREATE (u)-[r:HAS_SKILL {
        proficiency: 0.85,
        confidence: 0.9,
        source: 'inferred',
        updated_at: $now,
        last_assessed_at: $now,
        assessment_count: 5
    }]->(s)
    """
    async with driver.session(database=NEO4J_DATABASE) as session:
        await session.run(
            query,
            {
                "user_id": user_id,
                "skill_id": skill_id,
                "name": name,
                "category": category,
                "description": description,
                "now": now,
            },
        )


async def create_pattern(
    driver,
    user_id: str,
    pattern_id: str,
    pattern_type: str = "coding_style",
    description: str = "Prefers functional programming patterns",
    confidence: float = 0.75,
) -> None:
    """Create a BehavioralPattern node and link it to the user Entity."""
    now = datetime.now(UTC).isoformat()
    query = """
    MATCH (u:Entity {entity_id: $user_id})
    CREATE (bp:BehavioralPattern {
        pattern_id: $pattern_id,
        pattern_type: $pattern_type,
        description: $description,
        confidence: $confidence,
        first_observed_at: $now,
        last_confirmed_at: $now,
        observation_count: 4
    })
    CREATE (u)-[:EXHIBITS_PATTERN]->(bp)
    """
    async with driver.session(database=NEO4J_DATABASE) as session:
        await session.run(
            query,
            {
                "user_id": user_id,
                "pattern_id": pattern_id,
                "pattern_type": pattern_type,
                "description": description,
                "confidence": confidence,
                "now": now,
            },
        )


async def create_interest(
    driver,
    user_id: str,
    target_entity_id: str,
    target_name: str,
    target_type: str = "concept",
    weight: float = 0.9,
    source: str = "inferred",
) -> None:
    """Create an INTERESTED_IN edge from user to a target Entity."""
    now = datetime.now(UTC).isoformat()
    query = """
    MATCH (u:Entity {entity_id: $user_id})
    CREATE (t:Entity {
        entity_id: $target_entity_id,
        name: $target_name,
        entity_type: $target_type,
        first_seen: $now,
        last_seen: $now,
        mention_count: 1
    })
    CREATE (u)-[:INTERESTED_IN {
        weight: $weight,
        source: $source,
        updated_at: $now
    }]->(t)
    """
    async with driver.session(database=NEO4J_DATABASE) as session:
        await session.run(
            query,
            {
                "user_id": user_id,
                "target_entity_id": target_entity_id,
                "target_name": target_name,
                "target_type": target_type,
                "weight": weight,
                "source": source,
                "now": now,
            },
        )


async def create_full_user_graph(driver, user_id: str) -> dict:
    """Create a complete user graph with all node types and return IDs."""
    name = f"Test User {user_id[-8:]}"
    profile_id = f"{PREFIX}profile-{uuid.uuid4().hex[:8]}"
    pref_id = f"{PREFIX}pref-{uuid.uuid4().hex[:8]}"
    skill_id = f"{PREFIX}skill-{uuid.uuid4().hex[:8]}"
    pattern_id = f"{PREFIX}pattern-{uuid.uuid4().hex[:8]}"
    interest_target_id = f"{PREFIX}topic-{uuid.uuid4().hex[:8]}"

    await create_user_entity(driver, user_id, name)
    await create_user_profile(driver, user_id, name, profile_id)
    await create_preference(driver, user_id, pref_id)
    await create_skill(driver, user_id, skill_id)
    await create_pattern(driver, user_id, pattern_id)
    await create_interest(
        driver,
        user_id,
        interest_target_id,
        "machine-learning",
        "concept",
    )

    return {
        "user_id": user_id,
        "name": name,
        "profile_id": profile_id,
        "pref_id": pref_id,
        "skill_id": skill_id,
        "pattern_id": pattern_id,
        "interest_target_id": interest_target_id,
    }


# ---------------------------------------------------------------------------
# Tests: Profile
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_profile_retrieval(neo4j_driver, http_client):
    """Create Entity + UserProfile in Neo4j, retrieve via API."""
    user_id = f"{PREFIX}profile-{uuid.uuid4().hex[:8]}"
    display_name = "Alice E2E"

    await create_user_entity(neo4j_driver, user_id, display_name)
    await create_user_profile(neo4j_driver, user_id, display_name)

    resp = await http_client.get(f"/v1/users/{user_id}/profile")

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    profile = resp.json()
    assert profile["user_id"] == user_id
    assert profile["display_name"] == display_name
    assert profile["timezone"] == "UTC"
    assert profile["language"] == "en"


@pytest.mark.asyncio
async def test_user_profile_not_found(http_client):
    """GET profile for a non-existent user returns 404."""
    resp = await http_client.get(f"/v1/users/{PREFIX}nonexistent-user/profile")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Preferences
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_preferences_retrieval(neo4j_driver, http_client):
    """Create Entity + Preferences in Neo4j, retrieve via API."""
    user_id = f"{PREFIX}prefs-{uuid.uuid4().hex[:8]}"

    await create_user_entity(neo4j_driver, user_id, "Pref User")
    pref_id_1 = f"{PREFIX}pref-vim-{uuid.uuid4().hex[:8]}"
    pref_id_2 = f"{PREFIX}pref-dark-{uuid.uuid4().hex[:8]}"

    await create_preference(
        neo4j_driver,
        user_id,
        pref_id_1,
        category="tool",
        key="vim",
        polarity="positive",
    )
    await create_preference(
        neo4j_driver,
        user_id,
        pref_id_2,
        category="ui",
        key="dark-mode",
        polarity="positive",
    )

    resp = await http_client.get(f"/v1/users/{user_id}/preferences")

    assert resp.status_code == 200
    prefs = resp.json()
    assert isinstance(prefs, list)
    assert len(prefs) == 2

    pref_ids = {p["preference_id"] for p in prefs}
    assert pref_id_1 in pref_ids
    assert pref_id_2 in pref_ids


@pytest.mark.asyncio
async def test_user_preferences_filter_by_category(neo4j_driver, http_client):
    """Filter preferences by category query param."""
    user_id = f"{PREFIX}prefs-filter-{uuid.uuid4().hex[:8]}"

    await create_user_entity(neo4j_driver, user_id, "Filter User")
    pref_tool = f"{PREFIX}pref-tool-{uuid.uuid4().hex[:8]}"
    pref_ui = f"{PREFIX}pref-ui-{uuid.uuid4().hex[:8]}"

    await create_preference(
        neo4j_driver,
        user_id,
        pref_tool,
        category="tool",
        key="emacs",
    )
    await create_preference(
        neo4j_driver,
        user_id,
        pref_ui,
        category="ui",
        key="light-mode",
    )

    resp = await http_client.get(
        f"/v1/users/{user_id}/preferences",
        params={"category": "tool"},
    )

    assert resp.status_code == 200
    prefs = resp.json()
    assert len(prefs) == 1
    assert prefs[0]["category"] == "tool"
    assert prefs[0]["key"] == "emacs"


@pytest.mark.asyncio
async def test_user_preferences_empty(http_client):
    """GET preferences for a non-existent user returns empty list."""
    resp = await http_client.get(f"/v1/users/{PREFIX}no-prefs/preferences")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Tests: Skills
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_skills_retrieval(neo4j_driver, http_client):
    """Create Entity + Skills in Neo4j, retrieve via API."""
    user_id = f"{PREFIX}skills-{uuid.uuid4().hex[:8]}"

    await create_user_entity(neo4j_driver, user_id, "Skill User")
    skill_id = f"{PREFIX}skill-py-{uuid.uuid4().hex[:8]}"

    await create_skill(
        neo4j_driver,
        user_id,
        skill_id,
        name="Python",
        category="programming",
    )

    resp = await http_client.get(f"/v1/users/{user_id}/skills")

    assert resp.status_code == 200
    skills = resp.json()
    assert isinstance(skills, list)
    assert len(skills) == 1
    assert skills[0]["skill_id"] == skill_id
    assert skills[0]["name"] == "Python"
    assert skills[0]["category"] == "programming"


@pytest.mark.asyncio
async def test_user_skills_empty(http_client):
    """GET skills for a non-existent user returns empty list."""
    resp = await http_client.get(f"/v1/users/{PREFIX}no-skills/skills")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Tests: Patterns
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_patterns_retrieval(neo4j_driver, http_client):
    """Create Entity + BehavioralPattern in Neo4j, retrieve via API."""
    user_id = f"{PREFIX}patterns-{uuid.uuid4().hex[:8]}"

    await create_user_entity(neo4j_driver, user_id, "Pattern User")
    pattern_id = f"{PREFIX}pattern-fp-{uuid.uuid4().hex[:8]}"

    await create_pattern(
        neo4j_driver,
        user_id,
        pattern_id,
        pattern_type="coding_style",
        description="Uses functional patterns",
        confidence=0.85,
    )

    resp = await http_client.get(f"/v1/users/{user_id}/patterns")

    assert resp.status_code == 200
    patterns = resp.json()
    assert isinstance(patterns, list)
    assert len(patterns) == 1
    assert patterns[0]["pattern_id"] == pattern_id
    assert patterns[0]["pattern_type"] == "coding_style"
    assert patterns[0]["confidence"] == 0.85


@pytest.mark.asyncio
async def test_user_patterns_empty(http_client):
    """GET patterns for a non-existent user returns empty list."""
    resp = await http_client.get(f"/v1/users/{PREFIX}no-patterns/patterns")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Tests: Interests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_interests_retrieval(neo4j_driver, http_client):
    """Create Entity + INTERESTED_IN edges, retrieve via API."""
    user_id = f"{PREFIX}interests-{uuid.uuid4().hex[:8]}"
    target_id = f"{PREFIX}topic-ml-{uuid.uuid4().hex[:8]}"

    await create_user_entity(neo4j_driver, user_id, "Interest User")
    await create_interest(
        neo4j_driver,
        user_id,
        target_id,
        target_name="machine-learning",
        target_type="concept",
        weight=0.95,
        source="inferred",
    )

    resp = await http_client.get(f"/v1/users/{user_id}/interests")

    assert resp.status_code == 200
    interests = resp.json()
    assert isinstance(interests, list)
    assert len(interests) == 1
    assert interests[0]["entity_id"] == target_id
    assert interests[0]["name"] == "machine-learning"
    assert interests[0]["entity_type"] == "concept"
    assert interests[0]["weight"] == 0.95
    assert interests[0]["source"] == "inferred"


@pytest.mark.asyncio
async def test_user_interests_empty(http_client):
    """GET interests for a non-existent user returns empty list."""
    resp = await http_client.get(f"/v1/users/{PREFIX}no-interests/interests")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Tests: GDPR Data Export
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gdpr_data_export(neo4j_driver, http_client):
    """Create full user graph, verify GDPR data export includes all sections."""
    user_id = f"{PREFIX}export-{uuid.uuid4().hex[:8]}"
    ids = await create_full_user_graph(neo4j_driver, user_id)

    resp = await http_client.get(f"/v1/users/{user_id}/data-export")

    assert resp.status_code == 200
    data = resp.json()

    # Top-level structure
    assert data["user_id"] == user_id
    assert data["profile"] is not None
    assert isinstance(data["preferences"], list)
    assert isinstance(data["skills"], list)
    assert isinstance(data["patterns"], list)
    assert isinstance(data["interests"], list)

    # Profile
    assert data["profile"]["user_id"] == user_id
    assert data["profile"]["display_name"] == ids["name"]

    # Preferences
    assert len(data["preferences"]) == 1
    assert data["preferences"][0]["preference_id"] == ids["pref_id"]
    assert data["preferences"][0]["category"] == "tool"

    # Skills
    assert len(data["skills"]) == 1
    assert data["skills"][0]["skill_id"] == ids["skill_id"]
    assert data["skills"][0]["name"] == "Python"

    # Patterns
    assert len(data["patterns"]) == 1
    assert data["patterns"][0]["pattern_id"] == ids["pattern_id"]

    # Interests
    assert len(data["interests"]) == 1
    assert data["interests"][0]["entity_id"] == ids["interest_target_id"]
    assert data["interests"][0]["name"] == "machine-learning"


@pytest.mark.asyncio
async def test_gdpr_data_export_empty_user(http_client):
    """GDPR export for non-existent user returns empty structure."""
    resp = await http_client.get(f"/v1/users/{PREFIX}no-data/data-export")

    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == f"{PREFIX}no-data"
    assert data["profile"] is None
    assert data["preferences"] == []
    assert data["skills"] == []
    assert data["patterns"] == []
    assert data["interests"] == []


# ---------------------------------------------------------------------------
# Tests: GDPR Cascade Deletion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gdpr_cascade_deletion(neo4j_driver, http_client):
    """Create full user graph, delete via API, verify all nodes removed."""
    user_id = f"{PREFIX}delete-{uuid.uuid4().hex[:8]}"
    await create_full_user_graph(neo4j_driver, user_id)

    # Verify data exists before deletion
    profile_resp = await http_client.get(f"/v1/users/{user_id}/profile")
    assert profile_resp.status_code == 200

    # Perform GDPR deletion
    delete_resp = await http_client.delete(f"/v1/users/{user_id}")

    assert delete_resp.status_code == 200
    delete_data = delete_resp.json()
    assert delete_data["status"] == "erased"
    assert delete_data["deleted_count"] >= 1

    # Verify profile is gone
    profile_after = await http_client.get(f"/v1/users/{user_id}/profile")
    assert profile_after.status_code == 404

    # Verify preferences are gone
    prefs_after = await http_client.get(f"/v1/users/{user_id}/preferences")
    assert prefs_after.status_code == 200
    assert prefs_after.json() == []

    # Verify skills edges are gone
    skills_after = await http_client.get(f"/v1/users/{user_id}/skills")
    assert skills_after.status_code == 200
    assert skills_after.json() == []

    # Verify patterns are gone
    patterns_after = await http_client.get(f"/v1/users/{user_id}/patterns")
    assert patterns_after.status_code == 200
    assert patterns_after.json() == []

    # Verify interests edges are gone
    interests_after = await http_client.get(f"/v1/users/{user_id}/interests")
    assert interests_after.status_code == 200
    assert interests_after.json() == []


@pytest.mark.asyncio
async def test_gdpr_deletion_anonymizes_entity(neo4j_driver, http_client):
    """After GDPR delete, Entity node should have name=REDACTED."""
    user_id = f"{PREFIX}anon-{uuid.uuid4().hex[:8]}"
    await create_full_user_graph(neo4j_driver, user_id)

    await http_client.delete(f"/v1/users/{user_id}")

    # Verify Entity node is anonymized in Neo4j directly
    query = "MATCH (e:Entity {entity_id: $user_id}) RETURN e.name AS name"
    async with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        result = await session.run(query, {"user_id": user_id})
        record = await result.single()

    assert record is not None, "Entity node should still exist after GDPR delete"
    assert record["name"] == "REDACTED"


@pytest.mark.asyncio
async def test_gdpr_deletion_removes_profile_node(neo4j_driver, http_client):
    """After GDPR delete, UserProfile node should be fully removed from Neo4j."""
    user_id = f"{PREFIX}profgone-{uuid.uuid4().hex[:8]}"
    ids = await create_full_user_graph(neo4j_driver, user_id)

    await http_client.delete(f"/v1/users/{user_id}")

    query = "MATCH (p:UserProfile {user_id: $user_id}) RETURN count(p) AS cnt"
    async with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        result = await session.run(query, {"user_id": user_id})
        record = await result.single()

    assert record["cnt"] == 0


@pytest.mark.asyncio
async def test_gdpr_deletion_removes_preference_nodes(neo4j_driver, http_client):
    """After GDPR delete, Preference nodes should be fully removed from Neo4j."""
    user_id = f"{PREFIX}prefgone-{uuid.uuid4().hex[:8]}"
    ids = await create_full_user_graph(neo4j_driver, user_id)
    pref_id = ids["pref_id"]

    await http_client.delete(f"/v1/users/{user_id}")

    query = "MATCH (p:Preference {preference_id: $pref_id}) RETURN count(p) AS cnt"
    async with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        result = await session.run(query, {"pref_id": pref_id})
        record = await result.single()

    assert record["cnt"] == 0


@pytest.mark.asyncio
async def test_gdpr_deletion_removes_pattern_nodes(neo4j_driver, http_client):
    """After GDPR delete, BehavioralPattern nodes should be fully removed."""
    user_id = f"{PREFIX}patgone-{uuid.uuid4().hex[:8]}"
    ids = await create_full_user_graph(neo4j_driver, user_id)
    pattern_id = ids["pattern_id"]

    await http_client.delete(f"/v1/users/{user_id}")

    query = "MATCH (b:BehavioralPattern {pattern_id: $pattern_id}) RETURN count(b) AS cnt"
    async with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        result = await session.run(query, {"pattern_id": pattern_id})
        record = await result.single()

    assert record["cnt"] == 0


@pytest.mark.asyncio
async def test_gdpr_delete_nonexistent_user(http_client):
    """GDPR delete for a non-existent user should succeed gracefully."""
    resp = await http_client.delete(f"/v1/users/{PREFIX}ghost-user")

    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted_count"] == 0
    assert data["status"] == "erased"


# ---------------------------------------------------------------------------
# Tests: Multiple items
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multiple_preferences(neo4j_driver, http_client):
    """User with multiple preferences returns all of them."""
    user_id = f"{PREFIX}multi-pref-{uuid.uuid4().hex[:8]}"
    await create_user_entity(neo4j_driver, user_id, "Multi Pref User")

    pref_ids = []
    for i, (cat, key) in enumerate(
        [
            ("tool", "vim"),
            ("ui", "dark-mode"),
            ("language", "python"),
        ]
    ):
        pref_id = f"{PREFIX}pref-multi-{i}-{uuid.uuid4().hex[:8]}"
        pref_ids.append(pref_id)
        await create_preference(
            neo4j_driver,
            user_id,
            pref_id,
            category=cat,
            key=key,
        )

    resp = await http_client.get(f"/v1/users/{user_id}/preferences")
    assert resp.status_code == 200
    prefs = resp.json()
    assert len(prefs) == 3

    returned_ids = {p["preference_id"] for p in prefs}
    for pid in pref_ids:
        assert pid in returned_ids


@pytest.mark.asyncio
async def test_multiple_skills(neo4j_driver, http_client):
    """User with multiple skills returns all of them, ordered by name."""
    user_id = f"{PREFIX}multi-skill-{uuid.uuid4().hex[:8]}"
    await create_user_entity(neo4j_driver, user_id, "Multi Skill User")

    skills_data = [
        ("Python", "programming"),
        ("Docker", "devops"),
        ("SQL", "databases"),
    ]
    skill_ids = []
    for name, category in skills_data:
        skill_id = f"{PREFIX}skill-{name.lower()}-{uuid.uuid4().hex[:8]}"
        skill_ids.append(skill_id)
        await create_skill(
            neo4j_driver,
            user_id,
            skill_id,
            name=name,
            category=category,
        )

    resp = await http_client.get(f"/v1/users/{user_id}/skills")
    assert resp.status_code == 200
    skills = resp.json()
    assert len(skills) == 3

    # Skills should be ordered by name (per the Cypher ORDER BY s.name)
    skill_names = [s["name"] for s in skills]
    assert skill_names == sorted(skill_names)


@pytest.mark.asyncio
async def test_multiple_interests(neo4j_driver, http_client):
    """User with multiple interests returns all, ordered by weight DESC."""
    user_id = f"{PREFIX}multi-int-{uuid.uuid4().hex[:8]}"
    await create_user_entity(neo4j_driver, user_id, "Multi Interest User")

    interests = [
        (f"{PREFIX}topic-ai-{uuid.uuid4().hex[:8]}", "artificial-intelligence", 0.95),
        (f"{PREFIX}topic-db-{uuid.uuid4().hex[:8]}", "databases", 0.7),
        (f"{PREFIX}topic-web-{uuid.uuid4().hex[:8]}", "web-dev", 0.5),
    ]

    for target_id, name, weight in interests:
        await create_interest(
            neo4j_driver,
            user_id,
            target_id,
            target_name=name,
            weight=weight,
        )

    resp = await http_client.get(f"/v1/users/{user_id}/interests")
    assert resp.status_code == 200
    result = resp.json()
    assert len(result) == 3

    # Should be ordered by weight DESC (per Cypher ORDER BY r.weight DESC)
    weights = [i["weight"] for i in result]
    assert weights == sorted(weights, reverse=True)
