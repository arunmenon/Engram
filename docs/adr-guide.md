# Engram ADR Guide

A plain-language walkthrough of the 18 Architecture Decision Records that define Engram's design. Written for developers joining the project or anyone who wants to understand _why_ the system works the way it does.

## What Are ADRs and Why Does Engram Have 18?

An Architecture Decision Record captures a significant technical choice: what was decided, what alternatives were rejected, and what trade-offs were accepted. Engram has 18 because the system spans event sourcing, graph knowledge representation, neuroscience-inspired memory tiers, LLM extraction, and multi-channel retrieval -- each requiring deliberate, documented choices.

Here is how data flows through the system at the highest level:

```
  Agent / Tool
       |
       v
  POST /v1/events/batch
       |
       v
  +------------------+       +-------------------+
  |   Redis Stack    | ----> | Projection Worker |
  | (Event Ledger)   |       | (Consumer Groups) |
  | Streams + JSON   |       +-------------------+
  |   + Search       |              |
  +------------------+              v
                            +---------------+
                            |    Neo4j      |
                            | (Graph View)  |
                            | 11 node types |
                            | 20 edge types |
                            +---------------+
                                    |
                                    v
                            POST /v1/context
                            POST /v1/query/subgraph
                            GET  /v1/lineage/{id}
                                    |
                                    v
                              Agent receives
                            provenance-annotated
                                 context
```

Events land in Redis (source of truth), get projected into Neo4j (query-optimized graph), and come back through the API with full provenance.

---

## Reading Roadmap

### Quick Start (5 ADRs)

If you have 30 minutes, read these in order to grasp the core architecture:

| Order | ADR      | Why Read It                                                            |
| ----- | -------- | ---------------------------------------------------------------------- |
| 1     | ADR-0001 | The foundational principle: traceability over memory                   |
| 2     | ADR-0003 | The dual-store architecture: Redis + Neo4j                             |
| 3     | ADR-0009 | The graph schema: 11 node types, 20 edge types, intent-aware retrieval |
| 4     | ADR-0007 | The memory model: four cognitive tiers from neuroscience               |
| 5     | ADR-0010 | The event store: why Redis replaced Postgres                           |

### Deep Dive (All 18)

For a thorough understanding, read in this dependency-respecting order:

ADR-0001 -> ADR-0002 -> ADR-0003 -> ADR-0004 -> ADR-0010 -> ADR-0007 -> ADR-0005 -> ADR-0008 -> ADR-0009 -> ADR-0011 -> ADR-0012 -> ADR-0013 -> ADR-0014 -> ADR-0006 -> ADR-0015 -> ADR-0016 -> ADR-0017 -> ADR-0018

This order ensures you never encounter an ADR that references concepts from one you have not yet read.

---

## Theme 1: Foundation

These two ADRs establish _what Engram is for_ and _what it is built with_.

### ADR-0001: Traceability-First Context Graph

**The system prioritizes tool-call traceability and provenance-annotated context retrieval over generalized memory features.**

Think of it like a court reporter who records every word verbatim before a legal researcher summarizes the case. The transcript (Redis) is the source of truth; the summary (Neo4j) is derived and rebuildable.

**Key decision:** MVP ships provenance first, memory features second. Memory-first designs (Mem0, Zep) were rejected because provenance becomes critical once agents reach production.

**In practice:** Every API response includes provenance pointers (event_id, global_position, session, agent, trace) so callers always know where context came from.

**Related:** ADR-0003 (dual store), ADR-0007/ADR-0008/ADR-0009 (memory and graph layers), ADR-0010 (event store).

### ADR-0002: Service Stack is Python + FastAPI

**Python + FastAPI was chosen for rapid API iteration, agent ecosystem fit, and mature async libraries.**

Think of it like choosing to build a restaurant kitchen where the whole chef team already speaks the language -- the Python agent ecosystem (LangChain, CrewAI, instructor, litellm) is where Engram's users live.

**Key decision:** Python over TypeScript/Node. Trade-off: runtime performance versus ecosystem alignment. Domain logic stays framework-agnostic (`domain/` has zero FastAPI imports).

