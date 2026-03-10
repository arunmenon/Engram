// Engram Neo4j Constraints
// Validated in Phase 0 — FROZEN for Phase 1+
// Per ADR-0011 Section 7: Neo4j enforceable constraints
//
// NOTE: Property existence (IS NOT NULL) constraints require Neo4j Enterprise Edition.
// Neo4j Community only supports UNIQUENESS constraints.
// NOT NULL enforcement is handled at the application layer (Pydantic + projection worker).

// Event node — uniqueness
CREATE CONSTRAINT event_pk IF NOT EXISTS FOR (e:Event) REQUIRE e.event_id IS UNIQUE;

// Entity node — uniqueness
CREATE CONSTRAINT entity_pk IF NOT EXISTS FOR (n:Entity) REQUIRE n.entity_id IS UNIQUE;

// Summary node — uniqueness
CREATE CONSTRAINT summary_pk IF NOT EXISTS FOR (s:Summary) REQUIRE s.summary_id IS UNIQUE;

// UserProfile node — uniqueness (ADR-0012)
CREATE CONSTRAINT userprofile_pk IF NOT EXISTS FOR (u:UserProfile) REQUIRE u.user_id IS UNIQUE;

// Preference node — uniqueness (ADR-0012)
CREATE CONSTRAINT preference_pk IF NOT EXISTS FOR (p:Preference) REQUIRE p.preference_id IS UNIQUE;

// Skill node — uniqueness (ADR-0012)
CREATE CONSTRAINT skill_pk IF NOT EXISTS FOR (sk:Skill) REQUIRE sk.skill_id IS UNIQUE;

// Workflow node — uniqueness (ADR-0012)
CREATE CONSTRAINT workflow_pk IF NOT EXISTS FOR (w:Workflow) REQUIRE w.workflow_id IS UNIQUE;

// BehavioralPattern node — uniqueness (ADR-0012)
CREATE CONSTRAINT behavioralpattern_pk IF NOT EXISTS FOR (b:BehavioralPattern) REQUIRE b.pattern_id IS UNIQUE;

// Belief node — uniqueness
CREATE CONSTRAINT belief_pk IF NOT EXISTS FOR (b:Belief) REQUIRE b.belief_id IS UNIQUE;

// Goal node — uniqueness
CREATE CONSTRAINT goal_pk IF NOT EXISTS FOR (g:Goal) REQUIRE g.goal_id IS UNIQUE;

// Episode node — uniqueness
CREATE CONSTRAINT episode_pk IF NOT EXISTS FOR (e:Episode) REQUIRE e.episode_id IS UNIQUE;

// Performance indexes
CREATE INDEX event_session_id IF NOT EXISTS FOR (e:Event) ON (e.session_id);

// Tenant isolation indexes (one per node label)
CREATE INDEX event_tenant_idx IF NOT EXISTS FOR (e:Event) ON (e.tenant_id);
CREATE INDEX entity_tenant_idx IF NOT EXISTS FOR (n:Entity) ON (n.tenant_id);
CREATE INDEX summary_tenant_idx IF NOT EXISTS FOR (s:Summary) ON (s.tenant_id);
CREATE INDEX userprofile_tenant_idx IF NOT EXISTS FOR (u:UserProfile) ON (u.tenant_id);
CREATE INDEX preference_tenant_idx IF NOT EXISTS FOR (p:Preference) ON (p.tenant_id);
CREATE INDEX skill_tenant_idx IF NOT EXISTS FOR (s:Skill) ON (s.tenant_id);
CREATE INDEX workflow_tenant_idx IF NOT EXISTS FOR (w:Workflow) ON (w.tenant_id);
CREATE INDEX behavioral_tenant_idx IF NOT EXISTS FOR (b:BehavioralPattern) ON (b.tenant_id);
CREATE INDEX belief_tenant_idx IF NOT EXISTS FOR (b:Belief) ON (b.tenant_id);
CREATE INDEX goal_tenant_idx IF NOT EXISTS FOR (g:Goal) ON (g.tenant_id);
CREATE INDEX episode_tenant_idx IF NOT EXISTS FOR (ep:Episode) ON (ep.tenant_id);

// Relationship indexes (Neo4j 5.7+) — accelerate edge-property queries
CREATE INDEX follows_rel_idx IF NOT EXISTS FOR ()-[r:FOLLOWS]-() ON (r.delta_ms);
CREATE INDEX similar_rel_idx IF NOT EXISTS FOR ()-[r:SIMILAR_TO]-() ON (r.similarity_score);
CREATE INDEX references_rel_idx IF NOT EXISTS FOR ()-[r:REFERENCES]-() ON (r.mention_count);

// Composite indexes — eliminate full scans on frequent multi-predicate queries
CREATE INDEX event_session_time_idx IF NOT EXISTS FOR (e:Event) ON (e.session_id, e.occurred_at);
CREATE INDEX event_type_tenant_idx IF NOT EXISTS FOR (e:Event) ON (e.event_type, e.tenant_id);
CREATE INDEX entity_type_tenant_idx IF NOT EXISTS FOR (e:Entity) ON (e.entity_type, e.tenant_id);

// Property indexes for hot queries
CREATE INDEX event_importance_idx IF NOT EXISTS FOR (e:Event) ON (e.importance_score);
CREATE INDEX event_access_count_idx IF NOT EXISTS FOR (e:Event) ON (e.access_count);
CREATE INDEX entity_name_idx IF NOT EXISTS FOR (e:Entity) ON (e.name);

// Vector indexes for embedding-based similarity search (Neo4j 5.26+)
CREATE VECTOR INDEX entity_embedding_idx IF NOT EXISTS
FOR (n:Entity) ON (n.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 384,
  `vector.similarity_function`: 'cosine'
}};
