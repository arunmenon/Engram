# Agent/Entity Ontologies and Graph Schema Standards

**Researcher**: researcher-2
**Date**: 2026-02-11
**Task**: Deep dive into agent/entity ontologies and graph schema formalisms
**Input**: ontology-discovery.md catalog, ADR-0009, cluster1-context-graphs.md

---

## Part A: Agent and Entity Ontologies

### A.1 FIPA Agent Management Ontology

**Spec**: http://www.fipa.org/specs/fipa00023/XC00023H.html
**Status**: IEEE standard (since 2005), foundational but dated
**Format**: Specification suite (pre-Semantic Web, not OWL)

#### Core Agent Model

FIPA defines a normative reference model for agent platforms with three mandatory components:

| Component | Role | Parallel in Context-Graph |
|-----------|------|---------------------------|
| **Agent** | Autonomous entity with identity, capabilities, communication | Entity node with `entity_type: agent` |
| **Agent Management System (AMS)** | Lifecycle management, white-pages directory of agent identifiers | Our event ledger tracking agent_id across sessions |
| **Directory Facilitator (DF)** | Yellow-pages service: agents register capabilities, others query them | Potential future capability-discovery over Entity nodes |

#### Agent Identifier (AID) Structure

FIPA's AID is the most carefully specified agent identity model in the standards literature:

```
agent-identifier:
  :name         <globally-unique-name>    # e.g. "agent1@platform.example.com"
  :addresses    <set-of-transport-URIs>   # physical contact points
  :resolvers    <set-of-AMS-addresses>    # where to look up this agent
```

Key design decisions:
- **Name is globally unique** -- constructed as `<agent-name>@<home-platform-HAP>`, stable across migrations
- **Addresses are mutable** -- an agent may change transport addresses without changing identity
- **Resolvers enable federation** -- agents on different platforms can discover each other via AMS federation

**Relevance to our Entity model**: Our current `entity_id` is "deterministic from name + type" (ADR-0009), which is simpler than FIPA's AID but follows the same principle: identity is separate from location. FIPA validates our design choice of stable entity identity independent of session or transport.

#### FIPA Communicative Acts

FIPA defines 22 communicative act types (performatives) based on speech act theory:

| Category | Acts | Context-Graph Mapping |
|----------|------|----------------------|
| Information passing | `inform`, `confirm`, `disconfirm` | `agent.output.*` event types |
| Requesting | `request`, `request-when`, `request-whenever` | `agent.invoke`, `tool.execute` |
| Negotiation | `propose`, `accept-proposal`, `reject-proposal` | Multi-agent coordination events |
| Querying | `query-if`, `query-ref` | `agent.query.*` event types |

**Assessment**: The 22-performative taxonomy is too fine-grained for LLM agent interactions (most are `inform` or `request`). However, the top-level categorization (information/requesting/negotiation/querying) provides a useful coarse classification for our `event_type` hierarchy. We could adopt a simplified 4-5 category scheme inspired by FIPA rather than the full 22 acts.

#### Limitations for Our Use Case

- Pre-LLM design assumes structured content languages (SL, KIF), not natural language
- No concept of memory, graph structure, or provenance
- Platform-centric model assumes agents live on managed platforms -- modern LLM agents are more fluid
- No entity types beyond "agent" -- no tools, resources, or concepts as first-class entities

---

### A.2 schema.org Action Model and SoftwareApplication

**Spec**: https://schema.org/Action, https://schema.org/SoftwareApplication
**Status**: W3C Community standard, current version V29.4 (December 2025)
**Format**: JSON-LD / RDFa / Microdata

#### Action Type Hierarchy

schema.org defines a rich action taxonomy that maps remarkably well to agent operation types:

```
Action
  ├── AssessAction (CheckAction, IgnoreAction)
  ├── ConsumeAction (ReadAction, ViewAction, ListenAction, UseAction)
  ├── CreateAction (WriteAction, DrawAction, PaintAction, PhotographAction)
  ├── FindAction (CheckAction, DiscoverAction, TrackAction)
  ├── InteractAction (CommunicateAction, FollowAction, JoinAction, SubscribeAction)
  ├── MoveAction (ArriveAction, DepartAction, TravelAction)
  ├── OrganizeAction (AllocateAction, ApplyAction, PlanAction)
  ├── SearchAction
  ├── TradeAction (BuyAction, SellAction, RentAction)
  ├── TransferAction (DownloadAction, SendAction, ReceiveAction)
  └── UpdateAction (AddAction, DeleteAction, ReplaceAction)
```

#### Action Role Decomposition

Every schema.org Action has these participation roles:

| Role | Property | Description | Context-Graph REFERENCES Role |
|------|----------|-------------|-------------------------------|
| **agent** | `schema:agent` | Direct performer (animate or inanimate) | `role: subject` |
| **instrument** | `schema:instrument` | Tool/device used to perform | `role: tool` |
| **object** | `schema:object` | Thing being acted upon | `role: object` |
| **result** | `schema:result` | Product/outcome of the action | `role: target` (or new `role: result`) |
| **participant** | `schema:participant` | Other entities involved | Could add `role: participant` |

