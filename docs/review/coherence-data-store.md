# Coherence Review: Data Store References Across ADRs

**Reviewer**: data-store-reviewer (automated)
**Date**: 2026-02-12
**Scope**: All 13 ADRs (0001--0013) checked for consistency with ADR-0010 (Redis replaces Postgres as event store)

## Summary

ADR-0010 establishes that Redis Stack (Streams + JSON + Search) replaces Postgres as the event store. ADRs 0001--0009 were written before ADR-0010 and contain Postgres references in their main text, which is acceptable when an amendment section clarifies the change. ADRs 0011--0013 were written after ADR-0010 and should reference Redis exclusively as the current event store.

**Total inconsistencies found: 17**
- Critical (stale references in post-Redis ADRs or in amendment text): 8
- Minor (main text of pre-Redis ADRs where amendment exists but wording is slightly ambiguous): 9

---

## Critical Issues

### Issue 1: ADR-0003 Main Text Still Says "Postgres + Neo4j" in Decision Section

**ADR**: 0003
**Section**: Decision (line 17)
**Quote**: `Use Postgres + Neo4j in a dual-store architecture.`
**Problem**: The Decision section -- the most authoritative section of an ADR -- still states "Postgres + Neo4j." While the amendment at lines 55-64 clarifies the change to Redis, the title of ADR-0003 itself is "Dual Store with Postgres Source of Truth and Neo4j Projection" and the Decision body says "Postgres MUST be the source of truth" (line 19) and "The projection model MUST support replay/rebuild from Postgres" (line 21). A reader skimming the Decision section gets the wrong architecture.
**Recommendation**: Either (a) update the title and Decision section to say "Redis + Neo4j" with a note that the original decision was Postgres, or (b) add a prominent "SUPERSEDED" callout at the top of the Decision section directing readers to the amendment.

### Issue 2: ADR-0004 Main Text Says "Ingestion MUST write immutable events to Postgres"

**ADR**: 0004
**Section**: Decision (line 17)
**Quote**: `Ingestion MUST write immutable events to Postgres and MUST be idempotent.`
**Problem**: Same pattern as Issue 1 -- the Decision section uses a MUST directive that references Postgres. The amendment (lines 79-89) clarifies the Redis change, but the normative Decision text is stale.
**Recommendation**: Same as Issue 1 -- add a "SUPERSEDED" callout or update the Decision text.

### Issue 3: ADR-0005 Main Text Says "transform Postgres events into Neo4j"

**ADR**: 0005
**Section**: Decision (line 16)
**Quote**: `A projector worker MUST asynchronously transform Postgres events into Neo4j nodes/edges.`
**Problem**: The Decision section's MUST directive references Postgres. The amendment (lines 56-58) clarifies Redis consumer groups replace Postgres polling, but the normative text is stale.
**Recommendation**: Same as Issues 1-2.

### Issue 4: ADR-0005 Amendment Still Says "polls Postgres events by global_position"

**ADR**: 0005
**Section**: Amendments, "Stage 1 Foundation" subsection (line 48)
**Quote**: `Stage 1 (this ADR): Event projection — polls Postgres events by global_position, MERGE into Neo4j with temporal and causal edges.`
**Problem**: This is in the amendment text added on 2026-02-11, the same date as ADR-0010. The amendment about Redis (lines 56-58) addresses the projection worker change, but the Stage 1 description in the earlier amendment still says "polls Postgres events." This is an amendment that was not updated when the subsequent Redis amendment was added.
**Recommendation**: Update line 48 to say "reads Redis events via consumer group" or add a note that this description is superseded by the Redis amendment below it.

### Issue 5: ADR-0007 Tier 3 Table Still Says "Postgres event ledger"

**ADR**: 0007
**Section**: Tier Definitions and Component Mapping table (line 53)
**Quote**: `|  Episodic         | Postgres event ledger   | Immutable, instance |`
**Problem**: The main-text table maps Tier 3 (Episodic) to "Postgres event ledger." The amendment at lines 217-219 says "Tier 3 (Episodic Memory) implementation changes from Postgres to Redis per ADR-0010." However, the table -- which is the primary reference for the tier architecture -- still says Postgres. This table is the most-referenced artifact in the tier architecture and should reflect the current state.
**Recommendation**: Update the table to say "Redis event store" for the Episodic tier, with a footnote referencing the original Postgres design.

### Issue 6: ADR-0007 Tier 3 Section Body References Postgres Multiple Times

