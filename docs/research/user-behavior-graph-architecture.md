# User Behavior Patterns and User-Centric Knowledge Graph Architectures

**Research Area**: Task #3 -- Behavior patterns, skill/competency modeling, personal knowledge graphs, derived vs explicit user data, multi-agent user modeling
**Date**: 2026-02-12
**Researcher**: researcher-3
**Context**: ADR-0007 (Memory Tier Architecture), ADR-0009 (Multi-Graph Schema), ADR-0011 (Ontological Foundation)

---

## Executive Summary

This document synthesizes research across five areas critical to extending the context-graph system with user personalization capabilities: (1) behavior pattern detection in graphs, (2) skill and competency modeling, (3) user-centric knowledge graph architectures (Personal Knowledge Graphs), (4) derived vs explicit user data with confidence/provenance, and (5) multi-agent user modeling. The findings directly inform how a user personalization layer should integrate with our existing cognitive memory tier architecture (ADR-0007), multi-graph schema (ADR-0009), and ontological foundation (ADR-0011).

**Key findings**:

- Personal Knowledge Graphs (PKGs) are a maturing research area with a well-defined ecosystem framework (Balog et al., 2024) that aligns naturally with our per-user subgraph architecture
- Procedural memory research (LEGOMem, MemP, MACLA) validates our ADR-0007 Tier 5 design and provides concrete patterns for the case-to-strategy-to-skill abstraction hierarchy
- The Memoria framework (2025) demonstrates a production-viable pattern for combining session-level summarization with weighted knowledge graph user modeling -- directly applicable to our system
- Mem0 (2025) provides a production-ready memory layer with graph-based memory achieving 26% improvement over flat approaches, confirming multi-graph is the right architecture for personalization
- The explicit/implicit/intentional-implicit trichotomy (CHI 2025) supersedes the traditional binary model and must be captured in our user preference ontology
- Multi-agent shared user knowledge requires a layered architecture: agent-specific procedural memory + shared user profile graph + cross-agent behavioral aggregation

---

## 1. Behavior Pattern Detection in Graphs

### 1.1 Frequent Subgraph Patterns as Behavior Signatures

Graph-based behavior modeling represents user actions as graph structures where recurring subgraph patterns serve as behavioral signatures. The core techniques include:

**Frequent subgraph mining (FSM)**: Algorithms like GraMi discover subgraphs appearing above a user-specified frequency threshold within a single large graph or across a collection of graphs. Recent work (AGCM-SLV, 2025) extends this to approximate subgraph matching with structural and label variations, which is critical for real-world behavior patterns that are similar but not identical across sessions.

**Temporal interaction graphs (TIGs)**: A TIG models sequences of interaction events at specific timestamps. The IJCAI 2025 survey on Temporal Interaction Graph Representation Learning identifies key advances including TIGPrompt, which uses task-specific tokens to modulate attention to temporal granularity. This is directly relevant to detecting behavioral routines from our event stream.

**Behavior trajectory mining**: In e-commerce and other domains, frequent sub-trajectory mining algorithms emphasize the order of user visits for trajectory analysis and prediction. Sequential recommendation algorithms consider both the temporal aspect of behavior and the significance of interactions.

### 1.2 Workflow and Routine Detection from Event Sequences

Detecting recurring workflows from agent event sequences connects directly to our procedural memory tier (ADR-0007 Tier 5). Three key 2025-2026 systems provide concrete patterns:

**MemP (Xu et al., 2025)**: Distills past agent trajectories into both fine-grained step-by-step instructions and higher-level script-like abstractions. MemP supports two strategies for building procedural memory:
- **Offline construction**: Building procedural memory from existing trajectories (maps to our projection worker processing historical events)
- **Online self-learning**: Starting from scratch, executing tasks while actively learning procedural memory (maps to real-time pattern detection during event ingestion)

MemP achieves an 87.14% success rate on ALFWorld with procedural memory, compared to 39.28% without memory for GPT-4o. Critically, procedural memory built from a stronger model retains its value when migrated to a weaker model, validating the idea of agent-independent procedural knowledge.

**LEGOMem (Microsoft, 2025)**: A modular procedural memory framework for multi-agent LLM systems. LEGOMem decomposes past task trajectories into reusable memory units:
- **Full-task memories**: Task-level plans and reasoning traces (stored at the orchestrator level)
- **Subtask memories**: Agent-specific behavior and tool interactions (stored per specialized agent)

These modular memories are stored in a memory bank, indexed by semantic embeddings, and reused at inference time. Key finding: *orchestrator memory is critical for task decomposition and delegation, while fine-grained agent memory improves execution accuracy*.