**Recommendation**: Adopt schema.org's role vocabulary for our REFERENCES edge `role` property. Currently our roles are `{subject, object, tool, target}`. schema.org suggests renaming/extending to:

```python
ENTITY_ROLES = {
    "agent":       "Direct performer (maps to schema:agent)",
    "instrument":  "Tool used (maps to schema:instrument)",
    "object":      "Thing acted upon (maps to schema:object)",
    "result":      "Outcome produced (maps to schema:result)",
    "participant": "Other involved entity (maps to schema:participant)",
}
```

#### Action Status Vocabulary

schema.org provides a formal action lifecycle:

| Status | Description | Our `status` field mapping |
|--------|-------------|---------------------------|
| `PotentialActionStatus` | Action not yet started | `pending` |
| `ActiveActionStatus` | Action in progress | `running` |
| `CompletedActionStatus` | Action finished successfully | `completed` |
| `FailedActionStatus` | Action ended with failure | `failed` |

**Recommendation**: Adopt these status values directly. They are web-standard and well-understood.

#### SoftwareApplication for Tool Entities

schema.org's `SoftwareApplication` type provides properties for modeling our tool Entity nodes:

- `applicationCategory`: Type of software (e.g., "SearchTool", "DatabaseTool")
- `operatingSystem`: Platform requirements
- `softwareVersion`: Version identifier
- `featureList`: Capabilities
- `permissions`: Required permissions

**Assessment**: More detailed than we need for MVP, but provides a standard vocabulary if we later enrich tool Entity nodes with capability metadata. The `applicationCategory` property could map to a future `tool_category` attribute on Entity nodes.

---

### A.3 BDI (Belief-Desire-Intention) Ontology

**Spec**: https://arxiv.org/abs/2511.17162 (November 2025)
**Status**: Recent OWL ontology, modular Ontology Design Pattern (ODP)
**Format**: OWL2

#### Core Architecture

The BDI Ontology (2025) provides a formal OWL encoding of the classic BDI model as a reusable Ontology Design Pattern:

```
Agent
  ├── has Belief     → Proposition (agent's model of the world)
  ├── has Desire     → Goal (agent's objectives/preferences)
  ├── has Intention  → Plan (agent's committed course of action)
  └── has Justification → Reason (why agent holds a mental state)
```

Key classes and relations:
- **Agent**: Entity capable of autonomous action and deliberation
- **Belief**: Agent's representation of world state (may be true, false, or uncertain)
- **Desire**: Agent's goal or preferred outcome
- **Intention**: Agent's commitment to execute a specific plan
- **Plan**: Sequence of actions intended to achieve a goal
- **Justification**: Reason linking mental states to their causes

#### T2B2T Paradigm (Triples-to-Beliefs-to-Triples)

The paper introduces a bidirectional translation between RDF knowledge and agent mental states:

1. **Triples -> Beliefs**: RDF triples from a knowledge graph are interpreted as agent beliefs
2. **Beliefs -> Reasoning**: Agent deliberates using BDI architecture (belief revision, plan selection)
3. **Reasoning -> Triples**: Agent's conclusions, intentions, and actions are serialized back to RDF

**Relevance to our project**: This paradigm directly parallels our graph-to-context-to-agent flow:
- Our Neo4j graph (triples/nodes/edges) provides context to agents
- Agents reason and take actions (events)
- Actions are captured back as events, projected into the graph

The BDI Ontology provides formal vocabulary for the "mental state" aspect that our system currently treats as opaque event payloads.

#### Relevance to Intent-Aware Retrieval

ADR-0009's intent classification (why/when/what/related/general) maps loosely to BDI concepts:

| ADR-0009 Intent | BDI Concept | Edge Focus |
|-----------------|-------------|------------|
| `why` | Justification / Belief revision | CAUSED_BY |
| `when` | Plan execution timeline | FOLLOWS |
| `what` | Belief state (what does agent know) | REFERENCES |
| `related` | Associative beliefs | SIMILAR_TO |

**Assessment**: The BDI Ontology is the most relevant recent formal model for agent cognition, but it models the internal deliberation process, which our system treats as a black box. We capture the external trace (events), not the internal states (beliefs, desires). The BDI vocabulary is useful for enrichment (e.g., classifying events as "belief update" vs. "plan execution" vs. "goal adoption") but should not be required in the core schema.

---

### A.4 Emerging: Agent Identity URI Scheme (2026)

**Spec**: https://arxiv.org/abs/2601.14567 (January 2026)
**Status**: Preprint, proposed standard
**Format**: URI scheme specification

#### URI Structure

```
agent://<trust-root>/<capability-path>/<agent-id>
```

Example: `agent://anthropic.com/assistant/chat/agent_01h455vb4pex5vsknk084sn02q`

Three orthogonal components:
1. **Trust root**: Organizational authority (e.g., `anthropic.com`)
2. **Capability path**: Hierarchical function description (e.g., `/assistant/chat`)
3. **Agent identifier**: TypeID combining type prefix + UUIDv7 (globally unique, sortable)

