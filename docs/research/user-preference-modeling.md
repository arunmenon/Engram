# User Preference and Interest Modeling Patterns

**Research Task**: Deep dive into how existing systems model user preferences, interests, and personalization in knowledge graphs.

**Date**: 2026-02-12
**Researcher**: researcher-2
**Context**: Informing ADR-0012 (User Personalization Ontology Extension) for the context-graph project

---

## 1. Preference Representation

### 1.1 Core Properties of a Preference

Research across recommendation systems, conversational AI memory, and ontology-based user modeling converges on a common set of properties that a well-structured preference must carry:

| Property | Description | Source/Precedent |
|----------|-------------|------------------|
| **strength/weight** | Numeric intensity of the preference (0.0-1.0 or 1-10 scale) | KGCN-UP (Nature 2025), Memoria (arXiv 2512.12686), Park et al. (2023) |
| **polarity** | Direction: positive, negative, or neutral | Rating-Aware Homogeneous Review Graphs (SIGIR 2025), ontology-based preference models |
| **confidence** | Certainty of the system's belief in this preference | Ontology-Based Management of Uncertain Preferences (Springer 2012), Zep entity resolution |
| **source** | How the preference was acquired: `explicit` (user stated), `inferred` (derived from behavior), `observed` (extracted from interaction pattern) | Jannach (2018) explicit/implicit feedback taxonomy, Memoria KG extraction |
| **context** | Scope/condition under which the preference applies (e.g., "prefer X for task Y but not Z") | Context-dependent preference models, POPI (arXiv 2510.17881), PrefPalette (arXiv 2507.13541) |
| **category** | Domain/topic classification of the preference | Zep Preference entity type (built-in `category` field) |
| **occurred_at / created_at** | When the preference was first expressed or inferred | Graphiti bi-temporal model, Memoria timestamp metadata |
| **last_confirmed_at** | When the preference was last reinforced | Ebbinghaus stability model (ADR-0008), Park et al. access reinforcement |
| **superseded_by** | Reference to a newer preference that replaces this one | A-MEM bidirectional evolution (Xu et al., 2025), Mem0 conflict detection |

### 1.2 Preference as Node vs. Preference as Edge

Two dominant patterns exist in the literature and production systems:

**Pattern A: Preference as a Node (Entity)**
- Used by: Zep/Graphiti, Memoria, schema.org-influenced models
- Structure: `(User)-[HAS_PREFERENCE]->(Preference)-[ABOUT]->(Entity)`
- Advantages: Rich property storage on the preference node, queryable by category, supports temporal versioning
- Example (Zep): Preference is a first-class entity type with `category`, `description`, `summary`, `created_at` properties. Users query preferences via `node_labels=["Preference"]`

**Pattern B: Preference as a Weighted Edge**
- Used by: KGCN-UP, traditional recommendation KGs, Mem0 graph memory
- Structure: `(User)-[PREFERS {weight: 0.8, polarity: "positive"}]->(Entity)`
- Advantages: Direct traversal, simpler schema, natural for graph algorithms (PageRank, GNN propagation)
- Example (Mem0): Directed labeled triplets like `"Alice" --prefers--> "dark roast coffee"`

**Recommendation for context-graph**: Pattern A (Preference as Node) is the better fit because:
1. Our architecture already uses property-rich nodes (Event, Entity, Summary per ADR-0011)
2. Preferences need provenance back to source events (traceability-first principle)
3. The node pattern naturally supports temporal versioning and decay scoring
4. Zep/Graphiti -- the closest production analog to our system -- uses this pattern

### 1.3 Explicit vs. Implicit Preference Signals

The literature distinguishes two primary signal types (Jannach 2018, ACM TIST 2014):

| Signal Type | Examples | Confidence | Volume |
|-------------|----------|------------|--------|
| **Explicit** | User states "I prefer Python", rates item 5/5, selects option | High (0.8-1.0) | Low (sparse) |
| **Implicit** | User repeatedly uses tool X, clicks on topic Y, spends time on Z | Medium (0.4-0.7) | High (abundant) |
| **Inferred** | System derives preference from ontology structure (interested in ML implies interested in AI) | Low-Medium (0.3-0.6) | Variable |

