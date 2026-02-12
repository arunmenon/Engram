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

ALL_CONSTRAINTS = [CONSTRAINT_EVENT_PK, CONSTRAINT_ENTITY_PK, CONSTRAINT_SUMMARY_PK]

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
    e.last_accessed_at = $last_accessed_at
""".strip()

MERGE_ENTITY_NODE = """
MERGE (n:Entity {entity_id: $entity_id})
SET n.name = $name,
    n.entity_type = $entity_type,
    n.first_seen = $first_seen,
    n.last_seen = $last_seen,
    n.mention_count = $mention_count
""".strip()

MERGE_SUMMARY_NODE = """
MERGE (s:Summary {summary_id: $summary_id})
SET s.scope = $scope,
    s.scope_id = $scope_id,
    s.content = $content,
    s.created_at = $created_at,
    s.event_count = $event_count,
    s.time_range = $time_range
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
MERGE (a)-[r:FOLLOWS]->(b)
SET r += $props
""".strip()

MERGE_CAUSED_BY = """
MATCH (a:Event {event_id: $source_id})
MATCH (b:Event {event_id: $target_id})
MERGE (a)-[r:CAUSED_BY]->(b)
SET r += $props
""".strip()

MERGE_SIMILAR_TO = """
MATCH (a:Event {event_id: $source_id})
MATCH (b:Event {event_id: $target_id})
MERGE (a)-[r:SIMILAR_TO]->(b)
SET r += $props
""".strip()

MERGE_REFERENCES = """
MATCH (a:Event {event_id: $source_id})
MATCH (b:Entity {entity_id: $target_id})
MERGE (a)-[r:REFERENCES]->(b)
SET r += $props
""".strip()

MERGE_SUMMARIZES = """
MATCH (a:Summary {summary_id: $source_id})
MATCH (b {event_id: $target_id})
MERGE (a)-[r:SUMMARIZES]->(b)
SET r += $props
""".strip()

MERGE_SAME_AS = """
MATCH (a:Entity {entity_id: $source_id})
MATCH (b:Entity {entity_id: $target_id})
MERGE (a)-[r:SAME_AS]->(b)
SET r += $props
""".strip()

MERGE_RELATED_TO = """
MATCH (a:Entity {entity_id: $source_id})
MATCH (b:Entity {entity_id: $target_id})
MERGE (a)-[r:RELATED_TO]->(b)
SET r += $props
""".strip()

MERGE_HAS_PROFILE = """
MATCH (a:Entity {entity_id: $source_id})
MATCH (b:UserProfile {profile_id: $target_id})
MERGE (a)-[r:HAS_PROFILE]->(b)
SET r += $props
""".strip()

MERGE_HAS_PREFERENCE = """
MATCH (a:Entity {entity_id: $source_id})
MATCH (b:Preference {preference_id: $target_id})
MERGE (a)-[r:HAS_PREFERENCE]->(b)
SET r += $props
""".strip()

MERGE_HAS_SKILL = """
MATCH (a:Entity {entity_id: $source_id})
MATCH (b:Skill {skill_id: $target_id})
MERGE (a)-[r:HAS_SKILL]->(b)
SET r += $props
""".strip()

MERGE_DERIVED_FROM = """
MATCH (a {preference_id: $source_id})
MATCH (b:Event {event_id: $target_id})
MERGE (a)-[r:DERIVED_FROM]->(b)
SET r += $props
""".strip()

MERGE_EXHIBITS_PATTERN = """
MATCH (a:Entity {entity_id: $source_id})
MATCH (b:BehavioralPattern {pattern_id: $target_id})
MERGE (a)-[r:EXHIBITS_PATTERN]->(b)
SET r += $props
""".strip()

MERGE_INTERESTED_IN = """
MATCH (a:Entity {entity_id: $source_id})
MATCH (b:Entity {entity_id: $target_id})
MERGE (a)-[r:INTERESTED_IN]->(b)
SET r += $props
""".strip()

MERGE_ABOUT = """
MATCH (a:Preference {preference_id: $source_id})
MATCH (b:Entity {entity_id: $target_id})
MERGE (a)-[r:ABOUT]->(b)
SET r += $props
""".strip()

MERGE_ABSTRACTED_FROM = """
MATCH (a:Workflow {workflow_id: $source_id})
MATCH (b:Workflow {workflow_id: $target_id})
MERGE (a)-[r:ABSTRACTED_FROM]->(b)
SET r += $props
""".strip()

MERGE_PARENT_SKILL = """
MATCH (a:Skill {skill_id: $source_id})
MATCH (b:Skill {skill_id: $target_id})
MERGE (a)-[r:PARENT_SKILL]->(b)
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
MERGE (a)-[r:FOLLOWS]->(b)
SET r += edge.props
""".strip()

BATCH_MERGE_CAUSED_BY = """
UNWIND $edges AS edge
MATCH (a:Event {event_id: edge.source_id})
MATCH (b:Event {event_id: edge.target_id})
MERGE (a)-[r:CAUSED_BY]->(b)
SET r += edge.props
""".strip()

# ---------------------------------------------------------------------------
# Phase 3: Traversal and context queries
# ---------------------------------------------------------------------------

GET_SESSION_EVENTS = """
MATCH (e:Event {session_id: $session_id})
RETURN e ORDER BY e.occurred_at DESC LIMIT $limit
""".strip()

GET_SESSION_EVENT_COUNT = """
MATCH (e:Event {session_id: $session_id})
RETURN count(e) AS cnt
""".strip()

GET_LINEAGE = """
MATCH path = (start:Event {event_id: $node_id})-[:CAUSED_BY*1..10]->(ancestor)
WITH start, nodes(path) AS chain_nodes, relationships(path) AS chain_rels,
     length(path) AS depth
