# ADR-0001: Traceability-First Context Graph

Status: **Accepted — Amended 2026-02-11**
Date: 2026-02-07
Updated: 2026-02-11
Supersedes: Original proposal (same number)
Amended-by: ADR-0007, ADR-0008, ADR-0009, ADR-0010 (see Amendments section)

## Context

The first repo goal is to create a context graph for agents. The highest-value MVP outcome is explaining agent behavior end-to-end: what happened, why, and from which source.

Research across four dimensions — industry precedents, adversarial analysis, agent framework landscape, and scale/operations — produced the following key findings:

1. **The provenance gap is real.** No existing agent observability tool (LangSmith, Langfuse, Arize Phoenix, AgentOps) provides provenance-annotated context retrieval for agents. All capture traces for human debugging but none return provenance pointers in context responses. This is a genuine, unfilled gap. (Source: agent-frameworks report, industry-precedents report)

2. **Memory-first products have strong market traction.** Mem0 ($24M raised, 41K GitHub stars, 186M API calls/quarter), Letta/MemGPT (#1 on Terminal-Bench), Zep/Graphiti (14K stars in 8 months), and LangMem all succeeded with memory-first designs. The market rewards low-friction recall over audit rigor. (Source: devils-advocate report)

3. **Event sourcing adds real complexity.** Production post-mortems document teams struggling with eventual consistency bugs, projection maintenance, and schema migration pain when adopting event sourcing prematurely. The dual-store architecture (Postgres + Neo4j + projection worker) requires significant infrastructure investment. (Source: devils-advocate report, scale-analysis report)

4. **The architecture is well-grounded in standards.** The design maps cleanly to OpenTelemetry's span model, W3C PROV-DM's provenance vocabulary, and proven CQRS/event sourcing patterns. This is not novel architecture — it is a novel *application* of proven architecture. (Source: industry-precedents report)

5. **OpenTelemetry is the ecosystem convergence point.** AutoGen, CrewAI, Semantic Kernel, and (via exporters) LangChain all emit OTel spans. OTel GenAI Semantic Conventions define `gen_ai.agent.id`, `gen_ai.conversation.id`, and `gen_ai.operation.name`. (Source: agent-frameworks report)

6. **Immutability and GDPR are in tension.** Append-only event ledgers conflict with Article 17 right-to-erasure. This requires Forgettable Payloads (PII in a separate mutable store, referenced by pseudonym) and crypto-shredding as defense-in-depth. Must be designed into the schema from day one. (Source: scale-analysis report)

Non-goals for MVP:
- Full long-term semantic memory platform
- UI-heavy analyst workflows
- Cross-tenant enterprise controls
- Sub-100ms projection lag guarantees

## Decision

The MVP MUST prioritize tool-call traceability and provenance over generalized memory features, while constraining architectural complexity to accelerate time-to-first-value.

### Core Commitments (non-negotiable)

The system MUST:

1. **Capture append-only event records** for agent and tool actions with idempotent ingestion
2. **Preserve causal lineage** between actions and outputs via `parent_event_id` chains
3. **Return provenance pointers in all context retrieval responses** — this is the primary differentiator and the feature no existing tool provides
4. **Support deterministic replay** of graph projection from source events via `global_position` ordering
5. **Separate PII from events** using the Forgettable Payloads pattern — `payload_ref` MUST NOT contain raw PII; personal data lives in a mutable reference store deletable on erasure request

### Complexity Constraints (learned from research)

The MVP SHOULD:

6. **Start with Postgres as the sole data store** for both event ledger and graph queries (using recursive CTEs or Apache AGE). Defer Neo4j to a later phase when graph query latency demonstrably exceeds Postgres capabilities. This cuts infrastructure from 3 components (Postgres + Neo4j + projector) to 1, reducing time-to-first-value from 8-12 weeks to 4-6 weeks
7. **Accept OTel spans as the primary ingestion format** via an OTLP adapter, mapping GenAI semantic conventions to the internal event schema. This covers the widest framework surface (AutoGen, CrewAI, Semantic Kernel, LangChain) with a single adapter
8. **Minimize required event fields** to lower producer friction. Required: `event_id`, `event_type`, `occurred_at`, `session_id`, `trace_id`. Optional but recommended: `agent_id`, `parent_event_id`, `tool_name`, `payload_ref`, `ended_at`, `status`, `schema_version`
9. **Enforce bounded queries** from day one — all graph/lineage queries MUST have `max_depth` (default 3), `max_nodes` (default 100), and `timeout_ms` (default 5000) limits

### Standards Alignment

The system SHOULD:

10. **Adopt W3C PROV-DM vocabulary** for graph edge types: `GENERATED_BY`, `USED`, `DERIVED_FROM`, `ATTRIBUTED_TO`, `INFORMED_BY` — rather than inventing ad-hoc relationship names
11. **Align event type namespace with OpenInference span kinds**: `agent.invoke`, `tool.execute`, `llm.generate`, `retriever.query`, `chain.run` — maintaining compatibility with the emerging OTel GenAI conventions
12. **Use `global_position` (BIGSERIAL)** for total event ordering, following EventStoreDB's `$all` stream pattern, enabling deterministic projection replay

### Phased Store Evolution

The architecture MUST support upgrading the query store without re-ingesting events:

- **Phase 1 (MVP):** Postgres-only. Event ledger in append-only table with range partitioning by `occurred_at`. Graph queries via recursive CTEs or Apache AGE extension. Provenance pointers in all responses.
- **Phase 2 (when validated):** Add Neo4j as a projection target if/when graph query complexity or latency exceeds Postgres capabilities. Async projection worker with cursor-based polling, MERGE-based idempotent writes, and `projection_lag_seconds` monitoring.
- **Phase 3 (at scale):** Redis Cluster for horizontal scaling, Neo4j causal clustering, payload offloading, hot/cold partitioning.

The event ledger schema and API contract MUST remain stable across all phases. Clients MUST NOT need to change when the query store upgrades.

## Consequences

### Positive

- **Unique value proposition**: provenance-annotated context retrieval — no existing tool offers this
- **Strong auditability**: immutable event history with causal lineage for debugging agent runs
- **Standards-aligned**: compatible with OTel, PROV-DM, and proven event sourcing patterns
- **Low producer friction**: OTel adapter as primary ingestion covers most frameworks with one integration
- **Reduced MVP complexity**: single-store Phase 1 cuts infrastructure and accelerates delivery
- **GDPR-ready**: Forgettable Payloads pattern designed in from day one
- **Clear upgrade path**: can add Neo4j, CDC, and scale features without breaking API contracts

### Negative

- **Slower delivery of memory features**: traceability-first means recall/memory is not the first capability shipped. This is a conscious bet that provenance is the higher-value differentiator for production agent deployments
- **Postgres graph query limitations**: recursive CTEs are 10-100x slower than Neo4j for deep traversals. This is acceptable for MVP but creates a known performance ceiling
- **Schema discipline required**: event producers must emit structured events with at minimum 5 required fields. Mitigated by OTel adapter handling the transformation
- **Adoption risk**: memory-first products (Mem0, Zep) have proven market traction. We are betting that provenance becomes critical as agents move from demos to production — this bet is unvalidated

### Risks to Monitor

| Risk | Mitigation |
|---|---|
| No demand for traceability in MVP users | Track feature usage; be willing to pivot scope toward memory if provenance queries see <10% adoption after 3 months |
| Postgres graph queries too slow | Benchmark at 10K sessions; trigger Neo4j Phase 2 if p95 lineage query >500ms |
| PII leaks into event payloads | Automated schema validation on ingest; `data_classification` field; integration tests |
| Event schema needs breaking changes | `schema_version` field + upcasting middleware; weak schema (tolerant JSONB) for payloads |

## Alternatives Considered

### 1. Memory-first design with light provenance
Rejected as the primary approach. The strongest evidence for this path is market traction (Mem0's $24M raise, 41K stars). However, memory without provenance produces context that agents cannot verify or explain. Every successful memory system will eventually need to answer "where did this memory come from?" — building provenance in from day one avoids a painful retrofit.

**Acknowledged risk:** If the market does not value provenance in the near term, this decision delays adoption. The phased store approach and minimal required fields are designed to mitigate this by reducing time-to-first-value.

### 2. Equal-priority memory + traceability
Rejected for MVP. Research confirms this dilutes scope. The system should be excellent at one thing (provenance-annotated context) before expanding to general memory. Memory features can layer on top of the event ledger once the core is proven.

### 3. Full dual-store (Postgres + Neo4j) from day one
Rejected for MVP. Research documents significant complexity tax from event sourcing with dual stores: projection lag management, dual-store failure modes, operational monitoring burden, and 2x infrastructure cost (~$180/mo vs ~$70/mo at startup). The phased approach (Postgres-only Phase 1, Neo4j Phase 2) preserves the architectural option while cutting MVP complexity.

### 4. Neo4j-only
Rejected. Append-only ledger semantics, deterministic replay via `global_position`, and GDPR compliance patterns (Forgettable Payloads, crypto-shredding) are better served by relational storage. Neo4j lacks the transactional guarantees needed for a source-of-truth event store.

## Research References

This decision is informed by four research reports:
- [Industry Precedents](../research/adr001-industry-precedents.md) — OTel, W3C PROV, event sourcing, ML lineage, agent observability
- [Devil's Advocate](../research/adr001-devils-advocate.md) — adoption risk, memory-first success stories, YAGNI, complexity tax, market timing
- [Agent Framework Landscape](../research/adr001-agent-frameworks.md) — LangChain, CrewAI, AutoGen, OpenAI Agents SDK, Semantic Kernel, emerging standards
- [Scale & Operations Analysis](../research/adr001-scale-analysis.md) — storage growth, GDPR, projection lag, Neo4j limits, failure modes, cost modeling

## Amendments

### 2026-02-11: Phased Store Evolution Revised

**What changed:** The Phased Store Evolution plan (Section "Phased Store Evolution") originally prescribed Postgres-only for Phase 1, deferring Neo4j to Phase 2. This phased approach is superseded in practice by ADR-0007, ADR-0008, and ADR-0009, which define a cognitive memory tier architecture requiring both Postgres (episodic memory) and Neo4j (semantic memory) from the initial implementation.

**Why:** Research on graph-based agent memory (nine papers across three clusters — see ADR-0007) independently confirmed that the dual-store architecture maps directly to the hippocampal-neocortical Complementary Learning Systems model. ADR-0008's consolidation pipeline and ADR-0009's multi-graph schema both require Neo4j as the semantic store. Implementing these features on Postgres-only recursive CTEs would negate the research-validated design.

**Impact on this ADR:**
- **Core Commitments (items 1-5)**: Unchanged. All remain non-negotiable.
- **Complexity Constraint item 6** ("Start with Postgres as the sole data store"): Superseded. The system now adopts dual-store from the initial build, consistent with ADR-0003. The original concern about infrastructure complexity is mitigated by the richer value proposition: four-tier memory, intent-aware retrieval, and consolidation/decay.
- **Phased Store Evolution**: Phase 1 (Postgres-only) is skipped. Implementation begins at Phase 2 (Postgres + Neo4j + projection worker). Phase 3 (CDC, clustering, offloading) remains a future target.
- **Complexity Constraint item 8** (minimal required fields): Extended by ADR-0007 with optional `importance_hint` field (SMALLINT, nullable). Named `importance_hint` (not `importance_score`) to distinguish it from the enrichment-computed `importance_score` in Neo4j. Backward-compatible — the field is optional on ingestion. See ADR-0004 amendment for the authoritative Postgres schema.
- **Standards Alignment (item 10)**: W3C PROV-DM is retained as the conceptual provenance vocabulary for interoperability. The operational graph edge types are now FOLLOWS, CAUSED_BY, SIMILAR_TO, REFERENCES, and SUMMARIZES (defined in ADR-0009), which are optimized for intent-aware traversal. A PROV-DM compatibility mapping is documented in ADR-0009's amendments section.

**What is preserved:** The traceability-first principle, immutable event ledger, provenance pointers in all responses, OTel ingestion, bounded queries, and GDPR Forgettable Payloads pattern all remain unchanged. The core differentiator — provenance-annotated context retrieval — is strengthened, not weakened, by the memory tier architecture.

### 2026-02-11: Redis Replaces Postgres as Event Store

**What changed:** Redis replaces Postgres as the event store per ADR-0010. The operational event ledger moves from Postgres (append-only table with BIGSERIAL ordering) to Redis Stack (Streams + JSON + Search). Redis serves as both the hot and cold event tier — stream entries are trimmed after the hot window while JSON documents are retained for cold queries.

**Impact on this ADR:**
- **Core Commitments (items 1-5)**: Unchanged. Append-only events, causal lineage, provenance pointers, deterministic replay, and Forgettable Payloads are all preserved with Redis implementations.
- **Complexity Constraint item 6**: Superseded. The event store is now Redis-only instead of Postgres.
- **Phased Store Evolution**: Updated. Phase 1 is Redis + Neo4j. Phase 2 adds enrichment pipeline. Phase 3 adds Redis Cluster for horizontal scaling.