For our system, explicit preferences come from user statements captured in event payloads. Implicit preferences emerge from behavioral patterns in the event stream (tool usage frequency, topic co-occurrence). Inferred preferences propagate through the entity hierarchy.

### 1.4 Context-Dependent Preferences

PrefPalette (arXiv 2507.13541) and POPI (arXiv 2510.17881) demonstrate that preferences are not monolithic -- they depend on context:

- **Task context**: "Prefer concise responses for code review, detailed responses for architecture discussion"
- **Temporal context**: "Prefer dark mode in evening, light mode in morning"
- **Tool context**: "Prefer Python for data analysis, Rust for systems programming"

This maps to a **qualified preference** pattern where the preference node carries a `context` property (or links to a context entity via `IN_CONTEXT` edge). This parallels PROV-O's qualification pattern already adopted in ADR-0011.

---

## 2. Interest Modeling

### 2.1 Topic-Based Interest Models

The dominant pattern in recommendation systems is a weighted user-topic relationship:

```
(User)-[INTERESTED_IN {weight: 0.7, last_updated: ...}]->(Topic)
```

Key research patterns:

- **KGCN-UP** (Nature 2025): Propagates user preferences through relational chains in a knowledge graph, refining interest representations by exploring multi-hop paths
- **RKGnet** (Nature 2025): Uses reinforcement learning to dynamically iterate user preferences within KGs, uncovering hierarchical latent interests
- **Multi-View KG** (IJCAI 2025): Captures user preferences through GNN-based multi-view fusion across semantic, structural, and temporal views

### 2.2 Hierarchical Interest Propagation

A critical pattern for our system: interests propagate up and down ontological hierarchies.

```
(User)-[INTERESTED_IN]->(Machine Learning)
    (Machine Learning)-[IS_A]->(Artificial Intelligence)
    (Machine Learning)-[HAS_SUBTOPIC]->(Deep Learning)
```

When a user shows interest in "Machine Learning", the system can infer:
- **Upward**: Partial interest in "Artificial Intelligence" (parent topic), with decayed weight
- **Downward**: Potential interest in "Deep Learning" (subtopic), with lower confidence

This maps directly to our existing entity hierarchy (ADR-0011 Section 3). ConceptEntity nodes already have type hierarchy potential. The propagation mechanism uses **spreading activation** (Crestani 1997, confirmed in modern ontology-based systems):

```
interest(parent) = alpha * max(interest(children))  # upward propagation
interest(child) = beta * interest(parent)             # downward propagation
```

Where `alpha` and `beta` are damping factors (typically 0.3-0.5).

### 2.3 Interest Decay and Reinforcement

This is where our ADR-0008 Ebbinghaus model directly applies to interest modeling:

| System | Decay Model | Reinforcement Mechanism |
|--------|-------------|------------------------|
| **Park et al. (2023)** | `recency = 0.995^hours` | Access count increments stability |
| **Memoria** | `w = e^(-a * x)` where a=0.02 | Recent triplets get higher weight in context |
| **MemoryBank** | `R = e^(-t/S)` with increasing S | Each successful recall increases stability S |
| **IFC (Music)** | Interest Forgetting Curve | Replay mechanism rekindles decayed interests |
| **TDTMF** | Non-linear temporal drift | Multi-period topic evolution tracking |
| **Our ADR-0008** | `score = e^(-t/S)`, S_base=168h | access_count increments, last_accessed_at update |

The convergence is striking: every major system uses exponential decay with access-based reinforcement. Our existing decay model (ADR-0008) is directly applicable to preference/interest nodes. The key insight is that **preferences are memories** and should follow the same retention lifecycle.

### 2.4 Long-Term vs. Short-Term Interests

Research distinguishes two temporal scales (Springer 2025, ScienceDirect 2024):

| Scale | Description | Modeling Pattern | Our Mapping |
|-------|-------------|------------------|-------------|
| **Long-term** | Stable preferences (language, editor, workflow style) | High stability S, slow decay | Semantic tier (Neo4j) |
| **Short-term** | Contextual interests (current project, active investigation) | Low stability S, fast decay | Episodic tier (Redis) → promoted if reinforced |

