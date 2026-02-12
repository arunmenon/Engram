# ADR-0011: Ontological Foundation for the Context Graph

Status: **Proposed**
Date: 2026-02-11
Amends: ADR-0001 (PROV-DM alignment), ADR-0004 (event schema), ADR-0007 (memory tiers), ADR-0009 (multi-graph schema)

## Context

The context-graph project captures immutable events from AI agents, stores them in Redis (episodic memory), and projects them into a Neo4j graph (semantic memory) with five edge types (FOLLOWS, CAUSED_BY, SIMILAR_TO, REFERENCES, SUMMARIZES) and three node types (Event, Entity, Summary). Five cognitive memory tiers (sensory, working, episodic, semantic, procedural) are mapped to system components (ADR-0007). A loose mapping to W3C PROV-DM exists (ADR-0001 Section 10, ADR-0009 PROV-DM compatibility table), but no formal ontology underpins the system.

Without a formal ontological foundation, the system has:

- **Ad-hoc vocabulary**: Edge types and entity roles are string conventions, not grounded in established standards. The same semantic relationship (e.g., "an agent performed this action") has different representations in different parts of the system.
- **Ambiguous PROV-DM mapping**: The ADR-0009 compatibility table maps SIMILAR_TO to `wasDerivedFrom`, which has incorrect semantics (derivation implies transformation, not similarity). SUMMARIZES maps to both `alternateOf` and `specializationOf`, which have opposing directional semantics.
- **No entity type formalism**: The five entity types (`agent`, `tool`, `user`, `resource`, `concept`) are an undocumented enum with no class hierarchy, no formal grounding, and no entity resolution strategy.
- **No event type taxonomy**: The dot-namespaced `event_type` values (`agent.invoke`, `tool.execute`, etc.) are string conventions with no formal type hierarchy or relationship to OTel GenAI conventions.
- **No formal schema for the property graph**: Neo4j edge endpoint constraints (e.g., "FOLLOWS only connects Event-to-Event") cannot be expressed in Neo4j's native constraint system and are enforced only in application code.
- **Informal cognitive tier naming**: Memory tier names (episodic, semantic, procedural) reference cognitive science concepts without formal grounding or analogical qualification.

### Research Basis

Four research deliverables inform this decision:

1. **Ontology Discovery** (Task #1): Cataloged 14 ontologies/standards across provenance, event, agent, cognitive, and graph schema domains.
2. **Provenance & Event Deep Dive** (Task #2): Detailed analysis of PROV-O tiers, qualification patterns, OTel GenAI conventions, SEM/Event-Model-F patterns, and a consolidated mapping table.
3. **Agent/Entity & Graph Schema Deep Dive** (Task #3): FIPA agent identity, schema.org Action roles, BDI ontology, entity resolution formalisms (SKOS/SSSOM), PG-Schema, SHACL, and Neo4j constraint analysis.
4. **Cognitive/Memory & Multi-Graph Deep Dive** (Task #4): MFO/CogAt taxonomy alignment, CLS theory formalization opportunity, retention tier modeling, MAGMA multi-graph formalism, and ontology modularization patterns.

Non-goals for this decision:
- Publishing a formal OWL ontology file for external consumption (documentation-level formalization is sufficient for MVP)
- Adopting RDF as a runtime data model (Neo4j property graph remains the implementation)
- Requiring developers to learn ontology engineering tooling (Protege, reasoners, etc.)
- Formalizing continuous decay functions in OWL axioms

## Decision

The context-graph project MUST adopt a layered ontological foundation that grounds existing vocabulary in established standards while preserving the operational edge type names optimized for intent-aware retrieval.

### 1. Foundational Ontology: PROV-O Profile with Custom Extensions

The system MUST define a PROV-O profile -- a domain-specific specialization of W3C PROV-O that reuses PROV-O's core vocabulary and extends it with custom terms for concepts PROV-O does not cover.

**PROV-O as conceptual layer, not implementation layer.** The operational vocabulary (our 5 edge types) remains the Neo4j implementation. PROV-O provides the conceptual vocabulary for documentation, interchange, and interoperability. This is a dual-vocabulary approach:

- **Operational vocabulary**: FOLLOWS, CAUSED_BY, SIMILAR_TO, REFERENCES, SUMMARIZES -- used in Neo4j traversal, Cypher queries, and API responses
- **Conceptual vocabulary**: PROV-O terms -- used in formal documentation, potential RDF export, and interoperability with provenance-aware systems

#### Node Type Grounding

| Context-Graph Node | PROV-O Mapping | Rationale |
|-------------------|----------------|-----------|
| `:Event` | `prov:Activity` | Events are bounded temporal units of work, the defining characteristic of PROV Activity |
| `:Entity` | `prov:Entity` | Entities are things referenced, used, or produced by activities |
| `:Entity (type=agent)` | `prov:SoftwareAgent` | AI agents are software agents in PROV-O's expanded terms |
| `:Entity (type=user)` | `prov:Agent` | Human users are agents but not software agents |
| `:Summary` | `prov:Entity` | Summaries are derived entities that are alternate representations of source events |
| Session boundary | `prov:Bundle` | A session is a named collection of provenance assertions |

#### Edge Type Grounding

| Operational Edge | PROV-O Grounding | Custom Extension | Rationale |
|-----------------|------------------|------------------|-----------|
| `CAUSED_BY` | `prov:wasInformedBy` | `mechanism` property (direct, inferred) | Activity-to-activity causal dependency via `parent_event_id`. PROV-O's qualified form (`qualifiedCommunication`) supports the mechanism metadata. |
| `REFERENCES` | `prov:used` (role=instrument), `prov:wasAttributedTo` (role=agent), inverse `prov:wasGeneratedBy` (role=result) | `role` property discriminates | Single edge type maps to multiple PROV-O relations; the `role` property selects the correct PROV-O term during export. |
| `SUMMARIZES` | `prov:alternateOf` | `cg:summarizes` | Summary is an alternate representation of source events. `prov:specializationOf` is NOT used -- specialization implies more detail, but summaries are less detailed. |
| `FOLLOWS` | No PROV-O equivalent | `cg:follows` | Temporal sequencing within a session. PROV-O models time as properties (`startedAtTime`, `endedAtTime`), not as ordering edges. P-Plan's `isPreceededBy` is the nearest precedent (planned ordering vs. our observed ordering). |
| `SIMILAR_TO` | No PROV-O equivalent | `cg:similarTo` | Semantic similarity (cosine above threshold). No provenance ontology models this concept. Origin: MAGMA graph memory architecture, not provenance standards. |

**Correction to ADR-0009 PROV-DM mapping:** The existing mapping incorrectly maps SIMILAR_TO to `wasDerivedFrom` and SUMMARIZES to `specializationOf`. These are corrected above. See Amendments section.

### 2. Event Type Taxonomy

The system MUST formalize the `event_type` field as a two-level hierarchy grounded in OTel GenAI Semantic Conventions, using the SEM (Simple Event Model) `EventType` pattern as the structural model.

#### Taxonomy

```
cg:EventType
  cg:AgentEvent
    cg:InvokeAgent          # OTel: invoke_agent
    cg:CreateAgent           # OTel: create_agent
  cg:ToolEvent
    cg:ExecuteTool           # OTel: execute_tool
  cg:LLMEvent
    cg:Chat                  # OTel: chat
    cg:TextCompletion        # OTel: text_completion
    cg:Embeddings            # OTel: embeddings
    cg:GenerateContent       # OTel: generate_content
  cg:ObservationEvent
    cg:ReceiveInput          # Agent receives external input
    cg:EmitOutput            # Agent produces output
  cg:SystemEvent
    cg:SessionStart          # Session lifecycle
    cg:SessionEnd
```

#### Serialization

Event types are serialized as dot-namespaced strings in the event schema (unchanged from current design):

| Taxonomy Class | `event_type` String | OTel `gen_ai.operation.name` |
|---------------|--------------------|-----------------------------|
| `cg:InvokeAgent` | `agent.invoke` | `invoke_agent` |
| `cg:CreateAgent` | `agent.create` | `create_agent` |
| `cg:ExecuteTool` | `tool.execute` | `execute_tool` |
| `cg:Chat` | `llm.chat` | `chat` |
| `cg:TextCompletion` | `llm.completion` | `text_completion` |
| `cg:Embeddings` | `llm.embed` | `embeddings` |

The taxonomy is extensible: new event types can be added as subtypes without breaking existing queries. The first dot-separated segment corresponds to the Level 1 category; subsequent segments correspond to the Level 2 action.

#### OTel Mapping

The OTLP adapter (ADR-0001 item 7) MUST translate between OTel operation names and our dot-namespace format:

```python
OTEL_TO_EVENT_TYPE = {
    "invoke_agent": "agent.invoke",
    "create_agent": "agent.create",
    "execute_tool": "tool.execute",
    "chat": "llm.chat",
    "text_completion": "llm.completion",
    "embeddings": "llm.embed",
    "generate_content": "llm.generate",
}
```

### 3. Entity Type Hierarchy

The system MUST formalize entity types as a two-level hierarchy grounded in PROV-O, with the current flat enum preserved for backward compatibility.

#### Hierarchy

```
prov:Agent
  cg:AgentEntity              # entity_type = "agent"
    # AI agents, LLM-based autonomous agents
  cg:UserEntity                # entity_type = "user"
    # Human users interacting with agents
  cg:ServiceEntity             # entity_type = "service" (new)
    # External APIs, platforms, third-party services

prov:Entity
  cg:ToolEntity                # entity_type = "tool"
    # Instruments used by agents (MCP tools, functions, extensions)
  cg:ResourceEntity            # entity_type = "resource"
    # Data sources, documents, artifacts
  cg:ConceptEntity             # entity_type = "concept"
    # Abstract ideas, topics, categories
```

**New entity type: `service`**. External APIs and platforms (e.g., "OpenAI API", "GitHub", "Postgres") are currently conflated with `tool` or `resource`. The `service` type distinguishes platform-level services from individual tools. `service` inherits from `prov:Agent` because services act autonomously (accepting requests, producing responses) rather than being passively used.

#### Entity Roles on REFERENCES Edges

The `role` property on REFERENCES edges MUST be renamed to align with schema.org Action vocabulary:

| Current Role | New Role | schema.org Mapping | PROV-O Mapping | Description |
|-------------|----------|-------------------|----------------|-------------|
| `subject` | `agent` | `schema:agent` | `prov:wasAssociatedWith` | Direct performer of the action |
| `tool` | `instrument` | `schema:instrument` | `prov:used` | Tool/device used to perform |
| `object` | `object` | `schema:object` | (none -- acted-upon thing) | Thing being acted upon |
| `target` | `result` | `schema:result` | inverse `prov:wasGeneratedBy` | Product/outcome of the action |
| (new) | `participant` | `schema:participant` | (none) | Other involved entity |

**Migration**: The projection worker MUST write new edges with the updated role names. Existing edges with old role names remain valid until the next full re-projection from Redis events.

#### Entity Resolution Strategy

Entity resolution MUST follow a three-tier approach inspired by SKOS and SSSOM:

| Tier | Condition | Action | Confidence |
|------|-----------|--------|------------|
| **Exact match** | Normalized `name` + `entity_type` are identical | Merge into single Entity node | 1.0 (deterministic) |
| **Close match** | Embedding similarity > 0.9 between entity descriptions | Create `SAME_AS` edge with confidence score | 0.9+ (semi-automatic) |
| **Related match** | Family/version relationship (e.g., "GPT-4" and "GPT-4o") | Create `RELATED_TO` edge with confidence score | Variable (enrichment) |

Exact matches are handled in the projection worker (Stage 1). Close and related matches are deferred to the enrichment pipeline (Stage 2) with human-reviewable confidence scores. The system MUST NOT auto-merge entities at the close or related level.

### 4. Multi-Graph View Formalism

The system's five edge types define five orthogonal semantic views over a shared node set. This architecture MUST be documented using MVKG (Multi-View Knowledge Graph) vocabulary:

#### Formal Definition

```
G = (N, E, T_n, T_e, L_n, L_e, P, V)

where:
  N = set of nodes (Event UNION Entity UNION Summary)
  E = set of edges (FOLLOWS UNION CAUSED_BY UNION SIMILAR_TO UNION REFERENCES UNION SUMMARIZES)
  T_n = {Event, Entity, Summary}
  T_e = {FOLLOWS, CAUSED_BY, SIMILAR_TO, REFERENCES, SUMMARIZES}
  L_n : N -> T_n   (node labeling function)
  L_e : E -> T_e   (edge labeling function)
  P = property schema per type
  V = property value constraints
```

Five semantic views are defined as typed subgraphs:

| View | Notation | Nodes | Edges | Query Focus |
|------|----------|-------|-------|-------------|
| Temporal | `V_temporal` | Event | FOLLOWS | "When did this happen?" |
| Causal | `V_causal` | Event | CAUSED_BY | "Why did this happen?" |
| Semantic | `V_semantic` | Event | SIMILAR_TO | "What else is related?" |
| Entity | `V_entity` | Event, Entity | REFERENCES | "Who/what was involved?" |
| Hierarchical | `V_hierarchical` | Event, Summary | SUMMARIZES | "What is the high-level picture?" |

Intent-aware retrieval (ADR-0009) is a **decision fusion** mechanism that dynamically weights which views to traverse based on query intent. Each view produces a subgraph, and the results are merged with intent-dependent edge weights. This parallels MAGMA's adaptive traversal policy.

**Implementation**: Neo4j's native typed relationships serve as the multi-graph mechanism. No materialized view layer or separate databases are needed. Each view is accessed via Cypher pattern matching with relationship type filters:

```cypher
// Temporal view
MATCH (a:Event)-[f:FOLLOWS]->(b:Event) RETURN a, f, b

// Entity view
MATCH (a:Event)-[r:REFERENCES]->(e:Entity) RETURN a, r, e
```

### 5. Graph Schema Definition (PG-Schema)

The graph schema MUST be documented formally in PG-Schema notation. PG-Schema provides edge endpoint constraints that Neo4j cannot natively express.

#### Node Types

```
CREATE NODE TYPE Event (
  event_id         STRING NOT NULL,
  event_type       STRING NOT NULL,
  occurred_at      ZONED DATETIME NOT NULL,
  session_id       STRING NOT NULL,
  agent_id         STRING NOT NULL,
  trace_id         STRING NOT NULL,
  global_position  INTEGER NOT NULL,
  tool_name        STRING,
  keywords         LIST<STRING>,
  summary          STRING,
  embedding        LIST<FLOAT>,
  importance_score INTEGER,
  access_count     INTEGER DEFAULT 0,
  last_accessed_at ZONED DATETIME
)

CREATE NODE TYPE Entity (
  entity_id   STRING NOT NULL,
  name        STRING NOT NULL,
  entity_type STRING NOT NULL,
  first_seen  ZONED DATETIME NOT NULL,
  last_seen   ZONED DATETIME NOT NULL,
  mention_count INTEGER DEFAULT 1
)

CREATE NODE TYPE Summary (
  summary_id  STRING NOT NULL,
  scope       STRING NOT NULL,
  scope_id    STRING NOT NULL,
  content     STRING NOT NULL,
  created_at  ZONED DATETIME NOT NULL,
  event_count INTEGER NOT NULL,
  time_range  LIST<ZONED DATETIME>
)
```

#### Edge Types with Endpoint Constraints

```
CREATE EDGE TYPE FOLLOWS (
  session_id STRING NOT NULL,
  delta_ms   INTEGER NOT NULL
) FROM Event TO Event

CREATE EDGE TYPE CAUSED_BY (
  mechanism STRING NOT NULL
) FROM Event TO Event

CREATE EDGE TYPE SIMILAR_TO (
  score FLOAT NOT NULL
) FROM Event TO Event

CREATE EDGE TYPE REFERENCES (
  role STRING NOT NULL
) FROM Event TO Entity

CREATE EDGE TYPE SUMMARIZES ()
  FROM Summary TO Event
  | FROM Summary TO Summary

CREATE EDGE TYPE SAME_AS (
  confidence    FLOAT NOT NULL,
  justification STRING NOT NULL
) FROM Entity TO Entity

CREATE EDGE TYPE RELATED_TO (
  confidence    FLOAT NOT NULL,
  justification STRING NOT NULL
) FROM Entity TO Entity
```

#### Key Constraints

```
CREATE KEY Event (event_id)
CREATE KEY Entity (entity_id)
CREATE KEY Summary (summary_id)
```

#### Enforcement

PG-Schema is the formal specification. Enforcement is layered:

| Rule Category | PG-Schema Expressible | Neo4j Enforceable | Enforcement Layer |
|--------------|----------------------|-------------------|-------------------|
| Property uniqueness | Yes | Yes | Neo4j constraint |
| Property existence (NOT NULL) | Yes | Yes | Neo4j constraint |
| Property type | Yes | Yes (5.9+) | Neo4j constraint |
| Edge endpoint types | Yes | No | Projection worker validation |
| Value ranges (importance 1-10) | Yes | No | Projection worker validation |
| String patterns (event_type dot-namespace) | Yes | No | API-level validation |
| Enum values (role, mechanism) | Yes | No | Projection worker validation |

SHACL adoption is deferred. If formal validation pipelines or compliance reporting are needed, SHACL shapes can be added via the neosemantics (n10s) plugin without changing the underlying schema.

### 6. Cognitive Tier Formalization

The five memory tiers (ADR-0007) MUST be documented with formal vocabulary that references established cognitive science ontologies, using explicit analogical qualification.

#### Tier Classes with Grounding

| Tier | Class | MFO Grounding | CogAt Grounding | Implementation |
|------|-------|---------------|-----------------|----------------|
| Sensory | `cg:SensoryTier` | `mf:perception` (analogical) | `cognitiveatlas:sensory_memory` | API ingestion buffer |
| Working | `cg:WorkingTier` | `mf:working_memory` (analogical) | `cognitiveatlas:working_memory` | Context API response assembly |
| Episodic | `cg:EpisodicTier` | `mf:episodic_memory` (analogical) | `cognitiveatlas:episodic_memory` | Redis event store |
| Semantic | `cg:SemanticTier` | `mf:semantic_memory` (analogical) | `cognitiveatlas:semantic_memory` | Neo4j graph projection |
| Procedural | `cg:ProceduralTier` | `mf:procedural_memory` (analogical) | `cognitiveatlas:procedural_memory` | Neo4j pattern subgraph (future) |

**Analogical qualification**: All grounding annotations MUST use `skos:closeMatch` (not `owl:equivalentClass`) to indicate analogical rather than literal equivalence. The system's "episodic memory" is a computational analog to biological episodic memory, not a claim about neuroscience.

#### CLS Vocabulary

The Complementary Learning Systems mapping (ADR-0007: Redis = hippocampus, Neo4j = neocortex, projection worker = systems consolidation) SHOULD be documented using a lightweight CLS vocabulary:

```
cg:ComplementaryLearningSystem
  cg:FastLearningSystem         # Rapid, detailed, instance-specific
    implementedBy: Redis event store
    CLSAnalogy: hippocampal encoding
  cg:SlowLearningSystem         # Gradual, abstract, relational
    implementedBy: Neo4j graph projection
    CLSAnalogy: neocortical consolidation
  cg:ConsolidationProcess       # Transfers knowledge fast -> slow
    implementedBy: Projection worker (Stages 1-3)
    CLSAnalogy: systems consolidation / hippocampal replay
```

This is the first formal representation of CLS theory for a computational agent memory system. It is defined as project-specific vocabulary, not a general-purpose ontology.

#### Consolidation Stage Formalization

The three consolidation stages (ADR-0008) are formalized as ordered phases:

```
cg:EventProjection   -- Stage 1: Fast-path MERGE from Redis to Neo4j
cg:Enrichment        -- Stage 2: Derived attributes (keywords, embeddings, importance)
cg:ReConsolidation   -- Stage 3: Periodic cross-event relationship discovery

cg:EventProjection precedes cg:Enrichment
cg:Enrichment precedes cg:ReConsolidation
```

#### Retention Tier Formalization

The retention tiers (ADR-0008) are formalized as discrete classes with membership criteria, rather than modeling continuous decay as OWL axioms:

| Retention Tier | Age Range | Policy | Ontology Class |
|---------------|-----------|--------|----------------|
| Hot | < 24 hours | Full detail: all nodes, all edges, all derived attributes | `cg:HotTier` |
| Warm | 24h -- 7 days | Full nodes; low-importance SIMILAR_TO edges pruned | `cg:WarmTier` |
| Cold | 7 -- 30 days | Only nodes with importance >= 5 or access >= 3 retained | `cg:ColdTier` |
| Archive | > 30 days | Removed from Neo4j; retained in Redis cold tier | `cg:ArchiveTier` |

The Ebbinghaus decay formula (`score = e^(-t/S)`) is documented in code and ADR-0008, not in the ontology. OWL 2 DL cannot express exponential functions or query-dependent computation.

### 7. Schema Enforcement Strategy

Validation MUST be layered:

| Layer | Mechanism | What It Validates | When |
|-------|-----------|-------------------|------|
| **API** | Pydantic v2 strict mode | Event envelope structure, required fields, `event_type` dot-namespace pattern | Ingestion time |
| **Neo4j** | Native constraints (Cypher DDL) | Property uniqueness, existence, type | Projection time |
| **Projection worker** | Application code | Edge endpoint types, enum values, value ranges | Projection time |
| **SHACL** (future) | neosemantics shapes | Full graph validation with machine-readable reports | Periodic audit |

The concrete Neo4j constraints for MVP:

```cypher
-- Event node
CREATE CONSTRAINT event_pk FOR (e:Event) REQUIRE e.event_id IS UNIQUE;
CREATE CONSTRAINT event_id_not_null FOR (e:Event) REQUIRE e.event_id IS NOT NULL;
CREATE CONSTRAINT event_type_not_null FOR (e:Event) REQUIRE e.event_type IS NOT NULL;
CREATE CONSTRAINT event_occurred_not_null FOR (e:Event) REQUIRE e.occurred_at IS NOT NULL;
CREATE CONSTRAINT event_session_not_null FOR (e:Event) REQUIRE e.session_id IS NOT NULL;
CREATE CONSTRAINT event_gp_not_null FOR (e:Event) REQUIRE e.global_position IS NOT NULL;

-- Entity node
CREATE CONSTRAINT entity_pk FOR (n:Entity) REQUIRE n.entity_id IS UNIQUE;
CREATE CONSTRAINT entity_id_not_null FOR (n:Entity) REQUIRE n.entity_id IS NOT NULL;
CREATE CONSTRAINT entity_name_not_null FOR (n:Entity) REQUIRE n.name IS NOT NULL;
CREATE CONSTRAINT entity_type_not_null FOR (n:Entity) REQUIRE n.entity_type IS NOT NULL;

-- Summary node
CREATE CONSTRAINT summary_pk FOR (s:Summary) REQUIRE s.summary_id IS UNIQUE;
CREATE CONSTRAINT summary_id_not_null FOR (s:Summary) REQUIRE s.summary_id IS NOT NULL;
CREATE CONSTRAINT summary_scope_not_null FOR (s:Summary) REQUIRE s.scope IS NOT NULL;
```

### Ontology Module Structure

The ontology SHOULD be organized into logical modules for documentation clarity, even if not published as separate OWL files:

```
cg-core         -- Node types, edge types, core properties, PROV-O mapping
cg-events       -- Event type taxonomy, status values, OTel mapping
cg-entities     -- Entity type hierarchy, roles, resolution strategy
cg-memory       -- Memory tier classes, CLS vocabulary, consolidation stages
cg-views        -- Multi-view definitions, intent-aware retrieval vocabulary
cg-retention    -- Retention tiers, decay parameters
```

Each module has a defined concern and can be referenced independently. Consumers who only need the core graph schema do not need to understand the cognitive memory vocabulary, and vice versa.

## Consequences

### Positive

- **Formal PROV-O grounding**: Causal and attribution edges now have precise PROV-O semantics. Any provenance-aware system can interpret our graph via the documented mapping.
- **Corrected PROV-DM mapping**: The ADR-0009 mapping table errors (SIMILAR_TO -> `wasDerivedFrom`, SUMMARIZES -> `specializationOf`) are fixed with correct semantic grounding.
- **Event type interoperability**: The formalized event type taxonomy with OTel mapping enables bidirectional translation between our events and OTel spans, covering all major agent frameworks.
- **Entity type clarity**: The two-level hierarchy (prov:Agent -> agent/user/service; prov:Entity -> tool/resource/concept) provides formal grounding while the flat enum preserves backward compatibility.
- **Schema.org role alignment**: REFERENCES edge roles now use widely understood vocabulary (agent, instrument, object, result) instead of ad-hoc strings.
- **Formal graph schema**: PG-Schema documentation captures endpoint constraints that Neo4j cannot enforce, serving as the authoritative schema definition.
- **Qualified cognitive grounding**: Memory tier names are formally linked to MFO/CogAt with explicit analogical qualification, preventing overreach claims about neuroscience.
- **Entity resolution strategy**: The three-tier approach (exact/close/related) prevents destructive over-merging while enabling incremental entity linking.
- **New entity-entity edges**: `SAME_AS` and `RELATED_TO` edges formalize entity resolution results, providing a path to cross-session entity tracking.

### Negative

- **Dual vocabulary overhead**: Developers must understand both operational names (FOLLOWS, CAUSED_BY) and PROV-O names (wasInformedBy, used). Mitigated by: PROV-O terms are documentation-only, not used in code.
- **Role rename migration**: Changing REFERENCES `role` values from `{subject, tool, target}` to `{agent, instrument, result}` requires re-projection. Mitigated by: Neo4j is a derived projection -- trigger full re-projection from Redis events.
- **New entity type**: Adding `service` expands the entity type enum, requiring updates to validation code and enrichment heuristics.
- **PG-Schema has no tooling**: The formal schema serves as documentation only -- no production validator exists. Mitigated by: enforcement is layered across Neo4j constraints and application code.
- **CLS vocabulary is novel**: No existing ontology formalizes CLS for computational systems. Our vocabulary has no external validators. Mitigated by: vocabulary is lightweight, internal-only, and annotated with literature references.

### Risks to Monitor

| Risk | Mitigation |
|------|------------|
| PROV-O alignment constrains future edge type evolution | PROV-O is conceptual, not implementation layer. We can add operational edge types without PROV-O coverage (as we already do with FOLLOWS and SIMILAR_TO). |
| Event type taxonomy becomes too rigid | Taxonomy is extensible via new subtypes. The dot-namespace format allows ad-hoc types that do not yet have taxonomy entries. |
| Entity resolution over-merges across sessions | Three-tier approach with high thresholds (0.9+ for close match). Exact match only for deterministic normalization. Human review for semi-automatic matches. |
| Schema.org role names conflict with existing client integrations | Role rename is a breaking change for API consumers reading REFERENCES edges. Mitigate by supporting both old and new names during a transition period. |

## Alternatives Considered

### 1. Full PROV-O implementation (replace operational edge types with PROV-O names)

Rejected. PROV-O relation names (`wasInformedBy`, `wasAttributedTo`) are optimized for provenance interchange, not for intent-aware graph traversal. Our operational names (CAUSED_BY, REFERENCES) map directly to query intents (why, who/what). Renaming edges to PROV-O terms would break the clean intent-to-edge-type mapping that is ADR-0009's highest-value design feature (MAGMA's ablation study shows intent-aware weighting is the largest performance factor).

### 2. RDF/OWL as runtime data model (replace Neo4j with a triple store)

Rejected. Our schema requires properties on edges (FOLLOWS has `delta_ms`, CAUSED_BY has `mechanism`, SIMILAR_TO has `score`, REFERENCES has `role`). In RDF, edge properties require reification (verbose intermediate nodes), which is both slower for traversal and counter to property graph idioms. Neo4j's native edge properties are the correct model for our data.

### 3. SHACL for graph validation from day one

Deferred. SHACL via neosemantics (n10s) provides more expressive validation than Neo4j constraints (value ranges, patterns, edge endpoint types, closed shapes). However, it adds complexity (RDF shapes for a property graph, n10s plugin dependency, SHACL debugging). Neo4j constraints plus application-level validation are sufficient for MVP. SHACL becomes valuable if formal validation pipelines or compliance reporting are needed.

### 4. No formal ontology (keep ad-hoc vocabulary)

Rejected. The current ad-hoc vocabulary has demonstrable problems: incorrect PROV-DM mapping (SIMILAR_TO -> `wasDerivedFrom`), ambiguous entity roles, no entity resolution strategy, and no event type formalism. These will compound as the system grows. Formal grounding now prevents costly vocabulary migration later.

### 5. Build a completely custom ontology from scratch

Rejected. Existing standards (PROV-O, schema.org, SEM, PG-Schema) cover 80% of our vocabulary needs. Building from scratch would be slower, less interoperable, and harder to validate. Custom terms are needed only for FOLLOWS, SIMILAR_TO, SUMMARIZES, and the cognitive tier vocabulary.

## Impact on Existing ADRs

### ADR-0001 (Traceability-First Context Graph)

- **Section 10 (W3C PROV-DM)**: Deepened. PROV-DM is no longer just a referenced standard but the formal conceptual foundation. The mapping is precise per the tables in this ADR.
- **No breaking changes.** All core commitments (immutable events, provenance pointers, bounded queries) are preserved and strengthened.

### ADR-0004 (Event Schema)

- **`event_type` field**: Gains a formal two-level taxonomy grounded in OTel GenAI conventions. Existing dot-namespaced values remain valid. The taxonomy is additive, not restrictive.
- **`status` field**: SHOULD adopt schema.org action status vocabulary (`pending`, `running`, `completed`, `failed`) for formal grounding. Existing values remain acceptable.
- **No schema changes required.** The taxonomy formalizes existing string conventions without changing the field type or adding new fields.

### ADR-0007 (Memory Tier Architecture)

- **Tier naming**: Formally grounded in MFO and Cognitive Atlas with `skos:closeMatch` annotations. Existing tier names are unchanged.
- **CLS mapping**: Formalized with lightweight CLS vocabulary. The existing prose mapping (Redis = hippocampus, Neo4j = neocortex) gains formal class definitions.
- **No behavioral changes.** The tier architecture operates identically; this ADR adds formal vocabulary and grounding.

### ADR-0009 (Multi-Graph Schema)

- **PROV-DM compatibility table (Amendment 1)**: Updated with corrections:
  - `SIMILAR_TO -> wasDerivedFrom (loose)` corrected to `SIMILAR_TO -> custom cg:similarTo (no PROV-O equivalent)`
  - `SUMMARIZES -> specializationOf` corrected to `SUMMARIZES -> alternateOf`
  - `CAUSED_BY -> wasGeneratedBy, wasInformedBy` narrowed to `CAUSED_BY -> wasInformedBy` (wasGeneratedBy applies to REFERENCES, not CAUSED_BY)
- **REFERENCES edge roles**: Renamed from `{subject, object, tool, target}` to `{agent, object, instrument, result, participant}` per schema.org Action vocabulary
- **New edge types**: `SAME_AS` and `RELATED_TO` added for entity resolution (Entity-to-Entity edges with confidence and justification)
- **Formal graph schema**: PG-Schema definition added as the authoritative schema specification
- **Multi-view formalism**: Explicit MVKG vocabulary for describing the five semantic views

## Research References

### Provenance Standards
- W3C PROV-O: The PROV Ontology -- https://www.w3.org/TR/prov-o/
- W3C PROV-DM: The PROV Data Model -- https://www.w3.org/TR/prov-dm/
- P-Plan Ontology -- https://www.opmw.org/model/p-plan/
- ProvONE -- https://purl.dataone.org/provone-v1-dev

### Event/Activity Standards
- OpenTelemetry GenAI Semantic Conventions -- https://opentelemetry.io/docs/specs/semconv/gen-ai/
- OpenTelemetry GenAI Agent Spans -- https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/
- Simple Event Model (SEM) -- https://semanticweb.cs.vu.nl/2009/11/sem/
- Event Ontology (motools) -- https://motools.sourceforge.net/event/event.html
- Event-Model-F (DOLCE+DnS) -- https://arxiv.org/abs/2411.16609

### Agent/Entity Standards
- schema.org Action -- https://schema.org/Action
- schema.org SoftwareApplication -- https://schema.org/SoftwareApplication
- FIPA Agent Management -- http://www.fipa.org/specs/fipa00023/XC00023H.html
- BDI Ontology (2025) -- https://arxiv.org/abs/2511.17162
- SKOS Reference -- https://www.w3.org/TR/skos-reference/
- SSSOM -- https://mapping-commons.github.io/sssom/

### Cognitive/Memory Ontologies
- Mental Functioning Ontology (MFO) -- https://obofoundry.org/ontology/mf.html
- Cognitive Atlas -- https://cognitiveatlas.org/
- Cognitive Paradigm Ontology (CogPO) -- http://www.cogpo.org/

### Graph Schema Standards
- PG-Schema (Angles et al., 2023) -- https://arxiv.org/abs/2211.10962
- SHACL -- https://www.w3.org/TR/shacl/
- GQL (ISO/IEC 39075) -- https://en.wikipedia.org/wiki/Graph_Query_Language
- Neo4j Constraints -- https://neo4j.com/docs/cypher-manual/current/constraints/

### Multi-Graph and Multi-View
- MAGMA (Jiang et al., 2026). "MAGMA: A Multi-Graph based Agentic Memory Architecture." arXiv:2601.03236
- Yang et al. (2025). "A Survey on Multi-View Knowledge Graph." IJCAI 2025
- MV4PG (Han et al., 2024) -- https://arxiv.org/abs/2411.18847

### Neuroscience
- McClelland, McNaughton & O'Reilly (1995). "Why There Are Complementary Learning Systems in the Hippocampus and Neocortex." Psychological Review
- Kumaran, Hassabis & McClelland (2016). "What Learning Systems do Intelligent Agents Need?" Trends in Cognitive Sciences
