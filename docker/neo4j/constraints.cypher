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