#### Key Design Principles

- **Topology-independent**: Identity does not change when agent migrates between hosts
- **Capability-based discovery**: Query by capability path prefix, not by endpoint
- **Cryptographic attestation**: PASETO tokens for identity verification
- **DHT-based resolution**: O(log N) lookup without centralized registry

**Relevance to our Entity model**: Our current `entity_id` is "deterministic from name + type" which is a simple hash-based scheme. The Agent Identity URI Scheme suggests a more structured approach:

```
Current:   entity_id = hash("gpt-4o" + "agent")
Proposed:  entity_id = "agent://openai.com/completion/chat/gpt-4o"
```

The URI scheme provides richer identity information (trust root, capabilities) that could be encoded in Entity node properties rather than the ID itself. For MVP, our current scheme is sufficient, but we should ensure our `entity_id` format is extensible to accommodate structured identifiers like this.

---

### A.5 Entity Resolution Formalisms

Entity resolution -- determining when two references denote the same real-world entity -- is critical for our Entity nodes. Three formal approaches exist:

#### A.5.1 OWL `owl:sameAs`

The strongest identity assertion: two URIs refer to the *same* individual. In OWL semantics, all properties of one are inferred for the other (complete merging).

```turtle
:gpt-4 owl:sameAs :gpt-4-0613 .
# Everything true of :gpt-4 is now true of :gpt-4-0613 and vice versa
```

**Problem for us**: `owl:sameAs` is too strong. "GPT-4" and "gpt-4o" are related but not identical -- they have different capabilities, contexts, and behaviors. Using `sameAs` would incorrectly merge their properties.

#### A.5.2 SKOS Mapping Properties

SKOS provides graduated identity assertions:

| Property | Strength | Meaning | Example |
|----------|----------|---------|---------|
| `skos:exactMatch` | Strong | Same concept across schemes | `tool:gpt-4-0613` exactMatch `tool:gpt-4-june-2023` |
| `skos:closeMatch` | Moderate | Nearly identical, some context difference | `tool:gpt-4` closeMatch `tool:gpt-4-turbo` |
| `skos:broadMatch` | Hierarchical | One is a broader concept | `tool:gpt-4-family` broadMatch `tool:gpt-4o` |
| `skos:narrowMatch` | Hierarchical | One is a narrower concept | `tool:gpt-4o` narrowMatch `tool:gpt-4-family` |
| `skos:relatedMatch` | Weak | Associated but different | `tool:gpt-4` relatedMatch `tool:claude-3` |

**Recommendation**: SKOS provides exactly the right granularity for our entity resolution needs. We should model entity relationships using SKOS-inspired edge types rather than binary same/different.

#### A.5.3 SSSOM (Simple Standard for Sharing Ontology Mappings)

**Spec**: https://mapping-commons.github.io/sssom/
**Status**: Community standard, active development (2024 update)

SSSOM formalizes entity mappings as structured triples with metadata:

```
subject_id | predicate_id | object_id | mapping_justification | confidence
tool:gpt-4 | skos:closeMatch | tool:gpt-4-turbo | semapv:ManualMappingCuration | 0.9
```

Key metadata fields:
- **mapping_justification**: Why this mapping exists (manual, lexical, semantic, composite)
- **confidence**: Numeric confidence score
- **subject_source / object_source**: Which ontology/dataset each entity comes from

**Relevance**: SSSOM provides a formal framework for our entity resolution pipeline. When the enrichment worker determines that two Entity nodes refer to related concepts, it could store the mapping as an SSSOM-style record with justification and confidence, rather than a simple binary merge.

#### Proposed Entity Resolution Strategy for Context-Graph

Combining these formalisms, we recommend a three-tier approach:

| Tier | Mechanism | Edge Type | Automation |
|------|-----------|-----------|------------|
| **Exact match** | Deterministic: same normalized name + type | Merge into single Entity node | Automatic (projection worker) |
| **Close match** | High-confidence similarity (>0.9) | `SAME_AS` edge between Entity nodes | Semi-automatic (enrichment + human review) |
| **Related match** | Lower-confidence association | `RELATED_TO` edge between Entity nodes | Enrichment worker with confidence score |

This preserves the distinction between identical entities (merged), near-identical entities (linked with `SAME_AS`), and associated entities (linked with `RELATED_TO`), avoiding the over-merging problem of `owl:sameAs`.

---

### A.6 Cross-Ontology Entity Type Comparison

How should our Entity node `entity_type` enum be grounded? Here is a comparison across standards:

| Our Entity Type | PROV-O | schema.org | FIPA | BDI | OTel GenAI |
|----------------|--------|------------|------|-----|------------|
| `agent` | `prov:Agent` | `schema:agent` (role) | `fipa:Agent` | `bdi:Agent` | `gen_ai.agent.id` |
| `tool` | `prov:Entity` (used) | `schema:instrument` (role) | -- | -- | `gen_ai.tool.type` |
| `user` | `prov:Agent` | `schema:Person` | `fipa:Agent` | `bdi:Agent` | -- |
| `resource` | `prov:Entity` | `schema:Thing` | -- | -- | `gen_ai.data_source` |
| `concept` | `prov:Entity` | `schema:Thing` | -- | `bdi:Belief` | -- |