Multi-scale temporal hierarchical attention (ScienceDirect 2023) shows that treating all interests at a single time scale degrades recommendation quality. The hierarchical approach -- short-term interests feed into long-term interest evolution -- maps to our consolidation pipeline (Stage 1 captures short-term, Stage 3 discovers long-term patterns).

---

## 3. User-Entity Relationship Types

### 3.1 Relationship Taxonomy from Production Systems

Surveying recommendation KGs, conversational AI memory, and adaptive learning systems reveals a consistent set of user-entity edge types:

| Relationship | Description | Properties | Source |
|-------------|-------------|------------|--------|
| **PREFERS** | Active positive preference | weight, polarity, context, source | Mem0, Zep, recommendation KGs |
| **AVOIDS** | Active negative preference | weight, reason, context | Rating-aware review graphs, POPI |
| **INTERESTED_IN** | Topic/domain interest | weight, last_updated, source | KGCN-UP, FOAF `foaf:interest` |
| **USES** | Regular tool/resource usage | frequency, last_used, proficiency | Adaptive learning systems |
| **CREATED** | Authorship/production relationship | created_at | PROV-O `wasGeneratedBy` (inverse) |
| **KNOWS_ABOUT** | Knowledge/competency in a domain | proficiency_level (1-10), confidence | Competency ontologies (Springer 2021) |
| **BELONGS_TO** | Organizational/group membership | role, since | FOAF `foaf:member` |
| **SIMILAR_TO_USER** | User-user similarity | score, basis (shared preferences, behavior) | Collaborative filtering KGs |

### 3.2 Zep/Graphiti Built-in Entity Types (Production Reference)

Zep provides the most mature production implementation of user-centric graph memory:

**Default Entity Types:**
1. `User` -- singleton representing the human participant
2. `Assistant` -- singleton representing the AI agent
3. `Preference` -- user preferences, choices, opinions (prioritized classification)
4. `Location` -- physical/virtual places
5. `Event` -- time-bound activities
6. `Object` -- physical items, tools, devices
7. `Topic` -- subjects, knowledge domains
8. `Organization` -- companies, institutions
9. `Document` -- information content

**Default Edge Types:**
- `LOCATED_AT` -- entity exists at location
- `OCCURRED_AT` -- event happened at time/place

**Custom entity types** are defined as Pydantic models with domain-specific properties. Protected attribute names: `uuid`, `name`, `group_id`, `labels`, `created_at`, `summary`, `attributes`, `name_embedding`.

### 3.3 Mem0 Graph Memory Patterns

Mem0 uses directed labeled triplets with dynamic relationship types:

- Relationships are extracted by LLM from conversation: `lives_in`, `prefers`, `owns`, `happened_on`
- **Conflict Detection**: When new information contradicts existing graph edges, an LLM-powered Update Resolver decides: deprecate old, strengthen new, or merge
- Storage: Neo4j (or Memgraph/Neptune/Kuzu) for graph, vector DB for embeddings

### 3.4 Recommendation System KG Edge Types

Standard patterns from KG-based recommender systems:

```
(User)-[RATED {score: 4.5}]->(Item)
(User)-[PURCHASED {date: ...}]->(Item)
(User)-[VIEWED {count: 3, last: ...}]->(Item)
(Item)-[BELONGS_TO]->(Category)
(Item)-[HAS_ATTRIBUTE]->(Attribute)
(Category)-[IS_SUBCATEGORY_OF]->(Category)
```

### 3.5 Adaptive Learning / Competency Models

Competency ontologies (Springer 2021, ResearchGate) define user-skill relationships with rich metadata:

```
(User)-[HAS_COMPETENCY]->(Skill)
  Properties:
    - performance_level: A(awareness), B(familiarization), C(productivity), D(expertise)
    - or numeric scale: 1-10
    - frequency, scope, autonomy, complexity indicators
    - last_assessed_at
```

This pattern is relevant for modeling agent users' skill levels with tools, topics, and workflows.

### 3.6 Mapping to Our Architecture

Our existing entity types (ADR-0011): `agent`, `user`, `service`, `tool`, `resource`, `concept`

Proposed new relationship types for user personalization:

| New Edge Type | Endpoints | Properties | Maps to ADR-0011 |
|--------------|-----------|------------|-------------------|
| `HAS_PREFERENCE` | User → Preference (new node type) | - | Extension to REFERENCES |
| `INTERESTED_IN` | User → Concept | weight, source, last_updated | Specialization of REFERENCES with role |
| `PREFERS_TOOL` | User → Tool | weight, context, source | Specialization of REFERENCES with role |
| `AVOIDS` | User → Entity (any) | weight, reason, source | New edge type |
| `HAS_PROFICIENCY` | User → Concept/Tool | level (1-10), last_assessed | New edge type |

---

## 4. Cross-Session Identity

### 4.1 Identity Graph Patterns

Cross-session user identity is a solved problem in marketing/AdTech with direct applicability to our system:

**Identity Graph Architecture** (RudderStack, Aerospike, TigerGraph):
- Core concept: A persistent graph where user identifiers are nodes and identity links are edges
- Node types: `email`, `device_id`, `cookie`, `account_id`, `phone`
- Edge types: `SAME_PERSON` with confidence score and match type (deterministic, probabilistic)
- Resolution strategies: deterministic (exact match on email/phone) vs. probabilistic (behavioral similarity)

**Our ADR-0011 already defines this pattern:**
- `SAME_AS` edge between Entity nodes with `confidence` and `justification` properties
- Three-tier resolution: Exact match (1.0), Close match (>0.9), Related match (variable)
- The identity graph pattern from industry validates our approach

### 4.2 How Zep Handles Cross-Session Identity

Zep's approach to cross-session identity:
- Each user has a `user_id` that persists across sessions
- The knowledge graph accumulates facts and preferences tied to this user identity
- Bi-temporal model tracks both event occurrence time and ingestion time
- Graph edges include validity intervals for temporal reasoning
- `group_id` enables shared context across users in the same organization

### 4.3 Memoria's Cross-Session Approach

Memoria (arXiv 2512.12686) handles cross-session identity through:
- Username-based triplet association
- Incremental KG construction: new session data connects to existing user nodes
- Conflict resolution when new statements contradict earlier ones
- Recency-weighted retrieval ensures current preferences take priority

### 4.4 Mapping to Our System

Our system has `session_id` and `agent_id` on every event (ADR-0004). For user personalization:

1. **User Entity Resolution**: When a new session starts, resolve the user entity against existing UserEntity nodes using the three-tier strategy (ADR-0011 Section 3)
2. **Preference Continuity**: Link preferences to the resolved UserEntity, not to the session. Sessions provide provenance (when/where the preference was expressed), but the preference belongs to the user
3. **Session-Scoped vs. User-Scoped Context**: The context API should distinguish:
   - Session context: events, tools, entities from the current session
   - User context: accumulated preferences, interests, proficiencies across all sessions

This is a critical architectural distinction. Our current REFERENCES edges connect Events to Entities. User preferences should connect **User entities** to other entities, persisting beyond any single session.

---

## 5. Privacy Considerations

### 5.1 GDPR Requirements for User Preference Data

User preferences constitute personal data under GDPR Article 4(1) when they can identify or relate to a natural person. Key requirements:

| GDPR Article | Requirement | Impact on Preference Storage |
|-------------|-------------|------------------------------|
| Art. 6 | Lawful basis for processing | Preference collection needs consent or legitimate interest |
| Art. 7 | Conditions for consent | Consent must be specific, informed, and withdrawable |
| Art. 13/14 | Information obligations | Users must know what preferences are stored and why |
| Art. 15 | Right of access | Users can request all stored preferences |
| Art. 16 | Right to rectification | Users can correct inaccurate preferences |
| Art. 17 | Right to erasure | Users can request deletion of all preference data |
| Art. 20 | Right to data portability | Preferences must be exportable in machine-readable format |
| Art. 25 | Data protection by design | Privacy must be built into the architecture |

### 5.2 Our Existing Privacy Mechanisms

ADR-0001 establishes **Forgettable Payloads** -- event payloads can be independently deleted while preserving the event envelope (metadata). This pattern extends naturally to preferences:

- **Preference Envelope**: The fact that a user has a preference of a certain type, its weight, and its provenance chain -- structural metadata that may be retained
- **Preference Payload**: The actual content of the preference (what the user prefers) -- forgettable data subject to erasure requests

### 5.3 Privacy-Preserving Preference Patterns

