"""Cypher query templates for Neo4j graph operations.

All queries use MERGE for idempotent writes. Relationship types are
statically defined because Neo4j Community Edition does not support
APOC procedures for dynamic relationship creation.

Source: ADR-0009, ADR-0011
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Constraints (matches docker/neo4j/constraints.cypher)
# ---------------------------------------------------------------------------

CONSTRAINT_EVENT_PK = (
    "CREATE CONSTRAINT event_pk IF NOT EXISTS FOR (e:Event) REQUIRE e.event_id IS UNIQUE"
)

CONSTRAINT_ENTITY_PK = (
    "CREATE CONSTRAINT entity_pk IF NOT EXISTS FOR (n:Entity) REQUIRE n.entity_id IS UNIQUE"
)

CONSTRAINT_SUMMARY_PK = (
    "CREATE CONSTRAINT summary_pk IF NOT EXISTS FOR (s:Summary) REQUIRE s.summary_id IS UNIQUE"
)

CONSTRAINT_USERPROFILE_PK = (
    "CREATE CONSTRAINT userprofile_pk IF NOT EXISTS FOR (u:UserProfile) REQUIRE u.user_id IS UNIQUE"
)

CONSTRAINT_PREFERENCE_PK = (
    "CREATE CONSTRAINT preference_pk IF NOT EXISTS "
    "FOR (p:Preference) REQUIRE p.preference_id IS UNIQUE"
)

CONSTRAINT_SKILL_PK = (
    "CREATE CONSTRAINT skill_pk IF NOT EXISTS FOR (s:Skill) REQUIRE s.skill_id IS UNIQUE"
)

CONSTRAINT_WORKFLOW_PK = (
    "CREATE CONSTRAINT workflow_pk IF NOT EXISTS FOR (w:Workflow) REQUIRE w.workflow_id IS UNIQUE"
)

CONSTRAINT_BEHAVIORALPATTERN_PK = (
    "CREATE CONSTRAINT behavioralpattern_pk IF NOT EXISTS "
    "FOR (b:BehavioralPattern) REQUIRE b.pattern_id IS UNIQUE"
)

CONSTRAINT_BELIEF_PK = (
    "CREATE CONSTRAINT belief_pk IF NOT EXISTS FOR (b:Belief) REQUIRE b.belief_id IS UNIQUE"
)

CONSTRAINT_GOAL_PK = (
    "CREATE CONSTRAINT goal_pk IF NOT EXISTS FOR (g:Goal) REQUIRE g.goal_id IS UNIQUE"
)

CONSTRAINT_EPISODE_PK = (
    "CREATE CONSTRAINT episode_pk IF NOT EXISTS FOR (e:Episode) REQUIRE e.episode_id IS UNIQUE"
)

ALL_CONSTRAINTS = [
    CONSTRAINT_EVENT_PK,
    CONSTRAINT_ENTITY_PK,
    CONSTRAINT_SUMMARY_PK,
    CONSTRAINT_USERPROFILE_PK,
    CONSTRAINT_PREFERENCE_PK,
    CONSTRAINT_SKILL_PK,
    CONSTRAINT_WORKFLOW_PK,
    CONSTRAINT_BEHAVIORALPATTERN_PK,
    CONSTRAINT_BELIEF_PK,
    CONSTRAINT_GOAL_PK,
    CONSTRAINT_EPISODE_PK,
]

# ---------------------------------------------------------------------------
# Performance indexes
# ---------------------------------------------------------------------------

INDEX_EVENT_SESSION_ID = (
    "CREATE INDEX event_session_id IF NOT EXISTS FOR (e:Event) ON (e.session_id)"
)

# ---------------------------------------------------------------------------
# Tenant isolation indexes (one per node label)
# ---------------------------------------------------------------------------

INDEX_EVENT_TENANT = "CREATE INDEX event_tenant_idx IF NOT EXISTS FOR (e:Event) ON (e.tenant_id)"
INDEX_ENTITY_TENANT = "CREATE INDEX entity_tenant_idx IF NOT EXISTS FOR (n:Entity) ON (n.tenant_id)"
INDEX_SUMMARY_TENANT = (
    "CREATE INDEX summary_tenant_idx IF NOT EXISTS FOR (s:Summary) ON (s.tenant_id)"
)
INDEX_USERPROFILE_TENANT = (
    "CREATE INDEX userprofile_tenant_idx IF NOT EXISTS FOR (u:UserProfile) ON (u.tenant_id)"
)
INDEX_PREFERENCE_TENANT = (
    "CREATE INDEX preference_tenant_idx IF NOT EXISTS FOR (p:Preference) ON (p.tenant_id)"
)
INDEX_SKILL_TENANT = "CREATE INDEX skill_tenant_idx IF NOT EXISTS FOR (s:Skill) ON (s.tenant_id)"
INDEX_WORKFLOW_TENANT = (
    "CREATE INDEX workflow_tenant_idx IF NOT EXISTS FOR (w:Workflow) ON (w.tenant_id)"
)
INDEX_BEHAVIORAL_TENANT = (
    "CREATE INDEX behavioral_tenant_idx IF NOT EXISTS FOR (b:BehavioralPattern) ON (b.tenant_id)"
)
INDEX_BELIEF_TENANT = "CREATE INDEX belief_tenant_idx IF NOT EXISTS FOR (b:Belief) ON (b.tenant_id)"
INDEX_GOAL_TENANT = "CREATE INDEX goal_tenant_idx IF NOT EXISTS FOR (g:Goal) ON (g.tenant_id)"
INDEX_EPISODE_TENANT = (
    "CREATE INDEX episode_tenant_idx IF NOT EXISTS FOR (ep:Episode) ON (ep.tenant_id)"
)

TENANT_INDEXES = [
    INDEX_EVENT_TENANT,
    INDEX_ENTITY_TENANT,
    INDEX_SUMMARY_TENANT,
    INDEX_USERPROFILE_TENANT,
    INDEX_PREFERENCE_TENANT,
    INDEX_SKILL_TENANT,
    INDEX_WORKFLOW_TENANT,
    INDEX_BEHAVIORAL_TENANT,
    INDEX_BELIEF_TENANT,
    INDEX_GOAL_TENANT,
    INDEX_EPISODE_TENANT,
]

# ---------------------------------------------------------------------------
# Relationship indexes (Neo4j 5.7+) — accelerate edge-property queries
# ---------------------------------------------------------------------------

INDEX_FOLLOWS_REL = (
    "CREATE INDEX follows_rel_idx IF NOT EXISTS FOR ()-[r:FOLLOWS]-() ON (r.delta_ms)"
)
INDEX_SIMILAR_REL = (
    "CREATE INDEX similar_rel_idx IF NOT EXISTS FOR ()-[r:SIMILAR_TO]-() ON (r.similarity_score)"
)
INDEX_REFERENCES_REL = (
    "CREATE INDEX references_rel_idx IF NOT EXISTS FOR ()-[r:REFERENCES]-() ON (r.mention_count)"
)

RELATIONSHIP_INDEXES = [
    INDEX_FOLLOWS_REL,
    INDEX_SIMILAR_REL,
    INDEX_REFERENCES_REL,
]

# ---------------------------------------------------------------------------
# Composite indexes — eliminate full scans on multi-predicate queries
# ---------------------------------------------------------------------------

INDEX_EVENT_SESSION_TIME = (
    "CREATE INDEX event_session_time_idx IF NOT EXISTS "
    "FOR (e:Event) ON (e.session_id, e.occurred_at)"
)
INDEX_EVENT_TYPE_TENANT = (
    "CREATE INDEX event_type_tenant_idx IF NOT EXISTS FOR (e:Event) ON (e.event_type, e.tenant_id)"
)
INDEX_ENTITY_TYPE_TENANT = (
    "CREATE INDEX entity_type_tenant_idx IF NOT EXISTS "
    "FOR (e:Entity) ON (e.entity_type, e.tenant_id)"
)

COMPOSITE_INDEXES = [
    INDEX_EVENT_SESSION_TIME,
    INDEX_EVENT_TYPE_TENANT,
    INDEX_ENTITY_TYPE_TENANT,
]

# ---------------------------------------------------------------------------
# Property indexes for hot queries
# ---------------------------------------------------------------------------

INDEX_EVENT_IMPORTANCE = (
    "CREATE INDEX event_importance_idx IF NOT EXISTS FOR (e:Event) ON (e.importance_score)"
)
INDEX_EVENT_ACCESS_COUNT = (
    "CREATE INDEX event_access_count_idx IF NOT EXISTS FOR (e:Event) ON (e.access_count)"
)
INDEX_ENTITY_NAME = "CREATE INDEX entity_name_idx IF NOT EXISTS FOR (e:Entity) ON (e.name)"

PROPERTY_INDEXES = [
    INDEX_EVENT_IMPORTANCE,
    INDEX_EVENT_ACCESS_COUNT,
    INDEX_ENTITY_NAME,
]

ALL_INDEXES = [
    INDEX_EVENT_SESSION_ID,
    *TENANT_INDEXES,
    *RELATIONSHIP_INDEXES,
    *COMPOSITE_INDEXES,
    *PROPERTY_INDEXES,
]

# ---------------------------------------------------------------------------
# Vector indexes
# ---------------------------------------------------------------------------

VECTOR_INDEX_ENTITY_EMBEDDING = (
    "CREATE VECTOR INDEX entity_embedding_idx IF NOT EXISTS "
    "FOR (n:Entity) ON (n.embedding) "
    "OPTIONS {indexConfig: {"
    "`vector.dimensions`: 384, "
    "`vector.similarity_function`: 'cosine'"
    "}}"
)

ALL_VECTOR_INDEXES = [VECTOR_INDEX_ENTITY_EMBEDDING]

# ---------------------------------------------------------------------------
# Node MERGE queries
# ---------------------------------------------------------------------------

MERGE_EVENT_NODE = """
MERGE (e:Event {event_id: $event_id})
SET e.event_type = $event_type,
    e.occurred_at = $occurred_at,
    e.session_id = $session_id,
    e.agent_id = $agent_id,
    e.trace_id = $trace_id,
    e.tool_name = $tool_name,
    e.global_position = $global_position,
    e.keywords = $keywords,
    e.summary = $summary,
    e.importance_score = $importance_score,
    e.access_count = $access_count,
    e.last_accessed_at = $last_accessed_at,
    e.tenant_id = $tenant_id