**In practice:** Multiple processes (API server, projection worker, enrichment worker, consolidation worker) share the same domain library.

**Related:** ADR-0008 (workers), ADR-0010 (async Redis client).

---

## Theme 2: Data Layer

Three ADRs define how events are stored, validated, and physically organized in Redis.

### ADR-0003: Dual Store -- Redis Source of Truth, Neo4j Projection

**Redis serves as the immutable event ledger while Neo4j holds a query-optimized, fully rebuildable graph projection.**

Think of it like a hospital with an emergency room and a medical research library. Redis is the ER -- fast intake, never loses a record. Neo4j is the research library -- organized for complex queries. If the library burns down, rebuild it from the ER's records. This maps to the Complementary Learning Systems model from neuroscience: hippocampus (Redis) for rapid encoding, neocortex (Neo4j) for consolidated knowledge.

**Key decision:** Two stores, not one. Neo4j alone lacks an append-only ledger; Redis alone lacks graph traversal. Trade-off: operational complexity and eventual consistency.

**In practice:** Events land in Redis Streams. Projection workers write them into Neo4j. Neo4j is disposable -- wipeable and replayable from Redis at any time.

**Related:** ADR-0001 (immutable ledger principle), ADR-0007 (memory tier mapping), ADR-0010 (Redis details).

### ADR-0004: Immutable Event Ledger with Idempotent Ingestion

**Events are immutable once written, and ingestion is idempotent -- safe to retry, impossible to corrupt.**

Think of it like a banking ledger where every transaction is written in permanent ink. If a duplicate deposit slip arrives, the bank quietly rejects it rather than double-crediting the account.

**Key decision:** Append-only with deduplication. Mutable records were rejected because they break auditability and replay determinism.

**In practice:** An atomic Lua script checks a dedup sorted set, then writes to the global stream, session stream, and JSON document in one operation. `global_position` (the Redis Stream entry ID) gives every event a total ordering.

**Related:** ADR-0007 (episodic tier), ADR-0009 (events become graph nodes), ADR-0010 (Lua script).

### ADR-0010: Redis as Event Store

**Redis Stack (Streams + JSON + Search) replaces Postgres as the sole event store, providing sub-millisecond ingestion and push-based consumer groups.**

Think of it like replacing a filing cabinet (Postgres) with a high-speed conveyor belt (Redis Streams) plus a document scanner (RediSearch) and labeled bins (RedisJSON). The filing cabinet required polling; the conveyor belt pushes items to consumers instantly.

**Key decision:** Redis over Postgres. Polling-based consumption adds latency, and Postgres is overqualified for append-only workloads. Trade-off: 1-second AOF data loss window, no schema enforcement, 90-day retention ceiling.

**In practice:** Each event gets three structures: global stream entry, session stream entry, and JSON document. Hot (0-7 days) and cold (7+ days) tiers.

**Related:** ADR-0003 (dual-store), ADR-0004 (Lua dedup), ADR-0005 (consumers), ADR-0014 (archival beyond 90 days).

---

## Theme 3: Graph and Schema

Five ADRs define how events become a graph, what that graph looks like, and how the system understands what you are asking for.

### ADR-0005: Asynchronous Projection Worker with Replay Support

**An async projection worker transforms Redis events into Neo4j graph nodes and edges, decoupling ingestion from graph queries.**

Think of it like a newsroom where reporters file stories into a wire service (Redis), and an editorial team (projection worker) organizes them into a newspaper layout (Neo4j). Reporters never wait for the paper to print before filing the next story.

**Key decision:** Asynchronous, not synchronous. Inline projection was rejected because it couples ingestion latency to graph writes and amplifies failures.

**In practice:** XREADGROUP consumer groups deliver events with push semantics. The worker micro-batches writes, defers ACK until Neo4j confirms, and routes failures to a dead-letter queue. Full replay rebuilds Neo4j from scratch.

**Related:** ADR-0008 (later pipeline stages), ADR-0010 (source streams), ADR-0013 (four-consumer architecture).

### ADR-0009: Multi-Graph Schema and Intent-Aware Retrieval

**The Neo4j graph uses four edge categories (temporal, causal, semantic, entity) with intent-aware retrieval that weights traversal based on query classification.**