**ADR**: 0007
**Section**: Tier 3: Episodic Memory (lines 83-98)
**Quote (line 83)**: `The Postgres event ledger IS the episodic memory store.`
**Quote (line 88)**: `Long-term storage | Immutable append-only ledger with BIGSERIAL ordering`
**Quote (line 90)**: `Single-shot learning | Each event captured once; idempotent ON CONFLICT DO NOTHING`
**Problem**: Three stale references in the Tier 3 body:
  - "Postgres event ledger" should be "Redis event store"
  - "BIGSERIAL ordering" should be "Redis Stream entry ID ordering"
  - "ON CONFLICT DO NOTHING" should reference the Lua dedup script
The amendment at lines 217-219 acknowledges the change but does not correct these specific references.
**Recommendation**: These are in the main text of a pre-Redis ADR, so the amendment approach is acceptable. However, the amendment should explicitly list these three items as superseded (currently it only says "implementation changes from Postgres to Redis" without specifying which references).

### Issue 7: ADR-0009 Node Schema Says "global_position : INTEGER"

**ADR**: 0009
**Section**: Graph Schema, Event Node properties (line 58)
**Quote**: `global_position  : INTEGER`
**Problem**: Per ADR-0010, `global_position` changes from BIGSERIAL (integer) to a Redis Stream entry ID (string, e.g., "1707644400000-0"). The ADR-0009 amendment (lines 320-322) says "provenance.global_position format changes from integer to Redis Stream entry ID string." However, the node schema definition at line 58 still declares `global_position` as `INTEGER` instead of `STRING`.
**Recommendation**: Update the Event Node schema to declare `global_position : STRING` with a comment explaining it is a Redis Stream entry ID.

### Issue 8: ADR-0009 Provenance Example Says "source": "postgres"

**ADR**: 0009
**Section**: Provenance in Query Responses, example JSON (line 226)
**Quote**: `"source": "postgres"`
**Problem**: The provenance example still shows `"source": "postgres"` and `"global_position": 12345` (integer). The amendment at lines 320-322 says these should be `"redis"` and a stream ID string respectively, but the example code block was not updated.
**Recommendation**: Update the example JSON to show `"source": "redis"` and `"global_position": "1707644400000-0"`.

---

## Minor Issues

### Issue 9: ADR-0001 Main Text References "Postgres + Neo4j + projection worker" Complexity

**ADR**: 0001
**Section**: Context, finding 3 (line 19)
**Quote**: `The dual-store architecture (Postgres + Neo4j + projection worker) requires significant infrastructure investment.`
**Problem**: Historical context reference. The amendment at lines 143-150 clarifies the Redis change. This is acceptable as historical context but could confuse readers.
**Severity**: Minor -- the amendment adequately addresses this.

### Issue 10: ADR-0001 Phase 1 Still Says "Postgres-only"

**ADR**: 0001
**Section**: Phased Store Evolution, Phase 1 (line 68)
**Quote**: `Phase 1 (MVP): Postgres-only.`
**Problem**: The phased store evolution section describes Postgres-only Phase 1. The amendment at lines 148-150 updates this to "Phase 1 is Redis + Neo4j." The main text is acceptable as the original decision record.
**Severity**: Minor -- amendment covers this.

### Issue 11: ADR-0001 "Postgres graph query limitations" in Consequences

**ADR**: 0001
**Section**: Negative Consequences (line 89)
**Quote**: `Postgres graph query limitations: recursive CTEs are 10-100x slower than Neo4j for deep traversals.`
**Problem**: References Postgres query limitations that are no longer relevant since Postgres is no longer in the architecture.
**Severity**: Minor -- historical context in original decision text.

### Issue 12: ADR-0004 Amendment Section Header Says "Complete Postgres event schema"

**ADR**: 0004
**Section**: Amendments, first amendment (line 53)
**Quote**: `Complete Postgres event schema:`
**Problem**: The first amendment (pre-Redis, same date) describes the "Complete Postgres event schema." The second amendment (lines 79-89) clarifies that the ledger moves to Redis. The schema field definitions remain valid, but the heading "Complete Postgres event schema" is stale.
**Recommendation**: Consider renaming to "Complete event schema" since the schema is now implemented in Redis.

### Issue 13: ADR-0004 Amendment References "BIGSERIAL" and "Postgres column constraints"

**ADR**: 0004
**Section**: Amendments, first amendment (line 63)
**Quote**: `global_position (BIGSERIAL, auto-assigned — total ordering for deterministic replay per ADR-0001)`
**Problem**: The first amendment defines `global_position` as BIGSERIAL. The second amendment (line 85) correctly supersedes this: "Changes from BIGSERIAL (auto-incrementing integer) to a Redis Stream entry ID (string)." The issue is that a reader of the "Complete Postgres event schema" section sees BIGSERIAL without immediately seeing the correction.
**Severity**: Minor -- the second amendment adequately clarifies.

### Issue 14: ADR-0007 Inter-Tier Flow Says "Events ingested into Postgres"

