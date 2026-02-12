# Ontology Discovery: Standards and Ontologies for the Context Graph

Date: 2026-02-11
Status: Research deliverable for ADR-0011

## Purpose

This document catalogs the most relevant ontologies and standards across five areas that inform a formal ontology for the context-graph project. The project captures immutable events from AI agents, stores them in Redis, projects them into a Neo4j graph with 5 edge types (FOLLOWS, CAUSED_BY, SIMILAR_TO, REFERENCES, SUMMARIZES) and 3 node types (Event, Entity, Summary), and uses 5 cognitive memory tiers (sensory, working, episodic, semantic, procedural).

The current system has a loose mapping to W3C PROV-DM (documented in ADR-0001 and ADR-0009's PROV-DM compatibility table) but no formal ontology underneath. This discovery identifies which standards should inform ADR-0011.

---

## 1. Provenance Ontologies

### 1.1 W3C PROV-O (The PROV Ontology)

**Spec**: https://www.w3.org/TR/prov-o/
**Status**: W3C Recommendation (2013), widely adopted
**Format**: OWL2 (conforms to OWL-RL profile)

**Core model**: Three types and seven core relations:
- **Types**: Entity (things), Activity (processes), Agent (responsible parties)
- **Relations**: `wasGeneratedBy`, `used`, `wasDerivedFrom`, `wasAttributedTo`, `wasAssociatedWith`, `actedOnBehalfOf`, `wasInformedBy`

**Organization**: Terms are layered into three tiers -- Starting Point (core triples), Expanded (qualified relationships with roles/timing), and Qualified (reified influence patterns for attaching metadata to relationships).

**Why it matters for context-graph**:
- ADR-0001 already commits to PROV-DM vocabulary. PROV-O is its OWL encoding.
- The Entity/Activity/Agent triangle maps directly to our Event/Entity node types and agent attribution.
- `wasInformedBy` maps to our CAUSED_BY edge; `wasAttributedTo` maps to REFERENCES with role=agent.
- The Qualified pattern (e.g., `qualifiedGeneration` with `atTime`) provides a formal mechanism for the metadata we attach to edges (e.g., `mechanism: direct|inferred` on CAUSED_BY).
- PROV-O's Bundle concept supports "provenance of provenance" -- relevant for our re-projection model where Neo4j is derived from Redis.

**Gap**: PROV-O has no built-in temporal sequencing relationship (our FOLLOWS edge). It models time as properties on activities (`startedAtTime`, `endedAtTime`), not as explicit temporal ordering edges. Also lacks semantic similarity or hierarchical summarization concepts.

### 1.2 P-Plan (Ontology for Provenance and Plans)

**Spec**: https://www.opmw.org/model/p-plan/
**Status**: Stable, OWL2 extension of PROV-O
**Format**: OWL2

**Core model**: Extends PROV-O with plan-level abstractions:
- **Plan**: A `p-plan:Plan` is a `prov:Entity` representing an intended workflow
- **Step**: A `p-plan:Step` is a planned activity (linked to execution via `correspondsToStep`)
- **Variable**: A `p-plan:Variable` represents planned inputs/outputs (linked via `correspondsToVariable`)
- **Ordering**: `p-plan:isPreceededBy` captures step dependencies

**Why it matters for context-graph**:
- Directly relevant to our **Procedural Memory** tier (ADR-0007 Tier 5). Tool-use policies and learned workflows are exactly "plans" in P-Plan terms.
- The Plan/Step/Variable model maps to our future WORKFLOW and STEP node types.
- `isPreceededBy` provides a formal precedent for our FOLLOWS edge -- both model ordering of planned/actual steps.
- The `correspondsToStep` link between plan and execution parallels our distinction between procedural patterns (abstract) and episodic traces (concrete).

**Gap**: P-Plan is designed for scientific workflows with static plans, not adaptive agent plans that evolve during execution. Agent tool selection is dynamic, not pre-declared.

### 1.3 ProvONE (DataONE Provenance for Scientific Workflows)

**Spec**: https://purl.dataone.org/provone-v1-dev
**Status**: Stable, extends W3C PROV
**Format**: OWL

**Core model**: Extends PROV with computational workflow concepts:
- **Program**: Computational task with input/output Ports (atomic or composite)
- **Port**: Input/output connection points on Programs
- **Channel**: Connections between Ports across Programs
- **Execution**: Runtime trace of a Program (its Plan)
- **Data/Visualization/Document**: Typed entities produced by execution

**Why it matters for context-graph**:
- The Program/Port/Channel model formalizes tool interfaces -- relevant for modeling agent tool invocations where tools have defined inputs/outputs.
- The Execution class parallels our event traces: an Execution is a runtime record of a Program, just as our Events are runtime records of agent/tool actions.
- ProvONE's composite Program concept (nested workflows) maps to our agent-invoking-agent patterns via `parent_event_id` chains.

**Gap**: ProvONE is designed for batch scientific workflows, not interactive agent sessions. No concept of sessions, real-time streaming, or intent-aware retrieval.

### Summary: Provenance Recommendations

| Standard | Relevance | Adoption Priority |
|----------|-----------|-------------------|
| **PROV-O** | Core provenance vocabulary, already referenced in ADR-0001 | **Must adopt** -- formalize the existing loose mapping |
| **P-Plan** | Procedural memory tier, plan/step patterns | **Should adopt** -- when Tier 5 is implemented |
| **ProvONE** | Tool interface modeling, composite execution | **May reference** -- useful patterns but over-specified for agent use case |

---

## 2. Event/Activity Ontologies

### 2.1 OpenTelemetry GenAI Semantic Conventions

**Spec**: https://opentelemetry.io/docs/specs/semconv/gen-ai/
**Status**: Development (pre-stable), active evolution in 2025-2026
**Format**: Attribute naming conventions (not OWL/RDF -- these are key-value span attributes)

**Core model for agents**:
- **Agent spans**: `gen_ai.operation.name = invoke_agent`, with `gen_ai.agent.id`, `gen_ai.agent.name`, `gen_ai.agent.description`
- **Tool spans**: `gen_ai.tool.type` describes tool execution bridging agents to external APIs
- **Span kinds**: CLIENT (remote agent invocation), INTERNAL (in-process agent)
- **Data sources**: Grounding data used by agents (databases, document collections, etc.)
- **Provider discrimination**: `gen_ai.provider.name` identifies the GenAI provider (e.g., `aws.bedrock`)

**Why it matters for context-graph**:
- ADR-0001 commits to OTel as the primary ingestion format. These conventions define the attribute vocabulary our OTLP adapter must parse.
- `gen_ai.agent.id` and `gen_ai.agent.name` map directly to our `agent_id` field and Entity nodes of type `agent`.
- `gen_ai.tool.type` and tool span attributes map to our `tool_name` field and Entity nodes of type `tool`.
- The span parent/child hierarchy maps to our `parent_event_id` chains and CAUSED_BY edges.
- OTel's `gen_ai.conversation.id` maps to our `session_id`.

**Gap**: OTel conventions are flat attribute key-value pairs, not a graph ontology. They define vocabulary but not relationships. No concept of semantic similarity, summarization, or memory tiers.

### 2.2 Event Ontology (motools)

**Spec**: https://motools.sourceforge.net/event/event.html
**Status**: Stable (2007), widely referenced in linked data communities
**Format**: OWL

**Core model**: An Event is "an arbitrary classification of a space/time region, by a cognitive agent." Events have:
- **Agents**: Active participants (e.g., performer, engineer)
- **Factors**: Passive things with a role (e.g., instrument, score)
- **Products**: Things produced by the event
- **Time**: Linked to Timeline Ontology (Instant, Interval)
- **Place**: Spatial location

**Why it matters for context-graph**:
- The agent/factor/product decomposition maps to our REFERENCES edge roles: `subject` (agent), `tool` (factor/instrument), `object` (product).
- The distinction between active agents and passive factors provides formal grounding for distinguishing tool-as-agent vs. tool-as-instrument in our entity model.
- The Timeline Ontology integration (Instant/Interval) provides a formal model for our FOLLOWS temporal backbone.

**Gap**: Designed for cultural/media events, not computational processes. No concept of causality chains, provenance, or derived knowledge. Very lightweight -- may be too simple for our needs.

### 2.3 Simple Event Model (SEM)

**Spec**: https://semanticweb.cs.vu.nl/2009/11/sem/
**Status**: Stable (2011), domain-independent
**Format**: OWL

**Core model**: Minimal-commitment event model with:
- **sem:Event**: Core event class
- **sem:Actor**: Participant in events (maps to Agent)
- **sem:Place**: Where events occur
- **sem:Time**: When events occur
- **sem:Role**: Role-based participation (connects Actor to Event with a typed role)
- **sem:EventType**: Classification of events (parallels our dot-namespaced `event_type`)

**Why it matters for context-graph**:
- SEM's Role-based participation model is directly relevant to our REFERENCES edge `role` property (subject, object, tool, target). SEM formalizes this pattern.
- SEM's `sem:EventType` hierarchy provides a model for formalizing our dot-namespaced event types (`agent.invoke`, `tool.execute`, etc.) into a type taxonomy.
- SEM was designed to be domain-independent with minimal semantic commitment -- which aligns with our framework-agnostic domain principle.
- Supports `sem:subEventOf` for mereological (part-whole) relationships, relevant for grouping events into episodes.

**Gap**: No causality modeling. No provenance. No similarity or summarization. SEM is intentionally minimal.

### Summary: Event/Activity Recommendations

| Standard | Relevance | Adoption Priority |
|----------|-----------|-------------------|
| **OTel GenAI Conventions** | Ingestion vocabulary, agent/tool attribute naming | **Must adopt** -- already committed in ADR-0001 |
| **SEM** | Role-based participation, event type hierarchy, domain-independence | **Should reference** -- inform REFERENCES edge role model and event type taxonomy |
| **Event Ontology** | Agent/factor/product distinction, timeline integration | **May reference** -- useful conceptual model but overlaps with PROV-O |

---

## 3. Agent/Tool Ontologies

### 3.1 FIPA ACL and Agent Platform Standards

**Spec**: http://www.fipa.org/specs/fipa00086/XC00086C.html (Ontology Service)
**Status**: IEEE standard (since 2005), foundational but dated
**Format**: Specification suite (not OWL -- predates Semantic Web maturity)

**Core model**:
- **Agent**: Autonomous entity with identity, capable of communication
- **Agent Platform**: Infrastructure hosting agents (directory, messaging)
- **ACL (Agent Communication Language)**: 22 performatives (communicative acts) based on BDI logic -- e.g., `inform`, `request`, `propose`, `query-if`
- **Ontology Service**: Shared vocabulary for agent communication domains
- **Content Language**: Structured content within messages (SL, RDF, etc.)

**Why it matters for context-graph**:
- FIPA's agent identity model (agent name, address, platform) parallels our agent_id + Entity node approach.
- The communicative act taxonomy (22 performatives) provides a formal classification for agent-to-agent interaction events -- potentially mappable to event_type subtypes under `agent.communicate.*`.
- FIPA's BDI (Belief-Desire-Intention) semantics formalize the intentional stance: agents have beliefs about state, desires about goals, and intentions about plans. This is relevant to our intent-aware retrieval (ADR-0009) where query intent classifies traversal.
- The Ontology Service specification addresses exactly our need: shared vocabulary between agents for interpreting event payloads.

**Gap**: FIPA is a pre-LLM standard designed for classical multi-agent systems. Its message structure assumes structured content languages, not natural language. The 22 performatives may be too fine-grained for LLM agent interactions where most communication is `inform` or `request`. No graph or memory concepts.

### 3.2 schema.org Action Model

**Spec**: https://schema.org/Action
**Status**: Widely adopted web standard, active maintenance
**Format**: JSON-LD / RDFa / Microdata

**Core model**: An Action has:
- **agent**: The direct performer or driver (animate or inanimate)
- **object**: The thing acted upon (patient/theme)
- **instrument**: The tool used to perform the action
- **result**: The product of the action
- **target**: An EntryPoint describing how to invoke the action
- **startTime / endTime**: Temporal bounds
- **actionStatus**: PotentialActionStatus, ActiveActionStatus, CompletedActionStatus, FailedActionStatus

**Why it matters for context-graph**:
- The agent/object/instrument/result decomposition maps directly to our REFERENCES edge roles with even clearer semantics than we currently have.
- `actionStatus` provides a formal vocabulary for our event `status` field (currently string).
- The SoftwareApplication type can formally type our tool Entity nodes.
- schema.org's widespread adoption means our event data could be serialized in a format understood by web crawlers, search engines, and linked data consumers if needed.
- The Action type hierarchy (SearchAction, CreateAction, UpdateAction, etc.) provides a ready-made taxonomy for agent action types.

**Gap**: schema.org is designed for web markup, not computational provenance. No causality chains, no memory tiers, no graph traversal concepts. Very flat model -- single-level actions, not nested workflows.

### 3.3 Emerging: MCP/A2A Protocol Models

**Not a formal ontology** but worth noting:
- **Model Context Protocol (MCP)**: Anthropic's protocol defines tools, resources, and prompts as first-class objects with JSON Schema descriptions. Tools have `name`, `description`, `inputSchema`.
- **Agent-to-Agent Protocol (A2A)**: Google's protocol defines agents with `AgentCard` (name, description, capabilities, skills) and tasks with lifecycle states.

**Why it matters for context-graph**:
- These are the de facto 2025-2026 standards for agent-tool and agent-agent interaction.
- MCP's tool schema could inform our Entity node attributes for tools.
- A2A's task lifecycle (submitted, working, input-required, completed, failed) maps to event status tracking.
- Neither is formalized as an ontology, creating an opportunity for this project to formalize the mapping.

### Summary: Agent/Tool Recommendations

| Standard | Relevance | Adoption Priority |
|----------|-----------|-------------------|
| **schema.org Action** | Agent/object/instrument/result roles, action status, action type taxonomy | **Should adopt** -- formalize REFERENCES edge roles using schema.org vocabulary |
| **FIPA ACL** | Agent identity, communicative acts, BDI intent model | **Should reference** -- inform intent classification and agent interaction event types |
| **MCP/A2A** | Tool schema, agent capabilities, task lifecycle | **Should monitor** -- not yet formal ontologies but define the integration surface |

---

## 4. Cognitive/Memory Ontologies

### 4.1 Mental Functioning Ontology (MFO)

**Spec**: https://obofoundry.org/ontology/mf.html
**Source**: https://github.com/jannahastings/mental-functioning-ontology
**Status**: Active development, OBO Foundry registered
**Format**: OWL (built on BFO -- Basic Formal Ontology)

**Core model**: An overarching ontology for mental functioning:
- Built on **BFO** (Basic Formal Ontology) and related to **OGMS** (Ontology for General Medical Science)
- Covers mental processes (cognition, perception, memory) and traits (intelligence, personality)
- Module **MFO-MD** covers mental disorders
- Module **MFO-EM** covers emotions and affective phenomena
- Partially aligned with Cognitive Atlas and CogPO

**Why it matters for context-graph**:
- MFO provides the most formal OWL-based representation of cognitive memory types. Its taxonomy of mental processes includes memory subtypes (episodic, semantic, procedural, working) that directly correspond to our Tier 2-5 architecture (ADR-0007).
- Being BFO-based means it follows a rigorous upper ontology -- if we ground our memory tier names in MFO terms, we get formal interoperability with the broader biomedical ontology ecosystem.
- The process/trait distinction (processes happen, traits persist) maps to our event/entity distinction.

**Gap**: MFO models human mental functioning, not AI agent memory systems. The mapping is metaphorical -- our "episodic memory" (Redis event store) is not literally episodic memory in the neuroscience sense. Using MFO terms requires careful qualification that these are analogical, not literal, uses.

### 4.2 Cognitive Paradigm Ontology (CogPO)

**Spec**: http://www.cogpo.org/
**BioPortal**: https://bioportal.bioontology.org/ontologies/COGPO
**Status**: Active, BFO-compliant
**Format**: OWL

**Core model**: Describes experimental conditions in cognitive neuroscience:
- **Stimuli presented**: What the subject perceives
- **Instructions given**: Task demands
- **Responses requested**: Expected behavioral output
- Compliant with BFO; harmonized with RadLex, NeuroLex, OBI

**Why it matters for context-graph**:
- CogPO's stimulus/instruction/response pattern maps to our event lifecycle: an agent receives input (stimulus), processes instructions (context from working memory), and produces a response (tool invocation or output).
- CogPO provides formal terms for cognitive paradigms used in experiments -- if we model agent behavior evaluation as a kind of cognitive experiment, CogPO vocabulary could classify agent evaluation protocols.

**Gap**: CogPO is designed for fMRI/neuroimaging experiments, not AI systems. Very domain-specific to cognitive neuroscience labs. The mapping is a stretch for our use case.

### 4.3 Cognitive Atlas (CogAt)

**Spec**: https://cognitiveatlas.org/
**Status**: Active collaborative knowledge base
**Format**: Web-based knowledge graph (not OWL -- informal ontology)

**Core model**: Two fundamental categories:
- **Mental concepts**: Unobservable psychological processes/structures (e.g., episodic memory, working memory, attention, decision-making)
- **Mental tasks**: Observable operations used to measure those constructs (e.g., Stroop task, N-back task)
- Concepts linked by relationships: `is_a`, `is_part_of`, `is_measured_by`

**Why it matters for context-graph**:
- Cognitive Atlas provides the most comprehensive taxonomy of memory types: episodic memory, semantic memory, procedural memory, working memory, sensory memory -- exactly our five tiers.
- The concept/task distinction parallels our semantic knowledge (abstract concepts) vs. episodic traces (concrete task executions).
- The `is_measured_by` relationship is interesting: it formalizes how abstract cognitive constructs are operationalized -- relevant to how our memory tiers are measured/evaluated.

**Gap**: Not a formal OWL ontology. More of a knowledge base / wiki than a machine-readable standard. Cannot be directly imported into an ontology.

### Summary: Cognitive/Memory Recommendations

| Standard | Relevance | Adoption Priority |
|----------|-----------|-------------------|
| **MFO** | Formal OWL taxonomy of memory types, BFO-grounded | **Should reference** -- use MFO terms as formal grounding for memory tier names, with explicit "analogical use" qualification |
| **Cognitive Atlas** | Comprehensive memory type taxonomy, concept/task distinction | **Should reference** -- use as the vocabulary source for tier naming, even though not machine-readable |
| **CogPO** | Stimulus/instruction/response pattern | **May reference** -- useful conceptual frame but too domain-specific for direct adoption |

---

## 5. Graph Schema Standards

### 5.1 PG-Schema (Property Graph Schema)

**Spec**: https://arxiv.org/abs/2211.10962 (Angles et al., 2023)
**Status**: Academic proposal, influencing GQL/ISO standardization
**Format**: Formal specification (not OWL -- schema language for property graphs)

**Core model**:
- **PG-Types**: Flexible type definitions for nodes and edges with multi-inheritance
- **Node types**: Named types with required/optional property sets and label constraints
- **Edge types**: Named types with source/target node type constraints and property sets
- **PG-Keys**: Uniqueness and key constraints over property combinations
- **Type inheritance**: Node/edge types can inherit from parent types

**Why it matters for context-graph**:
- PG-Schema is designed specifically for property graphs like Neo4j -- it is the most natural schema language for formalizing our 3 node types and 5 edge types.
- The type system with property constraints can formally express our node schemas (Event with required `event_id`, `event_type`, `occurred_at`; optional `keywords`, `embedding`, etc.).
- Edge type constraints can enforce that FOLLOWS only connects Event-to-Event, REFERENCES connects Event-to-Entity, SUMMARIZES connects Summary-to-Event or Summary-to-Summary.
- PG-Keys can express our uniqueness constraints (e.g., `event_id` uniqueness on Event nodes).
- PG-Schema is on track to influence GQL (ISO/IEC 39075) version 2 DDL -- adopting PG-Schema now positions us for standards compliance.

**Gap**: PG-Schema is an academic proposal, not yet an ISO standard. No production tooling exists for PG-Schema validation. Neo4j's native constraints are less expressive than PG-Schema.

### 5.2 SHACL (Shapes Constraint Language)

**Spec**: https://www.w3.org/TR/shacl/
**Status**: W3C Recommendation (2017)
**Format**: RDF (shapes described as RDF graphs)

**Core model**:
- **Shapes**: Constraints on the structure and content of RDF graphs
- **Node shapes**: Constraints on nodes (required properties, value types, cardinality)
- **Property shapes**: Constraints on property values (ranges, patterns, lists)
- **Validation reports**: Machine-readable constraint violation reports (themselves RDF)
- **Closed-world validation**: Unlike OWL's open-world assumption, SHACL validates against expected shapes

**Why it matters for context-graph**:
- SHACL provides production-ready schema validation that could be applied to our graph data.
- The closed-world validation model matches our use case: we know the expected node/edge shapes and want to enforce them, not infer new knowledge.
- SHACL validation reports (as RDF triples) could feed into our provenance chain -- "this node was validated against shape X at time T."
- SHACL has Neo4j integration via neosemantics (n10s) plugin, providing a practical path to adoption.
- Can be used alongside PROV-O to validate that provenance graphs conform to expected patterns.

**Gap**: SHACL is designed for RDF graphs, not property graphs. Translation between property graph schemas and SHACL shapes requires an RDF-to-PG mapping layer. This adds complexity if we are not already using RDF.

### 5.3 Neo4j Native Constraints + Graph Data Science Schema

**Spec**: https://neo4j.com/docs/cypher-manual/current/constraints/
**Status**: Production (Neo4j 5.x)
**Format**: Cypher DDL

**Core capabilities**:
- **Property uniqueness constraints**: Unique property combinations per label/type
- **Property existence constraints**: Required properties per label/type
- **Property type constraints**: Type checking per property (Neo4j 5.9+)
- **Node key constraints**: Composite uniqueness + existence
- **Schema-optional model**: Constraints are additive, not required

**Why it matters for context-graph**:
- This is what we will actually use in production. Neo4j's native constraints are the enforcement layer.
- Property type constraints (new in 5.9) can enforce that `embedding` is a `LIST<FLOAT>`, `importance_score` is an `INTEGER`, etc.
- Node key constraints can enforce `event_id` uniqueness on Event nodes.
- The schema-optional model aligns with our re-projection approach: we can evolve constraints without migration.

**Gap**: Neo4j constraints are less expressive than PG-Schema or SHACL. No edge endpoint type constraints (cannot enforce that FOLLOWS only connects Event-to-Event at the schema level). No inheritance. No cross-property validation rules.

### Summary: Graph Schema Recommendations

| Standard | Relevance | Adoption Priority |
|----------|-----------|-------------------|
| **PG-Schema** | Formal property graph type system, edge endpoint constraints | **Should adopt** -- define our schema formally in PG-Schema notation for documentation, even if enforcement uses Neo4j constraints |
| **Neo4j Constraints** | Production enforcement of schema rules | **Must use** -- the actual enforcement layer |
| **SHACL** | Validation framework with reporting | **May adopt later** -- if we add RDF export or need formal validation pipelines |

---

## Cross-Cutting Analysis

### Mapping Current Architecture to Ontology Concepts

| Context-Graph Concept | PROV-O | OTel GenAI | schema.org | SEM | P-Plan |
|----------------------|--------|------------|------------|-----|--------|
| Event node | Activity | Span | Action | sem:Event | (execution) |
| Entity node | Entity | - | Thing | sem:Actor | - |
| Summary node | Entity (alternate) | - | - | - | - |
| agent_id | Agent | gen_ai.agent.id | agent | sem:Actor | - |
| tool_name | Entity (used) | gen_ai.tool.type | instrument | sem:Actor (role) | p-plan:Step |
| CAUSED_BY | wasInformedBy | parent span | - | - | - |
| FOLLOWS | (no mapping) | span ordering | - | sem:Time | isPreceededBy |
| REFERENCES | wasAttributedTo, used | - | agent/object/instrument | sem:Role | - |
| SIMILAR_TO | wasDerivedFrom (loose) | - | - | - | - |
| SUMMARIZES | alternateOf | - | - | - | - |
| session_id | Bundle | gen_ai.conversation.id | - | - | p-plan:Plan |
| parent_event_id | wasInformedBy | parent_span_id | - | sem:subEventOf | isPreceededBy |

### Ontology Stack Recommendation

Based on this discovery, the recommended ontology stack for ADR-0011 is:

```
Layer 4 (Schema enforcement): Neo4j native constraints
Layer 3 (Schema definition):  PG-Schema notation for formal documentation
Layer 2 (Domain vocabulary):  Custom context-graph ontology combining:
                               - PROV-O core (Entity/Activity/Agent + relations)
                               - OTel GenAI conventions (attribute naming)
                               - schema.org Action roles (agent/instrument/object/result)
                               - SEM patterns (role-based participation, event types)
Layer 1 (Upper ontology):     PROV-DM as conceptual foundation
                               MFO/CogAt terms for memory tier naming (analogical use)
```

### Key Design Decisions for ADR-0011

1. **PROV-O is the base**: Our custom ontology should be defined as a PROV-O profile (extending, not replacing, PROV concepts). This preserves interoperability with the broader provenance ecosystem.

2. **OTel GenAI for ingestion vocabulary**: The attribute naming conventions from OTel define our API surface and event field names. This is an ingestion concern, not a graph concern.

3. **schema.org Action for entity roles**: Formalize our REFERENCES edge `role` values using schema.org's agent/instrument/object/result vocabulary instead of ad-hoc strings.

4. **PG-Schema for graph structure**: Document the Neo4j schema formally using PG-Schema notation. This provides a language-independent schema definition that survives if we change graph databases.

5. **Memory tier terminology**: Reference MFO and Cognitive Atlas for formal grounding of tier names, but explicitly qualify that these are analogical uses -- our "episodic memory" is a computational analogy, not a claim about neuroscience.

6. **FOLLOWS edge needs original vocabulary**: No existing ontology cleanly models our temporal sequencing edge. PROV-O uses time properties, not ordering edges. P-Plan's `isPreceededBy` is the closest but models planned ordering, not observed ordering. We should define FOLLOWS as a custom extension.

7. **SIMILAR_TO is novel**: Semantic similarity edges have no precedent in provenance or event ontologies. This is a graph-native concept from the agent memory literature (MAGMA), not from ontology standards. Define as custom vocabulary.

---

## References

### Provenance Ontologies
- W3C PROV-O: https://www.w3.org/TR/prov-o/
- W3C PROV-DM: https://www.w3.org/TR/prov-dm/
- P-Plan: https://www.opmw.org/model/p-plan/
- OPMW: https://www.opmw.org/ontology/
- ProvONE: https://purl.dataone.org/provone-v1-dev

### Event/Activity Ontologies
- OTel GenAI Semantic Conventions: https://opentelemetry.io/docs/specs/semconv/gen-ai/
- OTel GenAI Agent Spans: https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/
- Event Ontology: https://motools.sourceforge.net/event/event.html
- Simple Event Model: https://semanticweb.cs.vu.nl/2009/11/sem/

### Agent/Tool Ontologies
- schema.org Action: https://schema.org/Action
- schema.org SoftwareApplication: https://schema.org/SoftwareApplication
- FIPA Ontology Service: http://www.fipa.org/specs/fipa00086/XC00086C.html
- FIPA ACL: via IEEE Computer Society

### Cognitive/Memory Ontologies
- Mental Functioning Ontology: https://obofoundry.org/ontology/mf.html
- Cognitive Paradigm Ontology: http://www.cogpo.org/
- Cognitive Atlas: https://cognitiveatlas.org/

### Graph Schema Standards
- PG-Schema: https://arxiv.org/abs/2211.10962
- SHACL: https://www.w3.org/TR/shacl/
- Neo4j Constraints: https://neo4j.com/docs/cypher-manual/current/constraints/
- GQL (ISO/IEC 39075): https://en.wikipedia.org/wiki/Graph_Query_Language