**MACLA (2025)**: Learning Hierarchical Procedural Memory through Bayesian Selection and Contrastive Refinement. MACLA compresses 2,851 training trajectories into 187 reusable procedures through semantic abstraction. This validates the experiential hierarchy described in ADR-0007: case-based (raw traces) -> strategy-based (abstracted workflows) -> skill-based (executable procedures).

### 1.3 Connection to Our Procedural Memory Tier (ADR-0007 Tier 5)

ADR-0007 defines procedural memory as a future tier that should:
- Extract repeated successful event sequences into reusable workflow patterns
- Follow the experiential hierarchy: case -> strategy -> skill
- Store as specialized subgraph patterns in Neo4j with `WORKFLOW` and `STEP` node types

The research validates this design and provides implementation specifics:

| ADR-0007 Concept | Research Validation | Implementation Guidance |
|-------------------|---------------------|------------------------|
| Case-based memory | MemP "trajectory preservation" stage | Store raw event sequences in Redis (episodic tier) |
| Strategy-based memory | LEGOMem "full-task memories" | Abstract into workflow subgraphs in Neo4j with temporal and causal edges |
| Skill-based memory | MACLA "semantic abstraction" | Compress into reusable procedure nodes with Bayesian selection for which procedures to retain |
| Pattern extraction | MemP offline construction + MACLA contrastive refinement | Projection worker Stage 3 (re-consolidation) extracts patterns from Redis event sequences |
| Multi-agent sharing | LEGOMem orchestrator vs agent memory | Shared procedural memory bank indexed by semantic embeddings, with role-specific retrieval |

**Proposed node types for procedural memory**:

```
(:Workflow {
  workflow_id: STRING,
  name: STRING,
  abstraction_level: STRING,  // "case" | "strategy" | "skill"
  success_rate: FLOAT,
  execution_count: INTEGER,
  avg_duration_ms: INTEGER,
  source_session_ids: LIST<STRING>,
  embedding: LIST<FLOAT>
})

(:Step {
  step_id: STRING,
  ordinal: INTEGER,
  action_type: STRING,       // maps to event_type taxonomy
  tool_name: STRING,
  preconditions: STRING,
  postconditions: STRING
})

(:Workflow)-[:HAS_STEP {ordinal: INT}]->(:Step)
(:Step)-[:NEXT_STEP {condition: STRING}]->(:Step)
(:Workflow)-[:ABSTRACTED_FROM]->(:Workflow)  // case -> strategy -> skill chain
```

---

## 2. Skill and Competency Modeling

### 2.1 Knowledge Tracing Models

Knowledge tracing (KT) is the task of modeling a learner's evolving knowledge state over time. The field has evolved through three generations:

**Bayesian Knowledge Tracing (BKT)**: The classical model using four parameters -- initial knowledge probability, post-mastery error probability, mastery acquisition probability, and forgetting probability. BKT's limitations include inability to model non-linear skill progression patterns and complex learning behaviors.

**Deep Knowledge Tracing (DKT)**: Introduced RNNs for sequential learner interaction modeling. DKT analyzes sequential interactions, models evolving knowledge, and predicts skill mastery over time. A 2025 systematic review (2015-2025) identifies critical reliability issues in educational deployments.

**Graph-based Knowledge Tracing (2025)**: The current frontier uses graph neural networks:
- **Dual Graph Convolutional Networks**: Construct dual graph structures with students and skills as nodes to resolve data sparsity and skill correlation challenges
- **Multi-View Question-Skill Networks (MVQSN)**: Construct complementary relational views to model student knowledge states comprehensively
- **BKTransformer**: A transformer-based sequence modeling technique generating temporally-evolving BKT parameters

### 2.2 Competency Ontologies and Skill Taxonomies

**Enterprise skill graphs**: Neo4j's enterprise knowledge graph approach models people, documents, messages, and their relationships, enriching the graph with skills and linking people to skills based on content they created. This is directly analogous to linking our agent/user entities to competency nodes based on observed behavior patterns.

**Knowledge graph for talent competency (2025)**: Recent work integrates Graph Convolutional Networks (GCN), Reinforcement Learning (RL), and Deep Collaborative Filtering (DCF), where the GCN module captures complex multi-relational structures between jobs and candidates. The hybrid model can forecast emerging roles, identify skill gaps, and recommend tailored training programs.

**AI-driven knowledge graphs for learning personalization (2025)**: Natural language models extract key topics and concepts from training materials, while domain-specific ontologies map data to recognized skill frameworks, aligning content with job roles and competencies. Corporate training systems provide a 360-degree view of skill development with dynamically recommended paths aligned with role-based competency models.

### 2.3 Skill Evolution Over Time (Learning Curves)

The experiential memory hierarchy (Hu et al., 2025 -- "Memory in the Age of AI Agents") proposes three stages of memory evolution that map directly to skill development:

1. **Storage** (trajectory preservation): Raw interaction logs -- analogous to novice behavior where every step is recorded
2. **Reflection** (trajectory refinement): Identifying successful patterns -- analogous to intermediate skill where heuristics are forming
3. **Experience** (trajectory abstraction): Compressed procedural knowledge -- analogous to expert skill where actions are automated

**MACLA's Bayesian selection** provides a concrete mechanism for modeling this progression: procedures are retained, refined, or deprecated based on their success rate across applications, implementing a natural learning curve where frequently successful patterns are strengthened and failing patterns are forgotten.

### 2.4 Relevance to User Personalization

For our context-graph system, user skill modeling could be represented as:

```
(:User)-[:HAS_SKILL {
  proficiency: FLOAT,        // 0.0 to 1.0 (derived from knowledge tracing)
  confidence: FLOAT,         // confidence in the proficiency estimate
  last_assessed_at: DATETIME,
  assessment_count: INTEGER,
  source: STRING             // "observed" | "declared" | "inferred"
}]->(:Skill {
  skill_id: STRING,
  name: STRING,
  category: STRING,
  parent_skill_id: STRING    // skill taxonomy hierarchy
})
```

This enables adaptive agent behavior: agents can adjust their assistance level based on the user's observed proficiency with specific tools, workflows, or domains.

---

## 3. User-Centric Knowledge Graph Architectures (Personal Knowledge Graphs)

### 3.1 PKG Definition and Ecosystem

The foundational work on Personal Knowledge Graphs is the Balog et al. survey and roadmap (2024, published in AI Open journal). Their definition:

> A personal knowledge graph (PKG) is a knowledge graph (KG) where a single individual, called the owner of the PKG, has full read and write access to the KG, and the exclusive right to grant others read and write access to any specified part of the KG.

The PKG ecosystem framework identifies three core challenges:

1. **Population**: How to populate the PKG from heterogeneous data sources (conversations, documents, browsing history, tool usage)
2. **Representation and Management**: How to represent personal knowledge (RDF-based vocabulary with provenance and access rights)
3. **Utilization**: How to use PKGs for downstream tasks (conversational agents, recommender systems, personal assistants)

**PKG API (2024)**: A practical implementation providing:
- A user-facing PKG Client for administering personal data via natural language statements
- A service-oriented PKG API that external services can query
- An RDF-based PKG vocabulary supporting statements with properties for access rights and provenance

### 3.2 User Subgraph vs Separate User Graph Architecture

This is a critical architecture decision for our system. The research and industry practice reveal three patterns:

#### Pattern A: User Subgraph Within Shared Graph

The user's personal data lives as a subgraph within the same Neo4j database as the domain/system graph, connected via typed relationships.

```
(:User {user_id})-[:HAS_PREFERENCE]->(:Preference)
(:User)-[:HAS_SKILL]->(:Skill)
(:User)-[:PERFORMED]->(:Event)  // links to existing event nodes
```

**Pros**:
- Single query can traverse from user preferences to domain knowledge
- Entity resolution connects user concepts to system entities naturally
- Simpler operational model (one database)
- GraphRAG subgraph retrieval works seamlessly across user + domain data

**Cons**:
- Multi-tenant isolation requires careful access control (Row-Level Security analog in graph)
- User data deletion (GDPR) must traverse the entire graph
- Risk of "noisy neighbor" -- one user's dense subgraph affecting query performance

**Used by**: Meta (social knowledge graph), LinkedIn (Economic Graph), most recommendation systems

#### Pattern B: Separate User Graph Database

Each user (or tenant) gets their own graph database or a logically isolated partition.

**Pros**:
- Strong data isolation by default
- Simple GDPR deletion (drop the entire user graph)
- No cross-user interference

**Cons**:
- Cannot traverse from user graph to domain graph in a single query
- Higher operational cost (more database instances)
- Entity resolution between user graph and domain graph requires cross-database joins

**Used by**: Some healthcare systems, high-compliance environments

#### Pattern C: Hybrid -- User Subgraph with Namespace Isolation

The user's personal data uses a namespace prefix on node labels and properties, enabling logical isolation within a shared graph.

```
(:User_123:User)-[:HAS_PREFERENCE]->(:User_123:Preference)
// or using a property-based approach:
(:Preference {owner_id: "user_123"})
```

**Pros**:
- Logical isolation with single-database simplicity
- Cypher queries can filter by owner_id efficiently (indexed property)
- Cross-domain traversal possible when authorized

**Cons**:
- Requires discipline in query construction (always include owner_id filter)
- Not a hard security boundary

### 3.3 Recommendation for Our System

