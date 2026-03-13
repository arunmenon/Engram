# Tech Debt: Competitor-Inspired Capabilities

> Novel capabilities observed in competitor systems (Mem0, Zep, Letta, Cognee, and emerging research) that Engram should evaluate for adoption. Prioritized by strategic value to Engram's traceability-first mission.

*Created: March 2026. Cross-referenced against Engram codebase, platform-readiness-gap-analysis.md, and retrieval-improvement-plan.md.*

---

## Priority Definitions

| Priority | Meaning |
|----------|---------|
| **P0** | Directly strengthens Engram's core traceability/auditability claim. Missing this undermines positioning. |
| **P1** | Materially improves retrieval quality or operational efficiency. Competitive table stakes by mid-2026. |
| **P2** | Valuable enhancement. Not urgent but strengthens the platform. |
| **P3+** | Future consideration. Relevant for later phases or specific verticals. |

---

## P0 — Core to Engram's Mission

### TD-001: Bitemporal Fact Tracking with Validity Windows

**Observed in:** Zep (temporal knowledge graph)

**What it does:** Every fact stores both `event_time` (when it occurred in the real world) and `ingestion_time` (when Engram learned about it). When new information contradicts an existing fact, the old fact gets a `validity_end` timestamp — it's not deleted, but marked as superseded. This enables "what was true at time T?" queries.

**Why Engram needs it:** Engram claims traceability-first, but currently can't answer "what did the agent believe about user X at the time it made decision Y?" The SUPERSEDES edge type exists in the schema but has no automated lifecycle. Zep's approach — LLM-driven contradiction detection with bitemporal invalidation — is the gold standard for auditable memory.

**Current Engram state:** SUPERSEDES and CONTRADICTS edge types defined in `domain/models.py`. No automated extraction of contradictions. No validity windows on nodes. No time-scoped graph traversal queries.

**Implementation scope:**

- Add `validity_start` and `validity_end` fields to Belief and Preference nodes (schema extension, not frozen-field modification)
- Add contradiction detection in `worker/extraction.py` — after entity extraction, query existing graph for conflicting facts on same entity
- New Cypher queries in `adapters/neo4j/queries.py` for time-windowed traversal: `WHERE n.validity_end IS NULL OR n.validity_end > $query_time`
- Populate SUPERSEDES edges automatically when contradictions detected

**Effort:** Large (touches extraction, projection, queries). 2-3 sprint cycles.

---

### TD-002: Feedback-Driven Edge Reweighting

**Observed in:** Cognee (memify pipeline)

**What it does:** After the initial graph projection, a background pipeline continuously optimizes the graph based on actual usage. Edges that are frequently traversed during retrieval get strengthened. Nodes that are never returned in context responses get weakened. The graph learns what actually matters from agent behavior, not just from content analysis.

**Why Engram needs it:** Engram's 4-factor Ebbinghaus decay scoring (recency, importance, relevance, user_affinity) is computed at query time from static properties. It never learns. If the agent consistently retrieves Node A but ignores Node B, both keep the same importance weight. Cognee's feedback loop closes this gap — the graph adapts to how it's actually used.

**Current Engram state:** `domain/scoring.py` computes `score_node()` with 4 static factors. `last_accessed_at` and `access_count` fields exist on nodes but are only used for a simple recency boost, not for systematic feedback. `adapters/neo4j/maintenance.py` has batch pruning but no reweighting. The retrieval improvement plan identifies this as gap #11 (static edge weight matrix).

**Implementation scope:**

- Track retrieval outcomes: log which nodes were returned in Atlas responses and whether the agent used them (via subsequent event correlation)
- Store retrieval telemetry in Redis: `retrieval:{node_id}:returned_count`, `retrieval:{node_id}:used_count`
- Background worker (could extend C4 consolidation or be a new C5) that reads telemetry and updates `importance_score` on Neo4j nodes
- Exponential moving average to prevent single-query spikes from distorting weights

**Effort:** Medium. New telemetry layer + batch reweighting job. 1-2 sprint cycles.

---

### TD-003: Fact Consistency Validation at Ingest

**Observed in:** HaluMem framework (Nov 2025), Zep extraction pipeline

**What it does:** After LLM extraction produces entity-relation triplets, a validation step checks each fact against the existing graph for: duplicate detection (vector similarity), temporal consistency (contradicts same-session fact?), entity consistency (entity type matches historical records?), and confidence scoring (0–1 per extracted fact).

