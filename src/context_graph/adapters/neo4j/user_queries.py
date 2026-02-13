"""User-specific Neo4j queries for personalization (ADR-0012).

Provides CRUD operations for user profile, preferences, skills,
behavioral patterns, and interests. All writes use MERGE for
idempotent upserts. Includes GDPR-compliant delete and export.

Source: ADR-0012
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import structlog

if TYPE_CHECKING:
    from neo4j import AsyncDriver

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Cypher Templates — Read
# ---------------------------------------------------------------------------

_GET_USER_PROFILE = """
MATCH (e:Entity {entity_id: $user_id})-[:HAS_PROFILE]->(p:UserProfile)
RETURN p
LIMIT 1
""".strip()

_GET_USER_PREFERENCES = """
MATCH (e:Entity {entity_id: $user_id})-[:HAS_PREFERENCE]->(p:Preference)
WHERE $active_only = false OR p.superseded_by IS NULL
RETURN p
ORDER BY p.last_confirmed_at DESC
""".strip()

_GET_USER_SKILLS = """
MATCH (e:Entity {entity_id: $user_id})-[:HAS_SKILL]->(s:Skill)
RETURN s
ORDER BY s.name
""".strip()

_GET_USER_PATTERNS = """
MATCH (e:Entity {entity_id: $user_id})-[:EXHIBITS_PATTERN]->(b:BehavioralPattern)
RETURN b
ORDER BY b.last_confirmed_at DESC
""".strip()

_GET_USER_INTERESTS = """
MATCH (e:Entity {entity_id: $user_id})-[r:INTERESTED_IN]->(target:Entity)
RETURN target.entity_id AS entity_id,
       target.name AS name,
       target.entity_type AS entity_type,
       r.weight AS weight,
       r.source AS source
ORDER BY r.weight DESC
""".strip()

# ---------------------------------------------------------------------------
# Cypher Templates — Write
# ---------------------------------------------------------------------------

_MERGE_USER_PROFILE = """
MERGE (e:Entity {entity_id: $user_id})
ON CREATE SET e.name = $display_name,
              e.entity_type = 'user',
              e.first_seen = $now,
              e.last_seen = $now,
              e.mention_count = 1
ON MATCH SET e.last_seen = $now
WITH e
MERGE (e)-[:HAS_PROFILE]->(p:UserProfile {profile_id: $profile_id})
SET p.user_id = $user_id,
    p.display_name = $display_name,
    p.timezone = $timezone,
    p.language = $language,
    p.communication_style = $communication_style,
    p.technical_level = $technical_level,
    p.created_at = coalesce(p.created_at, $now),
    p.updated_at = $now
""".strip()

_MERGE_PREFERENCE = """
MERGE (p:Preference {preference_id: $preference_id})
SET p.category = $category,
    p.key = $key,
    p.polarity = $polarity,
    p.strength = $strength,
    p.confidence = $confidence,
    p.source = $source,
    p.context = $context,
    p.scope = coalesce($scope, 'global'),
    p.scope_id = $scope_id,
    p.observation_count = coalesce(p.observation_count, 0) + 1,
    p.first_observed_at = coalesce(p.first_observed_at, $now),
    p.last_confirmed_at = $now,
    p.superseded_by = $superseded_by
""".strip()

_MERGE_HAS_PREFERENCE_EDGE = """
MATCH (e:Entity {entity_id: $user_entity_id})
MATCH (p:Preference {preference_id: $preference_id})
MERGE (e)-[:HAS_PREFERENCE]->(p)
""".strip()

_MERGE_PREFERENCE_ABOUT = """
MATCH (p:Preference {preference_id: $preference_id})
MERGE (target:Entity {entity_id: $target_entity_id})
ON CREATE SET target.name = $target_name,
              target.entity_type = $target_type,
              target.first_seen = $now,
              target.last_seen = $now,
              target.mention_count = 1
ON MATCH SET target.last_seen = $now
MERGE (p)-[:ABOUT]->(target)
""".strip()

_MERGE_DERIVED_FROM = """
MATCH (source {%s: $source_id})
MATCH (e:Event {event_id: $event_id})
MERGE (source)-[r:DERIVED_FROM]->(e)
SET r.method = $method,
    r.session_id = $session_id,
    r.extracted_at = $now