**Observations**:

1. **agent and user are both `prov:Agent`**: PROV-O does not distinguish human agents from software agents. We should keep them separate in our model (different capabilities, different trust levels) but acknowledge they share the PROV-O supertype.

2. **tool is role-dependent**: In PROV-O, a tool is an Entity that is `used` by an Activity. In schema.org, "instrument" is a role on an Action, not a type. This suggests our `tool` entity type should be understood as "an entity that commonly plays the instrument role" rather than an inherent type.

3. **concept has no strong standard mapping**: Our `concept` type is the most ad-hoc. SKOS Concept Schemes provide a formal model for organizing concepts, but concept extraction from agent events is inherently fuzzy.

**Recommendation**: Keep the current 5-type enum (`agent`, `tool`, `user`, `resource`, `concept`) for MVP but formally document each type's mapping to PROV-O and schema.org. In a future version, consider making entity_type a hierarchical taxonomy rather than a flat enum:

```
entity_type hierarchy:
  prov:Agent
    ├── agent (software agent / LLM agent)
    ├── user (human user)
    └── service (external API / platform)
  prov:Entity
    ├── tool (instrument used by agents)
    ├── resource (data source, document, artifact)
    └── concept (abstract idea, topic, category)
```

---

## Part B: Graph Schema Standards

### B.1 PG-Schema (Property Graph Schema)

**Spec**: https://arxiv.org/abs/2211.10962 (Angles et al., 2023, published in ACM SIGMOD 2023)
**Status**: Academic standard, influencing GQL/ISO 39075 v2 DDL
**Format**: Formal specification language for property graphs

#### Core Concepts

PG-Schema provides a type system for property graphs with three key constructs:

**1. Node Types** -- Named types with label constraints and property sets:

```
CREATE NODE TYPE Event (
  event_id     STRING NOT NULL,
  event_type   STRING NOT NULL,
  occurred_at  DATETIME NOT NULL,
  session_id   STRING NOT NULL,
  agent_id     STRING NOT NULL,
  trace_id     STRING NOT NULL,
  tool_name    STRING,
  global_position INTEGER NOT NULL,
  keywords     LIST<STRING>,
  summary      STRING,
  embedding    LIST<FLOAT>,
  importance_score INTEGER,
  access_count INTEGER DEFAULT 0,
  last_accessed_at DATETIME
)
```

**2. Edge Types** -- Named types with endpoint constraints and property sets:

```
CREATE EDGE TYPE FOLLOWS (
  session_id  STRING NOT NULL,
  delta_ms    INTEGER NOT NULL
) FROM Event TO Event

CREATE EDGE TYPE CAUSED_BY (
  mechanism   STRING NOT NULL  -- 'direct' | 'inferred'
) FROM Event TO Event

CREATE EDGE TYPE SIMILAR_TO (
  score       FLOAT NOT NULL
) FROM Event TO Event  -- undirected semantics

CREATE EDGE TYPE REFERENCES (
  role        STRING NOT NULL  -- 'agent' | 'instrument' | 'object' | 'result'
) FROM Event TO Entity

CREATE EDGE TYPE SUMMARIZES ()
  FROM Summary TO Event
  | FROM Summary TO Summary
```

**3. PG-Keys** -- Uniqueness and key constraints:

```
CREATE KEY Event (event_id)
CREATE KEY Entity (entity_id)
CREATE KEY Summary (summary_id)
```

**4. Type Inheritance** -- Multi-inheritance for specialization:

```
CREATE NODE TYPE ToolInvocationEvent EXTENDS Event (
  tool_name STRING NOT NULL,
  duration_ms INTEGER
)
```

#### Endpoint Constraints

The most valuable PG-Schema feature for our project is **edge endpoint constraints** -- the ability to formally specify which node types an edge can connect. This is exactly what Neo4j's native constraints cannot express:

| Edge Type | PG-Schema Constraint | Neo4j Enforcement |
|-----------|---------------------|-------------------|
| FOLLOWS | `FROM Event TO Event` | Must enforce in application code |
| CAUSED_BY | `FROM Event TO Event` | Must enforce in application code |
| SIMILAR_TO | `FROM Event TO Event` | Must enforce in application code |
| REFERENCES | `FROM Event TO Entity` | Must enforce in application code |
| SUMMARIZES | `FROM Summary TO (Event \| Summary)` | Must enforce in application code |

**Recommendation**: Define our schema formally in PG-Schema notation in the codebase documentation, even though enforcement will use Neo4j constraints (for what they can express) plus application-level validation (for what they cannot). PG-Schema serves as the specification; Neo4j constraints + projection worker code serve as the enforcement.

#### Relationship to GQL (ISO/IEC 39075)

GQL v1 was published in April 2024 as ISO/IEC 39075:2024. It defines a query language but has limited schema support. PG-Schema is designed to inform GQL v2's DDL (Data Definition Language), anticipated in the next ISO cycle.

