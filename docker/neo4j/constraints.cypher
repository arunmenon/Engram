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

// Performance indexes
CREATE INDEX event_session_id IF NOT EXISTS FOR (e:Event) ON (e.session_id);

// Vector indexes for embedding-based similarity search (Neo4j 5.26+)
CREATE VECTOR INDEX entity_embedding_idx IF NOT EXISTS
FOR (n:Entity) ON (n.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 384,
  `vector.similarity_function`: 'cosine'
}};