""".strip()

_MERGE_SKILL = """
MERGE (s:Skill {skill_id: $skill_id})
SET s.name = $name,
    s.category = $category,
    s.description = $description,
    s.created_at = coalesce(s.created_at, $now)
""".strip()

_MERGE_HAS_SKILL_EDGE = """
MATCH (e:Entity {entity_id: $user_entity_id})
MATCH (s:Skill {skill_id: $skill_id})
MERGE (e)-[r:HAS_SKILL]->(s)
SET r.proficiency = $proficiency,
    r.confidence = $confidence,
    r.source = $source,
    r.updated_at = $now
""".strip()

_MERGE_INTERESTED_IN = """
MATCH (e:Entity {entity_id: $user_entity_id})
MERGE (target:Entity {entity_id: $target_entity_id})
ON CREATE SET target.name = $target_name,
              target.entity_type = $target_type,
              target.first_seen = $now,
              target.last_seen = $now,
              target.mention_count = 1
ON MATCH SET target.last_seen = $now
MERGE (e)-[r:INTERESTED_IN]->(target)
SET r.weight = $weight,
    r.source = $source,
    r.updated_at = $now
""".strip()

# ---------------------------------------------------------------------------
# Cypher Templates — GDPR
# ---------------------------------------------------------------------------

_DELETE_USER_DATA = """
MATCH (e:Entity {entity_id: $user_id})
OPTIONAL MATCH (e)-[:HAS_PROFILE]->(p:UserProfile)
DETACH DELETE p
WITH DISTINCT e
OPTIONAL MATCH (e)-[:HAS_PREFERENCE]->(pref:Preference)
DETACH DELETE pref
WITH DISTINCT e
OPTIONAL MATCH (e)-[:EXHIBITS_PATTERN]->(bp:BehavioralPattern)
DETACH DELETE bp
WITH DISTINCT e
OPTIONAL MATCH (e)-[:HAS_SKILL]->(s:Skill)
DETACH DELETE s
WITH DISTINCT e
SET e.name = 'REDACTED',
    e.entity_type = 'user'
RETURN count(e) AS affected
""".strip()

_EXPORT_USER_PROFILE = """
MATCH (e:Entity {entity_id: $user_id})-[:HAS_PROFILE]->(p:UserProfile)
RETURN properties(p) AS profile
LIMIT 1
""".strip()

_EXPORT_USER_PREFERENCES = """
MATCH (e:Entity {entity_id: $user_id})-[:HAS_PREFERENCE]->(p:Preference)
RETURN properties(p) AS preference
""".strip()

_EXPORT_USER_SKILLS = """
MATCH (e:Entity {entity_id: $user_id})-[:HAS_SKILL]->(s:Skill)
RETURN properties(s) AS skill
""".strip()

_EXPORT_USER_PATTERNS = """
MATCH (e:Entity {entity_id: $user_id})-[:EXHIBITS_PATTERN]->(b:BehavioralPattern)
RETURN properties(b) AS pattern
""".strip()

_EXPORT_USER_INTERESTS = """
MATCH (e:Entity {entity_id: $user_id})-[r:INTERESTED_IN]->(target:Entity)
RETURN target.entity_id AS entity_id,
       target.name AS name,
       target.entity_type AS entity_type,
       r.weight AS weight,
       r.source AS source
""".strip()


# ---------------------------------------------------------------------------
# Read Functions
# ---------------------------------------------------------------------------


async def get_user_profile(
    driver: AsyncDriver,
    database: str,
    user_id: str,
) -> dict[str, Any] | None:
    """Fetch a user's profile node. Returns None if not found."""
    async with driver.session(database=database) as session:
        result = await session.run(_GET_USER_PROFILE, {"user_id": user_id})
        record = await result.single()

    if record is None:
        return None
    return dict(record["p"])


