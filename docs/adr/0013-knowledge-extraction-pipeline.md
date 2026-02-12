# ADR-0013: Knowledge Extraction Pipeline

Status: **Proposed**
Date: 2026-02-12
Updated: 2026-02-12 (revised to async-first architecture with Redis Streams)
Extends: ADR-0008 (consolidation and decay), ADR-0010 (Redis event store), ADR-0011 (ontological foundation), ADR-0012 (user personalization ontology)

## Context

ADRs 0011 and 0012 define **what** the knowledge graph looks like: 8 node types (Event, Entity, Summary, UserProfile, Preference, Skill, Workflow, BehavioralPattern), 16 edge types, and detailed property constraints including enums, float ranges, and provenance requirements. ADR-0008 defines a three-stage consolidation pipeline (event projection, enrichment, re-consolidation) with decay and active forgetting. What remains undefined is **how** knowledge gets extracted from unstructured conversation text and structured event data into these graph types.

The primary use case is **conversational agents for SMB merchants** (PayPal-style payment/commerce platform). Merchants interact with AI support agents about payment settings, invoicing, disputes, shipping, analytics, and compliance. During these conversations, merchants implicitly and explicitly reveal preferences, skills, behavioral patterns, and interests that the system must capture, validate, and persist with full provenance.

### Why Fully Async

Within a conversation session, the agent already has the full transcript in its context window. It does not need to query the graph to recall what the merchant said 3 turns ago. The graph serves **cross-session** context -- when the merchant returns days or weeks later. Since cross-session retrieval is never latency-sensitive to the millisecond, all knowledge extraction can be async without degrading the agent experience.

Redis Streams provide the natural coordination mechanism. Events are written to a stream (sub-millisecond, in-memory), and consumer groups process them asynchronously with guaranteed delivery, automatic redelivery on failure, and built-in ordering. This replaces the polling-based projection worker model and eliminates any need for synchronous extraction on the API hot path.

### Extraction Sources

Four processing stages exist, handled by async consumers:

| Source | Consumer | LLM Required | Trigger |
|--------|----------|-------------|---------|
| Structured events (temporal ordering, causal links, entity mentions) | Graph Projection (Consumer 1) | No (structural operations + optional rule-based fallback) | Per-event from Redis Stream |
| Session conversation text (preferences, skills, interests, entities) | Session Extraction (Consumer 2) | Yes (per-session batch) | Session end or every N turns |
| Event metadata (keywords, embeddings, importance scores) | Enrichment (Consumer 3) | No (local embedding model) | Per-event-batch from Redis Stream |
| Cross-session aggregated patterns (workflows, behavioral patterns) | Consolidation & Maintenance (Consumer 4) | Yes (periodic batch) | Configurable schedule (default: every 6 hours) |