**Assessment**: PG-Schema is the best available formalism for property graph schemas. Its academic pedigree (SIGMOD 2023) and influence on ISO standardization make it a strong choice for our schema documentation format. However, no production tooling exists for PG-Schema validation -- we must translate the formal schema into Neo4j constraints and application-level checks.

---

### B.2 RDF/OWL vs. Property Graphs -- Trade-offs for Neo4j

This is a foundational architectural question. Should our ontology be expressed in RDF/OWL (and mapped to Neo4j) or natively in property graph terms?

#### Comparison Matrix

| Dimension | RDF/OWL | Property Graph (Neo4j) |
|-----------|---------|----------------------|
| **Schema formalism** | OWL2 (decidable FOL subset) with automated reasoning | PG-Schema (proposed), Neo4j constraints (production) |
| **Validation** | SHACL (W3C standard, closed-world) | Neo4j constraints (limited) + application code |
| **Identity** | URIs (globally unique, dereferenceable) | Node IDs (database-local) + property-based keys |
| **Relationships** | Triples (subject-predicate-object), no properties on edges | Relationships with properties (first-class) |
| **Edge properties** | Requires reification (verbose, complex) | Native support (`delta_ms` on FOLLOWS, `score` on SIMILAR_TO) |
| **Multi-valued properties** | Native (multiple triples for same predicate) | Native (LIST types in Neo4j 5.x) |
| **Querying** | SPARQL (declarative, federated) | Cypher/GQL (imperative traversal, local) |
| **Performance** | Slower for deep traversals | Optimized for graph traversal |
| **Tooling maturity** | Protege, Jena, RDFlib, SHACL validators | Neo4j, Cypher, APOC, GDS |
| **Developer adoption** | Niche (semantic web community) | Broad (industry standard) |
| **Standards compliance** | W3C standards (PROV-O, SHACL, OWL) | Emerging (GQL ISO 39075) |
| **Interoperability** | High (linked data, SPARQL federation) | Low (vendor-specific, improving with GQL) |

#### Key Trade-off: Edge Properties

Our schema requires properties on edges (FOLLOWS has `delta_ms`, CAUSED_BY has `mechanism`, SIMILAR_TO has `score`, REFERENCES has `role`). In RDF, edge properties require reification:

```turtle
# RDF reification of "Event1 CAUSED_BY Event2 with mechanism=direct"
_:rel1 rdf:type rdf:Statement ;
       rdf:subject :Event1 ;
       rdf:predicate :CAUSED_BY ;
       rdf:object :Event2 ;
       :mechanism "direct" .
```

This is verbose and complicates queries. In Neo4j:

```cypher
(e1:Event)-[:CAUSED_BY {mechanism: "direct"}]->(e2:Event)
```

This is the primary reason our architecture uses Neo4j rather than a triple store.

#### Hybrid Approach: Property Graph Core + OWL Documentation

**Recommendation**: Use property graphs (Neo4j) as the runtime data model and query engine, but document the ontology in OWL/PROV-O terms for interoperability. This means:

1. **Runtime**: Neo4j with Cypher queries, property-rich edges, PG-Schema documentation
2. **Interchange**: If RDF export is needed, use neosemantics (n10s) to translate Neo4j data to RDF with PROV-O vocabulary
3. **Validation**: Neo4j native constraints for enforceable rules; SHACL shapes (via n10s) for comprehensive validation if needed
4. **Documentation**: OWL-style class/property definitions in prose, mapped to PG-Schema node/edge types

This avoids the performance and complexity costs of RDF while preserving interoperability with the provenance standards ecosystem.

---

### B.3 SHACL (Shapes Constraint Language) for Graph Validation

**Spec**: https://www.w3.org/TR/shacl/
**Status**: W3C Recommendation (2017)
**Format**: RDF (shapes described as RDF graphs)

#### Core Validation Model

SHACL defines shapes that constrain graph data:

```turtle
:EventShape a sh:NodeShape ;
    sh:targetClass :Event ;
    sh:property [
        sh:path :event_id ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
    ] ;
    sh:property [
        sh:path :event_type ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
        sh:pattern "^[a-z]+\\.[a-z]+.*$" ;  # dot-namespaced
    ] ;
    sh:property [
        sh:path :importance_score ;
        sh:datatype xsd:integer ;
        sh:minInclusive 1 ;
        sh:maxInclusive 10 ;
    ] .
```

#### SHACL vs. Neo4j Constraints

| Capability | SHACL | Neo4j Constraints |
|------------|-------|-------------------|
| Property existence | `sh:minCount 1` | `CREATE CONSTRAINT ... IS NOT NULL` |
| Property type | `sh:datatype` | `CREATE CONSTRAINT ... IS :: TYPE` (5.9+) |
| Property uniqueness | `sh:uniqueLang` (limited) | `CREATE CONSTRAINT ... IS UNIQUE` |
| Value range | `sh:minInclusive`, `sh:maxInclusive` | Not supported |
| Pattern matching | `sh:pattern` (regex) | Not supported |
| Edge endpoint types | `sh:class` on path target | Not supported |
| Closed shapes | `sh:closed true` (no extra properties) | Not supported |
| Cross-property rules | SPARQL-based constraints | Not supported |