Research identifies several patterns applicable to graph-based preference storage:

**Pattern 1: Consent-Linked Preferences**
```
(User)-[HAS_PREFERENCE {consent_id: "...", consent_scope: "personalization"}]->(Preference)
```
Each preference edge carries a reference to the consent record that authorized its creation. When consent is withdrawn, all preferences linked to that consent are erasable.

**Pattern 2: Tiered Privacy Levels**
| Level | Data | Retention | Erasure Behavior |
|-------|------|-----------|------------------|
| **Anonymous** | Aggregated preference statistics | Indefinite | Not subject to individual erasure |
| **Pseudonymous** | Preferences linked to session_id (not user identity) | Session-scoped | Deleted with session |
| **Identified** | Preferences linked to resolved UserEntity | User-scoped | Deleted on erasure request |

**Pattern 3: Cascade Erasure in Graph Databases**
When a user exercises right to erasure, the system must:
1. Delete the UserEntity node
2. Cascade delete all `HAS_PREFERENCE`, `INTERESTED_IN`, `PREFERS_TOOL`, `HAS_PROFICIENCY` edges
3. Delete all Preference nodes exclusively owned by this user
4. Anonymize (not delete) edges in the event graph that reference this user -- replace user identity with tombstone
5. Propagate deletion to all downstream systems (GDPR Art. 19 notification requirement)

**Pattern 4: Privacy-Preserving Graph Techniques** (PMC 2025)
- **Differential privacy**: Add calibrated noise to preference weights before exposure
- **k-anonymity**: Ensure preference patterns cannot uniquely identify users
- **Graph perturbation**: Modify edge structure to prevent re-identification while preserving aggregate statistics

### 5.4 Mapping to Our Architecture

Our system's privacy story for user preferences:

1. **Forgettable Payloads (ADR-0001)**: Preference content is stored as a forgettable payload. The preference node in Neo4j carries structural metadata; the actual preference content can be independently erased
2. **Retention Tiers (ADR-0008)**: Preferences follow the same Hot/Warm/Cold/Archive lifecycle. Cold preferences (not accessed for 7-30 days) are candidates for summary-and-prune
3. **Consent Tracking**: Each preference creation event should carry a consent reference. The event ledger provides audit trail for when preferences were created and on what legal basis
4. **Erasure Endpoint**: A dedicated API endpoint to cascade-delete all data associated with a user identity, leveraging Neo4j's graph traversal to find all connected preference/interest nodes

### 5.5 GDPR-Specific Architectural Requirements

For ADR-0012, the following must be addressed:

1. **Data subject access**: API endpoint to export all preferences for a user in JSON-LD (machine-readable, portable)
2. **Preference provenance**: Every preference must trace back to the source event(s) that created it -- this is already our core design principle
3. **Consent withdrawal propagation**: When consent is withdrawn, all derived preference data (Neo4j projections) must be deleted, while the consent withdrawal event itself is retained in the event ledger as an audit record
4. **Purpose limitation**: Preferences collected for "personalization" cannot be repurposed for "analytics" without separate consent

---

## 6. Synthesis: Patterns Mapping to Our Architecture

### 6.1 Proposed Preference/Interest Node Type

Based on the research, a `Preference` node type for our system:

```
CREATE NODE TYPE Preference (
  preference_id    STRING NOT NULL,       -- UUID, primary key
  user_id          STRING NOT NULL,       -- FK to UserEntity
  category         STRING NOT NULL,       -- domain classification
  polarity         STRING NOT NULL,       -- "positive", "negative", "neutral"
  strength         FLOAT NOT NULL,        -- 0.0 to 1.0
  confidence       FLOAT NOT NULL,        -- 0.0 to 1.0
  source           STRING NOT NULL,       -- "explicit", "inferred", "observed"
  context          STRING,                -- optional scope qualifier
  created_at       ZONED DATETIME NOT NULL,
  last_confirmed_at ZONED DATETIME NOT NULL,
  access_count     INTEGER DEFAULT 0,     -- for decay reinforcement
  stability        FLOAT DEFAULT 168.0,   -- Ebbinghaus S factor (hours)
  superseded_by    STRING,                -- reference to replacing preference
  consent_ref      STRING                 -- reference to consent record
)
```