""".strip()

BATCH_MERGE_EVENT_NODES = """
UNWIND $events AS evt
MERGE (e:Event {event_id: evt.event_id})
SET e.event_type = evt.event_type,
    e.occurred_at = evt.occurred_at,
    e.session_id = evt.session_id,
    e.agent_id = evt.agent_id,
    e.trace_id = evt.trace_id,
    e.tool_name = evt.tool_name,
    e.global_position = evt.global_position,
    e.keywords = evt.keywords,
    e.summary = evt.summary,
    e.importance_score = evt.importance_score,
    e.access_count = evt.access_count,
    e.last_accessed_at = evt.last_accessed_at,
    e.tenant_id = evt.tenant_id
""".strip()

MERGE_ENTITY_NODE = """
MERGE (n:Entity {entity_id: $entity_id})
SET n.name = $name,
    n.entity_type = $entity_type,
    n.first_seen = $first_seen,
    n.last_seen = $last_seen,
    n.mention_count = $mention_count,
    n.embedding = $embedding,
    n.tenant_id = $tenant_id
""".strip()

MERGE_SUMMARY_NODE = """
MERGE (s:Summary {summary_id: $summary_id})
SET s.scope = $scope,
    s.scope_id = $scope_id,
    s.content = $content,
    s.created_at = $created_at,
    s.event_count = $event_count,
    s.time_range = $time_range,
    s.tenant_id = $tenant_id
