# ADR-0003: Dual Store with Postgres Source of Truth and Neo4j Projection

Status: **Accepted — Amended 2026-02-11**
Date: 2026-02-07
Updated: 2026-02-11
Validated-by: ADR-0007 (memory tiers), ADR-0008 (consolidation), ADR-0009 (multi-graph schema)
Amended-by: ADR-0010 (Redis replaces Postgres as event store)

## Context
The system needs immutable event durability and efficient relationship traversal. A single store can do part of this well, but MVP requires both reliable event ledger semantics and graph-native traversal performance.

Non-goals for MVP:
- Multi-region active-active storage
- Zero-lag strong consistency between stores

## Decision

> **Note (ADR-0010):** The Decision text below reflects the original design. Per ADR-0010, Postgres has been replaced by Redis as the event store. The dual-store is now Redis + Neo4j. See the Amendments section for details.

Use Postgres + Neo4j in a dual-store architecture.

Postgres MUST be the source of truth for immutable context events.  
Neo4j MUST hold a query-optimized projection built from Postgres events.  
The projection model MUST support replay/rebuild from Postgres.

## Consequences
Positive:
- Durable append-only event history
- Efficient graph traversal for lineage/context queries
- Clear recovery path via projection replay

Negative:
- Operational complexity of two datastores
- Eventual consistency lag between write and graph projection
- More integration testing surface

## Alternatives Considered
1. Postgres-only (recursive queries)  
Rejected for MVP due to expected graph traversal complexity and ergonomics.
2. Neo4j-only
Rejected because append-only ledger and replay semantics are better anchored in relational event storage.

## Amendments

### 2026-02-11: Promoted to Accepted; Role Clarification

**What changed:** Status promoted from Proposed to Accepted. The dual-store architecture is now validated by nine research papers (ADR-0007) as mapping to the Complementary Learning Systems model from cognitive neuroscience.

**Role clarification:** ADR-0007 assigns specific cognitive roles to each store:
- **Postgres** = episodic memory (hippocampus): rapid encoding, immutable detailed traces, temporal ordering
- **Neo4j** = semantic memory (neocortex): consolidated relational knowledge, query-optimized, multi-hop traversal
- **Projection worker** = systems consolidation: async replay writing structure from episodic to semantic store

This resolves the earlier tension with ADR-0001's Phase 1 Postgres-only plan. ADR-0001 has been amended to acknowledge that dual-store is adopted from the initial build.

**Note:** ADR-0001's original concern about dual-store complexity (projection lag management, dual-store failure modes, operational monitoring) remains valid and must be addressed in implementation. The complexity is now justified by the richer value proposition defined in ADR-0007 through ADR-0009.

### 2026-02-11: Redis Replaces Postgres as Event Store

**What changed:** The dual store is now Redis (event store, all tiers) + Neo4j (graph projection) per ADR-0010. Redis serves as both hot and cold event storage.

**Role clarification update:** The CLS mapping updates with Redis adoption:
- **Redis** = hippocampus (fast episodic encoding): sub-millisecond append-only event capture via Streams (hot), JSON document retention for cold queries. Stream entries are trimmed after the hot window; JSON documents persist for the full retention period.
- **Neo4j** = neocortex (consolidated semantic knowledge): query-optimized graph projection, multi-hop traversal, enriched node properties (unchanged)
- **Projection worker** = systems consolidation: Redis consumer groups replace Postgres polling (push-based delivery, built-in crash recovery via Pending Entry List)

**Impact:** Postgres is no longer part of the dual-store architecture. References to "Postgres source of truth" in this ADR are superseded by Redis as the operational event store. The architecture is a true dual-store: Redis (episodic) + Neo4j (semantic). The core principle -- immutable event durability separate from query-optimized graph projection -- remains unchanged.