**SHACL is strictly more expressive** than Neo4j constraints. The key capabilities SHACL adds:
- Value range validation (`importance_score` between 1-10)
- Pattern matching (`event_type` must be dot-namespaced)
- Edge endpoint validation (REFERENCES must target Entity nodes)
- Closed shape validation (no unexpected properties)

#### Neo4j Integration via neosemantics (n10s)

The neosemantics plugin provides SHACL validation for Neo4j:

```cypher
// Load SHACL shapes
CALL n10s.validation.shacl.import.fetch("file:///shapes/event-shapes.ttl", "Turtle")

// Validate entire graph
CALL n10s.validation.shacl.validate()
YIELD focusNode, nodeType, shapeId, propertyShape, offendingValue, resultMessage

// Validate specific nodes
CALL n10s.validation.shacl.validateSet(nodeList)
```

**Assessment**: SHACL via n10s is a viable validation path but adds complexity (RDF shapes for a property graph, n10s plugin dependency). For MVP, Neo4j native constraints plus application-level validation in the projection worker are sufficient. SHACL becomes valuable if/when we need:
- Formal validation reports (for compliance/auditing)
- Cross-property validation rules
- RDF export with shape conformance

**Recommendation**: Defer SHACL adoption. Document validation rules in PG-Schema notation. Enforce via Neo4j constraints + projection worker validation. Add SHACL as a future enhancement for formal validation pipelines.

---

### B.4 Neo4j Native Schema Constraints

**Spec**: https://neo4j.com/docs/cypher-manual/current/constraints/
**Status**: Production (Neo4j 5.x, property type constraints since 5.9)

#### Concrete Schema for Context-Graph

Based on ADR-0009 node/edge types, the following Neo4j constraints should be defined:

```cypher
-- Event node constraints
CREATE CONSTRAINT event_pk FOR (e:Event) REQUIRE e.event_id IS UNIQUE;
CREATE CONSTRAINT event_id_exists FOR (e:Event) REQUIRE e.event_id IS NOT NULL;
CREATE CONSTRAINT event_type_exists FOR (e:Event) REQUIRE e.event_type IS NOT NULL;
CREATE CONSTRAINT event_occurred_at_exists FOR (e:Event) REQUIRE e.occurred_at IS NOT NULL;
CREATE CONSTRAINT event_session_id_exists FOR (e:Event) REQUIRE e.session_id IS NOT NULL;
CREATE CONSTRAINT event_agent_id_exists FOR (e:Event) REQUIRE e.agent_id IS NOT NULL;
CREATE CONSTRAINT event_global_position_exists FOR (e:Event) REQUIRE e.global_position IS NOT NULL;

-- Property type constraints (Neo4j 5.9+ Enterprise)
CREATE CONSTRAINT event_id_type FOR (e:Event) REQUIRE e.event_id IS :: STRING;
CREATE CONSTRAINT event_type_type FOR (e:Event) REQUIRE e.event_type IS :: STRING;
CREATE CONSTRAINT event_occurred_at_type FOR (e:Event) REQUIRE e.occurred_at IS :: ZONED DATETIME;
CREATE CONSTRAINT event_importance_type FOR (e:Event) REQUIRE e.importance_score IS :: INTEGER;

-- Entity node constraints
CREATE CONSTRAINT entity_pk FOR (n:Entity) REQUIRE n.entity_id IS UNIQUE;
CREATE CONSTRAINT entity_id_exists FOR (n:Entity) REQUIRE n.entity_id IS NOT NULL;
CREATE CONSTRAINT entity_name_exists FOR (n:Entity) REQUIRE n.name IS NOT NULL;
CREATE CONSTRAINT entity_type_exists FOR (n:Entity) REQUIRE n.entity_type IS NOT NULL;

-- Summary node constraints
CREATE CONSTRAINT summary_pk FOR (s:Summary) REQUIRE s.summary_id IS UNIQUE;
CREATE CONSTRAINT summary_id_exists FOR (s:Summary) REQUIRE s.summary_id IS NOT NULL;
CREATE CONSTRAINT summary_scope_exists FOR (s:Summary) REQUIRE s.scope IS NOT NULL;
```

#### Gaps in Neo4j Constraint Coverage

| Required Validation | Neo4j Support | Workaround |
|--------------------|---------------|------------|
| Edge endpoint types (FOLLOWS: Event->Event only) | Not supported | Projection worker validates during MERGE |
| `entity_type` enum values | Not supported | Application-level validation |
| `importance_score` range (1-10) | Not supported | Application-level validation |
| `event_type` dot-namespace pattern | Not supported | Application-level validation |
| `mechanism` enum on CAUSED_BY | Not supported | Application-level validation |
| `role` enum on REFERENCES | Not supported | Application-level validation |

**Recommendation**: Implement the above Cypher constraints in a migration script. Add application-level validation in the projection worker for everything Neo4j cannot enforce. Document the complete validation rules in PG-Schema notation as the source of truth.