""".strip()

MERGE_BELIEF_NODE = """
MERGE (b:Belief {belief_id: $belief_id})
SET b.belief_text = $belief_text,
    b.confidence = $confidence,
    b.category = $category,
    b.created_at = $created_at,
    b.last_confirmed_at = $last_confirmed_at,
    b.confirmation_count = $confirmation_count,
    b.superseded_by = $superseded_by,
    b.tenant_id = $tenant_id
""".strip()

MERGE_GOAL_NODE = """
MERGE (g:Goal {goal_id: $goal_id})
SET g.description = $description,
    g.status = $status,
    g.created_at = $created_at,
    g.last_active_at = $last_active_at,
    g.priority = $priority,
    g.evidence_count = $evidence_count,
    g.tenant_id = $tenant_id
""".strip()

MERGE_EPISODE_NODE = """
MERGE (e:Episode {episode_id: $episode_id})
SET e.session_id = $session_id,
    e.start_time = $start_time,
    e.end_time = $end_time,
    e.event_count = $event_count,
    e.episode_type = $episode_type,
    e.summary_id = $summary_id,
    e.tenant_id = $tenant_id
""".strip()

# ---------------------------------------------------------------------------
# Edge MERGE queries — one per EdgeType (Neo4j Community, no APOC)
# ---------------------------------------------------------------------------

# Each template expects: $source_id, $target_id, plus relationship properties.
# The source/target node labels and ID fields vary by edge type.

# We use a two-step pattern:
#   MATCH source by label + id field
#   MATCH target by label + id field
#   MERGE relationship
#   SET properties

# Helper: source_label, source_id_field, target_label, target_id_field per edge type
# is handled in store.py. The templates below are the raw Cypher per relationship type.

MERGE_FOLLOWS = """
MATCH (a:Event {event_id: $source_id})
MATCH (b:Event {event_id: $target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:FOLLOWS]->(b)
SET r += $props
""".strip()

MERGE_CAUSED_BY = """
MATCH (a:Event {event_id: $source_id})
MATCH (b:Event {event_id: $target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:CAUSED_BY]->(b)
SET r += $props
""".strip()

MERGE_SIMILAR_TO = """
MATCH (a:Event {event_id: $source_id})
MATCH (b:Event {event_id: $target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:SIMILAR_TO]->(b)
SET r += $props
""".strip()

MERGE_REFERENCES = """
MATCH (a:Event {event_id: $source_id})
MATCH (b:Entity {entity_id: $target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:REFERENCES]->(b)
SET r += $props
""".strip()

MERGE_SUMMARIZES = """
MATCH (a:Summary {summary_id: $source_id})
MATCH (b {event_id: $target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:SUMMARIZES]->(b)
SET r += $props
""".strip()

MERGE_SAME_AS = """
MATCH (a:Entity {entity_id: $source_id})
MATCH (b:Entity {entity_id: $target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:SAME_AS]->(b)
SET r += $props
""".strip()

MERGE_RELATED_TO = """
MATCH (a:Entity {entity_id: $source_id})
MATCH (b:Entity {entity_id: $target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:RELATED_TO]->(b)
SET r += $props
""".strip()

MERGE_HAS_PROFILE = """
MATCH (a:Entity {entity_id: $source_id})
MATCH (b:UserProfile {profile_id: $target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:HAS_PROFILE]->(b)
SET r += $props
""".strip()

MERGE_HAS_PREFERENCE = """
MATCH (a:Entity {entity_id: $source_id})
MATCH (b:Preference {preference_id: $target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:HAS_PREFERENCE]->(b)
SET r += $props
""".strip()

MERGE_HAS_SKILL = """
MATCH (a:Entity {entity_id: $source_id})
MATCH (b:Skill {skill_id: $target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:HAS_SKILL]->(b)
SET r += $props
""".strip()

MERGE_DERIVED_FROM = """
MATCH (a {preference_id: $source_id})
MATCH (b:Event {event_id: $target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:DERIVED_FROM]->(b)
SET r += $props
""".strip()

MERGE_EXHIBITS_PATTERN = """
MATCH (a:Entity {entity_id: $source_id})
MATCH (b:BehavioralPattern {pattern_id: $target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:EXHIBITS_PATTERN]->(b)
SET r += $props
""".strip()

MERGE_INTERESTED_IN = """
MATCH (a:Entity {entity_id: $source_id})
MATCH (b:Entity {entity_id: $target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:INTERESTED_IN]->(b)
SET r += $props
""".strip()

MERGE_ABOUT = """
MATCH (a:Preference {preference_id: $source_id})
MATCH (b:Entity {entity_id: $target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:ABOUT]->(b)
SET r += $props
""".strip()

MERGE_ABSTRACTED_FROM = """
MATCH (a:Workflow {workflow_id: $source_id})
MATCH (b:Workflow {workflow_id: $target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:ABSTRACTED_FROM]->(b)
SET r += $props
""".strip()

MERGE_PARENT_SKILL = """
MATCH (a:Skill {skill_id: $source_id})
MATCH (b:Skill {skill_id: $target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:PARENT_SKILL]->(b)
SET r += $props
""".strip()

MERGE_CONTRADICTS = """
MATCH (a:Belief {belief_id: $source_id})
MATCH (b:Belief {belief_id: $target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:CONTRADICTS]->(b)
SET r += $props
""".strip()

MERGE_SUPERSEDES = """
MATCH (a:Belief {belief_id: $source_id})
MATCH (b:Belief {belief_id: $target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:SUPERSEDES]->(b)
SET r += $props
""".strip()

MERGE_PURSUES = """
MATCH (a:Entity {entity_id: $source_id})
MATCH (b:Goal {goal_id: $target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:PURSUES]->(b)
SET r += $props
""".strip()

MERGE_CONTAINS = """
MATCH (a:Episode {episode_id: $source_id})
MATCH (b:Event {event_id: $target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:CONTAINS]->(b)
SET r += $props
""".strip()

# ---------------------------------------------------------------------------
# Batch edge creation via UNWIND
# ---------------------------------------------------------------------------

# For batch edges of a single type, we UNWIND a list of parameter maps.
# Each edge type needs its own batch query. For Phase 2, we provide
# batch templates for FOLLOWS and CAUSED_BY (used by Consumer 1).

BATCH_MERGE_FOLLOWS = """
UNWIND $edges AS edge
MATCH (a:Event {event_id: edge.source_id})
MATCH (b:Event {event_id: edge.target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:FOLLOWS]->(b)
SET r += edge.props
""".strip()

BATCH_MERGE_CAUSED_BY = """
UNWIND $edges AS edge
MATCH (a:Event {event_id: edge.source_id})
MATCH (b:Event {event_id: edge.target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:CAUSED_BY]->(b)
SET r += edge.props
""".strip()

# ---------------------------------------------------------------------------
# Batch node MERGE templates (UNWIND) — remaining node types
# ---------------------------------------------------------------------------

BATCH_MERGE_ENTITY_NODES = """
UNWIND $nodes AS node
MERGE (n:Entity {entity_id: node.entity_id})
SET n.name = node.name,
    n.entity_type = node.entity_type,
    n.first_seen = node.first_seen,
    n.last_seen = node.last_seen,
    n.mention_count = node.mention_count,
    n.embedding = node.embedding,
    n.tenant_id = node.tenant_id
""".strip()

BATCH_MERGE_SUMMARY_NODES = """
UNWIND $nodes AS node
MERGE (s:Summary {summary_id: node.summary_id})
SET s.scope = node.scope,
    s.scope_id = node.scope_id,
    s.content = node.content,
    s.created_at = node.created_at,
    s.event_count = node.event_count,
    s.time_range = node.time_range,
    s.tenant_id = node.tenant_id
""".strip()

BATCH_MERGE_BELIEF_NODES = """
UNWIND $nodes AS node
MERGE (b:Belief {belief_id: node.belief_id})
SET b.belief_text = node.belief_text,
    b.confidence = node.confidence,
    b.category = node.category,
    b.created_at = node.created_at,
    b.last_confirmed_at = node.last_confirmed_at,
    b.confirmation_count = node.confirmation_count,
    b.superseded_by = node.superseded_by,
    b.tenant_id = node.tenant_id
""".strip()

BATCH_MERGE_GOAL_NODES = """
UNWIND $nodes AS node
MERGE (g:Goal {goal_id: node.goal_id})
SET g.description = node.description,
    g.status = node.status,
    g.created_at = node.created_at,
    g.last_active_at = node.last_active_at,
    g.priority = node.priority,
    g.evidence_count = node.evidence_count,
    g.tenant_id = node.tenant_id
""".strip()

BATCH_MERGE_EPISODE_NODES = """
UNWIND $nodes AS node
MERGE (e:Episode {episode_id: node.episode_id})
SET e.session_id = node.session_id,
    e.start_time = node.start_time,
    e.end_time = node.end_time,
    e.event_count = node.event_count,
    e.episode_type = node.episode_type,
    e.summary_id = node.summary_id,
    e.tenant_id = node.tenant_id
""".strip()

# ---------------------------------------------------------------------------
# Batch edge MERGE templates (UNWIND) — remaining 18 edge types
# ---------------------------------------------------------------------------

BATCH_MERGE_SIMILAR_TO = """
UNWIND $edges AS edge
MATCH (a:Event {event_id: edge.source_id})
MATCH (b:Event {event_id: edge.target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:SIMILAR_TO]->(b)
SET r += edge.props
""".strip()

BATCH_MERGE_REFERENCES = """
UNWIND $edges AS edge
MATCH (a:Event {event_id: edge.source_id})
MATCH (b:Entity {entity_id: edge.target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:REFERENCES]->(b)
SET r += edge.props
""".strip()

BATCH_MERGE_SUMMARIZES = """
UNWIND $edges AS edge
MATCH (a:Summary {summary_id: edge.source_id})
MATCH (b {event_id: edge.target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:SUMMARIZES]->(b)
SET r += edge.props
""".strip()

BATCH_MERGE_SAME_AS = """
UNWIND $edges AS edge
MATCH (a:Entity {entity_id: edge.source_id})
MATCH (b:Entity {entity_id: edge.target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:SAME_AS]->(b)
SET r += edge.props
""".strip()

BATCH_MERGE_RELATED_TO = """
UNWIND $edges AS edge
MATCH (a:Entity {entity_id: edge.source_id})
MATCH (b:Entity {entity_id: edge.target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:RELATED_TO]->(b)
SET r += edge.props
""".strip()

BATCH_MERGE_HAS_PROFILE = """
UNWIND $edges AS edge
MATCH (a:Entity {entity_id: edge.source_id})
MATCH (b:UserProfile {profile_id: edge.target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:HAS_PROFILE]->(b)
SET r += edge.props
""".strip()

BATCH_MERGE_HAS_PREFERENCE = """
UNWIND $edges AS edge
MATCH (a:Entity {entity_id: edge.source_id})
MATCH (b:Preference {preference_id: edge.target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:HAS_PREFERENCE]->(b)
SET r += edge.props
""".strip()

BATCH_MERGE_HAS_SKILL = """
UNWIND $edges AS edge
MATCH (a:Entity {entity_id: edge.source_id})
MATCH (b:Skill {skill_id: edge.target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:HAS_SKILL]->(b)
SET r += edge.props
""".strip()

BATCH_MERGE_DERIVED_FROM = """
UNWIND $edges AS edge
MATCH (a {preference_id: edge.source_id})
MATCH (b:Event {event_id: edge.target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:DERIVED_FROM]->(b)
SET r += edge.props
""".strip()

BATCH_MERGE_EXHIBITS_PATTERN = """
UNWIND $edges AS edge
MATCH (a:Entity {entity_id: edge.source_id})
MATCH (b:BehavioralPattern {pattern_id: edge.target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:EXHIBITS_PATTERN]->(b)
SET r += edge.props
""".strip()

BATCH_MERGE_INTERESTED_IN = """
UNWIND $edges AS edge
MATCH (a:Entity {entity_id: edge.source_id})
MATCH (b:Entity {entity_id: edge.target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:INTERESTED_IN]->(b)
SET r += edge.props
""".strip()

BATCH_MERGE_ABOUT = """
UNWIND $edges AS edge
MATCH (a:Preference {preference_id: edge.source_id})
MATCH (b:Entity {entity_id: edge.target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:ABOUT]->(b)
SET r += edge.props
""".strip()

BATCH_MERGE_ABSTRACTED_FROM = """
UNWIND $edges AS edge
MATCH (a:Workflow {workflow_id: edge.source_id})
MATCH (b:Workflow {workflow_id: edge.target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:ABSTRACTED_FROM]->(b)
SET r += edge.props
""".strip()

BATCH_MERGE_PARENT_SKILL = """
UNWIND $edges AS edge
MATCH (a:Skill {skill_id: edge.source_id})
MATCH (b:Skill {skill_id: edge.target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:PARENT_SKILL]->(b)
SET r += edge.props
""".strip()

BATCH_MERGE_CONTRADICTS = """
UNWIND $edges AS edge
MATCH (a:Belief {belief_id: edge.source_id})
MATCH (b:Belief {belief_id: edge.target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:CONTRADICTS]->(b)
SET r += edge.props
""".strip()

BATCH_MERGE_SUPERSEDES = """
UNWIND $edges AS edge
MATCH (a:Belief {belief_id: edge.source_id})
MATCH (b:Belief {belief_id: edge.target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:SUPERSEDES]->(b)
SET r += edge.props
""".strip()

BATCH_MERGE_PURSUES = """
UNWIND $edges AS edge
MATCH (a:Entity {entity_id: edge.source_id})
MATCH (b:Goal {goal_id: edge.target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:PURSUES]->(b)
SET r += edge.props
""".strip()

BATCH_MERGE_CONTAINS = """
UNWIND $edges AS edge
MATCH (a:Episode {episode_id: edge.source_id})
MATCH (b:Event {event_id: edge.target_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
MERGE (a)-[r:CONTAINS]->(b)
SET r += edge.props
""".strip()

# ---------------------------------------------------------------------------
# Phase 3: Traversal and context queries
# ---------------------------------------------------------------------------

GET_SESSION_EVENTS = """
MATCH (e:Event {session_id: $session_id})
WHERE e.tenant_id = $tenant_id
RETURN e ORDER BY e.occurred_at DESC LIMIT $limit
""".strip()

GET_SESSION_EVENT_COUNT = """
MATCH (e:Event {session_id: $session_id})
WHERE e.tenant_id = $tenant_id
RETURN count(e) AS cnt
""".strip()

GET_LINEAGE = """
MATCH path = (start:Event {event_id: $node_id})-[:CAUSED_BY*1..10]->(ancestor)
WHERE start.tenant_id = $tenant_id
  AND ALL(n IN nodes(path) WHERE n.tenant_id = $tenant_id)
WITH start, nodes(path) AS chain_nodes, relationships(path) AS chain_rels,
     length(path) AS depth
WHERE depth <= $max_depth
RETURN start, chain_nodes, chain_rels
LIMIT $max_nodes
""".strip()

GET_EVENT_NEIGHBORS = """
MATCH (e:Event {event_id: $event_id})
WHERE e.tenant_id = $tenant_id
OPTIONAL MATCH (e)-[r]->(neighbor)
WHERE neighbor.tenant_id = $tenant_id
RETURN e, type(r) AS rel_type, properties(r) AS rel_props,
       labels(neighbor) AS neighbor_labels, properties(neighbor) AS neighbor_props,
       neighbor.event_id AS neighbor_event_id,
       neighbor.entity_id AS neighbor_entity_id,
       neighbor.summary_id AS neighbor_summary_id
LIMIT $neighbor_limit
""".strip()

GET_EVENT_NEIGHBORS_BATCH = """
UNWIND $event_ids AS eid
MATCH (e:Event {event_id: eid})
WHERE e.tenant_id = $tenant_id
OPTIONAL MATCH (e)-[r]->(neighbor)
WHERE neighbor.tenant_id = $tenant_id
RETURN e.event_id AS seed_event_id,
       type(r) AS rel_type, properties(r) AS rel_props,
       labels(neighbor) AS neighbor_labels, properties(neighbor) AS neighbor_props,
       neighbor.event_id AS neighbor_event_id,
       neighbor.entity_id AS neighbor_entity_id,
       neighbor.summary_id AS neighbor_summary_id
LIMIT $neighbor_limit
""".strip()

GET_ENTITY_WITH_EVENTS = """
MATCH (ent:Entity {entity_id: $entity_id})
WHERE ent.tenant_id = $tenant_id
OPTIONAL MATCH (evt:Event)-[r:REFERENCES]->(ent)
WHERE evt.tenant_id = $tenant_id
RETURN ent, evt, properties(r) AS ref_props
ORDER BY evt.occurred_at DESC
LIMIT $limit
""".strip()

GET_ENTITY_WITH_CLUSTER = """
MATCH (ent:Entity {entity_id: $entity_id})
WHERE ent.tenant_id = $tenant_id
OPTIONAL MATCH (ent)-[:SAME_AS*0..3]-(related:Entity)
WHERE related.tenant_id = $tenant_id
WITH DISTINCT related
OPTIONAL MATCH (evt:Event)-[r:REFERENCES]->(related)
WHERE evt.tenant_id = $tenant_id
RETURN related AS ent, evt, properties(r) AS ref_props
ORDER BY evt.occurred_at DESC
LIMIT $limit
""".strip()

CONSOLIDATE_ENTITY_CLUSTER = """
UNWIND $member_ids AS mid
MATCH (member:Entity {entity_id: mid})
WHERE member.tenant_id = $tenant_id
MATCH (canonical:Entity {entity_id: $canonical_id})
WHERE canonical.tenant_id = $tenant_id AND member <> canonical
MERGE (member)-[r:SAME_AS]->(canonical)
SET r.confidence = 1.0,
    r.justification = 'transitive_closure',
    r.resolved_at = $resolved_at
""".strip()

UPDATE_ACCESS_COUNT = """
MATCH (e:Event {event_id: $event_id})
WHERE e.tenant_id = $tenant_id
SET e.access_count = coalesce(e.access_count, 0) + 1,
    e.last_accessed_at = $now
""".strip()

BATCH_UPDATE_ACCESS_COUNT = """
UNWIND $event_ids AS eid
MATCH (e:Event {event_id: eid})
WHERE e.tenant_id = $tenant_id
SET e.access_count = coalesce(e.access_count, 0) + 1,
    e.last_accessed_at = $now
""".strip()

UPDATE_EVENT_ENRICHMENT = """
MATCH (e:Event {event_id: $event_id})
WHERE e.tenant_id = $tenant_id
SET e.keywords = $keywords,
    e.importance_score = $importance_score
""".strip()

UPDATE_EVENT_EMBEDDING = """
MATCH (e:Event {event_id: $event_id})
WHERE e.tenant_id = $tenant_id
SET e.embedding = $embedding
""".strip()

# ---------------------------------------------------------------------------
# Neo4j vector index search (entity embeddings)
# ---------------------------------------------------------------------------

SEARCH_SIMILAR_ENTITIES = """
CALL db.index.vector.queryNodes('entity_embedding_idx', $top_k, $query_embedding)
YIELD node, score
WHERE score >= $threshold AND node.tenant_id = $tenant_id
RETURN node.entity_id AS entity_id, node.name AS name,
       node.entity_type AS entity_type, score
ORDER BY score DESC
""".strip()

GET_SESSION_EDGES = """
MATCH (a:Event {session_id: $session_id})-[r]->(b:Event {session_id: $session_id})
WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
  AND a.event_id IN $event_ids AND b.event_id IN $event_ids
RETURN a.event_id AS source, b.event_id AS target,
       type(r) AS edge_type, properties(r) AS props
""".strip()

GET_SESSION_NEIGHBORS = """
MATCH (e:Event {session_id: $session_id})-[r]->(n)
WHERE e.tenant_id = $tenant_id
  AND e.event_id IN $event_ids
  AND NOT n:Event
  AND n.tenant_id = $tenant_id
RETURN e.event_id AS source_event_id,
       type(r) AS edge_type, properties(r) AS edge_props,
       labels(n) AS neighbor_labels, properties(n) AS neighbor_props,
       coalesce(n.entity_id, n.preference_id, n.skill_id,
                n.profile_id, n.summary_id, n.pattern_id,
                n.workflow_id, n.belief_id, n.goal_id,
                n.episode_id) AS neighbor_id
LIMIT 500
""".strip()

GET_NEIGHBOR_INTER_EDGES = """
UNWIND $neighbor_ids AS nid
MATCH (a)-[r]->(b)
WHERE coalesce(a.entity_id, a.preference_id, a.skill_id,
               a.profile_id, a.pattern_id, a.workflow_id) = nid
  AND NOT a:Event AND NOT b:Event
  AND a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id
  AND coalesce(b.entity_id, b.preference_id, b.skill_id,
               b.profile_id, b.pattern_id, b.workflow_id) IN $neighbor_ids
RETURN coalesce(a.entity_id, a.preference_id, a.skill_id,
                a.profile_id, a.pattern_id, a.workflow_id) AS source,
       coalesce(b.entity_id, b.preference_id, b.skill_id,
                b.profile_id, b.pattern_id, b.workflow_id) AS target,
       type(r) AS edge_type, properties(r) AS props
LIMIT 200
""".strip()

GET_SUBGRAPH_SEED_EVENTS = """
MATCH (e:Event {session_id: $session_id})
WHERE e.tenant_id = $tenant_id
RETURN e ORDER BY e.occurred_at DESC LIMIT $seed_limit
""".strip()

# ---------------------------------------------------------------------------
# Intent-based seed selection strategies (Phase 1.2)
# ---------------------------------------------------------------------------

GET_SEED_CAUSAL_ROOTS = """
MATCH (e:Event {session_id: $session_id})
WHERE e.tenant_id = $tenant_id AND (e)<-[:CAUSED_BY]-()
WITH e, size([(x)-[:CAUSED_BY]->(e) | x]) AS caused_count
RETURN e ORDER BY caused_count DESC, e.occurred_at DESC
LIMIT $seed_limit
""".strip()

GET_SEED_ENTITY_HUBS = """
MATCH (e:Event {session_id: $session_id})-[:REFERENCES]->(ent:Entity)
WHERE e.tenant_id = $tenant_id
WITH e, count(ent) AS entity_count
RETURN e ORDER BY entity_count DESC, e.occurred_at DESC
LIMIT $seed_limit
""".strip()

GET_SEED_TEMPORAL_ANCHORS = """
MATCH (e:Event {session_id: $session_id})
WHERE e.tenant_id = $tenant_id AND e.importance_score IS NOT NULL
RETURN e ORDER BY e.importance_score DESC, e.occurred_at ASC
LIMIT $seed_limit
""".strip()

GET_SEED_USER_PROFILE = """
MATCH (e:Event {session_id: $session_id})-[:REFERENCES]->(ent:Entity)
WHERE e.tenant_id = $tenant_id
  AND ((ent)-[:HAS_PROFILE]->() OR (ent)-[:HAS_PREFERENCE]->())
WITH e, count(ent) AS profile_links
RETURN e ORDER BY profile_links DESC, e.occurred_at DESC
LIMIT $seed_limit
""".strip()

GET_SEED_SIMILAR_CLUSTER = """
MATCH (e:Event {session_id: $session_id})
WHERE e.tenant_id = $tenant_id
OPTIONAL MATCH (e)-[:SIMILAR_TO]-(other:Event)
WITH e, count(other) AS sim_count
RETURN e ORDER BY sim_count DESC, e.occurred_at DESC
LIMIT $seed_limit
""".strip()

GET_SEED_WORKFLOW_PATTERN = """
MATCH (e:Event {session_id: $session_id})
WHERE e.tenant_id = $tenant_id
  AND (e.event_type STARTS WITH 'tool.' OR e.event_type STARTS WITH 'workflow.')
RETURN e ORDER BY e.occurred_at ASC
LIMIT $seed_limit
""".strip()

# ---------------------------------------------------------------------------
# Cross-session entity retrieval (Phase 1.3)
# ---------------------------------------------------------------------------

GET_ENTITY_CROSS_SESSION_EVENTS = """
MATCH (e:Event {session_id: $session_id})-[:REFERENCES]->(ent:Entity)
WHERE e.tenant_id = $tenant_id
WITH DISTINCT ent
MATCH (other:Event)-[:REFERENCES]->(ent)
WHERE other.session_id <> $session_id AND other.tenant_id = $tenant_id
RETURN other AS e ORDER BY other.occurred_at DESC
LIMIT $limit
""".strip()

# ---------------------------------------------------------------------------
# Graph compaction queries (Task 3)
# ---------------------------------------------------------------------------

COUNT_SESSION_EVENTS = """
MATCH (e:Event {session_id: $session_id, tenant_id: $tenant_id})
RETURN count(e) AS event_count
""".strip()

GET_SUMMARIZED_EVENT_IDS = """
MATCH (s:Summary)-[:SUMMARIZES]->(e:Event {session_id: $session_id, tenant_id: $tenant_id})
WHERE e.occurred_at < $cutoff_iso
RETURN e.event_id AS event_id
ORDER BY e.occurred_at ASC
""".strip()

GET_CROSS_REFERENCED_EVENT_IDS = """
MATCH (e:Event {session_id: $session_id, tenant_id: $tenant_id})
  <-[:REFERENCES]-(ent:Entity {tenant_id: $tenant_id})
MATCH (ent)-[:REFERENCES]->(other:Event {tenant_id: $tenant_id})
WHERE other.session_id <> $session_id
RETURN DISTINCT e.event_id AS event_id
""".strip()

GET_RECENT_EVENT_IDS = """
MATCH (e:Event {session_id: $session_id, tenant_id: $tenant_id})
RETURN e.event_id AS event_id
ORDER BY e.occurred_at DESC
LIMIT $keep_recent
""".strip()

DETACH_DELETE_EVENTS_BY_IDS = """
UNWIND $event_ids AS eid
MATCH (e:Event {event_id: eid, tenant_id: $tenant_id})
DETACH DELETE e
RETURN count(*) AS deleted_count
""".strip()

GET_TENANT_NODE_COUNTS = """
MATCH (n {tenant_id: $tenant_id})
RETURN labels(n)[0] AS label, count(n) AS cnt
""".strip()

GET_STALE_SESSIONS = """
MATCH (e:Event {tenant_id: $tenant_id})
WITH e.session_id AS sid, count(e) AS cnt, max(e.occurred_at) AS latest
WHERE cnt >= $min_events AND latest < $cutoff_iso
RETURN sid AS session_id, cnt AS event_count
ORDER BY latest ASC
LIMIT $batch_limit
""".strip()

# ---------------------------------------------------------------------------
# Cleanup (for testing)
# ---------------------------------------------------------------------------

DELETE_ALL = "MATCH (n) DETACH DELETE n"