**ADR**: 0007
**Section**: Inter-Tier Flow (line 134)
**Quote**: `1. Events ingested into Postgres (episodic capture — fast, detailed)`
**Problem**: Main text describes the inter-tier flow with Postgres. Amendment covers this at lines 217-219.
**Severity**: Minor -- main text of pre-Redis ADR.

### Issue 15: ADR-0007 Neuroscience Mapping Says "Postgres = hippocampus"

**ADR**: 0007
**Section**: Inter-Tier Flow, neuroscience mapping (line 139)
**Quote**: `Postgres = hippocampus (rapid encoding, detailed episodic traces, index-based storage)`
**Problem**: Main text maps Postgres to hippocampus. The amendment at line 219 updates this: "CLS mapping updated: Redis = hippocampus." The Phased Deployment Note amendment (line 215) also says "CLS mapping (Postgres=hippocampus, Neo4j=neocortex)" -- this was written before the Redis amendment and is now stale.
**Recommendation**: The Phased Deployment Note at line 215 should acknowledge the Redis change or be marked as superseded by the Redis amendment.

### Issue 16: ADR-0008 Context Says "poll Postgres events, MERGE into Neo4j"

**ADR**: 0008
**Section**: Context (line 8)
**Quote**: `The projection worker (ADR-0005) currently performs a single-pass transformation: poll Postgres events, MERGE into Neo4j.`
**Problem**: Context section references Postgres polling. The amendment at lines 248-254 clarifies the Redis change.
**Severity**: Minor -- historical context in pre-Redis ADR.

### Issue 17: ADR-0009 Schema Migration Path Says "re-projection from Postgres events"

**ADR**: 0009
**Section**: Schema Migration Path (line 247)
**Quote**: `2. Trigger full re-projection from Postgres events`
**Problem**: The schema migration instructions reference Postgres. The amendment acknowledges provenance source changes but does not update the migration path text.
**Severity**: Minor -- main text of pre-Redis ADR. The procedure is the same, just substitute "Redis" for "Postgres."

---

## ADRs With No Data Store Issues

### ADR-0002: Service Stack
Clean. The amendment at lines 60-62 correctly states "asyncpg replaced by redis-py (async mode) per ADR-0010. Alembic removed." No stale references remain.

### ADR-0006: Context Query and Lineage API
Clean. The amendment at lines 122-124 correctly updates provenance format. No stale Postgres references in the main text (this ADR is API-focused and does not reference the data store directly).

### ADR-0010: Redis as Event Store
This is the authoritative ADR for the Redis adoption. It correctly references Postgres as the "previous" or "current" architecture being replaced. All references to Postgres are appropriate historical context. No issues.

### ADR-0011: Ontological Foundation
Clean. Written after ADR-0010. References Redis correctly throughout:
- Line 9: "stores them in Redis (episodic memory)"
- Line 335: "Redis event store" for Episodic Tier
- Line 348: "Redis event store" for Fast Learning System
All data store references are consistent with ADR-0010.

### ADR-0012: User Personalization Ontology
Clean. Written after ADR-0010. References Redis correctly:
- Line 557: "Mark source events in Redis as erased"
- Line 560: "marking events as erased in Redis and re-projecting"
- Line 687: "marking events as erased in Redis"
No Postgres references. All data store references are consistent with ADR-0010.

### ADR-0013: Knowledge Extraction Pipeline
Clean. Written after ADR-0010. Uses Redis Streams throughout as the coordination mechanism:
- Line 52: "XADD event to Redis Stream"
- Line 78-101: Full Redis Stream consumer group architecture
- Line 112: "Stream IDs are timestamp-based, naturally ordered"
No Postgres references. All data store references are consistent with ADR-0010.

---

## Recommendations

### Priority 1: Fix Critical Issues in Amendment Text (Issues 4, 7, 8)
These are cases where amendment text itself is stale or where schema definitions conflict with ADR-0010. They should be corrected because amendments are the authoritative "current state" -- if an amendment is wrong, the ADR system is unreliable.

### Priority 2: Add SUPERSEDED Callouts to Decision Sections (Issues 1, 2, 3)
The Decision sections of ADR-0003, ADR-0004, and ADR-0005 contain MUST directives that reference Postgres. While amendments exist, the Decision section is the most-read part of an ADR. A prominent "Note: This decision's data store references are superseded by ADR-0010" callout would prevent misreadings.

### Priority 3: Update ADR-0007 Tier Table (Issues 5, 6)
The tier mapping table in ADR-0007 is the most-referenced artifact in the memory tier architecture. It should reflect the current Redis-based architecture, not the original Postgres design.

### Priority 4: Minor Issues (Issues 9-17)
These are all in the main text of pre-Redis ADRs where amendments adequately clarify the change. They are acceptable as historical records but could benefit from inline editor's notes for clarity.