### 6.2 Proposed Edge Types

```
CREATE EDGE TYPE HAS_PREFERENCE ()
  FROM Entity (type=user) TO Preference

CREATE EDGE TYPE ABOUT ()
  FROM Preference TO Entity

CREATE EDGE TYPE INTERESTED_IN (
  weight    FLOAT NOT NULL,
  source    STRING NOT NULL,
  last_updated ZONED DATETIME NOT NULL
) FROM Entity (type=user) TO Entity (type=concept)

CREATE EDGE TYPE PREFERS_TOOL (
  weight    FLOAT NOT NULL,
  context   STRING,
  source    STRING NOT NULL
) FROM Entity (type=user) TO Entity (type=tool)

CREATE EDGE TYPE HAS_PROFICIENCY (
  level     INTEGER NOT NULL,   -- 1-10
  confidence FLOAT NOT NULL,
  last_assessed ZONED DATETIME NOT NULL
) FROM Entity (type=user) TO Entity (type=concept | type=tool)
```

### 6.3 Decay Model Integration

Preferences and interests should use the same decay scoring as events (ADR-0008):

```
score(pref, t_now) = w_r * recency(pref, t_now)
                   + w_s * pref.strength
                   + w_c * pref.confidence

recency(pref, t_now) = e^(-t_elapsed / pref.stability)
t_elapsed = hours since max(pref.created_at, pref.last_confirmed_at)
```

When a preference is confirmed (user restates it or behavior reinforces it):
- `last_confirmed_at` updates
- `stability` increases by `S_boost` (ADR-0008 pattern)
- `access_count` increments
- `confidence` may increase (especially for `inferred` → `observed` promotion)

### 6.4 Consolidation Pipeline Integration

| Stage | Preference Processing |
|-------|----------------------|
| **Stage 1** (Event Projection) | Extract explicit preferences from event payloads; create Preference nodes and HAS_PREFERENCE edges |
| **Stage 2** (Enrichment) | Infer implicit preferences from behavioral patterns (tool usage frequency, topic co-occurrence); compute interest weights |
| **Stage 3** (Re-Consolidation) | Discover cross-session preference patterns; merge/supersede conflicting preferences; propagate interests through hierarchy |

### 6.5 Context API Integration

The context API response should include a `user_context` section:

```json
{
  "nodes": { ... },
  "edges": [ ... ],
  "user_context": {
    "preferences": [
      {
        "id": "pref-123",
        "category": "coding_style",
        "polarity": "positive",
        "strength": 0.85,
        "about": "entity-456",
        "source": "explicit",
        "provenance": { "source_events": ["evt-789"], "created_at": "..." }
      }
    ],
    "interests": [
      {
        "topic": "entity-101",
        "weight": 0.7,
        "source": "observed"
      }
    ],
    "proficiencies": [
      {
        "entity": "entity-202",
        "level": 7,
        "confidence": 0.8
      }
    ]
  },
  "meta": { ... }
}
```

---

## 7. Key Research References

### Production Systems
- **Zep/Graphiti**: Temporal knowledge graph for agent memory with built-in Preference entity type. https://help.getzep.com/graphiti/core-concepts/custom-entity-and-edge-types
- **Mem0**: Graph memory for AI agents with directed labeled triplets. https://docs.mem0.ai/open-source/features/graph-memory
- **Memoria** (arXiv 2512.12686): Scalable agentic memory with weighted KG-based user modeling. https://arxiv.org/abs/2512.12686

### Preference Representation
- KGCN-UP: Knowledge Graph Convolutional Networks with User Preferences. https://www.nature.com/articles/s41598-025-14150-5
- Fine-Grained User Preference Learning. https://www.sciopen.com/article/10.26599/TST.2024.9010216
- Ontology-Based Management of Uncertain Preferences. https://link.springer.com/chapter/10.1007/978-3-642-31715-6_15
- Capturing Knowledge of User Preferences: Ontologies in Recommender Systems. https://arxiv.org/pdf/cs/0203011
- PrefPalette: Personalized Preference Modeling with Latent Attributes. https://arxiv.org/html/2507.13541
- POPI: Personalizing LLMs via Optimized Preference Inference. https://arxiv.org/html/2510.17881