**Pattern A (User Subgraph Within Shared Graph) is the recommended approach** for the context-graph system, for these reasons:

1. **Our graph is already per-session scoped**: Events are already tagged with `session_id` and `agent_id`. Adding `user_id` as another scoping dimension follows the same pattern.
2. **Cross-domain traversal is essential**: The entire value proposition of the context graph is connecting agent actions (domain) to user context (personal). Separate databases would defeat this purpose.
3. **PROV-O alignment**: User preferences and behaviors are `prov:Entity` instances attributed to `prov:Agent` (the user). They naturally belong in the same provenance graph as events.
4. **ADR-0009 entity nodes already support this**: The existing `:Entity` node type with `entity_type = "user"` provides the anchor point for user subgraphs. User preferences, skills, and behavioral patterns would be additional node types connected to the user entity.
5. **Access control via projection**: Since Neo4j is a derived projection (ADR-0003), user-specific data can be filtered at the projection layer. The projection worker can enforce user-scoped access by only projecting data the requesting agent is authorized to see.

### 3.4 Memoria Framework -- Production-Viable Pattern

Memoria (2025) provides the most directly applicable architecture for our system. It integrates:

1. **Dynamic session-level summarization**: Compresses ongoing conversations into session summaries (maps to our Summary nodes via SUMMARIZES edges)
2. **Weighted knowledge graph user modeling**: Incrementally captures user traits, preferences, and behavioral patterns as structured entities and relationships
3. **Exponential Weighted Average for conflict resolution**: When new observations conflict with existing user model entries, EWA balances recency vs historical weight
4. **Plug-and-play integration**: Designed to work with existing LLM systems without architectural changes

Results: 87.1% accuracy on personalization benchmarks, 38.7% latency reduction, reduced token usage. The hybrid architecture enables both short-term dialogue coherence and long-term personalization.

### 3.5 Mem0 -- Production-Ready Memory Layer

Mem0 (ECAI 2025) is the most production-tested memory system for AI agents:

- **Core approach**: Dynamically extracts, consolidates, and retrieves salient information from conversations through dedicated memory extraction and update modules
- **Graph memory variant**: Uses graph-based memory representations to capture complex relational structures among conversational elements
- **Results**: 26% improvement in LLM-as-a-Judge metric over OpenAI, 91% lower p95 latency, 90%+ token cost savings
- **Key insight**: Graph memory achieves ~2% higher scores than flat memory, confirming that relational structure matters for personalization

Mem0's architecture validates our multi-graph approach (ADR-0009): user knowledge benefits from the same typed-edge decomposition (temporal, causal, semantic, entity) that we use for agent events.

---

## 4. Derived vs Explicit User Data

### 4.1 The Explicit/Implicit/Intentional-Implicit Trichotomy

The traditional binary model of user feedback (explicit vs implicit) has been superseded by a trichotomy identified at CHI 2025:

| Category | Definition | Examples | Confidence |
|----------|-----------|----------|------------|
| **Explicit** | Direct input expressing preferences | Ratings, keyword specifications, stated preferences | High (user stated it) |
| **Implicit (Unintentional)** | System infers from behavior without user awareness | Dwell time, scroll depth, click patterns | Medium (inferred) |
| **Implicit (Intentional)** | User consciously employs behaviors to shape system output | Deliberately liking content to train recommendations, strategic tool selection | High (user intended it, but expressed indirectly) |

The "intentional implicit" category is particularly relevant for AI agent interactions: users may deliberately choose certain tools or workflows to teach the agent their preferences, without explicitly stating a preference. Our ontology must capture this distinction.

### 4.2 Knowledge Graph Integration for Preference Modeling

Recent KG-augmented recommendation research (2025) demonstrates two complementary approaches:

**Explicit preference extraction**: Instruction-tuned LLMs extract explicit mentions of preferences from conversation ("I prefer Python over JavaScript") and store them as structured preference nodes.

**Implicit preference inference**: KG-augmented context enables inference of implicit interests. For example, if a user consistently uses `tool.execute` events targeting database operations, the system can infer a "database administration" interest without the user stating it.

**Graph Convolutional Networks with User Preferences (KGCN-UP, 2025)**: Predicts user-item interactions based on user preferences and item relationships within a knowledge graph. The model captures complex multi-relational structures, providing a template for how our REFERENCES edges could be weighted by user preference signals.

### 4.3 Confidence Models for Derived Data

A key requirement is tracking confidence in derived user knowledge. Research suggests a multi-dimensional confidence model:

```
(:UserPreference {
  preference_id: STRING,
  category: STRING,
  value: STRING,

  // Source tracking
  source_type: STRING,       // "explicit" | "implicit_unintentional" | "implicit_intentional" | "inferred"

  // Confidence dimensions
  confidence: FLOAT,          // 0.0 to 1.0 overall confidence
  observation_count: INTEGER,  // number of supporting observations
  last_observed_at: DATETIME,
  first_observed_at: DATETIME,

  // Decay-aware
  decay_score: FLOAT,         // Ebbinghaus decay (ADR-0008)
  reinforcement_count: INTEGER // times preference was re-confirmed
})
```

**Provenance chain**: Each UserPreference node MUST be traceable back to source events via edges:

```
(:UserPreference)-[:DERIVED_FROM {
  derivation_method: STRING,  // "stated" | "frequency_analysis" | "llm_inference" | "pattern_match"
  derived_at: DATETIME
}]->(:Event)
```

This aligns with our traceability-first principle (ADR-0001) -- every piece of user knowledge has provenance back to the source events that generated it.

### 4.4 Conflict Resolution Between Explicit and Derived Data

When derived preferences conflict with explicit statements, the resolution strategy should be:

1. **Explicit always wins**: If the user explicitly states a preference, it overrides any derived preference
2. **Intentional implicit > unintentional implicit**: Deliberate behavior signals are weighted higher than passive observations
3. **Recency weighting**: More recent observations are weighted higher (using the Ebbinghaus decay from ADR-0008)
4. **Observation count**: Preferences supported by many observations are more confident than those from single events
5. **Memoria's EWA approach**: Exponential Weighted Average provides a principled way to balance these factors

---

## 5. Multi-Agent User Modeling

### 5.1 Agent-Specific vs Shared User Models

When multiple agents serve the same user (our core multi-agent scenario), user knowledge must be partitioned:

**Agent-specific knowledge**: Tool preferences, workflow patterns, and procedural memory that are specific to one agent's domain. Example: Agent A knows the user prefers SQL over Python for data queries.

**Shared user knowledge**: Core user profile, general preferences, skill levels, and behavioral patterns that are relevant across all agents. Example: The user's timezone, communication style, and technical proficiency level.

**Cross-agent behavioral aggregation**: Patterns that emerge only when viewing the user's behavior across multiple agents. Example: The user tends to delegate complex tasks to Agent B but handles simple tasks with Agent A, revealing a trust/delegation pattern.

### 5.2 LEGOMem's Multi-Agent Memory Architecture

LEGOMem (Microsoft, AAMAS 2026) provides the most directly applicable pattern for multi-agent user modeling:

```
Orchestrator Memory (shared):
  - Full-task memories: task-level plans, reasoning traces
  - User profile: preferences, skills, behavioral patterns
  - Cross-agent coordination history

Agent Memory (per-agent):
  - Subtask memories: agent-specific behavior, tool interactions
  - Agent-specific user preferences (tool choice, style)
  - Procedural memory for the agent's domain
```

Key finding from their experiments: "orchestrator memory is critical for effective task decomposition and delegation, while fine-grained agent memory improves execution accuracy." This validates a layered architecture where shared user knowledge informs task routing, while agent-specific knowledge improves individual execution.

### 5.3 AGENTiGraph -- Multi-Agent Knowledge Graph Framework

AGENTiGraph (CIKM 2025) provides a suite of functionalities including relation judgment, prerequisite prediction, path searching for personalized learning paths, concept clustering, subgraph completion, and idea generation -- all operating on a shared knowledge graph accessed by multiple specialized agents. This confirms the user subgraph within shared graph pattern (Pattern A from Section 3.2).

### 5.4 Proposed Multi-Agent User Knowledge Architecture

For the context-graph system, we propose a three-layer user knowledge model:

```
Layer 1: Core User Profile (shared across all agents)
  (:User)-[:HAS_PROFILE]->(:UserProfile {
    timezone, language, communication_style,
    technical_level, domain_expertise
  })
  (:User)-[:HAS_PREFERENCE {scope: "global"}]->(:Preference)
  (:User)-[:HAS_SKILL]->(:Skill)

Layer 2: Agent-Specific User Context (per agent)
  (:User)-[:HAS_AGENT_CONTEXT {agent_id: STRING}]->(:AgentContext {
    preferred_tools: LIST<STRING>,
    workflow_style: STRING,
    interaction_history_summary: STRING,
    trust_level: FLOAT
  })
  (:User)-[:HAS_PREFERENCE {scope: "agent", agent_id: STRING}]->(:Preference)

Layer 3: Cross-Agent Behavioral Patterns (derived)
  (:User)-[:EXHIBITS_PATTERN]->(:BehavioralPattern {
    pattern_type: STRING,    // "delegation" | "escalation" | "routine" | "avoidance"
    description: STRING,
    confidence: FLOAT,
    observation_count: INTEGER,
    involved_agents: LIST<STRING>
  })
```