**Why Engram needs it:** Engram's projection is mechanical — events become nodes via deterministic Lua scripts and Cypher MERGE. No semantic validation occurs. If the LLM extracts "Sarah works at Acme" in Session 1 and "Sarah works at Globex" in Session 3, both coexist in the graph without conflict detection. For a traceability-first system, allowing contradictory facts to silently coexist undermines the trust proposition.

**Current Engram state:** `worker/extraction.py` runs LLM extraction at session end (Consumer 2). No post-extraction validation. The `domain/entity_resolution.py` module exists with three-tier resolution logic (exact match, fuzzy match, semantic match) but is focused on merging entities, not validating facts.

**Implementation scope:**

- Add validation step in `worker/extraction.py` after LLM extraction and before Neo4j projection
- Query existing graph for same-entity facts; compare with extracted facts using vector similarity
- Flag contradictions with CONTRADICTS edges and mark old facts with `validity_end` (ties into TD-001)
- Add `extraction_confidence` field (float 0–1) to extracted nodes
- Log validation results for audit trail

**Effort:** Medium. Primarily extraction pipeline changes. 1-2 sprint cycles.

---

### TD-004: Wire Embeddings into Query Path

**Observed in:** Every competitor (Mem0, Zep, Cognee, GraphRAG all use embeddings for retrieval)

**What it does:** Use vector similarity between the query embedding and stored node embeddings to compute genuine relevance scores during retrieval.

**Why Engram needs it:** This is already identified as **CRITICAL Gap #1** in `retrieval-improvement-plan.md`. The embedding infrastructure is 95% built — `adapters/embedding/service.py` has a working `SentenceTransformerEmbedder`, Consumer 3 computes embeddings, and RediSearch vector indexes are configured. But `score_node()` is called without `query_embedding`, so `relevance_score` defaults to 0.5 for every node. The entire relevance dimension of scoring is disabled.

**Current Engram state:** Infrastructure complete but disconnected. One wiring change transforms scoring from 3-factor (recency, importance, user_affinity) to 4-factor (+ relevance).

**Implementation scope:**

- Compute query embedding in context retrieval endpoint (`api/routes/context.py`)
- Pass query embedding to `score_node()` in `domain/scoring.py`
- Use cosine similarity against stored node embeddings
- Small change, massive impact

**Effort:** Small. This is a wiring fix, not new infrastructure. Days, not sprints.

---

## P1 — Competitive Table Stakes

### TD-005: Memory-Aware Routing by Intent Granularity

**Observed in:** AMA (Always-on Memory Agent, Google, Jan 2026)

**What it does:** Instead of returning the full graph for every query, route to specific subgraph layers based on classified intent. "When did X happen?" routes to the episodic layer (raw events with timestamps). "What is true about X?" routes to the fact layer (deduplicated, validated facts). "What's related to X?" routes to the semantic layer (entity embeddings, multi-hop paths).

**Why Engram needs it:** Engram already classifies 8 intent types (`domain/intent.py`), but every intent returns the same Atlas response shape from the full graph. For large graphs, this wastes tokens and increases latency. Granularity routing means "why" queries return causal chains (CAUSED_BY edges), "when" queries return temporal chains (FOLLOWS edges), and "personalize" queries return user profile subgraphs (HAS_PREFERENCE, HAS_SKILL edges).

**Current Engram state:** Intent classification exists and works. Edge weight matrix in `domain/intent.py` assigns different weights per intent, but the query still traverses the full graph. Retrieval improvement plan identifies this as gap #4 (intent classification is rule-based and simplistic).

**Implementation scope:**

- Map intent types to primary edge types for traversal (config, not code): `why → CAUSED_BY`, `when → FOLLOWS`, `personalize → HAS_PREFERENCE + HAS_SKILL`, etc.
- Add layer filtering in `adapters/neo4j/queries.py` — constrain Cypher traversal to intent-relevant edge types
- Return layer metadata in Atlas `meta` block so the agent knows which subgraph it received

**Effort:** Medium. Query layer changes + configuration. 1 sprint cycle.

---

### TD-006: Semantic Deduplication in Entity Graph

**Observed in:** Mem0 (Mem0^g graph memory)

**What it does:** After entity extraction, a deduplication pass clusters entities by vector similarity and uses LLM reasoning to decide: are these the same entity? Mem0 uses graph relationship context for disambiguation — two entities named "Sarah" are distinguished by their relational neighborhoods (e.g., "Sarah who works at Acme" vs "Sarah the customer").