### Interest Modeling and Temporal Evolution
- Hierarchical Long and Short-term User Preference Modeling. https://link.springer.com/article/10.1007/s11704-025-41181-y
- Multi-scale Temporal Hierarchical Attention for Sequential Recommendation. https://www.sciencedirect.com/science/article/abs/pii/S0020025523007119
- Capturing Dynamic User Preferences: Non-Linear Forgetting and Evolving Topics. https://www.mdpi.com/2079-8954/13/11/1034
- Incorporating Forgetting Curve and Memory Replay for Evolving Recommendation. https://www.sciencedirect.com/science/article/abs/pii/S0306457325000123
- TDTMF: Temporal Interest Drift and Topic Evolution. https://www.sciencedirect.com/science/article/abs/pii/S0306457322001467

### User-Entity Relationships
- Graph-native memory for conversational AI personalization. https://vertextlabs.com/graph-native-memory-conversational-ai-personalization/
- Knowledge Graph-Augmented LLMs for Conversational Recommendations. https://arxiv.org/html/2411.14459
- Competency Ontology for Learning Environments Personalization. https://slejournal.springeropen.com/articles/10.1186/s40561-021-00160-z
- FOAF Ontology. https://en.wikipedia.org/wiki/FOAF

### Cross-Session Identity
- Identity Resolution and Privacy Compliance with Identity Graphs. https://cdp.com/articles/how-to-implement-identity-resolution-and-privacy-compliance-with-an-identity-graph-in-a-cdp/
- What is an Identity Graph? https://www.rudderstack.com/blog/identity-graph/
- Zep Temporal Knowledge Graph Architecture. https://arxiv.org/abs/2501.13956

### Privacy
- Privacy-Preserving Graph Machine Learning Survey. https://pmc.ncbi.nlm.nih.gov/articles/PMC12056661/
- Privacy-Preserving Publishing of Knowledge Graphs. https://strict.dista.uninsubria.it/projects/privacy-preserving-publishing-of-knowledge-graphs/
- GDPR Article 17 Right to Erasure. https://gdpr-info.eu/art-17-gdpr/

### Recommendation System KGs
- Survey on Knowledge Graph-Based Recommender Systems. https://arxiv.org/abs/2003.00911
- Enhancing Knowledge Graph Recommendations through Deep RL. https://www.nature.com/articles/s41598-025-31109-8
- Recommending on Graphs: Comprehensive Review. https://link.springer.com/article/10.1007/s11257-023-09359-w

---

## 8. Summary of Key Findings for ADR-0012

1. **Preference as Node**: Model preferences as first-class nodes (not just weighted edges) to support provenance, temporal versioning, and decay. Zep and Memoria both validate this pattern in production.

2. **Decay applies to preferences**: The Ebbinghaus model from ADR-0008 directly applies. Preferences that are not reinforced should decay. Every major system uses exponential decay with access-based reinforcement.

3. **Source provenance is essential**: Every preference must carry its source (explicit/inferred/observed) and trace back to source events. This aligns with our traceability-first principle.

4. **Hierarchical interest propagation**: Interests propagate through concept hierarchies. Our existing ConceptEntity nodes can support this with spreading activation algorithms.

5. **Cross-session persistence**: Preferences belong to User entities, not sessions. Sessions provide provenance context, but the preference graph persists across sessions.

6. **Privacy by design**: User preferences are personal data. The Forgettable Payloads pattern (ADR-0001) extends naturally. Cascade erasure, consent tracking, and tiered privacy levels are required.

7. **Context-dependent preferences**: Preferences are not absolute -- they depend on task, temporal, and domain context. The qualified preference pattern (with context property) handles this.

8. **Consolidation pipeline integration**: Stage 1 extracts explicit preferences, Stage 2 infers implicit ones, Stage 3 discovers cross-session patterns. This extends ADR-0008 naturally.

9. **Zep/Graphiti is the closest production analog**: Their built-in Preference entity type, bi-temporal model, and custom entity/edge type system provide a validated reference architecture.

10. **Dual-scale interest modeling**: Long-term stable preferences (high stability S) vs. short-term contextual interests (low stability S) map to our semantic tier (Neo4j) vs. episodic tier (Redis) distinction.