WHERE depth <= $max_depth
RETURN start, chain_nodes, chain_rels
LIMIT $max_nodes
""".strip()

GET_EVENT_NEIGHBORS = """
MATCH (e:Event {event_id: $event_id})
OPTIONAL MATCH (e)-[r]->(neighbor)
RETURN e, type(r) AS rel_type, properties(r) AS rel_props,
       labels(neighbor) AS neighbor_labels, properties(neighbor) AS neighbor_props,
       neighbor.event_id AS neighbor_event_id,
       neighbor.entity_id AS neighbor_entity_id,
       neighbor.summary_id AS neighbor_summary_id
""".strip()

GET_ENTITY_WITH_EVENTS = """
MATCH (ent:Entity {entity_id: $entity_id})
OPTIONAL MATCH (evt:Event)-[r:REFERENCES]->(ent)
RETURN ent, evt, properties(r) AS ref_props
ORDER BY evt.occurred_at DESC
LIMIT $limit
""".strip()

UPDATE_ACCESS_COUNT = """
MATCH (e:Event {event_id: $event_id})
SET e.access_count = coalesce(e.access_count, 0) + 1,
    e.last_accessed_at = $now
""".strip()

BATCH_UPDATE_ACCESS_COUNT = """
UNWIND $event_ids AS eid
MATCH (e:Event {event_id: eid})
SET e.access_count = coalesce(e.access_count, 0) + 1,
    e.last_accessed_at = $now
""".strip()

UPDATE_EVENT_ENRICHMENT = """
MATCH (e:Event {event_id: $event_id})
SET e.keywords = $keywords,
    e.importance_score = $importance_score
""".strip()

GET_SUBGRAPH_SEED_EVENTS = """
MATCH (e:Event {session_id: $session_id})
RETURN e ORDER BY e.occurred_at DESC LIMIT $seed_limit
""".strip()

# ---------------------------------------------------------------------------
# Cleanup (for testing)
# ---------------------------------------------------------------------------

DELETE_ALL = "MATCH (n) DETACH DELETE n"