Think of it like a library with separate indexes for timeline, causation, similarity, and people/places. Ask "why did X happen?" and the librarian searches the causation index first. Ask "what is X?" and the entity index takes priority. MAGMA research showed 45.5% higher reasoning accuracy with this approach.

**Key decision:** Typed edge views with intent-aware weighting. A single generic edge type (loses traversal semantics) and separate databases per view (impractical cross-view queries) were both rejected.

**In practice:** 11 node types, 20 edge types, 8 intent classifications. Three retrieval channels (graph, vector, BM25) fused via Reciprocal Rank Fusion.

**Related:** ADR-0005 (projection), ADR-0008 (decay scoring), ADR-0011 (ontological grounding), ADR-0012 (personalization).

### ADR-0011: Ontological Foundation for the Context Graph

**A layered ontological foundation grounds the vocabulary in PROV-O, schema.org, OTel, and PG-Schema while preserving operational edge names optimized for retrieval.**

Think of it like a bilingual dictionary mapping street names to official cartographic designations. You navigate with street names (FOLLOWS, CAUSED_BY) because they are fast. The official map uses cartographic terms (prov:wasGeneratedBy) for standards compliance.

**Key decision:** Dual vocabulary -- operational names in Neo4j, PROV-O names in documentation. Full PROV-O (slow traversal) and RDF/OWL (needs reification for edge properties) were both rejected.

**In practice:** Six ontology modules formalize the type system, correcting ADR-0009 mapping errors and grounding event types in OpenTelemetry conventions.

**Related:** ADR-0004 (provenance model), ADR-0009 (schema grounding), ADR-0012 (personalization vocabulary).

### ADR-0012: User Personalization Ontology Extension

**Five new node types and nine new edge types enable graph-based user modeling with provenance-backed preferences.**

Think of it like a personal shopper building a customer profile -- noting you prefer dark roast (preference), learned from your Tuesday order (provenance), updated when you switch to medium roast (decay-driven evolution).

**Key decision:** Preferences are first-class graph nodes with triple-path structure: who (HAS_PREFERENCE), what (ABOUT), why (DERIVED_FROM).

**In practice:** Four source types: explicit, implicit-intentional, implicit-unintentional, and inferred. Preferences evolve via Ebbinghaus decay. GDPR compliance through cascade deletion.

**Related:** ADR-0008 (decay scoring), ADR-0009 (graph schema), ADR-0011 (ontology), ADR-0013 (extraction populates these nodes).

### ADR-0013: Knowledge Extraction Pipeline

**Four async consumers extract knowledge using LLM-based extraction and statistical analysis, with mandatory provenance via DERIVED_FROM edges.**

Think of it like an intelligence agency with four analyst desks. Desk 1 maps timelines (structural, no LLM). Desk 2 reads transcripts for insights (LLM, Haiku-class). Desk 3 cross-references databases (embeddings). Desk 4 reviews for patterns (consolidation, Sonnet-class). Every finding must cite the supporting paragraph -- no unsourced claims.

**Key decision:** All extraction is async, never blocking the API. Per-session batching (not per-turn) yields 39% better LLM performance. Pydantic models serve triple duty: validation, LLM structured output, and API schema.

**In practice:** Consumer 2 fires on session end, writes extracted knowledge to Neo4j with DERIVED_FROM edges. A hard evidence gate requires `source_quote` verifiable by substring match.

**Related:** ADR-0008 (consolidation), ADR-0010 (source streams), ADR-0011/ADR-0012 (extracted types).

---

## Theme 4: Memory Intelligence

Three ADRs model how the system remembers, forgets, and ages knowledge over time.

### ADR-0007: Cognitive Memory Tier Architecture

**Four cognitive tiers -- sensory, working, episodic, semantic -- mapped to system components, formalize the neuroscience-inspired CLS model.**

Think of it like human memory itself. Flash of recognition (sensory tier = API buffer). Holding a phone number while dialing (working tier = context response, max 100 nodes). Last year's birthday party (episodic tier = Redis ledger). Knowing Paris is France's capital (semantic tier = Neo4j graph).