No production agent memory system (Mem0, Zep/Graphiti, Memoria, A-MEM, MAGMA) covers our full extraction needs. Entity and Preference extraction have production validation; Skill, Workflow, and BehavioralPattern extraction are **novel to our system** with no production precedent (researcher-2, Section 6.6; reviewer-2, Gap #6). Event-level provenance via DERIVED_FROM edges is our key differentiator -- no production system implements this (researcher-2, Section 8.3; reviewer-2, "Provenance Gap" observation).

### Research Basis

This ADR synthesizes findings from three research tracks and three independent reviews:

1. **LLM-Based Extraction Techniques** (researcher-1): Prompt engineering, structured output, confidence scoring, model selection, hallucination detection, and per-knowledge-type extraction strategies.
2. **Production Extraction Pipelines** (researcher-2): Architecture analysis of Mem0, Zep/Graphiti, Memoria, A-MEM, and MAGMA -- extraction prompts, conflict resolution, entity resolution, cost/latency profiles.
3. **Ontology-Guided Extraction and Validation** (researcher-3): Schema-as-prompt patterns, four-layer validation pipeline, entity resolution during extraction, confidence calibration, ontology evolution, SHACL validation.
4. **Review feedback** (reviewer-1, reviewer-2, reviewer-3): Corrections to SPIRES applicability claims, NLI source-type differentiation, cost figure sourcing discipline, knowledge type coverage gaps, per-extraction validation, async graph consistency, embedding-based entity retrieval, and separate extraction paths for text vs. behavioral data.

## Decision

### 1. Extraction Architecture Overview

The extraction pipeline uses an **async-first, four-consumer model** coordinated via Redis Streams. All knowledge extraction happens asynchronously -- nothing blocks the API request path except writing the raw event to the Redis Stream.

```
API Request
    |
    v
XADD event to Redis Stream (<1ms, in-memory)
    |
    +---> Return 202 Accepted to caller
    |
    +---> [Consumer 1: Graph Projection (per-event, async)]
    |       Structural edges: FOLLOWS, CAUSED_BY
    |       Event nodes in Neo4j
    |       Optional: rule-based entity extraction (regex/alias dict) as resilience fallback
    |       Latency: <50ms per event | No LLM
    |
    +---> [Consumer 2: Session Extraction (per-session, async)]
    |       ALL knowledge extraction: entities, preferences, skills, interests
    |       Triggered on system.session_end event or every N turns
    |       Full four-layer validation + provenance
    |       Latency: 2-10s per session | LLM (Haiku/Flash-class)
    |
    +---> [Consumer 3: Enrichment (per-event-batch, async)]
    |       Derived attributes: keywords, embeddings, importance_score
    |       Similarity edges: SIMILAR_TO (cosine > 0.85)
    |       Entity reference edges: REFERENCES (from entity mentions)
    |       Latency: 50-500ms per event batch | Embedding model (no LLM API)
    |
    +---> [Consumer 4: Consolidation & Maintenance (scheduled)]
            Cross-session: workflows, behavioral patterns, preference merging
            Hierarchical summarization, active forgetting/pruning
            Reflection triggers (importance sum > 150)
            Latency: minutes per batch | LLM (Sonnet-class) + statistical analysis
```

**Core principle: Ontology-as-extraction-schema.** Our cg-user ontology (ADR-0011/0012) drives extraction prompts directly. Pydantic models serve triple duty: (a) defining the extraction target schema for LLM prompts, (b) validating LLM output automatically via the Instructor library, and (c) mapping validated output to Neo4j graph operations. This avoids open-ended extraction followed by schema mapping -- the approach validated by SPIRES/OntoGPT for schema-driven extraction (researcher-1, Section 1.1; researcher-3, Section 2.1).

**Qualification on SPIRES**: SPIRES is validated primarily on biomedical text extraction, not conversational preference extraction. The schema-as-prompt *pattern* is transferable; SPIRES-specific benchmarks are not directly applicable to our domain (reviewer-1, Gap #1).

### 2. Redis Stream Coordination

Events flow through a single Redis Stream consumed by independent consumer groups. Each consumer group processes events at its own pace with guaranteed delivery.

```
Redis Stream: "events:{namespace}"
    |
    ├── Consumer Group: "graph-projection"
    │     Consumers: 1-4 (scalable)
    │     Reads: every event
    │     Acknowledges: after Neo4j structural projection completes
    │     Processing: <50ms per event
    │
    ├── Consumer Group: "session-extraction"
    │     Consumers: 1-2
    │     Reads: system.session_end events (or turn-count threshold events)
    │     On trigger: XRANGE to collect all events for that session
    │     Acknowledges: after extraction + validation + Neo4j write completes
    │     Processing: 2-10s per session
    │
    ├── Consumer Group: "enrichment"
    │     Consumers: 1-2
    │     Reads: every event (after Consumer 1 has projected structural edges)
    │     Computes: keywords, embeddings, importance_score on Event nodes
    │     Creates: SIMILAR_TO edges (cosine > 0.85), REFERENCES edges
    │     Acknowledges: after all derived attributes written to Neo4j
    │     Processing: 50-500ms per event batch
    │
    └── Consumer Group: "consolidation"
          Consumers: 1
          Reads: scheduled trigger events (configurable schedule, default: every 6 hours, consistent with ADR-0008)
          On trigger: pattern detection + hierarchical summarization + active forgetting
          Also runs on reflection trigger (importance sum > REFLECTION_THRESHOLD)
          Acknowledges: after all maintenance tasks complete
          Processing: minutes per batch
```

**Why Redis Streams over polling:**

| Concern | Polling (old design) | Redis Streams |
|---------|---------------------|---------------|
| Event delivery | Worker polls with cursor, tracks position | Consumer group auto-delivers, tracks offset per consumer |
| Worker crash recovery | Event may be reprocessed or lost depending on cursor state | Pending Entry List (PEL) auto-redelivers unacknowledged events |
| Parallel workers | Requires distributed locking or partitioning | Consumer groups natively distribute events across consumers |
| Backpressure | Worker falls behind silently | Stream length (`XLEN`) is monitorable; consumer lag is trackable |
| Ordering | Relies on `global_position BIGSERIAL` | Stream IDs are timestamp-based, naturally ordered |

**Session extraction trigger:** When a `system.session_end` event arrives in the stream, Consumer 2 collects all events for that session via `XRANGE` (or a secondary session-indexed structure in Redis) and runs LLM extraction over the full transcript. For long-running sessions, an intermediate trigger fires every N turns (configurable, default 10) to extract mid-session, reducing the delay before knowledge reaches the graph.

### Stage-to-Consumer Mapping

ADR-0008 defines a three-stage consolidation lifecycle. This ADR maps those stages to four Redis Stream consumer groups, adding a dedicated consumer for LLM-based session extraction that ADR-0008 did not anticipate.

| ADR-0008 Stage | Consumer | What Moved | What's New |
|---------------|----------|------------|------------|
| Stage 1: Event Projection | Consumer 1: Graph Projection | Structural edges (FOLLOWS, CAUSED_BY), event nodes | Optional rule-based entity fallback |
| (not in ADR-0008) | Consumer 2: Session Extraction | -- | LLM-based extraction of preferences, skills, entities, interests from conversation text |
| Stage 2: Enrichment | Consumer 3: Enrichment | Keywords, embeddings, importance_score, SIMILAR_TO edges, REFERENCES edges | -- |
| Stage 3: Re-Consolidation | Consumer 4: Consolidation & Maintenance | Cross-event relationship discovery, hierarchical summarization, active forgetting/pruning, reflection triggers, centrality-based importance updates | Workflow extraction, behavioral pattern detection, cross-session preference merging |

**Ordering dependency**: Consumer 3 (enrichment) SHOULD wait for Consumer 1 (structural projection) to complete for a given event before computing derived attributes. This is achieved by reading from the same stream but with a processing delay (Consumer 3 processes events that Consumer 1 has already acknowledged). Consumer 2 operates independently on session boundaries. Consumer 4 operates on a schedule and reads from Neo4j, not directly from the stream.

### 3. Consumer 1: Structural Graph Projection (No LLM)

Consumer 1 reads every event from the stream and performs structural graph operations only. No knowledge extraction occurs here -- this consumer builds the graph backbone that Consumer 2, Consumer 3, and Consumer 4 operate on.

**What gets projected:**

| Operation | Source | Output | Method |
|-----------|--------|--------|--------|
| Event node creation | Event payload | Event node in Neo4j | Direct mapping |
| Temporal ordering | `occurred_at` timestamps | FOLLOWS edges | Timestamp comparison |
| Causal relationships | `parent_event_id` references | CAUSED_BY edges | Direct mapping |
| Session grouping | `session_id` on events | session_id property on Event nodes (enables session-scoped queries) | Direct mapping |

**Optional resilience fallback:** Consumer 1 may also perform lightweight rule-based entity extraction (regex patterns + domain alias dictionary) as a fallback when LLM services are unavailable. This produces Entity nodes with lower confidence (`confidence: 0.5`) and `derivation_method: "rule_extraction"` on the DERIVED_FROM edge. When Consumer 2 processes the session, it supersedes or confirms these preliminary entities with LLM-extracted, higher-confidence versions.

```python
# Resilience fallback: regex entity extraction (only when LLM consumer is behind/down)
MERCHANT_ENTITY_PATTERNS = {
    "service": r"PayPal|Stripe|Square|Shopify|WooCommerce|QuickBooks|Xero",
    "tool": r"dashboard|invoice generator|analytics tool|report builder",
    "concept": r"chargeback|dispute|refund|settlement|PCI compliance",
}
```

**Explicit preference events:** When a `user.preference.stated` event arrives, Consumer 1 can parse the structured payload directly into a Preference node (no LLM needed because the event already encodes category, key, polarity, and value). This follows Mem0's CRUD decision model (researcher-2, Section 1.4; reviewer-2, Recommendation #6) adapted for our ontology.

**Latency:** <50ms per event. No LLM calls, no external API dependencies. All operations are deterministic.

### 4. Consumer 2: Session Knowledge Extraction (LLM)

Consumer 2 is the primary extraction consumer. It processes complete session transcripts via LLM, extracting all knowledge types in a single pass.

**Trigger:** Fires when a `system.session_end` event arrives, or when a turn-count threshold is reached (configurable, default every 10 turns for long sessions). On trigger, the consumer collects all events for the session from Redis and reconstructs the conversation transcript.

**Why per-session batch, not per-turn:** Research shows LLMs exhibit 39% lower performance in multi-turn conversations when processing turns independently (researcher-1, Section 7.4). Full-session batch extraction provides cross-turn context (preferences stated in one turn and confirmed in another), is more token-efficient (amortized prompt overhead), and avoids early-turn bias. This aligns with Memoria's session-level extraction and MAGMA's slow-path consolidation (researcher-2, Sections 3.7, 5.5).

**Schema-as-prompt with Pydantic models.** Each cg-user node type has a corresponding extraction Pydantic model passed to the LLM via function calling / tool use (researcher-1, Section 2.3; researcher-3, Section 2.4). The Instructor library handles automatic validation and retry on schema violations:

```python
class ExtractedPreference(BaseModel):
    category: Literal["tool", "workflow", "communication",
                       "domain", "environment", "style"]
    key: str = Field(description="Preference key, e.g. 'notification_method'")
    polarity: Literal["positive", "negative", "neutral"]
    strength: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    source: Literal["explicit", "implicit_intentional",
                     "implicit_unintentional"]
    context: str | None = None
    about_entity: str | None = None
    source_quote: str = Field(
        description="EXACT quote from conversation supporting this extraction")
    source_turn_index: int | None = Field(
        None, description="Turn index in the conversation for provenance")
```

**Function calling as structured output mechanism.** Each ontology node type becomes a "tool" the model can invoke (e.g., `extract_preference`, `extract_skill_signal`, `extract_interest`). This provides natural multi-type extraction in a single pass, schema enforcement via `strict: true`, and framework alignment with both Anthropic and OpenAI APIs (researcher-1, Section 2.3).

**Knowledge-type-specific extraction strategies** (researcher-1, Section 8):

| Knowledge Type | Strategy | Key Extraction Signals |
|---------------|----------|----------------------|
| **Preferences** | Sentiment-aware prompting with polarity/strength calibration | "I always want...", "I prefer...", "don't use..." |
| **Skills** | Behavioral evidence aggregation with proficiency rubric | Technical vocabulary usage, question complexity, self-declared competency |
| **Interests** | Topic frequency analysis + depth-of-engagement scoring | Repeated questions, documentation requests, deep discussion |
| **Entities** | LLM-based extraction with disambiguation + known-entity injection | Named services, tools, concepts mentioned in conversation |

**Extract from user messages only.** Both Mem0 and Memoria explicitly extract from user messages, not assistant messages. This prevents the system from memorizing its own outputs and creating feedback loops (researcher-2, Section 7.1 pattern #3; researcher-1, Section 10.5).

**Two-tier model strategy** (researcher-1, Section 4.4):

| Extraction Complexity | Model Class | Examples |
|----------------------|-------------|---------|
| Simple (explicit preferences, entity extraction) | Haiku-class ($0.15-$1.00/M input tokens) | GPT-4o-mini, Gemini Flash, Claude Haiku 4.5 |
| Complex (implicit preferences, skill assessment) | Sonnet-class ($2.50-$3.00/M input tokens) | GPT-4o, Claude Sonnet 4.5 |

**Routing**: Start all extractions with the Haiku-class model. If extraction confidence falls below 0.5 or the conversation contains complex reasoning signals (multi-step preferences, hedged language, corrections), escalate to Sonnet-class.

**Negation and correction handling within sessions.** Merchants frequently correct themselves mid-conversation ("Actually, make it monthly instead"). When the extraction detects correction signals ("actually", "wait", "instead", "changed my mind"), both the original and corrected preference are extracted. The original gets `superseded_by` pointing to the corrected version and its confidence is reduced to 0.2 (researcher-1, Section 10.1).

**Reconciliation with Consumer 1 outputs.** If Consumer 1's resilience fallback already created preliminary Entity or Preference nodes, Consumer 2's higher-confidence LLM extractions supersede them. Consumer 2 checks for existing nodes via entity resolution before creating new ones, reinforcing matches (observation_count++) or superseding conflicts.

### 5. Consumer 3: Enrichment (ADR-0008 Stage 2)

Consumer 3 reads events from the stream after Consumer 1 has projected structural edges, and computes derived attributes on Neo4j nodes. This consumer implements ADR-0008 Stage 2.

**Derived attributes computed per event:**

| Attribute | Method | Stored On | Purpose |
|-----------|--------|-----------|---------|
| `keywords` | NLP extraction from event payload | Event node | Keyword-based retrieval |
| `embedding` | Sentence-transformer (all-MiniLM-L6-v2, 384-dim) | Event node | Semantic similarity, SIMILAR_TO edges |
| `importance_score` | Rule-based from event_type + payload heuristics + importance_hint | Event node | Decay scoring (ADR-0008), retrieval ranking |
| `summary` | Compressed description of event content | Event node | Hierarchical summarization input |

**Edge creation:**

- `SIMILAR_TO` edges between events with `cosine(embedding_i, embedding_j) > 0.85` (ADR-0009 threshold)
- `REFERENCES` edges from entity mention extraction in event payloads

**Latency:** 50-500ms per event batch. Embedding computation is the bottleneck (~50-200ms per event with all-MiniLM-L6-v2). Batch processing amortizes model loading overhead.

**Relationship to Consumer 2:** Consumer 3 enriches ALL events (structural metadata). Consumer 2 extracts knowledge from conversation TEXT. They are complementary -- Consumer 3 provides the embeddings and importance scores that decay scoring (ADR-0008) requires, while Consumer 2 provides the user-knowledge nodes (Preferences, Skills, etc.) that personalization requires.

### 6. Consumer 4: Consolidation & Maintenance (ADR-0008 Stage 3)

Consumer 4 runs on a configurable schedule (default: every 6 hours, consistent with ADR-0008) or after N new sessions per user. It operates on session summaries and the existing user subgraph, not raw conversation transcripts.

**Workflow extraction** (novel -- no production precedent). Workflows represent recurring step sequences a merchant follows. Detection uses graph pattern matching on the existing event graph to identify repeated subgraph structures (e.g., `analytics.view -> pricing.update -> inventory.check`), followed by LLM interpretation to generate a human-readable workflow description (researcher-3, Section 9.3).

**BehavioralPattern detection** (novel -- no production precedent). Six pattern types are defined in ADR-0012: delegation, escalation, routine, avoidance, exploration, specialization. Detection uses session summary aggregation fed to a Sonnet-class model with pattern template matching prompts (researcher-1, Section 8.4).

**Cross-session preference merging** with `superseded_by` chains. When a preference extracted in session B contradicts one from session A, the newer preference creates a `superseded_by` link on the older one. This follows Graphiti's temporal edge invalidation pattern (researcher-2, Section 2.6) adapted for our Preference node model. Importantly, Graphiti's bulk processing path (`add_episode_bulk`) disables temporal conflict resolution -- our batch path MUST preserve conflict detection (reviewer-2, Gap #2).

**Self-consistency sampling for high-impact patterns.** For behavioral patterns (which influence agent behavior across all future sessions), extract N=3 times and measure agreement. This is cost-justified at Consumer 4's batch cadence (researcher-1, Section 3.2.2; researcher-3, Stage 3 validation recommendation).

**Separate extraction paths for text vs. behavioral data** (reviewer-3, Key Design Principle #6). Behavioral patterns like "merchant always uses mobile app" come from session metadata (device type, timestamps), not conversation text. These use statistical/frequency-based extraction, not LLM extraction:

```python
# Example: tool preference from usage frequency (no LLM needed)
async def extract_tool_preferences_from_usage(user_id: str, window_days: int = 30):
    tool_usage = await graph_store.get_tool_usage_frequency(user_id, window_days)
    for tool_name, usage_count, success_rate in tool_usage:
        if usage_count >= 3 and success_rate > 0.7:
            yield ExtractedPreference(
                category="tool",
                key=f"tool_usage_{normalize(tool_name)}",
                polarity="positive",
                strength=min(0.9, 0.3 + (usage_count / 20)),
                confidence=0.5,  # implicit_unintentional
                source="implicit_unintentional",
                about_entity=tool_name,
                source_quote=f"Used {usage_count} times in {window_days} days",
            )
```

This hybrid approach reduces LLM dependency by an estimated 40-60% compared to an all-LLM pipeline (researcher-3, Section 9.4).

**Hierarchical summarization** (ADR-0008 Stage 3). Generate Summary nodes at episode, session, and agent levels. Summary nodes link to source events via SUMMARIZES edges, preserving provenance. This compresses old event clusters before forgetting removes the detailed nodes.

**Active forgetting and pruning** (ADR-0008 Stage 3). Enforce retention tier boundaries defined in ADR-0008:
- Hot (<24h): full detail retained
- Warm (24h-7d): low-importance SIMILAR_TO edges pruned (score < 0.7)
- Cold (7-30d): only nodes with importance_score >= 5 or access_count >= 3 retained; summary nodes replace pruned clusters
- Archive (>30d): removed from Neo4j; retained in Redis cold tier

**Reflection triggers** (ADR-0008). When accumulated importance of recent events exceeds REFLECTION_THRESHOLD (default 150), trigger an immediate consolidation pass outside the regular schedule.

**Centrality-based importance updates.** Periodically recalculate importance_score for high-traffic nodes based on graph centrality metrics (degree, betweenness). This supplements the initial rule-based scoring from Consumer 3.

### 7. Entity Resolution Strategy

Entity resolution prevents duplicate nodes and maintains graph integrity. Our strategy is a three-tier approach (ADR-0011 Section 3) informed by Graphiti's hybrid resolution (researcher-2, Section 2.4):

| Tier | Method | When | Confidence |
|------|--------|------|------------|
| **Exact match** | Deterministic normalization (lowercase, strip, canonicalize via alias dictionary) | Consumer 1 (fallback) + Consumer 2 | 1.0 |
| **Close match** | Embedding similarity > 0.9 (cosine on entity name embeddings) | Consumer 2 | 0.9+ |
| **Related match** | LLM verification ("Are entity A and entity B the same?") | Consumer 4 (ambiguous cases only) | Variable |

**Known-entity injection into extraction prompts.** Following the Graphiti/Zep pattern, Consumer 2 extraction prompts include existing entities to enable resolution during extraction (researcher-3, Section 4.3). Entities are selected via **embedding-based retrieval** (top-50 by semantic similarity to the conversation text) plus **frequency-based inclusion** (top-20 most referenced entities), not a naive fixed-limit cutoff (reviewer-3, Gap #3).

**Domain alias dictionary** for merchant abbreviations where embedding similarity fails on low-entropy strings (reviewer-3, Gap #3):

```python
DOMAIN_ALIAS_DICT = {
    "quickbooks": ["QB", "QBO", "Quickbooks Online"],
    "paypal": ["PP"],
    "usps": ["United States Postal Service", "US Postal Service"],
    "fedex": ["Federal Express", "FedEx Ground"],
    "csv": ["CSV file", "CSV export", "spreadsheet export"],
}
```

### 8. Confidence Scoring Framework

Every node type in ADR-0012 carries a `confidence` field (0.0-1.0) that gates graph insertion, determines conflict resolution priority, and provides provenance transparency. The extraction pipeline must produce meaningful confidence scores from day one.

**MVP: Source-type priors** (researcher-3, Section 6.3 Phase 1; reviewer-1, Tier 2 Recommendation #6; reviewer-3, Gap #4). No logprobs, no self-consistency sampling at extraction time. Confidence is determined by source type:

| Source Type | Confidence Prior | Rationale |
|------------|-----------------|-----------|
| `explicit` | >= 0.7 | User directly stated the preference |
| `implicit_intentional` | >= 0.4 | User deliberately demonstrated a choice |
| `implicit_unintentional` | >= 0.3 | Inferred from passive behavioral patterns |
| `inferred` | >= 0.15 | Derived from other knowledge |

The LLM's self-reported confidence serves only as a **downward adjustment** -- it can reduce confidence below the source-type prior but never increase it above it. LLMs are systematically overconfident (researcher-1, Section 3.2.1).

**Evidence grounding as hard gate.** Every extraction MUST include a `source_quote` field with text from the conversation. If the quote does not exist in the source text (verified by substring match with fuzzy fallback), the extraction is rejected regardless of confidence (researcher-1, Section 6.3.1).

**NLI entailment differentiated by source type** (reviewer-1, Gap #3). For `explicit` sources, require strict entailment (NLI score > 0.7). For `implicit_*` and `inferred` sources, require only "not contradicted" (contradiction score < 0.5). Implicit extractions involve reasoning beyond literal text -- strict entailment is too aggressive for these.

**Post-MVP: calibration with production data.** After accumulating 1,000+ extractions, sample 200 across confidence buckets for human labeling (2 reviewers, Cohen's kappa > 0.7). Apply isotonic regression to calibrate raw confidence to empirical accuracy. DINCO and self-consistency are deferred to post-MVP (reviewer-1, Gap #2; reviewer-3, Gap #4).

### 9. Validation Pipeline

Extracted knowledge passes through a four-layer validation pipeline before graph insertion (researcher-3, Section 3.1). Following reviewer-3's key design principle: validate and accept **individual extractions independently**, not as a batch. If an LLM extracts 4 preferences and 1 is hallucinated, the 3 valid ones are accepted while the hallucinated one is rejected (reviewer-3, Gap #6).

**Layer definitions:**

| Layer | What It Checks | Mechanism | Latency |
|-------|---------------|-----------|---------|
| **Layer 1: Schema** | Type correctness, enum validity, required fields, value ranges | Pydantic v2 strict mode + Instructor retry | < 1ms |
| **Layer 2: Ontology Constraints** | Edge endpoint types, source-confidence alignment, cross-field consistency | Application-level validators | 1-5ms |
| **Layer 3: Graph Consistency** | Duplicate preferences, entity existence, supersession detection, cardinality | Neo4j queries | 10-50ms |
| **Layer 4: Confidence Gating** | Minimum confidence thresholds per source type and knowledge type | Threshold comparison | < 1ms |

**Consumer-specific validation paths:**

- **Consumer 1 (structural projection)**: Only structural validation (event schema, timestamp ordering). No Layers 1-4 needed -- structural edges have no confidence or ontology constraints beyond type correctness.
- **Consumer 1 (resilience fallback entities/preferences)**: Layers 1-2 only. Layer 3 (graph consistency) deferred to Consumer 2's reconciliation pass. Layer 4 uses a conservative confidence floor (0.5 for explicit, 0.3 for rule-based entities).
- **Consumer 2 (session extraction)**: Full four-layer validation on every individual extraction. All layers run synchronously within the consumer -- the consumer is async relative to the API, so it has latency budget.
- **Consumer 3 (enrichment)**: Layers 1-2 only (derived attributes are deterministic/model-based, not LLM-extracted). No confidence gating needed for embeddings and keywords.
- **Consumer 4 (consolidation)**: Full four-layer validation + self-consistency for behavioral patterns.

**Validation failure handling** (researcher-3, Section 3.7):

| Failure | Action |
|---------|--------|
| Schema violation (wrong type, invalid enum) | Retry via Instructor (up to 3 retries) |
| Retry exhausted | Reject and log; do not block pipeline |
| LLM API timeout or rate limit | Requeue event in Redis Stream with exponential backoff (max 3 retries) |
| Ontology constraint violation (edge endpoint) | Reject |
| Source-confidence misalignment | Accept with adjusted confidence |
| Duplicate preference detected | Merge: reinforce existing node's observation_count and stability |
| Contradicting preference detected | Accept and supersede: create new, set `superseded_by` on old |
| Below confidence threshold | Log to staging area for Consumer 4 review |

**Degenerate output detection** (reviewer-1, Gap #5): Flag extraction batches where the LLM produces suspiciously uniform values (e.g., all confidence = 0.5, all strength = 0.8). These indicate the model is not meaningfully calibrating per-extraction and the batch should be re-extracted with a higher-tier model.

### 10. Provenance Requirements

**Every extracted node MUST have a DERIVED_FROM edge to the source event(s) that produced it.** This is non-negotiable and is our system's primary differentiator over all surveyed production systems (researcher-2, Section 8.3; reviewer-2, "Provenance Gap" observation).

The DERIVED_FROM edge carries:

```
DERIVED_FROM {
    derivation_method: "rule_extraction" | "llm_extraction" | "statistical_inference" | "graph_pattern",
    derived_at: ZONED DATETIME,
    model_id: STRING,              -- e.g., "claude-haiku-4.5" (null for rule-based)
    prompt_version: STRING,        -- extraction prompt version for reproducibility
    evidence_quote: STRING,        -- the source_quote that grounded this extraction
    source_turn_index: INTEGER     -- which conversation turn the evidence came from
}
```

**Provenance granularity.** Consumer 2 processes the full session transcript but the `source_turn_index` and `evidence_quote` fields on DERIVED_FROM pinpoint the specific turn within the session. This provides turn-level provenance without requiring per-turn extraction.

This enables:
- **Auditing**: Why does the system think User X prefers email? Trace DERIVED_FROM to the source conversation event and specific turn.
- **Confidence recalibration**: When extraction prompts improve, existing nodes can be re-evaluated against their source events.
- **GDPR compliance**: When a user requests erasure, cascade from events through DERIVED_FROM to all derived knowledge.

### 11. Hallucination Mitigation

Hallucinated graph nodes are more dangerous than hallucinated chat responses because they persist and propagate -- downstream queries and agent behaviors are influenced by fabricated preferences (researcher-1, Section 6.1). The mitigation pipeline applies four checks in sequence:

**Check 1: Evidence grounding** (fast, string-based). Verify the `source_quote` exists in the source conversation text. Exact substring match with fuzzy fallback (threshold 0.85). Reject on failure. This catches fabricated evidence (researcher-1, Section 6.3.1).

**Check 2: NLI entailment** (medium cost, DeBERTa-based). Convert each extraction to a natural language claim and verify against source text. Differentiate by source type: strict entailment for `explicit`, "not contradicted" for `implicit_*` (reviewer-1, Gap #3). The NLI model (DeBERTa-v3-large) runs locally at ~5ms per claim. Reject if contradicted; reduce confidence by 0.2 if neutral for explicit sources.

**Check 3: Prompt injection sanitization.** Wrap conversation text in XML delimiters (`<conversation>...</conversation>`) in extraction prompts to reduce the risk of user content being interpreted as instructions. Function calling / tool use mode is inherently more resistant to output hijacking than plain JSON mode (reviewer-1, Gap #9).

**Check 4: Degenerate output detection.** Flag extraction batches with flat confidence distributions (standard deviation < 0.05 across a batch of 3+ extractions) or uniform strength values. These indicate the model is producing structurally valid but semantically uncalibrated output.

### 12. Concrete Extraction Example

To illustrate the full pipeline, consider this merchant conversation:

```
Merchant: "Hi, I need to change my dispute notification settings.
I always want email notifications for disputes, not those in-app
popups. They're easy to miss."

Agent: "Got it! I'll update that. Anything else?"

Merchant: "Yeah, can you set up automatic invoice reminders? I've
been using QuickBooks for my bookkeeping and I'd love if the invoices
could sync there automatically."

Agent: "For the QuickBooks integration, I'll need the API connection.
Have you worked with API integrations before?"

Merchant: "Oh yeah, I've done a bunch of API integrations for my store.
I connected Shopify, our shipping provider, and a couple of payment
gateways. I'm pretty comfortable with that stuff."
```

**Event flow:**
1. Each turn generates an event → XADD to Redis Stream
2. **Consumer 1** creates Event nodes, FOLLOWS edges, session structure in Neo4j (<50ms per event)
3. Session ends → `system.session_end` event arrives in stream
4. **Consumer 2** collects all session events, reconstructs transcript, runs LLM extraction

**Consumer 2 extraction output** (single LLM call over full session):

| Type | Key | Value | Source | Confidence | Turn |
|------|-----|-------|--------|------------|------|
| Preference | dispute_notification_method | email for disputes | explicit | 0.9 | 1 |
| Preference | in_app_popups | dislikes popups | explicit | 0.85 | 1 |
| Preference | bookkeeping_tool | uses QuickBooks | explicit | 0.8 | 3 |
| Preference | invoice_sync_automation | wants auto-sync | explicit | 0.85 | 3 |
| Skill | API integration | advanced proficiency | declared | 0.75 | 5 |
| Interest | workflow automation | moderate engagement | implicit | 0.6 | 3 |

**Graph operations generated** (after validation):

```cypher
// Resolve entities (MERGE for idempotency)
MERGE (qb:Entity {name: "QuickBooks", entity_type: "service"})
MERGE (email:Entity {name: "email notifications", entity_type: "concept"})

// Create preference with provenance
CREATE (p:Preference {preference_id: $id, category: "communication",
    key: "dispute_notification_method", polarity: "positive",
    strength: 0.95, confidence: 0.9, source: "explicit",
    context: "dispute_management"})
CREATE (user)-[:HAS_PREFERENCE]->(p)
CREATE (p)-[:ABOUT]->(email)
CREATE (p)-[:DERIVED_FROM {derivation_method: "llm_extraction",
    model_id: "claude-haiku-4.5", source_turn_index: 1,
    evidence_quote: "I always want email notifications for disputes"}]->(session_event)
```

Each extraction traces back to the source event with turn-level granularity, enabling full provenance queries: "Why does the system think this merchant prefers email for disputes?" returns the DERIVED_FROM edge with the evidence quote, turn index, and source event.

### 13. Cost and Latency Budget

**Estimated daily cost at 1,000 conversations/day** (average 8 turns per conversation) (researcher-1, Section 4.3):

| Consumer | Model | Calls/Day | Avg Tokens/Call | Daily Cost (est.) |
|----------|-------|-----------|-----------------|-------------------|
| Consumer 1 (graph projection) | None (structural operations) | 8,000 (per-event) | N/A | $0 |
| Consumer 2 (session extraction) | Claude Haiku 4.5 / Gemini Flash | 1,000 (per-session) | ~2,000 in + ~500 out | ~$4.50 |
| Consumer 3 (enrichment) | all-MiniLM-L6-v2 (local) | 8,000 (per-event) | N/A | ~$0 (local compute) |
| Consumer 4 (consolidation) | Claude Sonnet 4.5 | 100 (per-user-batch) | ~5,000 in + ~1,000 out | ~$3.00 |
| **Total** | | | | **~$7.50/day** |

With prompt caching (90% savings on system prompt + schema, ~60% of input tokens): effective daily cost drops to **~$4-5/day**.

**Note on cost figures**: Consumer 2 and Consumer 4 costs are estimates based on model pricing and estimated token counts, not reported benchmarks from production systems. Actual costs vary with conversation length, extraction complexity, and model choice (reviewer-2, Gap #1).

**Latency characteristics:**

| Consumer | Typical Latency | Bottleneck | User Impact |
|----------|----------------|-----------|-------------|
| Consumer 1 | <50ms per event | Neo4j MERGE operations | None -- async, user never waits |
| Consumer 2 | 2-10s per session | LLM generation (~2-5s) + validation (~100ms) | None -- async, runs after session or every N turns |
| Consumer 3 | 50-500ms per event batch | Embedding computation (~50-200ms per event) | None -- async, user never waits |
| Consumer 4 | 1-5 min per user batch | LLM generation + graph queries + self-consistency | None -- background scheduled job |

**Key insight**: Because all extraction is async, there is no latency budget that constrains model choice. Consumer 2 can use API-based models (no local model required) since network round-trip latency (200-500ms) is irrelevant when the consumer has a seconds-level budget. This eliminates the need for local model infrastructure.

### 14. Production Patterns Adopted

| Pattern | Source System | How We Adopt It | Why |
|---------|-------------|----------------|-----|
| **Async extraction with structural fast-path** | MAGMA | Consumer 1 = structural projection (no LLM); Consumer 2/3/4 = extraction and enrichment (async) | Adapted from MAGMA's dual-stream; our async-first design eliminates the sync extraction constraint while preserving the separation of structural vs. semantic operations (researcher-2, Section 5; reviewer-2, Recommendation #1) |
| **Bi-temporal model** | Graphiti | Track `first_observed_at`, `last_confirmed_at`, `superseded_by` on Preference nodes | Only production system with proper temporal model for fact evolution; maps to ADR-0012 Preference lifecycle (reviewer-2, Recommendation #2) |
| **LLM-decided CRUD for preferences** | Mem0 | For Consumer 2 preference extraction: ADD / UPDATE (reinforce) / SUPERSEDE | Flexible conflict resolution for explicit statements; adapted with deterministic priority rules as pre-LLM tiebreakers (reviewer-2, Recommendation #6) |
| **User-message-only extraction** | Mem0, Memoria | Consumer 2 extracts from merchant utterances only; agent utterances provide context only | Prevents memorizing agent outputs; avoids feedback loops (researcher-2, Section 7.1) |
| **EWA decay validation** | Memoria | Validates our Ebbinghaus model (ADR-0008); newer observations naturally dominate | Mathematical conflict resolution complement to our per-item stability factors (researcher-2, Section 3.3) |
| **Reflexion for extraction completeness** | Graphiti | Optional at Consumer 2: after initial extraction, verify no signals were missed | Adds ~30% cost but improves coverage. Adopt as A/B-testable option, not mandatory (reviewer-2, Gap #8) |
| **Redis Streams for event coordination** | Architecture decision | Consumer groups with guaranteed delivery replace polling-based projection worker | Natural fit for async-first extraction; provides ordering, backpressure, and crash recovery |

**Patterns explicitly avoided:**

- **Synchronous extraction on the API hot path**: The agent's context window provides within-session recall; the graph serves cross-session context. No extraction needs to complete before the API response returns.
- **A-MEM's schema-free approach**: Our ontology provides a precise target schema; schema-free extraction adds a mapping layer (researcher-2, Section 8.2)
- **Graphiti's bulk processing without edge invalidation**: Bulk path disables conflict detection, which we require for `superseded_by` chains (reviewer-2, Gap #2)
- **MAGMA's query-time-only conflict resolution**: Preferences need write-time resolution via `superseded_by`; unbounded contradiction accumulation degrades graph quality (reviewer-2, Recommendation #11)

### 15. Open Questions / Future Work

1. **Schema evolution and prompt versioning.** When the cg-user ontology adds new preference categories or behavioral pattern types, extraction prompts must be updated. A prompt versioning strategy (prompt version tracked on DERIVED_FROM edges) and few-shot example curation cadence need definition (reviewer-1, Gap #4).

2. **Multi-language extraction.** Merchants may converse in Spanish, Portuguese, Mandarin, and other languages. Frontier models support multilingual extraction natively, but confidence calibration may need per-language adjustment. No surveyed production system has been evaluated on non-English extraction (reviewer-2, Gap #9).

3. **Ground truth labeling and calibration.** The post-MVP confidence calibration requires a labeled dataset (200 initial samples, ~100/month ongoing). Labelers should be merchant support team members; 2 reviewers per sample; Cohen's kappa > 0.7 (researcher-3, Section 6.4).

4. **Evaluation methodology.** No standardized benchmark exists for conversational preference extraction. LoCoMo and LongMemEval test factual recall, not preference quality. We need a domain-specific evaluation: competency question pass rates ("Does the system correctly know User X prefers email for disputes?") and end-to-end personalization quality metrics (researcher-2, Section 10).

5. **SHACL batch validation.** Periodic SHACL validation against SHACL shapes (researcher-3, Section 8) as an audit mechanism. Deferred to post-MVP per ADR-0011 Section 7. Note: n10s has significant limitations for edge property validation (reviewer-3, Gap #5).

6. **Reflexion (Graphiti-style iterative verification).** Promising for Consumer 2 extraction completeness, but the accuracy-cost tradeoff is unquantified (no ablation study in the Graphiti paper). A/B test before adopting (reviewer-2, Gap #8).

7. **Extraction deduplication across sessions.** When a user restates a known preference, Consumer 2 currently re-extracts it. Context-aware extraction (injecting existing preferences into the prompt with "do not re-extract unless contradicted") reduces duplicates (reviewer-1, Gap #6; researcher-3, Section 4.3).

8. **Consumer 2 trigger tuning.** The mid-session extraction trigger (every N turns) trades freshness for cost. Optimal N depends on average conversation length and how quickly cross-session queries need updated knowledge. Start with N=10 and tune based on production data.

9. **Distinguishing transactional mentions from genuine signals.** A merchant asking "How do I process a refund?" is transactional (not a preference about refunds). The extraction prompt should distinguish task-oriented questions from genuine preference/interest signals. Evaluative language ("I like", "I prefer") and repeated engagement are stronger signals than one-off questions (researcher-1, Section 10.4).

## Consequences

### Positive

1. **Full provenance chain.** Every piece of user knowledge traces back to source events via DERIVED_FROM edges with turn-level granularity. This is unique among production agent memory systems and enables auditing, recalibration, and GDPR compliance.

2. **Cost-effective extraction.** Consumer 1 uses no LLM calls. Consumer 2 uses Haiku/Flash-class models. Consumer 3 uses a local embedding model. Only Consumer 4 (periodic, low-volume) uses Sonnet-class. Estimated daily cost of ~$4-8 for 1,000 conversations is operationally viable.

3. **Ontology-driven accuracy.** Schema-as-prompt with Pydantic enforcement achieves 80-90% schema compliance (researcher-3, Section 1.4). Enum constraints, value ranges, and cross-field validators catch most structural errors automatically.

4. **Simplified architecture.** Async-first design with Redis Stream consumer groups eliminates the synchronous extraction constraint. No local model infrastructure required -- all LLM calls use API models. Consumer groups provide natural parallelism, guaranteed delivery, and crash recovery.

5. **Graceful degradation.** Consumer 1's optional rule-based fallback provides basic entity and explicit preference extraction when LLM services are unavailable. Consumer 2/4 backfill when services recover. Consumer 3 (enrichment) operates independently of LLM availability. Redis Streams guarantee no events are lost during LLM outages -- they queue up and are processed when consumers resume.

6. **Knowledge type coverage.** The pipeline extracts all five cg-user node types (UserProfile, Preference, Skill, Workflow, BehavioralPattern) plus entities and interests, providing the richest user model of any surveyed system.

### Negative

1. **Novel extraction targets.** Skill, Workflow, and BehavioralPattern extraction have no production precedent. Accuracy and calibration for these types will require empirical tuning with no external benchmarks to guide expectations.

2. **LLM dependency for Consumer 2/4.** Implicit preference and skill extraction fundamentally require LLM reasoning. There is no cheaper alternative for these knowledge types. Model pricing changes or API availability issues directly affect extraction capability.

3. **Confidence calibration cold-start.** Source-type priors provide a reasonable baseline but are not empirically calibrated. The system will initially produce confidence scores that are directionally correct but not precisely calibrated. This improves only after accumulating labeled data.

4. **Extraction delay.** Knowledge from a conversation is not available in the graph until Consumer 2 processes it (2-10 seconds after session end, or after N turns). For the rare case where another system needs real-time within-session graph updates, this delay may be insufficient. The agent itself is unaffected (it has the conversation in context).

### Risks to Monitor

1. **Extraction hallucination rate.** Track the percentage of extractions rejected by evidence grounding and NLI checks. If rejection rate exceeds 30%, the extraction prompts or model selection need revision.

2. **Preference duplication rate.** Track how often Consumer 2 re-extracts already-known preferences. If duplication exceeds 20%, increase known-preference injection or adjust extraction prompts.

3. **Cost scaling.** The $4-8/day estimate assumes 1,000 conversations. If volume grows 10x, cost grows linearly. Monitor cost per extraction and evaluate whether Consumer 2 can shift to cheaper models (Gemini Flash) without quality loss.

4. **Behavioral pattern false positives.** Since BehavioralPattern extraction is novel, monitor the rate at which detected patterns are confirmed vs. rejected in user-facing personalization. Self-consistency sampling (N=3) at Consumer 4 mitigates this but does not eliminate it.

5. **Consumer lag.** Monitor Redis Stream consumer group lag (`XPENDING`). If Consumer 2 falls behind (e.g., due to LLM API rate limits), extraction freshness degrades. Mitigate by scaling consumer count or switching to cheaper/faster models.

## Alternatives Considered

1. **Synchronous extraction on the API hot path (original three-path design).** Rejected because the agent does not need graph-based recall for within-session context (it has the transcript in its context window). Synchronous extraction forced a < 500ms budget that required either no-LLM rule-based extraction (lower quality) or local model infrastructure (operational complexity). The async-first design produces the same results with simpler architecture.

2. **Local small LLM for fast-path extraction.** Considered as an enhancement to the synchronous design (1B-3B parameter model with constrained decoding, ~150ms latency). Rejected in favor of the async-first design which eliminates the latency constraint entirely, making local model infrastructure unnecessary.

3. **Per-turn extraction instead of per-session batch.** Rejected because LLMs exhibit 39% lower performance processing turns independently vs. full-session context (researcher-1, Section 7.4), and per-turn extraction is 3-5x more expensive due to repeated prompt overhead.

4. **Schema-free extraction followed by ontology mapping.** Rejected because our ontology provides a precise target schema. Schema-free extraction adds a post-extraction mapping layer that introduces error and complexity. Validated by the comparison of schema-guided vs. schema-free extraction in production systems (researcher-2, Section 8.2).

5. **Self-consistency sampling at Consumer 2 for all extractions.** Rejected for MVP because it multiplies Consumer 2 cost by 3-5x. Reserved for Consumer 4 high-impact patterns and offline quality monitoring of a 10% random sample (researcher-1, Section 3.3).

6. **DINCO confidence calibration from day one.** Rejected because DINCO requires domain-specific distractor generation and calibration data that does not exist at launch. Source-type priors provide a sufficient baseline for MVP (reviewer-1, Gap #2).

## Research References

### Research Reports
- `docs/research/extraction-landscape.md` -- Initial landscape analysis and research track definition
- `docs/research/extraction-llm-techniques.md` -- LLM-based extraction techniques (researcher-1)
- `docs/research/extraction-production-pipelines.md` -- Production system analysis (researcher-2)
- `docs/research/extraction-ontology-guided.md` -- Ontology-guided extraction and validation (researcher-3)

### Review Reports
- `docs/research/review-extraction-llm-techniques.md` -- Reviewer-1 critique
- `docs/research/review-extraction-production-pipelines.md` -- Reviewer-2 critique
- `docs/research/review-extraction-ontology-guided.md` -- Reviewer-3 critique

### Key External References
- SPIRES/OntoGPT (Caufield et al., Bioinformatics 2024): Schema-as-prompt extraction pattern
- ODKE+ (Apple, 2025): Per-type ontology snippet generation
- Zep/Graphiti (Rasmussen, 2025): Bi-temporal model, reflexion loops, entity resolution
- Mem0 (Chhikara et al., ECAI 2025): LLM-decided CRUD, user-message-only extraction
- Memoria (Khant et al., 2025): EWA decay, session-level extraction
- MAGMA (Jiang et al., 2026): Dual-stream architecture, multi-graph extraction
- StructEval (2025): LLM structured output benchmarks
- CISC (ACL Findings 2025): Confidence-informed self-consistency
- Instructor library: Pydantic-based structured LLM output with automatic retry