async def get_user_preferences(
    driver: AsyncDriver,
    database: str,
    user_id: str,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    """Fetch a user's preferences. When active_only=True, excludes superseded."""
    async with driver.session(database=database) as session:
        result = await session.run(
            _GET_USER_PREFERENCES,
            {"user_id": user_id, "active_only": active_only},
        )
        records = [record async for record in result]

    return [dict(record["p"]) for record in records]


async def get_user_skills(
    driver: AsyncDriver,
    database: str,
    user_id: str,
) -> list[dict[str, Any]]:
    """Fetch a user's skills."""
    async with driver.session(database=database) as session:
        result = await session.run(_GET_USER_SKILLS, {"user_id": user_id})
        records = [record async for record in result]

    return [dict(record["s"]) for record in records]


async def get_user_patterns(
    driver: AsyncDriver,
    database: str,
    user_id: str,
) -> list[dict[str, Any]]:
    """Fetch a user's behavioral patterns."""
    async with driver.session(database=database) as session:
        result = await session.run(_GET_USER_PATTERNS, {"user_id": user_id})
        records = [record async for record in result]

    return [dict(record["b"]) for record in records]


async def get_user_interests(
    driver: AsyncDriver,
    database: str,
    user_id: str,
) -> list[dict[str, Any]]:
    """Fetch a user's interests (INTERESTED_IN edges to entities)."""
    async with driver.session(database=database) as session:
        result = await session.run(_GET_USER_INTERESTS, {"user_id": user_id})
        records = [record async for record in result]

    return [
        {
            "entity_id": record["entity_id"],
            "name": record["name"],
            "entity_type": record["entity_type"],
            "weight": record["weight"],
            "source": record["source"],
        }
        for record in records
    ]


# ---------------------------------------------------------------------------
# Write Functions
# ---------------------------------------------------------------------------


async def write_user_profile(
    driver: AsyncDriver,
    database: str,
    profile_data: dict[str, Any],
) -> None:
    """Create or update a user profile with HAS_PROFILE edge."""
    now = datetime.now(UTC).isoformat()
    user_id = profile_data.get("user_id", "")
    profile_id = profile_data.get("profile_id", f"profile:{user_id}")

    params = {
        "user_id": user_id,
        "profile_id": profile_id,
        "display_name": profile_data.get("display_name"),
        "timezone": profile_data.get("timezone"),
        "language": profile_data.get("language"),
        "communication_style": profile_data.get("communication_style"),
        "technical_level": profile_data.get("technical_level"),
        "now": now,
    }

    async with driver.session(database=database) as session:

        async def _write(tx: Any) -> None:
            await tx.run(_MERGE_USER_PROFILE, params)

        await session.execute_write(_write)

    log.info("wrote_user_profile", user_id=user_id, profile_id=profile_id)


async def write_preference_with_edges(
    driver: AsyncDriver,
    database: str,
    user_entity_id: str,
    preference_data: dict[str, Any],
    source_event_ids: list[str],
    derivation_info: dict[str, Any],
) -> None:
    """Write a Preference node with HAS_PREFERENCE, ABOUT, and DERIVED_FROM edges."""
    now = datetime.now(UTC).isoformat()
    preference_id = preference_data.get("preference_id", f"pref:{uuid4().hex[:12]}")

    pref_params = {
        "preference_id": preference_id,
        "category": preference_data.get("category", "domain"),
        "key": preference_data.get("key", ""),
        "polarity": preference_data.get("polarity", "neutral"),
        "strength": preference_data.get("strength", 0.5),
        "confidence": preference_data.get("confidence", 0.5),
        "source": preference_data.get("source", "inferred"),
        "context": preference_data.get("context"),
        "scope": preference_data.get("scope", "global"),
        "scope_id": preference_data.get("scope_id"),
        "superseded_by": preference_data.get("superseded_by"),
        "now": now,
    }

    has_pref_params = {
        "user_entity_id": user_entity_id,
        "preference_id": preference_id,
    }

    async with driver.session(database=database) as session:

        async def _write(tx: Any) -> None:
            # Ensure user entity exists
            await tx.run(
                "MERGE (e:Entity {entity_id: $user_entity_id}) "
                "ON CREATE SET e.entity_type = 'user', "
                "e.name = $user_entity_id, "
                "e.first_seen = $now, "
                "e.last_seen = $now, "
                "e.mention_count = 1",
                {
                    "user_entity_id": user_entity_id,
                    "now": now,
                },
            )
            # Create preference node
            await tx.run(_MERGE_PREFERENCE, pref_params)
            # Create HAS_PREFERENCE edge
            await tx.run(_MERGE_HAS_PREFERENCE_EDGE, has_pref_params)

            # Create ABOUT edge if about_entity is specified
            about_entity = preference_data.get("about_entity")
            if about_entity:
                target_entity_id = f"entity:{about_entity}"
                await tx.run(
                    _MERGE_PREFERENCE_ABOUT,
                    {
                        "preference_id": preference_id,
                        "target_entity_id": target_entity_id,
                        "target_name": about_entity,
                        "target_type": "concept",
                        "now": now,
                    },
                )

            # Create DERIVED_FROM edges to source events
            for event_id in source_event_ids:
                query = _MERGE_DERIVED_FROM % "preference_id"
                await tx.run(
                    query,
                    {
                        "source_id": preference_id,
                        "event_id": event_id,
                        "method": derivation_info.get("method", "llm_extraction"),
                        "session_id": derivation_info.get("session_id", ""),
                        "now": now,
                    },
                )

        await session.execute_write(_write)

    log.info(
        "wrote_preference",
        preference_id=preference_id,
        user_entity_id=user_entity_id,
        source_events=len(source_event_ids),
    )


async def write_skill_with_edges(
    driver: AsyncDriver,
    database: str,
    user_entity_id: str,
    skill_data: dict[str, Any],
    source_event_ids: list[str],
    derivation_info: dict[str, Any],
) -> None:
    """Write a Skill node with HAS_SKILL and DERIVED_FROM edges."""
    now = datetime.now(UTC).isoformat()
    skill_id = skill_data.get("skill_id", f"skill:{uuid4().hex[:12]}")

    skill_params = {
        "skill_id": skill_id,
        "name": skill_data.get("name", ""),
        "category": skill_data.get("category", "domain_knowledge"),
        "description": skill_data.get("description"),
        "now": now,
    }

    has_skill_params = {
        "user_entity_id": user_entity_id,
        "skill_id": skill_id,
        "proficiency": skill_data.get("proficiency", 0.5),
        "confidence": skill_data.get("confidence", 0.5),
        "source": skill_data.get("source", "inferred"),
        "now": now,
    }

    async with driver.session(database=database) as session:

        async def _write(tx: Any) -> None:
            # Ensure user entity exists
            await tx.run(
                "MERGE (e:Entity {entity_id: $user_entity_id}) "
                "ON CREATE SET e.entity_type = 'user', "
                "e.name = $user_entity_id, "
                "e.first_seen = $now, "
                "e.last_seen = $now, "
                "e.mention_count = 1",
                {
                    "user_entity_id": user_entity_id,
                    "now": now,
                },
            )
            # Create skill node
            await tx.run(_MERGE_SKILL, skill_params)
            # Create HAS_SKILL edge
            await tx.run(_MERGE_HAS_SKILL_EDGE, has_skill_params)

            # Create DERIVED_FROM edges to source events
            for event_id in source_event_ids:
                query = _MERGE_DERIVED_FROM % "skill_id"
                await tx.run(
                    query,
                    {
                        "source_id": skill_id,
                        "event_id": event_id,
                        "method": derivation_info.get("method", "llm_extraction"),
                        "session_id": derivation_info.get("session_id", ""),
                        "now": now,
                    },
                )

        await session.execute_write(_write)

    log.info(
        "wrote_skill",
        skill_id=skill_id,
        user_entity_id=user_entity_id,
        source_events=len(source_event_ids),
    )


async def write_interest_edge(
    driver: AsyncDriver,
    database: str,
    user_entity_id: str,
    entity_name: str,
    entity_type: str,
    weight: float,
    source: str,
) -> None:
    """Create an INTERESTED_IN edge from user to a target entity."""
    now = datetime.now(UTC).isoformat()
    target_entity_id = f"entity:{entity_name}"

    params = {
        "user_entity_id": user_entity_id,
        "target_entity_id": target_entity_id,
        "target_name": entity_name,
        "target_type": entity_type,
        "weight": weight,
        "source": source,
        "now": now,
    }

    async with driver.session(database=database) as session:

        async def _write(tx: Any) -> None:
            # Ensure user entity exists
            await tx.run(
                "MERGE (e:Entity {entity_id: $user_entity_id}) "
                "ON CREATE SET e.entity_type = 'user', "
                "e.name = $user_entity_id, "
                "e.first_seen = $now, "
                "e.last_seen = $now, "
                "e.mention_count = 1",
                {
                    "user_entity_id": user_entity_id,
                    "now": now,
                },
            )
            await tx.run(_MERGE_INTERESTED_IN, params)

        await session.execute_write(_write)

    log.info(
        "wrote_interest",
        user_entity_id=user_entity_id,
        target=entity_name,
        weight=weight,
    )


# ---------------------------------------------------------------------------
# GDPR Functions
# ---------------------------------------------------------------------------


async def delete_user_data(
    driver: AsyncDriver,
    database: str,
    user_id: str,
) -> int:
    """GDPR cascade delete: remove all user-specific nodes and anonymize Entity.

    Deletes UserProfile, Preference, BehavioralPattern nodes and their edges.
    Removes HAS_SKILL and INTERESTED_IN edges. Anonymizes the Entity node
    (sets name to 'REDACTED').

    Returns the number of affected entities (0 or 1).
    """
    async with driver.session(database=database) as session:

        async def _delete(tx: Any) -> int:
            result = await tx.run(_DELETE_USER_DATA, {"user_id": user_id})
            record = await result.single()
            return record["affected"] if record else 0

        affected: int = await session.execute_write(_delete)

    log.info("gdpr_delete_user_data", user_id=user_id, affected=affected)
    return affected


async def export_user_data(
    driver: AsyncDriver,
    database: str,
    user_id: str,
) -> dict[str, Any]:
    """GDPR export: return all data associated with a user.

    Returns a dict with keys: profile, preferences, skills, patterns, interests.
    """
    export: dict[str, Any] = {
        "user_id": user_id,
        "profile": None,
        "preferences": [],
        "skills": [],
        "patterns": [],
        "interests": [],
    }

    async with driver.session(database=database) as session:
        # Profile
        profile_result = await session.run(_EXPORT_USER_PROFILE, {"user_id": user_id})
        profile_record = await profile_result.single()
        if profile_record:
            export["profile"] = dict(profile_record["profile"])

        # Preferences
        pref_result = await session.run(_EXPORT_USER_PREFERENCES, {"user_id": user_id})
        pref_records = [record async for record in pref_result]
        export["preferences"] = [dict(r["preference"]) for r in pref_records]

        # Skills
        skill_result = await session.run(_EXPORT_USER_SKILLS, {"user_id": user_id})
        skill_records = [record async for record in skill_result]
        export["skills"] = [dict(r["skill"]) for r in skill_records]

        # Patterns
        pattern_result = await session.run(_EXPORT_USER_PATTERNS, {"user_id": user_id})
        pattern_records = [record async for record in pattern_result]
        export["patterns"] = [dict(r["pattern"]) for r in pattern_records]

        # Interests
        interest_result = await session.run(_EXPORT_USER_INTERESTS, {"user_id": user_id})
        interest_records = [record async for record in interest_result]
        export["interests"] = [
            {
                "entity_id": r["entity_id"],
                "name": r["name"],
                "entity_type": r["entity_type"],
                "weight": r["weight"],
                "source": r["source"],
            }
            for r in interest_records
        ]

    log.info(
        "gdpr_export_user_data",
        user_id=user_id,
        preferences=len(export["preferences"]),
        skills=len(export["skills"]),
        patterns=len(export["patterns"]),
        interests=len(export["interests"]),
    )
    return export