**Key decision:** Four explicit tiers, not a simple short/long split. Nine research papers validated the CLS mapping. Trade-off: conceptual overhead for precise vocabulary about where data lives.

**In practice:** Events enter at sensory (API buffer), flow to episodic (Redis), get projected into semantic (Neo4j), and are assembled into working memory (API response) on demand.

**Related:** ADR-0003 (stores per tier), ADR-0008 (movement between tiers), ADR-0010 (episodic implementation), ADR-0012 (personalization as semantic knowledge).

### ADR-0008: Memory Consolidation, Decay, and Active Forgetting

**Three-stage consolidation with Ebbinghaus-inspired decay scoring, tiered retention, and active forgetting -- because forgetting is a feature, not a bug.**

Think of it like a librarian reviewing the stacks on a schedule. Popular books stay on the main floor. Rarely-touched books go to the basement. Forgotten materials get summarized onto a catalog card before recycling. The library stays useful because it curates, not hoards.

**Key decision:** Active decay on Neo4j; Redis ledger stays append-only. No-decay, TTL-only, and LRU alternatives were rejected for ignoring importance, recency, or relevance.

**In practice:** Decay score = weighted sum of recency, importance, relevance, user affinity (Ebbinghaus curve). Four Neo4j tiers: Hot (<24h), Warm (24h-7d), Cold (7-30d), Archive (>30d). Reflection trigger at accumulated importance >150.

**Related:** ADR-0005 (pipeline foundation), ADR-0007 (tier model), ADR-0012 (preference decay), ADR-0013 (extraction), ADR-0014 (archival).

### ADR-0014: Archival and Lifecycle Management

**Seven lifecycle gaps addressed to make consolidation and the event store production-ready.**

Think of it like a warehouse hiring a facilities manager. Scheduled reviews, expired stock removed, shelf space capped, and every item photographed before disposal.

**Key decision:** Archive before delete (GCS in production, filesystem in dev). Consolidation self-triggers every 6 hours. No-archive was rejected for compliance reasons.

**In practice:** Day 0 (Hot) -> Day 7 (Cold) -> Day 30 (summaries) -> Day 60 (GCS export) -> Day 90 (summaries + archive only) -> Day 365+ (Coldline). Includes PEL-safe trimming and orphan cleanup.

**Related:** ADR-0008 (consolidation pipeline), ADR-0010 (Redis retention).

---

## Theme 5: API and Integration

Two ADRs define what the outside world sees.

### ADR-0006: MVP Query API -- Context Retrieval and Lineage

**The MVP API ships context retrieval and lineage for immediate agent utility, with system-owned intent classification.**

Think of it like a hotel concierge. You say "Why do payments keep failing?" and the concierge determines you need causal analysis, temporal patterns, and entity context -- then assembles the answer. You never specify which index to search.

**Key decision:** Ship context retrieval and lineage first. Generic query DSL (premature) and ingest-only (no visible value) were both rejected.

**In practice:** All responses use the Atlas pattern: nodes (with provenance + scores), edges, pagination, metadata (intents, seeds, capacity). The system owns retrieval -- callers provide a query, not a traversal spec.

**Related:** ADR-0007/ADR-0008/ADR-0009 (models and scoring), ADR-0015 (SDK wrapper).

### ADR-0015: SDK and Integration Architecture

**A three-layer integration stack (Core SDK, MCP Server, Framework Adapters) reduces integration from around 25 lines to 3-5 lines.**

Think of it like a car with multiple interfaces to the same engine: steering wheel (Simple API -- `engram.record()`, `engram.recall()`), dashboard controls (Full API), phone mount adapters (Framework Adapters), and voice assistant (MCP Server). Different drivers, same engine.

**Key decision:** Three layers. Auto-generated SDK only (no session management) and MCP-only (Python devs need native SDK) were both rejected.

**In practice:** Simple API: `record()`, `recall()`, `trace()`. MCP Server: 7 tools. Framework adapters for LangChain, CrewAI, and others.

**Related:** ADR-0006 (underlying API), ADR-0009 (retrieval capabilities), ADR-0012 (personalization).

---

## Theme 6: Operations and Scale

Three ADRs cover security, observability, and the path to billions of nodes.