Layer 1 is populated from explicit user statements and high-confidence cross-session observations. Layer 2 is populated by individual agents from their interaction histories. Layer 3 is derived by the projection worker during re-consolidation (Stage 3) by analyzing patterns across agents.

---

## 6. Synthesis: Proposed User Personalization Graph Schema

### 6.1 New Node Types

Based on the research, the following node types should be added to the ADR-0009 schema:

```
CREATE NODE TYPE UserProfile (
  user_id         STRING NOT NULL,
  display_name    STRING,
  timezone        STRING,
  language        STRING,
  technical_level STRING,      // "novice" | "intermediate" | "expert"
  created_at      ZONED DATETIME NOT NULL,
  updated_at      ZONED DATETIME NOT NULL
)

CREATE NODE TYPE Preference (
  preference_id   STRING NOT NULL,
  category        STRING NOT NULL,       // "tool" | "workflow" | "communication" | "domain"
  key             STRING NOT NULL,
  value           STRING NOT NULL,
  source_type     STRING NOT NULL,       // "explicit" | "implicit_unintentional" | "implicit_intentional" | "inferred"
  confidence      FLOAT NOT NULL,
  scope           STRING NOT NULL,       // "global" | "agent" | "session"
  scope_id        STRING,               // agent_id or session_id when scope != "global"
  observation_count INTEGER DEFAULT 1,
  first_observed_at ZONED DATETIME NOT NULL,
  last_observed_at  ZONED DATETIME NOT NULL
)

CREATE NODE TYPE Skill (
  skill_id        STRING NOT NULL,
  name            STRING NOT NULL,
  category        STRING NOT NULL,
  parent_skill_id STRING,
  description     STRING
)

CREATE NODE TYPE Workflow (
  workflow_id         STRING NOT NULL,
  name                STRING NOT NULL,
  abstraction_level   STRING NOT NULL,   // "case" | "strategy" | "skill"
  success_rate        FLOAT,
  execution_count     INTEGER DEFAULT 1,
  avg_duration_ms     INTEGER,
  source_session_ids  LIST<STRING>,
  embedding           LIST<FLOAT>
)

CREATE NODE TYPE BehavioralPattern (
  pattern_id        STRING NOT NULL,
  pattern_type      STRING NOT NULL,     // "delegation" | "escalation" | "routine" | "avoidance"
  description       STRING NOT NULL,
  confidence        FLOAT NOT NULL,
  observation_count INTEGER DEFAULT 1,
  involved_agents   LIST<STRING>,
  first_detected_at ZONED DATETIME NOT NULL,
  last_confirmed_at ZONED DATETIME NOT NULL
)
```

### 6.2 New Edge Types

```
CREATE EDGE TYPE HAS_PROFILE ()
  FROM Entity TO UserProfile            // Entity where entity_type = "user"

CREATE EDGE TYPE HAS_PREFERENCE (
  scope    STRING NOT NULL,
  scope_id STRING
) FROM Entity TO Preference

CREATE EDGE TYPE HAS_SKILL (
  proficiency      FLOAT NOT NULL,
  confidence       FLOAT NOT NULL,
  last_assessed_at ZONED DATETIME,
  assessment_count INTEGER DEFAULT 1,
  source           STRING NOT NULL      // "observed" | "declared" | "inferred"
) FROM Entity TO Skill

CREATE EDGE TYPE DERIVED_FROM (
  derivation_method STRING NOT NULL,    // "stated" | "frequency_analysis" | "llm_inference" | "pattern_match"
  derived_at        ZONED DATETIME NOT NULL
) FROM Preference TO Event
  | FROM BehavioralPattern TO Event
  | FROM Skill TO Event

CREATE EDGE TYPE EXHIBITS_PATTERN ()
  FROM Entity TO BehavioralPattern

CREATE EDGE TYPE HAS_STEP (
  ordinal INTEGER NOT NULL
) FROM Workflow TO Event                // Step references the original event that formed this step

CREATE EDGE TYPE NEXT_STEP (
  condition STRING
) FROM Event TO Event                   // Within workflow context

CREATE EDGE TYPE ABSTRACTED_FROM ()
  FROM Workflow TO Workflow              // case -> strategy -> skill chain

CREATE EDGE TYPE PARENT_SKILL ()
  FROM Skill TO Skill                   // skill taxonomy hierarchy
```

### 6.3 New Graph Views (extending ADR-0009)

The multi-view formalism from ADR-0011 should be extended with a user personalization view:

| View | Notation | Nodes | Edges | Query Focus |
|------|----------|-------|-------|-------------|
| User Profile | `V_user` | Entity (user), UserProfile, Preference, Skill | HAS_PROFILE, HAS_PREFERENCE, HAS_SKILL | "What does the system know about this user?" |
| Behavioral | `V_behavioral` | Entity (user), BehavioralPattern, Workflow | EXHIBITS_PATTERN, ABSTRACTED_FROM | "How does this user typically work?" |
| Provenance | `V_provenance` | Preference, BehavioralPattern, Event | DERIVED_FROM | "Why does the system believe this about the user?" |

### 6.4 Intent-Aware Retrieval Extension

The intent weight matrix (ADR-0009) should be extended for user-personalization queries:

```python
INTENT_WEIGHTS = {
    # ... existing intents ...
    "who_is":  {CAUSED_BY: 1.0, FOLLOWS: 0.5, SIMILAR_TO: 1.0, REFERENCES: 3.0,
                HAS_PREFERENCE: 5.0, HAS_SKILL: 5.0, EXHIBITS_PATTERN: 4.0},
    "how_does": {CAUSED_BY: 2.0, FOLLOWS: 3.0, SIMILAR_TO: 1.0, REFERENCES: 2.0,
                 HAS_PREFERENCE: 2.0, HAS_SKILL: 3.0, EXHIBITS_PATTERN: 5.0},
}
```

### 6.5 PROV-O Grounding for New Edge Types

Following ADR-0011's dual-vocabulary approach:

| Operational Edge | PROV-O Grounding | Notes |
|-----------------|------------------|-------|
| `HAS_PREFERENCE` | `prov:wasAttributedTo` (inverse) | Preference is attributed to the user agent |
| `HAS_SKILL` | No PROV-O equivalent | `cg:hasSkill` -- custom extension |
| `DERIVED_FROM` | `prov:wasDerivedFrom` | Correct usage -- preferences are derived from events |
| `EXHIBITS_PATTERN` | No PROV-O equivalent | `cg:exhibitsPattern` -- custom extension |
| `ABSTRACTED_FROM` | `prov:wasDerivedFrom` | Workflow abstraction is a form of derivation |

---

## 7. Connection to Cognitive Memory Tiers (ADR-0007)

### 7.1 User Knowledge Across Memory Tiers

| Tier | User Knowledge Stored | Example |
|------|----------------------|---------|
| Sensory | Raw user interaction signals | Keystroke timing, mouse movement patterns (not stored) |
| Working | Current session user context | "User prefers verbose output in this session" |
| Episodic | Individual user interaction events | "User selected Python tool at 10:30 AM on 2026-02-11" |
| Semantic | Derived user knowledge graph | "User has expert-level Python skills (confidence: 0.92)" |
| Procedural | User's learned workflows | "User's data analysis routine: load CSV -> clean -> visualize -> export" |

### 7.2 Consolidation Path for User Knowledge

```
User interaction event (episodic, Redis)
  -> Projection worker extracts user-related entities (Stage 1)
  -> Enrichment derives preferences from behavior patterns (Stage 2)
  -> Re-consolidation discovers cross-session user patterns (Stage 3)
  -> Procedural memory extraction identifies user workflows (future Stage 4)
```

This consolidation path means user knowledge is **entirely derived from the immutable event ledger**, maintaining our traceability-first principle. No user knowledge exists in Neo4j that cannot be traced back to source events in Redis.

---

## 8. Privacy and Data Ownership Considerations

### 8.1 PKG Data Ownership Model

Following Balog et al.'s PKG definition, the user MUST be the owner of their personal knowledge graph with:
- **Full read access**: User can inspect all knowledge the system holds about them
- **Full write access**: User can correct, update, or delete their personal knowledge
- **Access control**: User can grant or revoke agent access to specific parts of their PKG

### 8.2 Right to Erasure

Since our Neo4j graph is a derived projection (ADR-0003), user data deletion follows a two-phase approach:
1. **Mark events as erased in Redis** (using the Forgettable Payloads pattern from ADR-0004)
2. **Re-project**: The projection worker rebuilds the graph without the erased events, naturally removing all derived user knowledge

This is a significant advantage of our architecture -- user data deletion does not require complex graph traversal to find and delete all derived knowledge. Re-projection handles it automatically.

### 8.3 Derived Data Transparency

Every derived preference, skill assessment, and behavioral pattern MUST include:
- `source_type` indicating how the knowledge was obtained
- `DERIVED_FROM` edges linking to source events
- `confidence` score indicating certainty
- API endpoint for users to contest or correct derived knowledge

---

## 9. Research References