**Why Engram needs it:** Engram's `domain/entity_resolution.py` has three-tier resolution (exact, fuzzy, semantic) but runs as a separate step, not integrated into the extraction pipeline. The retrieval improvement plan doesn't specifically flag this, but the codebase review shows entity resolution is defined but not fully wired. Duplicate entities degrade graph quality and confuse provenance trails.

**Current Engram state:** Entity resolution module exists with SAME_AS and RELATED_TO edge creation logic. Not clear if it runs automatically during extraction or requires manual triggering.

**Implementation scope:**

- Integrate entity resolution into `worker/extraction.py` as a post-extraction step
- After extracting entities, query existing graph for similar entities (vector similarity + name fuzzy match)
- If match found above threshold, create SAME_AS edge instead of new entity node
- Use relational context (neighboring edges) for disambiguation when names match but contexts differ

**Effort:** Medium. Integration work, not new algorithms. 1 sprint cycle.

---

### TD-007: Incremental Consolidation on Session End

**Observed in:** ReMe framework, StreamAgent (ICLR 2026)

**What it does:** Instead of batching consolidation on a fixed schedule (Engram's current 6-hour cycle), trigger consolidation incrementally when a session ends. Merge new session events into existing summaries rather than recomputing from scratch: `merge(old_summary, new_events) → delta_summary`.

**Why Engram needs it:** The 6-hour consolidation window means that for the first 5 hours and 59 minutes after ingestion, the graph has raw events but no summaries. Agents querying during this window get less structured context. Session-end triggering would produce summaries within seconds of session close.

**Current Engram state:** `worker/consolidation.py` runs on a configurable schedule (default 6 hours per `settings.py`). Consumer 2 (extraction) already triggers on session end. The consolidation logic in `domain/consolidation.py` groups events into episodes by temporal gaps. No incremental merge — it recomputes summaries from scratch.

**Implementation scope:**

- Add session-end trigger to Consumer 4 (in addition to scheduled runs)
- Implement `merge_summary()` in `domain/consolidation.py` that takes existing summary + new events → updated summary
- Cache hot summaries in Redis for fast access during merge
- Keep scheduled 6-hour runs for cross-session pattern detection

**Effort:** Medium. Consolidation pipeline changes. 1-2 sprint cycles.

---

### TD-008: OpenTelemetry Integration

**Observed in:** OpenTelemetry GenAI SIG semantic conventions (standardized 2025-2026)

**What it does:** Emits standardized trace spans for all memory operations (ingest, retrieve, project, consolidate) using OpenTelemetry semantic conventions. Enables any APM tool (Datadog, Jaeger, Honeycomb) to correlate agent decisions with memory operations.

**Why Engram needs it:** Identified as **CRITICAL Gap GAP-OPS-011** in platform-readiness-gap-analysis.md. Engram has structlog + Prometheus metrics + `trace_id` field in events, but no distributed tracing. The GenAI SIG defines standard span attributes (`gen_ai.operation.name`, `gen_ai.agent.id`, `gen_ai.memory.type`) that Engram should adopt to position as the default lineage backend for OTel-instrumented agents.

**Current Engram state:** Zero OpenTelemetry imports or dependencies. `trace_id` field exists in event schema but is never correlated. ADR-0017 (Observability Architecture) defines Prometheus metrics but doesn't mention OTel.

**Implementation scope:**

- Add `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi` to dependencies
- Instrument API middleware (`api/middleware.py`) with tracer
- Add spans in `adapters/redis/store.py` and `adapters/neo4j/store.py` for data operations
- Map Engram's `trace_id` to OTel trace context for end-to-end correlation
- Align span attributes with GenAI SIG conventions

**Effort:** Medium. Instrumentation layer, no core logic changes. 1 sprint cycle.

---

## P2 — Valuable Enhancements

### TD-009: Semantic Lossless Compression for Consolidation

**Observed in:** SimpleMem pattern, Active Context Compression (Jan 2026)

**What it does:** Instead of LLM-generated prose summaries (which lose structured information), extract core facts as subject-predicate-object triplets, score them by query frequency from past sessions, and recompose summaries from top-scored facts only. Achieves ~22% token savings with 100% fact retention.

**Current Engram state:** `domain/consolidation.py` creates episode-based summaries. LLM-based summarization is marked as TODO for Phase 5. Current summaries are deterministic groupings, not semantic compressions.

**Effort:** Medium. Consolidation logic changes. 1 sprint cycle.

---

### TD-010: Cryptographic Provenance Chain

**Observed in:** MemOS (July 2025)

**What it does:** Hash-chain facts: `H(fact | previous_fact | timestamp)` creates a tamper-evident audit trail. If any fact in the chain is retroactively modified, the chain breaks. This provides cryptographic proof that the event ledger hasn't been tampered with.

**Why Engram needs it:** Engram's immutable event ledger is an architectural principle, but nothing prevents a database admin from modifying Redis entries directly. Cryptographic chaining makes immutability verifiable, not just claimed. Critical for regulated industries.

**Current Engram state:** Events have `event_id` (UUID) and `global_position` (Redis Stream entry ID). No hash chaining. Lua ingest script enforces idempotent writes but doesn't verify chain integrity.

**Effort:** Medium. Add hash computation to ingest pipeline + verification endpoint. 1 sprint cycle.

---

### TD-011: Memory Access Audit Log

**Observed in:** MemOS, enterprise compliance patterns

**What it does:** Every memory read/write operation is logged with: who accessed it (agent_id), what was accessed (node_id), when (timestamp), why (query context), and what was returned. Separate from the event ledger — this is operational auditing, not event sourcing.

**Why Engram needs it:** Identified as **Gap GAP-SEC-013** in platform-readiness-gap-analysis (GDPR audit logging). Engram tracks what events created which nodes, but doesn't track who queried which nodes. For regulated deployments, knowing "Agent X retrieved Customer Y's preferences at time Z" is a compliance requirement.

**Current Engram state:** API logging exists in the frontend (`apiLogStore.ts`) but no server-side audit trail. No GDPR audit logging.

**Effort:** Small-Medium. Redis-based audit log + API middleware hook. 1 sprint cycle.

---

## P3+ — Future Phases

### TD-012: Multimodal Memory (Vision/Audio Embeddings)

**Observed in:** M3-Agent (Aug 2025)

**What it does:** Store visual and audio embeddings alongside text events. Cross-modal SIMILAR_TO edges connect related information across modalities.

**Relevance:** Only if Engram targets video/audio analysis agents. Not relevant for text-only customer support or coding agent use cases.

**Effort:** Large. New event types, embedding models, cross-modal projection logic. Phase 5+.

---

### TD-013: Agent Self-Editing of Memory

**Observed in:** Letta/MemGPT

**What it does:** Agents actively edit their own memory — promoting important facts to core memory, demoting irrelevant ones, rewriting summaries as understanding evolves.

**Relevance:** Philosophically conflicts with Engram's immutable-first design. The agent shouldn't be able to alter its own history. However, allowing agents to *annotate* (not modify) existing nodes with importance signals could preserve immutability while enabling agent-driven curation.

**Consideration:** Implement as "agent annotation" layer — agents create new Annotation nodes linked to existing events via ANNOTATES edges. Original events stay immutable. Agent's evolving understanding is captured as new events, not mutations.

**Effort:** Medium. New node type + agent API endpoint. Phase 4+.

---

## Cross-Reference: Existing Gap Documents

These tech debt items overlap with findings in existing Engram documentation:

| Tech Debt Item | Existing Reference |
|---|---|
| TD-004 (Wire embeddings) | retrieval-improvement-plan.md, Gap #1 (CRITICAL) |
| TD-005 (Intent routing) | retrieval-improvement-plan.md, Gap #4 (HIGH) |
| TD-008 (OpenTelemetry) | platform-readiness-gap-analysis.md, GAP-OPS-011 (CRITICAL) |
| TD-011 (Audit log) | platform-readiness-gap-analysis.md, GAP-SEC-013 (HIGH) |
| TD-001 (Bitemporal) | domain/models.py has SUPERSEDES/CONTRADICTS edges but no automation |
| TD-006 (Entity dedup) | domain/entity_resolution.py exists but integration unclear |

---

*Sources: Zep temporal KG architecture (arXiv:2501.13956), Mem0 production memory paper (arXiv:2504.19413), Cognee memify pipeline documentation, HaluMem evaluation framework (arXiv:2511.03506), OpenTelemetry GenAI SIG semantic conventions, MemOS architecture paper, AMA pattern (Google, 2026), SimpleMem compression, StreamAgent (ICLR 2026), M3-Agent multimodal memory, Letta Context Repositories blog.*