### ADR-0016: Security Architecture

**Two-tier bearer token auth with token bucket rate limiting, CORS, strict Pydantic validation, and SecretStr management.**

Think of it like building security: lobby badge (API key), executive key card (admin key), revolving door speed limit (rate limiting: 120/30s standard, 30/30s admin), and unlocked after hours for cleaning (dev mode).

**Key decision:** HMAC-safe constant-time bearer tokens, two tiers. Per-process rate limiting (not distributed). Trade-off: rate state not shared across processes.

**In practice:** Four secrets via SecretStr. Query bounds: max_nodes 500, max_depth 10.

**Related:** ADR-0014 (admin operations), ADR-0015 (SDK handles auth).

### ADR-0017: Observability Architecture

**Ten Prometheus metrics, structlog, X-Request-ID correlation, and layered health checks.**

Think of it like hospital patient monitoring: vital signs (Prometheus metrics), detailed charts (structlog), wristband IDs (X-Request-ID for request correlation), and quick pulse check vs. full diagnostic (liveness vs. admin health endpoint).

**Key decision:** In-process Prometheus and structlog, no external agent needed. Trade-off: no distributed tracing yet.

**In practice:** 10 metrics (HTTP, rate limits, ingestion, consumer lag, graph queries). X-Request-ID as UUID4 per request.

**Related:** ADR-0005 (consumer lag), ADR-0008 (consolidation metrics), ADR-0016 (rate limit metrics).

### ADR-0018: Billion-Scale Graph Architecture

**A four-phase scaling roadmap (10M to 10B+ nodes) triggered by quantitative thresholds, preserving the frozen GraphStore protocol.**

Think of it like city planning for growth. Phase A: neighborhoods (tenant-sharded Neo4j). Phase B: old town/new town split (time-partitioned). Phase C: upgrade the water main (Redis to Kafka). Phase D: redesign the grid only if you become a megacity (distributed graph). Do not build Phase D for a town of 10,000.

**Key decision:** Scale incrementally at measured thresholds, not speculatively. Per-session growth: ~40 nodes, ~65 edges, so timelines are predictable.

**In practice:** Phase A: ShardRouter (~1-2ms) with 150 virtual nodes. Rebalancing via event replay. Frozen GraphStore protocol means no adapter changes -- only routing changes.

**Related:** ADR-0003 (dual-store), ADR-0010 (Redis to Kafka in Phase C), ADR-0014 (archival bounds active graph size).

---

## Architecture Flow with ADR Annotations

```
  Agent / Tool Action
         |
         | ADR-0004 (immutable event, idempotent ingest)
         v
  +------------------+
  |   Redis Stack    |  ADR-0010 (Streams + JSON + Search)
  |   (Source of     |  ADR-0003 (dual-store, hippocampus role)
  |    Truth)        |  ADR-0007 (episodic memory tier)
  +------------------+
         |
         | ADR-0005 (async projection, consumer groups)
         v
  +------------------+
  | Projection       |  ADR-0013 (4 consumers: structural, extraction,
  | Workers          |            enrichment, consolidation)
  |                  |  ADR-0008 (decay scoring, active forgetting)
  +------------------+
         |
         v
  +------------------+
  |     Neo4j        |  ADR-0009 (11 nodes, 20 edges, intent-aware)
  |   (Graph View)   |  ADR-0011 (ontological grounding)
  |                  |  ADR-0012 (user personalization)
  |                  |  ADR-0007 (semantic memory tier)
  +------------------+
         |
         | ADR-0006 (Atlas response, system-owned retrieval)
         v
  +------------------+
  |   REST API       |  ADR-0016 (security, rate limiting)
  |   FastAPI        |  ADR-0017 (metrics, logging, health)
  |                  |  ADR-0002 (Python + FastAPI stack)
  +------------------+
         |
         | ADR-0015 (SDK, MCP, framework adapters)
         v
  Agent receives provenance-annotated context

  Lifecycle: ADR-0014 (archival, retention, cleanup)
  Scale:     ADR-0018 (sharding, partitioning, Kafka)
  Principles: ADR-0001 (traceability-first, provenance in all responses)
```