### Personal Knowledge Graphs
- Skjaeveland, Balog et al. (2024). "An Ecosystem for Personal Knowledge Graphs: A Survey and Research Roadmap." AI Open. [arXiv:2304.09572](https://arxiv.org/abs/2304.09572)
- Chakraborty et al. (2023). "A Comprehensive Survey of Personal Knowledge Graphs." WIREs Data Mining and Knowledge Discovery. [Wiley](https://wires.onlinelibrary.wiley.com/doi/abs/10.1002/widm.1513)
- Bernard et al. (2024). "PKG API: A Tool for Personal Knowledge Graph Management." WWW 2024 Companion. [arXiv:2402.07540](https://arxiv.org/html/2402.07540v1)

### Procedural Memory and Workflow Extraction
- Xu et al. (2025). "MemP: Exploring Agent Procedural Memory." [arXiv:2508.06433](https://arxiv.org/abs/2508.06433)
- Microsoft (2025). "LEGOMem: Modular Procedural Memory for Multi-agent LLM Systems for Workflow Automation." AAMAS 2026. [arXiv:2510.04851](https://arxiv.org/abs/2510.04851)
- Wu et al. (2025). "Learning Hierarchical Procedural Memory for LLM Agents through Bayesian Selection and Contrastive Refinement (MACLA)." [arXiv:2512.18950](https://arxiv.org/html/2512.18950v1)
- Li et al. (2025). "Synthesizing Procedural Memory: Challenges and Architectures in Automated Workflow Generation." [arXiv:2512.20278](https://arxiv.org/html/2512.20278)
- Liu et al. (2025). "A Benchmark for Procedural Memory Retrieval in Language Agents." [arXiv:2511.21730](https://arxiv.org/html/2511.21730v1)

### Memory Frameworks for Personalization
- Khant et al. (2025). "Memoria: A Scalable Agentic Memory Framework for Personalized Conversational AI." [arXiv:2512.12686](https://arxiv.org/abs/2512.12686)
- Chhikara et al. (2025). "Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory." ECAI. [arXiv:2504.19413](https://arxiv.org/abs/2504.19413)

### Multi-Agent Systems
- Jiang et al. (2026). "MAGMA: A Multi-Graph based Agentic Memory Architecture for AI Agents." [arXiv:2601.03236](https://arxiv.org/abs/2601.03236)
- AGENTiGraph (CIKM 2025). "A Multi-Agent Knowledge Graph Framework for Interactive, Domain-Specific LLM Chatbots." [ACM DL](https://dl.acm.org/doi/10.1145/3746252.3761459)

### Behavior Pattern Detection
- IJCAI 2025. "A Survey on Temporal Interaction Graph Representation Learning." [IJCAI](https://www.ijcai.org/proceedings/2025/1166.pdf)
- GraphRPM (2024). "Risk Pattern Mining on Industrial Large Attributed Graphs." [arXiv:2411.06878](https://arxiv.org/html/2411.06878)

### Knowledge Tracing and Skill Modeling
- (2025). "Deep knowledge tracing and cognitive load estimation for personalized learning path generation using neural network architecture." Scientific Reports. [Nature](https://www.nature.com/articles/s41598-025-10497-x)
- (2025). "Knowledge graph construction and talent competency prediction for human resource management." Ain Shams Engineering Journal. [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1110016825002194)
- Neo4j (2025). "Discovering Hidden Skills with an Enterprise Knowledge Graph." [Neo4j Blog](https://neo4j.com/blog/discovering-hidden-skills-enterprise-knowledge-graph/)

### User Preference Modeling
- (2025). "Beyond Explicit and Implicit: How Users Provide Feedback to Shape Personalized Recommendation Content." CHI 2025. [arXiv:2502.09869](https://arxiv.org/html/2502.09869v1)
- (2025). "Reasoning over User Preferences: Knowledge Graph-Augmented LLMs for Explainable Conversational Recommendations." [arXiv:2411.14459](https://arxiv.org/html/2411.14459)
- (2025). "Knowledge graph convolutional networks with user preferences for course recommendation." Scientific Reports. [Nature](https://www.nature.com/articles/s41598-025-14150-5)

### Experiential Memory Hierarchy
- Hu et al. (2025). "Memory in the Age of AI Agents: A Survey." [arXiv:2512.13564](https://arxiv.org/abs/2512.13564)
- Huang et al. (2026). "Rethinking Memory Mechanisms of Foundation Agents." [arXiv:2602.06052](https://arxiv.org/abs/2602.06052)
- (2025). "HiAgent: Hierarchical Working Memory Management for Solving Long-Horizon Agent Tasks." ACL 2025. [ACL Anthology](https://aclanthology.org/2025.acl-long.1575.pdf)

### Multi-Tenant Graph Architecture
- Memgraph (2025). "Multi-Tenancy in Graph Databases and Why Should You Care?" [Memgraph Blog](https://memgraph.com/blog/why-multi-tenancy-matters-in-graph-databases)