---

### B.5 Multi-Graph Views and Formalization

Our ADR-0009 architecture defines four "orthogonal edge views" (temporal, causal, semantic, entity) that share the same node set. This is a multi-graph formalization question.

#### Formal Definition

Following the Typed Property Graph model, our multi-view graph can be formalized as:

```
G = (N, E, T_n, T_e, L_n, L_e, P, V)

where:
  N = set of nodes (Event ∪ Entity ∪ Summary)
  E = set of edges (FOLLOWS ∪ CAUSED_BY ∪ SIMILAR_TO ∪ REFERENCES ∪ SUMMARIZES)
  T_n = {Event, Entity, Summary}  -- node type set
  T_e = {FOLLOWS, CAUSED_BY, SIMILAR_TO, REFERENCES, SUMMARIZES}  -- edge type set
  L_n : N → T_n  -- node labeling function
  L_e : E → T_e  -- edge labeling function
  P = property schema per type
  V = property value constraints
```

A **view** is a typed subgraph:

```
View_temporal = (N_event, E_follows)  where E_follows ⊆ E, type(e) = FOLLOWS
View_causal   = (N_event, E_caused)   where E_caused ⊆ E, type(e) = CAUSED_BY
View_semantic = (N_event, E_similar)  where E_similar ⊆ E, type(e) = SIMILAR_TO
View_entity   = (N_event ∪ N_entity, E_ref)  where E_ref ⊆ E, type(e) = REFERENCES
View_summary  = (N_all, E_summary)    where E_summary ⊆ E, type(e) = SUMMARIZES
```

#### MV4PG (Materialized Views for Property Graphs)

The recent MV4PG paper (Han et al., November 2024) formalizes property graph views following GQL specification:

- A view is defined as the union of conjunctive path queries forming a single output graph
- Views can be materialized for performance (up to 28x speedup on complex queries)
- View maintenance is templated -- automatically generated during view creation

**Relevance**: Our "views" are simpler than MV4PG's general framework -- they are type-filtered subgraphs, not arbitrary query results. In Cypher, a view query is just a label filter:

```cypher
// Temporal view
MATCH (e1:Event)-[f:FOLLOWS]->(e2:Event) RETURN e1, f, e2

// Causal view
MATCH (e1:Event)-[c:CAUSED_BY]->(e2:Event) RETURN e1, c, e2

// Entity view
MATCH (e:Event)-[r:REFERENCES]->(n:Entity) RETURN e, r, n
```

No materialization needed -- Neo4j's typed relationships already serve as "views" that can be traversed independently. The intent-aware retrieval (ADR-0009) combines views by weighting edge types during traversal.

#### MAGMA's Multi-Graph Formalization

MAGMA (from cluster1-context-graphs.md) formalizes its multi-graph as:

```
G_t = (N_t, E_t)  where E_t = E_temp ∪ E_causal ∪ E_sem ∪ E_ent
```

With each edge set having distinct semantics:
- `E_temp`: Strictly ordered, immutable temporal backbone
- `E_causal`: Directed, inferred causality with relevance scores
- `E_sem`: Undirected, embedding similarity above threshold
- `E_ent`: Connects events to entity abstractions

**Key property**: The edge sets are orthogonal -- they can be traversed independently or combined. MAGMA's adaptive traversal policy selects which edge types to follow based on query intent.

**Assessment**: Our ADR-0009 already adopts MAGMA's formalization. The formal definition above documents it explicitly. No additional formalism is needed -- typed relationships in Neo4j directly implement the multi-view concept.

---

## Part C: Key Questions Answered

### C.1 Should our Entity node types follow an existing ontology?

**Answer**: Partially. Our entity types should be **grounded in** existing ontologies but not **constrained by** them.

**Grounding**:
- `agent` and `user` map to `prov:Agent` (W3C PROV-O)
- `tool` maps to `schema:instrument` role (schema.org) and `prov:Entity` with `prov:used` relation
- `resource` maps to `prov:Entity` (W3C PROV-O)
- `concept` maps to `skos:Concept` (SKOS)

**Extension**:
- Keep the 5-type flat enum for MVP
- Document the PROV-O and schema.org mapping in the ontology specification
- Plan for hierarchical entity types in a future version (see A.6 above)

### C.2 What formalism for our multi-typed property graph?

**Answer**: PG-Schema notation for documentation and formal specification; Neo4j native constraints for production enforcement; application-level validation for rules that Neo4j cannot express.

The layered approach:
1. **PG-Schema** (formal spec): Defines node types, edge types with endpoint constraints, property constraints, keys
2. **Neo4j Constraints** (enforcement): Uniqueness, existence, type checks
3. **Projection Worker** (enforcement): Edge endpoint validation, enum validation, range checks, pattern matching
4. **SHACL** (future): Formal validation with machine-readable reports, if compliance requirements emerge

### C.3 How to handle entity resolution formally?

**Answer**: Three-tier approach inspired by SKOS and SSSOM:

| Tier | When | Action | Formalism |
|------|------|--------|-----------|
| **Exact** | Normalized name + type match | Merge to single Entity node | Deterministic (projection worker) |
| **Close** | High similarity (>0.9) detected | Add `SAME_AS` edge with confidence | SSSOM-style mapping with justification |
| **Related** | Lower similarity or family relation | Add `RELATED_TO` edge with confidence | SKOS `relatedMatch` semantics |

Key principle: **Never auto-merge entities that might be distinct.** Over-merging (false `sameAs`) is harder to fix than under-merging (missing links). Start with high-confidence exact matches only; add close/related matches during enrichment with human-reviewable confidence scores.

### C.4 Is there a standard for graph views?

**Answer**: Not yet, but the concept is well-formalized.

- **GQL (ISO 39075)** v1 does not include views. MV4PG proposes a formal view model that follows GQL specification for future versions.
- **MAGMA** formalizes multi-graph views as typed edge subsets of a shared node set -- this is the closest model to our architecture.
- **Neo4j** native typed relationships already function as implicit views -- no explicit view layer is needed.

For our architecture, the "view" concept is implemented through typed edge labels, not a separate view mechanism. Intent-aware traversal (ADR-0009) dynamically creates virtual views by selecting which edge types to follow per query.

---

## Part D: Recommendations Summary

### Standards Adoption Matrix

| Standard | Scope | Priority | How to Adopt |
|----------|-------|----------|-------------|
| **PROV-O** | Entity type grounding, provenance vocabulary | Must adopt | Map node/edge types to PROV-O terms in ontology doc |
| **schema.org Action** | Entity roles on REFERENCES edges, action status | Should adopt | Rename roles to schema.org vocabulary |
| **PG-Schema** | Formal graph schema specification | Should adopt | Document schema in PG-Schema notation |
| **Neo4j Constraints** | Production enforcement | Must use | Implement constraint migration script |
| **SKOS mapping properties** | Entity resolution graduated identity | Should adopt | Model entity resolution with SKOS-inspired semantics |
| **SSSOM** | Entity mapping metadata | May adopt | Add justification/confidence to entity resolution |
| **FIPA** | Agent identity patterns | Reference only | Validate our agent_id design, inform event_type taxonomy |
| **BDI Ontology** | Agent mental state vocabulary | Reference only | Potentially classify event payloads in enrichment |
| **Agent Identity URI** | Structured agent identifiers | Monitor | Ensure entity_id format is extensible |
| **SHACL** | Graph validation with reports | Defer | Add when formal validation pipelines are needed |
| **MV4PG** | Materialized graph views | Defer | Not needed -- typed edges serve as implicit views |

### Proposed Changes to ADR-0009

Based on this research, we recommend the following modifications:

1. **Rename REFERENCES edge roles** from `{subject, object, tool, target}` to `{agent, object, instrument, result, participant}` following schema.org Action vocabulary.

2. **Add entity resolution edges**: Introduce `SAME_AS` (high-confidence identity) and `RELATED_TO` (family/association) edges between Entity nodes, with `confidence` and `justification` properties.

3. **Formalize the schema in PG-Schema notation**: Add a formal schema definition section to ADR-0009 (or a new ADR) using PG-Schema syntax for node types, edge types, endpoint constraints, and keys.

4. **Add Neo4j constraint migration**: Include concrete Cypher constraint definitions as an appendix.

5. **Document PROV-O mapping**: Expand the existing PROV-DM compatibility table (ADR-0009 Amendment 1) to include node type mappings, not just edge type mappings.

6. **Make entity_type extensible**: Document entity_type as a leaf in a type hierarchy (prov:Agent -> agent/user; prov:Entity -> tool/resource/concept) rather than a flat enum, even if MVP enforces the flat enum.

---

## References

### Agent/Entity Ontologies
- FIPA Agent Management Specification: http://www.fipa.org/specs/fipa00023/XC00023H.html
- FIPA Ontology Service: http://www.fipa.org/specs/fipa00086/XC00086C.html
- schema.org Action: https://schema.org/Action
- schema.org SoftwareApplication: https://schema.org/SoftwareApplication
- BDI Ontology (2025): https://arxiv.org/abs/2511.17162
- Agent Identity URI Scheme (2026): https://arxiv.org/abs/2601.14567
- SKOS Reference: https://www.w3.org/TR/skos-reference/
- SSSOM: https://mapping-commons.github.io/sssom/

### Graph Schema Standards
- PG-Schema: https://arxiv.org/abs/2211.10962 (SIGMOD 2023)
- GQL (ISO/IEC 39075:2024): https://www.gqlstandards.org/
- SHACL: https://www.w3.org/TR/shacl/
- Neo4j Constraints: https://neo4j.com/docs/cypher-manual/current/constraints/
- neosemantics (n10s): https://neo4j.com/labs/neosemantics/
- MV4PG: https://arxiv.org/abs/2411.18847

### Context-Graph Project References
- ADR-0009: Multi-Graph Schema for Memory
- Cluster 1 Research: Context Graphs and Graph-Based Memory
- Ontology Discovery Catalog: docs/research/ontology-discovery.md