---

## ADR Dependency Map

```
ADR-0001 (Traceability Principles)
  |
  +---> ADR-0002 (Tech Stack)
  |
  +---> ADR-0003 (Dual Store)
  |       +---> ADR-0010 (Redis Event Store)
  |               +---> ADR-0014 (Archival)
  |
  +---> ADR-0004 (Immutable Ledger)
  |       +---> ADR-0010 (Lua dedup script)
  |
  +---> ADR-0005 (Projection Worker)
  |       +---> ADR-0008 (Consolidation + Decay)
  |               +---> ADR-0013 (Extraction Pipeline)
  |                       +---> ADR-0014 (Archival)
  |
  +---> ADR-0006 (Query API)
  |       +---> ADR-0015 (SDK + Integration)
  |
  +---> ADR-0007 (Memory Tiers)
  |       +---> ADR-0008 (Consolidation)
  |               +---> ADR-0012 (Personalization)
  |
  +---> ADR-0009 (Graph Schema)
  |       +---> ADR-0011 (Ontology)
  |               +---> ADR-0012 (Personalization)
  |                       +---> ADR-0013 (Extraction)
  |
  +---> ADR-0016 (Security)
  +---> ADR-0017 (Observability)
  +---> ADR-0018 (Scale)
```

**Key dependency chains:**

- **Data flow:** ADR-0001 -> ADR-0004 -> ADR-0010 -> ADR-0014 -> ADR-0018
- **Graph evolution:** ADR-0005 -> ADR-0009 -> ADR-0011 -> ADR-0012 -> ADR-0013
- **Memory model:** ADR-0007 -> ADR-0008 -> ADR-0013 -> ADR-0014
- **API surface:** ADR-0006 -> ADR-0015

---

## Quick Reference Table

| ADR      | Title                            | Theme      | One-Liner                                                              |
| -------- | -------------------------------- | ---------- | ---------------------------------------------------------------------- |
| ADR-0001 | Traceability-First Context Graph | Foundation | Provenance and traceability over memory features                       |
| ADR-0002 | Service Stack: Python + FastAPI  | Foundation | Python for ecosystem fit, FastAPI for async performance                |
| ADR-0003 | Dual Store: Redis + Neo4j        | Data Layer | Redis as source of truth, Neo4j as rebuildable projection              |
| ADR-0004 | Immutable Event Ledger           | Data Layer | Append-only events with idempotent ingestion via Lua                   |
| ADR-0005 | Async Projection Worker          | Graph      | Decoupled event-to-graph transformation with replay                    |
| ADR-0006 | MVP Query API                    | API        | Context retrieval and lineage with Atlas response pattern              |
| ADR-0007 | Cognitive Memory Tiers           | Memory     | Four neuroscience-inspired tiers: sensory, working, episodic, semantic |
| ADR-0008 | Consolidation, Decay, Forgetting | Memory     | Ebbinghaus decay scoring and active forgetting as a feature            |
| ADR-0009 | Multi-Graph Schema               | Graph      | 11 node types, 20 edge types, intent-aware retrieval                   |
| ADR-0010 | Redis Event Store                | Data Layer | Redis Streams + JSON + Search replaces Postgres                        |
| ADR-0011 | Ontological Foundation           | Graph      | PROV-O grounding with operational dual vocabulary                      |
| ADR-0012 | User Personalization             | Graph      | Preferences, skills, patterns as first-class graph nodes               |
| ADR-0013 | Knowledge Extraction Pipeline    | Memory     | Four async consumers with LLM extraction and evidence gates            |
| ADR-0014 | Archival and Lifecycle           | Memory     | Seven gaps fixed: scheduled cleanup, archive before delete             |
| ADR-0015 | SDK and Integration              | API        | Three-layer stack: Core SDK, MCP Server, Framework Adapters            |
| ADR-0016 | Security Architecture            | Operations | Two-tier auth, rate limiting, query bounds                             |
| ADR-0017 | Observability Architecture       | Operations | 10 Prometheus metrics, structlog, request correlation                  |
| ADR-0018 | Billion-Scale Graph              | Operations | Four-phase scaling from 10M to 10B+ nodes                              |
