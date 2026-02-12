# ADR-0012: User Personalization Ontology Extension (cg-user Module)

Status: **Proposed**
Date: 2026-02-12
Extends: ADR-0007 (memory tiers), ADR-0008 (consolidation and decay), ADR-0009 (multi-graph schema), ADR-0011 (ontological foundation)

## Context

The context-graph system captures immutable events from AI agents, projects them into a Neo4j graph with five edge types and three node types (ADR-0009), grounded in a formal PROV-O profile with six ontology modules (ADR-0011: cg-core, cg-events, cg-entities, cg-memory, cg-views, cg-retention). The system currently models agents, tools, resources, services, and concepts -- but has no formal model for **user personalization**: who the user is, what they prefer, what skills they have, how they typically work, and how these evolve over time.

User personalization is essential for adaptive agent behavior. Without it, every agent interaction starts from zero -- the system cannot remember that a user prefers Python over JavaScript, works best with verbose explanations, or has expert-level database skills. The research consensus across production systems (Zep/Graphiti, Mem0, Memoria) and academic literature is clear: graph-based user modeling with provenance-backed preferences significantly improves agent personalization quality.

### Research Basis

Three research deliverables inform this decision:

1. **User Modeling Ontology Discovery** (Task #1): Cataloged 12 ontologies/standards across user modeling, preference representation, behavior classification, and cross-platform identity domains. Key findings: no single standard covers our needs; GUMO provides dimension taxonomy; UPOS provides situation-dependent preferences; schema.org provides interoperable identity; FOAF provides interest linking; PAV provides versioning. All lack provenance tracing -- our key differentiator.

2. **User Preference and Interest Modeling Patterns** (Task #2): Deep analysis of preference representation, interest modeling, cross-session identity, and privacy patterns. Key findings: preferences should be modeled as first-class nodes (not weighted edges) per Zep/Graphiti pattern; the Ebbinghaus decay model (ADR-0008) directly applies to preferences; every preference must carry source provenance (explicit/implicit/inferred); context-dependent preferences require qualification; GDPR compliance requires cascade erasure and consent tracking.

3. **User Behavior and Graph Architecture Patterns** (Task #3): Research across behavior pattern detection, skill/competency modeling, personal knowledge graphs (PKGs), derived vs explicit user data, and multi-agent user modeling. Key findings: the CHI 2025 explicit/implicit(intentional)/implicit(unintentional) trichotomy supersedes the binary model; procedural memory research (LEGOMem, MemP, MACLA) validates ADR-0007 Tier 5 design with concrete patterns; LEGOMem's three-layer multi-agent architecture (core profile / agent-specific / cross-agent patterns) provides the user knowledge partitioning model; Pattern A (user subgraph within shared graph) is the recommended architecture.

### Design Principles

This ADR follows the project's established design principles:

- **Traceability over memory**: Every preference, skill assessment, and behavioral pattern must trace back to source events via `DERIVED_FROM` edges
- **Immutable events**: User preferences are projections derived from the event ledger, not independently created state
- **Framework-agnostic**: The cg-user module defines domain types with zero framework dependencies
- **Custom ontology grounded in standards**: Design custom vocabulary optimized for our use case, with documented mappings to established standards (PROV-O, schema.org, FOAF, GUMO) where they fit

Non-goals for this decision:
- Implementing KG embedding-based preference propagation (future optimization)
- Real-time preference inference on the ingestion critical path
- User-to-user social relationship modeling (outside scope)
- Parametric personalization (fine-tuning agent weights from user data)

## Decision

The context-graph project MUST define a `cg-user` ontology module that extends the existing ontological foundation (ADR-0011) with user personalization types, preserving the dual-vocabulary approach (operational names for Neo4j traversal, PROV-O grounding for conceptual documentation).

### 1. New Node Types

Five new node types are added to the graph schema. All types follow the PG-Schema notation established in ADR-0011 Section 5.

#### 1.1 UserProfile

Represents the persistent, cross-session profile of a user. One UserProfile per resolved user identity.

```
CREATE NODE TYPE UserProfile (
  profile_id       STRING NOT NULL,        -- UUID, primary key
  user_id          STRING NOT NULL,        -- FK to Entity (entity_type="user")
  display_name     STRING,                 -- user-chosen display name
  timezone         STRING,                 -- IANA timezone (e.g., "America/New_York")
  language         STRING,                 -- BCP 47 language tag (e.g., "en-US")
  communication_style STRING,              -- "concise" | "verbose" | "technical" | "casual"
  technical_level  STRING,                 -- "novice" | "intermediate" | "advanced" | "expert"
  created_at       ZONED DATETIME NOT NULL,
  updated_at       ZONED DATETIME NOT NULL
)

CREATE KEY UserProfile (profile_id)
```

**Grounding**: `UserProfile` maps to `schema:Person` properties (timezone, language) and GUMO's `BasicUserDimensions` (personality traits, long-lived characteristics). It is a `prov:Entity` attributed to the user agent.

#### 1.2 Preference

Represents a single user preference as a first-class node with full provenance. This follows the "Preference as Node" pattern validated by Zep/Graphiti and Memoria in production.

```
CREATE NODE TYPE Preference (
  preference_id     STRING NOT NULL,        -- UUID, primary key
  category          STRING NOT NULL,        -- "tool" | "workflow" | "communication" | "domain" | "environment" | "style"
  key               STRING NOT NULL,        -- preference key (e.g., "programming_language", "response_verbosity")
  polarity          STRING NOT NULL,        -- "positive" | "negative" | "neutral"
  strength          FLOAT NOT NULL,         -- 0.0 to 1.0, intensity of preference
  confidence        FLOAT NOT NULL,         -- 0.0 to 1.0, system certainty in this preference
  source            STRING NOT NULL,        -- "explicit" | "implicit_intentional" | "implicit_unintentional" | "inferred"
  context           STRING,                 -- optional scope qualifier (e.g., "data_analysis", "code_review")
  scope             STRING NOT NULL,        -- "global" | "agent" | "session"
  scope_id          STRING,                 -- agent_id or session_id when scope != "global"
  observation_count INTEGER DEFAULT 1,      -- supporting observation count
  first_observed_at ZONED DATETIME NOT NULL,
  last_confirmed_at ZONED DATETIME NOT NULL,
  access_count      INTEGER DEFAULT 0,      -- for decay reinforcement (ADR-0008 pattern)
  stability         FLOAT DEFAULT 168.0,    -- Ebbinghaus S factor in hours (ADR-0008 pattern)
  superseded_by     STRING,                 -- preference_id of replacement (for preference evolution)
  consent_ref       STRING                  -- reference to consent record (GDPR)
)

CREATE KEY Preference (preference_id)
```

**Core properties explained**:

| Property | Description | Research Source |
|----------|-------------|----------------|
| `strength` | How much the user prefers/avoids something (0.0-1.0) | KGCN-UP, Memoria, fuzzy preference models |
| `polarity` | Direction: like, dislike, or neutral | Rating-Aware Review Graphs (SIGIR 2025) |
| `confidence` | System certainty in this preference | Ontology-Based Uncertain Preferences (Springer 2012) |
| `source` | How acquired: explicit statement, intentional behavior, passive observation, or inference | CHI 2025 trichotomy (see Section 5) |
| `context` | Situation under which preference applies | UPOS situation-dependent sub-profiles |
| `scope` / `scope_id` | Visibility: global, agent-specific, or session-specific | LEGOMem multi-agent layers |
| `stability` | Ebbinghaus decay parameter; increases on reinforcement | ADR-0008 decay scoring |
| `superseded_by` | Points to newer preference that replaces this one | A-MEM bidirectional evolution |
| `consent_ref` | Links to consent record authorizing this preference | GDPR Art. 6-7 |

#### 1.3 Skill

Represents a skill or competency area that users can have proficiency in. Skills form a taxonomy via `PARENT_SKILL` edges.

```
CREATE NODE TYPE Skill (
  skill_id         STRING NOT NULL,        -- UUID, primary key
  name             STRING NOT NULL,        -- e.g., "Python", "SQL query optimization", "data visualization"
  category         STRING NOT NULL,        -- "programming_language" | "tool_proficiency" | "domain_knowledge" | "workflow_skill"
  description      STRING,                 -- human-readable description
  created_at       ZONED DATETIME NOT NULL
)

CREATE KEY Skill (skill_id)
```

**Grounding**: Maps to IMS LIP Competency component (skills/knowledge/abilities with levels). The `HAS_SKILL` edge carries proficiency metadata rather than the Skill node itself, following the knowledge tracing pattern from educational technology.

#### 1.4 Workflow

Represents a detected workflow pattern -- a recurring sequence of actions the user performs. This implements ADR-0007 Tier 5 (procedural memory) for user-specific workflows.

```
CREATE NODE TYPE Workflow (
  workflow_id        STRING NOT NULL,        -- UUID, primary key
  name               STRING NOT NULL,        -- e.g., "data analysis pipeline", "code review routine"
  abstraction_level  STRING NOT NULL,        -- "case" | "strategy" | "skill" (experiential hierarchy)
  success_rate       FLOAT,                  -- 0.0 to 1.0, derived from outcome tracking
  execution_count    INTEGER DEFAULT 1,      -- times this pattern has been observed
  avg_duration_ms    INTEGER,                -- average execution time
  source_session_ids LIST<STRING>,           -- sessions where this workflow was observed
  embedding          LIST<FLOAT>,            -- semantic embedding for similarity search
  created_at         ZONED DATETIME NOT NULL,
  updated_at         ZONED DATETIME NOT NULL
)

CREATE KEY Workflow (workflow_id)
```

**Grounding**: The three-level `abstraction_level` hierarchy is validated by three 2025-2026 systems:
- **Case** (raw traces): MemP trajectory preservation -- store raw event sequences
- **Strategy** (abstracted workflows): LEGOMem full-task memories -- abstract into workflow subgraphs
- **Skill** (executable procedures): MACLA semantic abstraction -- compress into reusable procedures via Bayesian selection

#### 1.5 BehavioralPattern

Represents a cross-agent or cross-session behavioral pattern detected from the user's interaction history.

```
CREATE NODE TYPE BehavioralPattern (
  pattern_id         STRING NOT NULL,        -- UUID, primary key
  pattern_type       STRING NOT NULL,        -- "delegation" | "escalation" | "routine" | "avoidance" | "exploration" | "specialization"
  description        STRING NOT NULL,        -- human-readable pattern description
  confidence         FLOAT NOT NULL,         -- 0.0 to 1.0
  observation_count  INTEGER DEFAULT 1,      -- supporting observation count
  involved_agents    LIST<STRING>,           -- agent_ids where pattern was observed
  first_detected_at  ZONED DATETIME NOT NULL,
  last_confirmed_at  ZONED DATETIME NOT NULL,
  access_count       INTEGER DEFAULT 0,      -- for decay reinforcement
  stability          FLOAT DEFAULT 336.0     -- Ebbinghaus S factor (2 weeks default -- patterns are more stable)
)

CREATE KEY BehavioralPattern (pattern_id)
```

**Grounding**: Extends OntobUMf's behavior modeling with activity stereotypes. `pattern_type` values are derived from multi-agent interaction analysis (LEGOMem, AGENTiGraph):
- **delegation**: User routes complex tasks to specific agents
- **escalation**: User switches agents when blocked
- **routine**: User follows consistent step sequences
- **avoidance**: User consistently avoids certain tools/approaches
- **exploration**: User frequently tries new tools/approaches
- **specialization**: User develops deep expertise in specific domains

### 2. New Edge Types

Nine new edge types connect user personalization nodes to the existing graph. All edge types include PG-Schema endpoint constraints.

```
CREATE EDGE TYPE HAS_PROFILE ()
  FROM Entity TO UserProfile
  -- Constraint: Entity.entity_type = "user"
  -- Cardinality: one UserProfile per user Entity

CREATE EDGE TYPE HAS_PREFERENCE ()
  FROM Entity TO Preference
  -- Constraint: Entity.entity_type = "user"

CREATE EDGE TYPE HAS_SKILL (
  proficiency       FLOAT NOT NULL,         -- 0.0 to 1.0 (derived from knowledge tracing)
  confidence        FLOAT NOT NULL,         -- confidence in proficiency estimate
  last_assessed_at  ZONED DATETIME NOT NULL,
  assessment_count  INTEGER DEFAULT 1,      -- observation count
  source            STRING NOT NULL         -- "observed" | "declared" | "inferred"
) FROM Entity TO Skill
  -- Constraint: Entity.entity_type = "user"

CREATE EDGE TYPE DERIVED_FROM (
  derivation_method STRING NOT NULL,        -- "stated" | "rule_extraction" | "llm_extraction" | "frequency_analysis" | "statistical_inference" | "pattern_match" | "graph_pattern" | "hierarchy_propagation"
  derived_at        ZONED DATETIME NOT NULL,
  model_id          STRING,                 -- LLM model used (e.g., "claude-haiku-4.5"); null for rule-based
  prompt_version    STRING,                 -- extraction prompt version for reproducibility; null for rule-based
  evidence_quote    STRING,                 -- source quote grounding this extraction
  source_turn_index INTEGER                 -- conversation turn index for provenance granularity
) FROM Preference TO Event
  | FROM BehavioralPattern TO Event
  | FROM Skill TO Event
  | FROM Workflow TO Event

CREATE EDGE TYPE EXHIBITS_PATTERN ()
  FROM Entity TO BehavioralPattern
  -- Constraint: Entity.entity_type = "user"

CREATE EDGE TYPE INTERESTED_IN (
  weight            FLOAT NOT NULL,         -- 0.0 to 1.0
  source            STRING NOT NULL,        -- "explicit" | "implicit" | "inferred"
  last_updated      ZONED DATETIME NOT NULL
) FROM Entity TO Entity
  -- Constraint: source Entity.entity_type = "user", target Entity.entity_type = "concept"

CREATE EDGE TYPE ABOUT ()
  FROM Preference TO Entity
  -- Links a Preference node to the Entity it concerns
  -- e.g., Preference("prefers Python") -[ABOUT]-> Entity("Python", type=concept)

CREATE EDGE TYPE ABSTRACTED_FROM ()
  FROM Workflow TO Workflow
  -- Links abstraction levels: case -> strategy -> skill chain

CREATE EDGE TYPE PARENT_SKILL ()
  FROM Skill TO Skill
  -- Skill taxonomy hierarchy: "Python" -> "Programming Languages" -> "Software Engineering"
```

**Edge type summary**:

| Edge Type | From | To | Properties | Purpose |
|-----------|------|----|------------|---------|
| `HAS_PROFILE` | Entity (user) | UserProfile | -- | Links user to their profile |
| `HAS_PREFERENCE` | Entity (user) | Preference | -- | Links user to preference nodes |
| `HAS_SKILL` | Entity (user) | Skill | proficiency, confidence, last_assessed_at, assessment_count, source | User skill with metadata |
| `DERIVED_FROM` | Preference/BehavioralPattern/Skill/Workflow | Event | derivation_method, derived_at | Provenance traceability |
| `EXHIBITS_PATTERN` | Entity (user) | BehavioralPattern | -- | Links user to behavioral patterns |
| `INTERESTED_IN` | Entity (user) | Entity (concept) | weight, source, last_updated | Topic/domain interest |
| `ABOUT` | Preference | Entity | -- | What the preference concerns |
| `ABSTRACTED_FROM` | Workflow | Workflow | -- | Experiential hierarchy chain |
| `PARENT_SKILL` | Skill | Skill | -- | Skill taxonomy hierarchy |

### 3. New Views (MVKG Extension)

The multi-view formalism from ADR-0011 Section 4 is extended with three user-centric views. Following the existing MVKG notation:

```
G_user = (N_user, E_user, T_n_user, T_e_user, L_n_user, L_e_user, P_user, V_user)

where:
  N_user = N_base UNION {UserProfile, Preference, Skill, Workflow, BehavioralPattern}
  E_user = E_base UNION {HAS_PROFILE, HAS_PREFERENCE, HAS_SKILL, DERIVED_FROM,
                          EXHIBITS_PATTERN, INTERESTED_IN, ABOUT, ABSTRACTED_FROM, PARENT_SKILL}
  T_n_user = T_n_base UNION {UserProfile, Preference, Skill, Workflow, BehavioralPattern}
  T_e_user = T_e_base UNION {HAS_PROFILE, HAS_PREFERENCE, HAS_SKILL, DERIVED_FROM,
                              EXHIBITS_PATTERN, INTERESTED_IN, ABOUT, ABSTRACTED_FROM, PARENT_SKILL}
```

Three new semantic views are added:

| View | Notation | Nodes | Edges | Query Focus |
|------|----------|-------|-------|-------------|
| User Profile | `V_user` | Entity (user), UserProfile, Preference, Skill, Entity (concept/tool) | HAS_PROFILE, HAS_PREFERENCE, HAS_SKILL, INTERESTED_IN, ABOUT | "What does the system know about this user?" |
| Behavioral | `V_behavioral` | Entity (user), BehavioralPattern, Workflow, Event | EXHIBITS_PATTERN, ABSTRACTED_FROM, DERIVED_FROM | "How does this user typically work?" |
| Provenance | `V_provenance` | Preference, BehavioralPattern, Skill, Event | DERIVED_FROM | "Why does the system believe this about the user?" |

These views compose with the existing five views (V_temporal, V_causal, V_semantic, V_entity, V_hierarchical) through the shared Event node type. For example, a query asking "Why does the system think this user prefers Python?" would traverse V_provenance (DERIVED_FROM edges from the Preference to source Events) and then optionally V_causal (CAUSED_BY edges between those Events).

**Intent weight matrix extension** for user-personalization queries:

```python
INTENT_WEIGHTS = {
    # ... existing intents from ADR-0009 ...
    "who_is": {
        CAUSED_BY: 1.0, FOLLOWS: 0.5, SIMILAR_TO: 1.0, REFERENCES: 3.0,
        SUMMARIZES: 1.0,
        HAS_PROFILE: 5.0, HAS_PREFERENCE: 5.0, HAS_SKILL: 5.0,
        EXHIBITS_PATTERN: 4.0, INTERESTED_IN: 4.0, ABOUT: 3.0,
        DERIVED_FROM: 2.0, ABSTRACTED_FROM: 1.0, PARENT_SKILL: 2.0,
        SAME_AS: 4.0, RELATED_TO: 3.0,
    },
    "how_does": {
        CAUSED_BY: 2.0, FOLLOWS: 3.0, SIMILAR_TO: 1.0, REFERENCES: 2.0,
        SUMMARIZES: 1.0,
        HAS_PROFILE: 1.0, HAS_PREFERENCE: 2.0, HAS_SKILL: 3.0,
        EXHIBITS_PATTERN: 5.0, INTERESTED_IN: 2.0, ABOUT: 1.0,
        DERIVED_FROM: 1.0, ABSTRACTED_FROM: 4.0, PARENT_SKILL: 1.0,
        SAME_AS: 1.0, RELATED_TO: 2.0,
    },
    "personalize": {
        CAUSED_BY: 1.0, FOLLOWS: 0.5, SIMILAR_TO: 1.5, REFERENCES: 2.0,
        SUMMARIZES: 1.0,
        HAS_PROFILE: 4.0, HAS_PREFERENCE: 5.0, HAS_SKILL: 4.0,
        EXHIBITS_PATTERN: 3.0, INTERESTED_IN: 4.0, ABOUT: 3.0,
        DERIVED_FROM: 3.0, ABSTRACTED_FROM: 1.0, PARENT_SKILL: 2.0,
        SAME_AS: 2.0, RELATED_TO: 2.0,
    },
}
```

### 4. Preference Model

The preference model uses the "Preference as Node" pattern, where each preference is a first-class graph node connected via three relationship paths:

```
(User Entity)-[HAS_PREFERENCE]->(Preference)-[ABOUT]->(Target Entity)
                                      |
                                      +-[DERIVED_FROM]->(Source Event)
```

This triple-path structure provides:
- **Who**: `HAS_PREFERENCE` links to the owning user
- **What**: `ABOUT` links to the entity the preference concerns
- **Why**: `DERIVED_FROM` links to the source event(s) that established the preference

**Preference lifecycle**:

```
1. Source event captured (e.g., user states "I prefer Python")
   -> Event node created in Neo4j via Stage 1 projection

2. Preference extracted (Stage 2 enrichment or explicit event type)
   -> Preference node created with properties
   -> HAS_PREFERENCE edge from User Entity
   -> ABOUT edge to target Entity ("Python")
   -> DERIVED_FROM edge to source Event

3. Preference reinforced (user restates or behavior confirms)
   -> last_confirmed_at updated
   -> stability increased by S_boost (ADR-0008 pattern)
   -> access_count incremented
   -> confidence may increase

4. Preference superseded (user contradicts previous preference)
   -> New Preference node created
   -> Old Preference.superseded_by set to new preference_id
   -> Old Preference remains in graph (immutable history)
```

### 5. Three-Tier Source Tracking

The `source` property on Preference nodes implements the CHI 2025 trichotomy, which supersedes the traditional binary explicit/implicit model:

| Source Type | Definition | Examples | Default Confidence | Volume |
|-------------|-----------|----------|-------------------|--------|
| `explicit` | User directly states a preference | "I prefer Python", "Use dark mode", rating/selection | 0.9 | Low (sparse) |
| `implicit_intentional` | User consciously employs behavior to shape system output | Deliberately selecting tools to train the agent, strategic workflow choices | 0.7 | Medium |
| `implicit_unintentional` | System infers from behavior without user awareness | Dwell time, click patterns, tool usage frequency, topic co-occurrence | 0.5 | High (abundant) |
| `inferred` | System derives from ontology structure or cross-preference reasoning | "Interested in ML" implies interest in "AI" (parent concept) | 0.3 | Variable |

**Source type determines initial confidence**. The confidence value evolves over time: implicit preferences gain confidence through repeated observation (observation_count); inferred preferences gain confidence when corroborated by direct signals.

**Conflict resolution priority** when sources disagree:
1. `explicit` always wins (highest authority)
2. `implicit_intentional` > `implicit_unintentional` (deliberate signals weighted higher)
3. Recency weighting via Ebbinghaus decay (ADR-0008)
4. Observation count as tiebreaker (more observations = higher confidence)

**Relationship to extraction confidence thresholds (ADR-0013):** The values above are the default initial confidence assigned when a preference is first created from a given source type. ADR-0013 Section 7 defines separate *minimum confidence thresholds* for graph insertion (explicit >= 0.7, implicit_intentional >= 0.4, implicit_unintentional >= 0.3, inferred >= 0.15). Default confidence should always exceed the minimum threshold for its source type. The LLM's self-reported confidence may adjust the default downward but never below the insertion threshold.

### 6. Consolidation Pipeline Integration

The three consolidation stages (ADR-0008) are extended to process user personalization data:

#### Stage 1: Event Projection (extended)

New event types for user personalization:

| Event Type | `event_type` String | Processing |
|------------|--------------------|-----------:|
| `cg:PreferenceStated` | `user.preference.stated` | Extract Preference node with source="explicit" |
| `cg:PreferenceRevoked` | `user.preference.revoked` | Set superseded_by on target Preference |
| `cg:SkillDeclared` | `user.skill.declared` | Create/update HAS_SKILL edge with source="declared" |
| `cg:ProfileUpdated` | `user.profile.updated` | Update UserProfile node properties |

Stage 1 MUST:
- Create Preference nodes from `user.preference.stated` events
- Create HAS_PREFERENCE and ABOUT edges connecting User -> Preference -> Entity
- Create DERIVED_FROM edges from Preference to source Event
- Handle preference revocation by setting `superseded_by`
- Create/update UserProfile from `user.profile.updated` events

#### Stage 2: Enrichment (extended)

Stage 2 adds implicit preference inference:

| Enrichment Task | Input | Output | Method |
|-----------------|-------|--------|--------|
| Tool preference inference | Tool usage frequency per user | Preference nodes (source="implicit_unintentional") | Frequency analysis: tools used > 3x with consistent success get positive preferences |
| Topic interest inference | Entity co-occurrence in user sessions | INTERESTED_IN edges | Topic frequency: concepts referenced > 5x across sessions get interest edges |
| Skill assessment | Tool execution success/failure patterns | HAS_SKILL edges with proficiency | Knowledge tracing: success rate over time estimates proficiency |
| Communication style inference | Response feedback patterns | UserProfile.communication_style update | Pattern matching on user interaction patterns |

Stage 2 MUST:
- Never create `explicit` source preferences -- only Stage 1 handles explicit user statements
- Set appropriate confidence based on source type (see Section 5 table)
- Create DERIVED_FROM edges linking inferred preferences to the source events that informed them

#### Stage 3: Re-Consolidation (extended)

Stage 3 adds cross-session user pattern discovery:

| Re-Consolidation Task | Input | Output |
|-----------------------|-------|--------|
| Cross-session preference merging | Preferences from multiple sessions for same user | Merged preference with higher confidence, updated observation_count |
| Behavioral pattern detection | Event sequences across user sessions | BehavioralPattern nodes with EXHIBITS_PATTERN edges |
| Workflow extraction | Repeated successful event sequences | Workflow nodes at "case" level, with ABSTRACTED_FROM chains for higher abstractions |
| Preference conflict resolution | Contradictory preferences for same user | superseded_by chain: older/weaker preference superseded by newer/stronger |
| Interest hierarchy propagation | INTERESTED_IN edges + concept hierarchy | New INTERESTED_IN edges with decayed weights for parent/child concepts |

### 7. Decay Model Integration

Preferences, skills, and behavioral patterns use the existing Ebbinghaus decay model from ADR-0008. Preferences are memories and follow the same retention lifecycle.

**Decay scoring for preferences**:

```
score(pref, t_now) = w_r * recency(pref, t_now)
                   + w_s * pref.strength
                   + w_c * pref.confidence

recency(pref, t_now) = e^(-t_elapsed / pref.stability)
t_elapsed = hours since max(pref.first_observed_at, pref.last_confirmed_at)
```

**Default weights**: `w_r = 1.0, w_s = 0.8, w_c = 0.8` -- slightly higher weight on recency to ensure stale preferences decay.

**Reinforcement on access** (reconsolidation, ADR-0008 pattern):
- When a preference is retrieved in a context API response: `access_count += 1`, `last_confirmed_at = now`, `stability += S_boost`
- When a preference is confirmed by user behavior: `observation_count += 1`, `confidence = min(1.0, confidence + 0.05)`, `stability += S_boost`

**Retention tier application to user nodes**:

| Tier | Preference Policy | Skill Policy | BehavioralPattern Policy |
|------|------------------|-------------|-------------------------|
| Hot (<24h) | All preferences retained | All skills retained | All patterns retained |
| Warm (24h-7d) | All retained; low-confidence (<0.3) inferred preferences pruned | All retained | All retained |
| Cold (7-30d) | Only preferences with strength >= 0.5 OR observation_count >= 3 | Only skills with assessment_count >= 2 | Only patterns with observation_count >= 3 |
| Archive (>30d) | Removed from Neo4j; summary preserves aggregate preference profile | Removed; skill profile preserved in summary | Removed; pattern summary preserved |

**Long-term vs. short-term preferences** (from dual-scale interest research):
- Long-term preferences (high stability S, slow decay): Stable characteristics like language preference, editor choice, communication style. Default `stability = 720.0` (30 days).
- Short-term preferences (low stability S, fast decay): Contextual interests tied to current projects. Default `stability = 168.0` (7 days).

The `stability` value is initialized based on the preference category:

| Category | Initial Stability (hours) | Rationale |
|----------|--------------------------|-----------|
| `communication` | 720 (30 days) | Communication style changes rarely |
| `environment` | 720 (30 days) | Environment preferences (dark mode, etc.) are stable |
| `tool` | 336 (14 days) | Tool preferences evolve with experience |
| `workflow` | 336 (14 days) | Workflow preferences evolve with projects |
| `domain` | 168 (7 days) | Domain interests shift with current work |
| `style` | 168 (7 days) | Coding/interaction style may be context-dependent |

### 8. Cross-Session User Identity

User identity persists across sessions via the existing Entity resolution strategy (ADR-0011 Section 3).

**Resolution flow**:

1. Every event carries a `user_id` field (or the system assigns one from authentication context)
2. The projection worker resolves the `user_id` against existing Entity nodes (entity_type="user") using the three-tier strategy:
   - **Exact match**: Normalized `user_id` matches existing Entity. Merge. Confidence 1.0.
   - **Close match**: Different `user_id` but high-confidence identity signal (same email, API key, etc.). Create `SAME_AS` edge with confidence >= 0.9.
   - **Related match**: Behavioral similarity suggests same user (same IP, similar patterns). Create `SAME_AS` edge with variable confidence.
3. Preferences, skills, and patterns are linked to the resolved User Entity, not to the session

**SAME_AS for user identity**:

```
(:Entity {entity_type: "user", name: "user_abc"})-[:SAME_AS {
  confidence: 0.95,
  justification: "shared_api_key"
}]->(:Entity {entity_type: "user", name: "user_xyz"})
```

When `SAME_AS` links are established, the system SHOULD present a unified user view by traversing `SAME_AS` edges during context assembly. The `SAME_AS` edge uses the existing edge type from ADR-0011 -- no new edge type is needed.

**Session-scoped vs. user-scoped context**: The context API (ADR-0006) MUST distinguish:
- **Session context**: Events, tools, and entities from the current session (existing behavior)
- **User context**: Accumulated preferences, interests, and proficiencies across all sessions for the resolved user (new behavior, gated by `include_user_context=true` query parameter)

### 9. Multi-Agent User Knowledge

When multiple agents serve the same user, user knowledge is partitioned into three layers following the LEGOMem architecture:

#### Layer 1: Core User Profile (shared across all agents)

```
(:Entity {entity_type: "user"})-[:HAS_PROFILE]->(:UserProfile)
(:Entity {entity_type: "user"})-[:HAS_PREFERENCE]->(:Preference {scope: "global"})
(:Entity {entity_type: "user"})-[:HAS_SKILL]->(:Skill)
```

Core profile is populated from:
- Explicit user statements (highest confidence)
- High-confidence cross-session observations (observation_count >= 5)
- Cross-agent pattern convergence (multiple agents observe the same preference)

#### Layer 2: Agent-Specific User Context (per agent)

```
(:Entity {entity_type: "user"})-[:HAS_PREFERENCE]->(:Preference {scope: "agent", scope_id: "agent_123"})
```

Agent-specific context captures:
- Tool preferences specific to one agent's domain
- Workflow patterns observed within a single agent's interaction history
- Communication style preferences that vary by agent type (e.g., verbose for research agent, concise for coding agent)

The `scope` and `scope_id` properties on the Preference node distinguish global from agent-specific preferences. An agent retrieving user context sees global preferences merged with its own agent-specific preferences. Agent-specific preferences override global preferences when both exist for the same key.

#### Layer 3: Cross-Agent Behavioral Patterns (derived)

```
(:Entity {entity_type: "user"})-[:EXHIBITS_PATTERN]->(:BehavioralPattern {
  involved_agents: ["agent_A", "agent_B", "agent_C"]
})
```

Cross-agent patterns are derived by Stage 3 re-consolidation by analyzing user behavior across agents:
- **Delegation patterns**: User routes complex tasks to Agent B but handles simple tasks with Agent A
- **Escalation patterns**: User switches from Agent A to Agent B when blocked
- **Specialization patterns**: User develops deep expertise with Agent C for a specific domain

### 10. Privacy and GDPR Compliance

User preferences constitute personal data under GDPR Article 4(1). The cg-user module integrates with existing privacy mechanisms and adds user-specific safeguards.

#### 10.1 Forgettable Payloads for Preference Content

Following the Forgettable Payloads pattern (ADR-0001):

- **Preference envelope** (structural metadata): The existence of a preference node, its category, strength, confidence, source, and provenance chain. This is metadata that may be retained for system integrity.
- **Preference payload** (forgettable content): The actual preference `key` and the linked Entity content (what the user prefers). Subject to erasure on request.

When a preference payload is erased:
- The Preference node retains its structural properties (preference_id, category, polarity, strength, confidence, source)
- The `key` field is replaced with a tombstone marker: `"[ERASED]"`
- The `ABOUT` edge target Entity's name is anonymized if exclusively referenced by erased preferences
- The `DERIVED_FROM` edges are preserved (provenance chain to events, whose payloads are also forgettable per ADR-0001)

#### 10.2 Cascade Erasure

When a user exercises the right to erasure (GDPR Article 17), the system MUST perform cascade deletion:

1. Delete the UserProfile node
2. Delete all Preference nodes connected via HAS_PREFERENCE from this user's Entity
3. Delete all BehavioralPattern nodes connected via EXHIBITS_PATTERN from this user's Entity
4. Remove all HAS_SKILL edges from this user's Entity (Skill nodes are shared and not deleted)
5. Remove all INTERESTED_IN edges from this user's Entity
6. Remove SAME_AS edges involving this user's Entity
7. Anonymize the User Entity node: replace `name` with tombstone, retain `entity_id` for referential integrity
8. Mark source events in Redis as erased (Forgettable Payloads mechanism)
9. The next re-projection naturally excludes erased data from Neo4j

Because Neo4j is a derived projection (ADR-0003), cascade erasure can alternatively be implemented by marking events as erased in Redis and triggering a re-projection -- the rebuilt graph will naturally exclude all derived user data. This is a significant architectural advantage.

#### 10.3 Consent Tracking

Each preference creation event SHOULD carry a `consent_ref` linking to the consent record that authorized its creation. The preference node's `consent_ref` field propagates this linkage.

When consent is withdrawn:
- All preferences linked to that consent_ref are eligible for erasure
- A `user.consent.withdrawn` event is appended to the event ledger (audit trail)
- The withdrawal event itself is retained in the ledger as a non-forgettable audit record

#### 10.4 Data Subject Access

The API MUST support a data export endpoint that returns all user data in a machine-readable format:

```
GET /v1/users/{user_id}/data-export
```

Response includes:
- UserProfile
- All Preference nodes with ABOUT targets
- All HAS_SKILL edges with Skill targets
- All BehavioralPattern nodes
- All INTERESTED_IN edges with targets
- Provenance chains (DERIVED_FROM edges to source events)

### 11. Procedural Memory Connection

Workflow and BehavioralPattern nodes connect to ADR-0007 Tier 5 (Procedural Memory), implementing the experiential hierarchy:

```
Tier 3 (Episodic): Raw event sequences in Redis
    |
    v  [Stage 1 projection]
Tier 4 (Semantic): Event nodes + FOLLOWS/CAUSED_BY edges in Neo4j
    |
    v  [Stage 3 re-consolidation -- workflow extraction]
Tier 5 (Procedural): Workflow nodes at "case" level
    |
    v  [Stage 3 re-consolidation -- abstraction]
Tier 5 (Procedural): Workflow nodes at "strategy" level
    |
    v  [Stage 3 re-consolidation -- further abstraction]
Tier 5 (Procedural): Workflow nodes at "skill" level
```

**Workflow-Event connection**: Workflow nodes at the "case" level link to their constituent Events via DERIVED_FROM edges. This preserves the traceability chain from abstract workflow -> concrete events -> immutable event ledger.

**Workflow abstraction chain**: Higher-level Workflow nodes link to lower-level ones via ABSTRACTED_FROM edges:

```
(:Workflow {abstraction_level: "skill", name: "data_analysis_pipeline"})
  -[:ABSTRACTED_FROM]->
(:Workflow {abstraction_level: "strategy", name: "csv_analysis_workflow"})
  -[:ABSTRACTED_FROM]->
(:Workflow {abstraction_level: "case", name: "session_abc_analysis_trace"})
  -[:DERIVED_FROM]->
(:Event {event_type: "tool.execute", tool_name: "csv_reader"})
```

**User-Workflow connection**: Users link to their workflows via their BehavioralPattern nodes (EXHIBITS_PATTERN) or directly via DERIVED_FROM chains. The BehavioralPattern serves as the summary/classification layer over raw Workflow observations.

### 12. Schema Enforcement

Following the layered enforcement strategy from ADR-0011 Section 7, new Neo4j constraints for user personalization types:

```cypher
-- UserProfile node
CREATE CONSTRAINT userprofile_pk FOR (p:UserProfile) REQUIRE p.profile_id IS UNIQUE;
CREATE CONSTRAINT userprofile_id_not_null FOR (p:UserProfile) REQUIRE p.profile_id IS NOT NULL;
CREATE CONSTRAINT userprofile_user_not_null FOR (p:UserProfile) REQUIRE p.user_id IS NOT NULL;

-- Preference node
CREATE CONSTRAINT preference_pk FOR (p:Preference) REQUIRE p.preference_id IS UNIQUE;
CREATE CONSTRAINT preference_id_not_null FOR (p:Preference) REQUIRE p.preference_id IS NOT NULL;
CREATE CONSTRAINT preference_category_not_null FOR (p:Preference) REQUIRE p.category IS NOT NULL;
CREATE CONSTRAINT preference_polarity_not_null FOR (p:Preference) REQUIRE p.polarity IS NOT NULL;
CREATE CONSTRAINT preference_strength_not_null FOR (p:Preference) REQUIRE p.strength IS NOT NULL;
CREATE CONSTRAINT preference_confidence_not_null FOR (p:Preference) REQUIRE p.confidence IS NOT NULL;
CREATE CONSTRAINT preference_source_not_null FOR (p:Preference) REQUIRE p.source IS NOT NULL;
CREATE CONSTRAINT preference_scope_not_null FOR (p:Preference) REQUIRE p.scope IS NOT NULL;

-- Skill node
CREATE CONSTRAINT skill_pk FOR (s:Skill) REQUIRE s.skill_id IS UNIQUE;
CREATE CONSTRAINT skill_id_not_null FOR (s:Skill) REQUIRE s.skill_id IS NOT NULL;
CREATE CONSTRAINT skill_name_not_null FOR (s:Skill) REQUIRE s.name IS NOT NULL;
CREATE CONSTRAINT skill_category_not_null FOR (s:Skill) REQUIRE s.category IS NOT NULL;

-- Workflow node
CREATE CONSTRAINT workflow_pk FOR (w:Workflow) REQUIRE w.workflow_id IS UNIQUE;
CREATE CONSTRAINT workflow_id_not_null FOR (w:Workflow) REQUIRE w.workflow_id IS NOT NULL;
CREATE CONSTRAINT workflow_name_not_null FOR (w:Workflow) REQUIRE w.name IS NOT NULL;
CREATE CONSTRAINT workflow_level_not_null FOR (w:Workflow) REQUIRE w.abstraction_level IS NOT NULL;

-- BehavioralPattern node
CREATE CONSTRAINT behavioralpattern_pk FOR (b:BehavioralPattern) REQUIRE b.pattern_id IS UNIQUE;
CREATE CONSTRAINT behavioralpattern_id_not_null FOR (b:BehavioralPattern) REQUIRE b.pattern_id IS NOT NULL;
CREATE CONSTRAINT behavioralpattern_type_not_null FOR (b:BehavioralPattern) REQUIRE b.pattern_type IS NOT NULL;
CREATE CONSTRAINT behavioralpattern_confidence_not_null FOR (b:BehavioralPattern) REQUIRE b.confidence IS NOT NULL;
```

**Projection worker validation** (application-level, not enforceable by Neo4j):

| Rule | Enforcement |
|------|-------------|
| HAS_PROFILE only from Entity (entity_type="user") | Projection worker validates source entity type |
| HAS_PREFERENCE only from Entity (entity_type="user") | Projection worker validates source entity type |
| HAS_SKILL only from Entity (entity_type="user") | Projection worker validates source entity type |
| INTERESTED_IN only from user Entity to concept Entity | Projection worker validates both endpoint types |
| Preference.strength in [0.0, 1.0] | Projection worker validates range |
| Preference.confidence in [0.0, 1.0] | Projection worker validates range |
| Preference.polarity in {"positive", "negative", "neutral"} | Projection worker validates enum |
| Preference.source in {"explicit", "implicit_intentional", "implicit_unintentional", "inferred"} | Projection worker validates enum |
| Preference.scope in {"global", "agent", "session"} | Projection worker validates enum |
| Workflow.abstraction_level in {"case", "strategy", "skill"} | Projection worker validates enum |

### 13. User Subgraph Architecture

The cg-user module adopts **Pattern A: User Subgraph Within Shared Graph** -- user personalization data lives as a subgraph within the same Neo4j database as the event/entity graph.

**Rationale** (from Task #3 analysis):

1. **Cross-domain traversal is essential**: The value of personalization comes from connecting user preferences to agent events. Separate databases would require cross-database joins, defeating the purpose.
2. **PROV-O alignment**: User preferences are `prov:Entity` instances attributed to `prov:Agent` (the user). They belong in the same provenance graph.
3. **Existing entity model supports it**: The Entity node with `entity_type="user"` already exists (ADR-0011). User personalization types extend from this anchor point.
4. **Access control via projection**: Neo4j is a derived projection (ADR-0003). The projection worker can enforce user-scoped access by filtering what gets projected for each requesting context.
5. **Re-projection handles deletion**: Because the graph is derived, user data deletion requires only marking events as erased in Redis and re-projecting. No complex graph traversal needed.

**Namespace isolation**: User-specific nodes carry the `user_id` property for logical isolation. All queries for user-specific data MUST include a `user_id` filter:

```cypher
// Retrieve user preferences
MATCH (u:Entity {entity_type: "user", entity_id: $user_id})
  -[:HAS_PREFERENCE]->(p:Preference)
  -[:ABOUT]->(e:Entity)
WHERE p.superseded_by IS NULL  // only active preferences
RETURN p, e
ORDER BY p.strength DESC, p.confidence DESC
```

### 14. PROV-O Grounding

Following ADR-0011's dual-vocabulary approach, new edge types are grounded in PROV-O where applicable and documented as custom extensions where PROV-O has no equivalent:

| Operational Edge | PROV-O Grounding | Custom Extension | Notes |
|-----------------|------------------|------------------|-------|
| `HAS_PROFILE` | `prov:wasAttributedTo` (inverse) | `cg:hasProfile` | Profile is attributed to the user agent |
| `HAS_PREFERENCE` | `prov:wasAttributedTo` (inverse) | `cg:hasPreference` | Preference is attributed to the user agent |
| `HAS_SKILL` | No PROV-O equivalent | `cg:hasSkill` | Custom -- PROV-O does not model competency |
| `DERIVED_FROM` | `prov:wasDerivedFrom` | -- | Direct PROV-O usage -- preferences are derived from events |
| `EXHIBITS_PATTERN` | No PROV-O equivalent | `cg:exhibitsPattern` | Custom -- PROV-O does not model behavioral patterns |
| `INTERESTED_IN` | No PROV-O equivalent | `cg:interestedIn` | Custom -- maps to `foaf:interest` in FOAF vocabulary |
| `ABOUT` | No PROV-O equivalent | `cg:about` | Custom -- maps to `foaf:topic` / `schema:about` |
| `ABSTRACTED_FROM` | `prov:wasDerivedFrom` | `cg:abstractedFrom` | Workflow abstraction is a form of derivation |
| `PARENT_SKILL` | No PROV-O equivalent | `cg:parentSkill` | Custom -- maps to `skos:broader` in SKOS vocabulary |

**Cross-vocabulary mappings** (documentation-level, not runtime):

| cg-user Term | schema.org | FOAF | GUMO | SKOS |
|-------------|------------|------|------|------|
| UserProfile | schema:Person | foaf:Person | gumo:UserModel | -- |
| Preference | -- | -- | gumo:Interest (partial) | -- |
| Skill | -- | -- | gumo:Ability | -- |
| INTERESTED_IN | schema:knowsAbout | foaf:interest | gumo:hasInterest | -- |
| PARENT_SKILL | -- | -- | -- | skos:broader |
| HAS_PROFILE | -- | -- | -- | -- |
| ABOUT | schema:about | foaf:topic | -- | -- |

### 15. Ontology Module Definition

The `cg-user` module is added to the ontology module structure defined in ADR-0011:

```
cg-core         -- Node types, edge types, core properties, PROV-O mapping
cg-events       -- Event type taxonomy, status values, OTel mapping
cg-entities     -- Entity type hierarchy, roles, resolution strategy
cg-memory       -- Memory tier classes, CLS vocabulary, consolidation stages
cg-views        -- Multi-view definitions, intent-aware retrieval vocabulary
cg-retention    -- Retention tiers, decay parameters
cg-user         -- (NEW) User personalization: UserProfile, Preference, Skill,
                --   Workflow, BehavioralPattern node types; HAS_PROFILE,
                --   HAS_PREFERENCE, HAS_SKILL, DERIVED_FROM, EXHIBITS_PATTERN,
                --   INTERESTED_IN, ABOUT, ABSTRACTED_FROM, PARENT_SKILL edge types;
                --   V_user, V_behavioral, V_provenance views;
                --   Source tracking taxonomy; Decay integration;
                --   Multi-agent user knowledge layers; Privacy patterns
```

**Module dependencies**:
- `cg-user` REQUIRES `cg-core` (Entity node type, PROV-O mapping)
- `cg-user` REQUIRES `cg-entities` (entity_type="user" resolution)
- `cg-user` REQUIRES `cg-retention` (Ebbinghaus decay parameters, retention tiers)
- `cg-user` REQUIRES `cg-events` (event type taxonomy for user.preference.*, user.skill.*, user.profile.* events)
- `cg-user` EXTENDS `cg-views` (adds V_user, V_behavioral, V_provenance views)
- `cg-user` EXTENDS `cg-memory` (implements Tier 5 procedural memory via Workflow nodes)

## Consequences

### Positive

- **Adaptive agent behavior**: Agents can adjust responses based on user preferences, skill levels, and behavioral patterns -- personalization quality improves with each interaction
- **Full provenance for user knowledge**: Every preference, skill assessment, and behavioral pattern traces back to source events via DERIVED_FROM edges. This is the system's key differentiator over Zep, Mem0, and Memoria, which lack event-level provenance
- **Decay-aware personalization**: Stale preferences decay naturally via the Ebbinghaus model. The system automatically prioritizes recent, reinforced preferences over old, unconfirmed ones
- **Multi-agent user continuity**: Users maintain a consistent profile across agent interactions. Global preferences provide baseline behavior; agent-specific preferences allow customization
- **Privacy by design**: Forgettable Payloads, cascade erasure, consent tracking, and data export are built into the architecture from the start -- not retrofitted
- **Research-validated patterns**: Node types and edge types are grounded in production systems (Zep/Graphiti, Mem0, Memoria) and peer-reviewed research (CHI 2025, ECAI 2025, AAMAS 2026)
- **Natural extension of existing architecture**: No new databases, no new infrastructure. User personalization types live in the same Neo4j graph, projected by the same worker, following the same consolidation pipeline
- **Procedural memory foundation**: Workflow and BehavioralPattern nodes provide the concrete implementation path for ADR-0007 Tier 5, validated by MemP, LEGOMem, and MACLA research

### Negative

- **Schema complexity**: Five new node types and nine new edge types significantly expand the graph schema. Developers must understand the full type system to write correct queries.
- **Enrichment compute cost**: Implicit preference inference (Stage 2) and cross-session pattern detection (Stage 3) add processing overhead to the consolidation pipeline.
- **Confidence calibration**: Default confidence values for different source types are heuristic. Real-world calibration requires production data and may vary by deployment.
- **Cold-start problem**: New users have no preferences, skills, or patterns. The system provides no personalization until enough events accumulate to build a user profile.
- **Preference explosion risk**: Users with many sessions may accumulate large numbers of preference nodes. Retention tier pruning mitigates this, but monitoring is required.
- **Entity resolution for users is imperfect**: Cross-session user identity relies on deterministic matching (user_id) and probabilistic signals (behavior similarity). False SAME_AS links could merge distinct users.

### Risks to Monitor

| Risk | Mitigation |
|------|------------|
| Preference graph grows unboundedly per user | Retention tier pruning (Section 7); limit max active preferences per user (configurable, default 500) |
| Implicit preference inference produces false positives | Conservative thresholds (>= 3 observations, >= 0.5 confidence); explicit preferences always override |
| GDPR cascade erasure misses derived data | Re-projection from clean event store is the definitive erasure mechanism; graph traversal is a supplementary fast-path |
| Multi-agent preference conflicts | Scope-based resolution: agent-specific overrides global; explicit overrides implicit; recency as tiebreaker |
| Workflow extraction produces trivial patterns | Minimum execution_count threshold (>= 3) before promoting case-level to strategy-level |
| Skill proficiency estimates are inaccurate | Label as "observed" source with confidence < 1.0; allow users to override via explicit skill declarations |

## Alternatives Considered

### 1. Adopt GUMO as the user model ontology directly

Rejected. GUMO provides a comprehensive user dimension taxonomy (~1000 groups) but has critical gaps: no provenance model, no context-dependent preferences, no confidence/uncertainty tracking, no cross-session identity, and no integration with event-sourced architectures. GUMO is also academically maintained with no active development since ~2012. We adopt GUMO's design insights (temporal decay on user dimensions, dimension taxonomy) but implement a custom vocabulary that integrates with our PROV-O foundation.

### 2. Model preferences as weighted edges instead of nodes

Rejected. The "Preference as Edge" pattern (`(User)-[PREFERS {weight: 0.8}]->(Entity)`) is simpler but cannot support: temporal versioning (preference evolution via superseded_by), provenance tracing (DERIVED_FROM edges from preference to source events), rich metadata (9 core properties), or the Forgettable Payloads pattern (which requires a deletable node, not just an edge property). Zep/Graphiti and Memoria both validate the "Preference as Node" pattern in production for these reasons.

### 3. Separate user graph database per user (Pattern B)

Rejected. A separate Neo4j database per user provides strong data isolation but prevents cross-domain traversal -- the entire value proposition of the context graph is connecting user preferences to agent events, entity knowledge, and causal chains. Separate databases would require cross-database joins. Our re-projection architecture makes cascade erasure simple even within a shared graph. Pattern A (user subgraph within shared graph) is recommended by the research (Section 3.3 of Task #3) and used by Meta, LinkedIn, and most recommendation systems.

### 4. Use schema.org/FOAF as the primary vocabulary

Rejected. schema.org Person and FOAF provide interoperable identity types but lack: preference strength/confidence quantification, temporal preference evolution, context-dependent preferences, event-sourced provenance, and decay integration. These standards are designed for web indexing and social networking, not AI agent personalization. We map to schema.org/FOAF at the documentation level (Section 14) for interoperability but use custom vocabulary for operational types.

### 5. Defer user personalization entirely

Rejected. The user explicitly requested this capability. Without personalization, the system cannot provide adaptive agent behavior -- every interaction starts from zero. The research basis is mature (production systems exist) and the architectural extension is natural (no new infrastructure required). The cold-start problem is real but bounded -- the system degrades gracefully to unpersonalized behavior when no user data exists.

## Impact on Existing ADRs

### ADR-0007 (Memory Tier Architecture)

- **Tier 5 (Procedural Memory)**: No longer "future" -- Workflow and BehavioralPattern nodes provide the concrete implementation. The experiential hierarchy (case -> strategy -> skill) is formalized with specific node types and ABSTRACTED_FROM edges.
- **User knowledge across tiers**: Documented mapping of user data to each tier (Section 7 of this ADR). Sensory = raw interaction signals; Working = current session user context; Episodic = individual user events; Semantic = derived user knowledge graph; Procedural = user workflows.
- **No breaking changes.** Existing tier definitions and component mappings are preserved.

### ADR-0008 (Memory Consolidation and Decay)

- **Consolidation stages extended**: All three stages gain user personalization processing (Section 6). Stage 1 handles explicit preference events; Stage 2 infers implicit preferences; Stage 3 discovers cross-session patterns.
- **Decay model extended**: Ebbinghaus scoring applies to Preference, Skill, and BehavioralPattern nodes with category-specific initial stability values (Section 7).
- **Retention tiers extended**: User-specific retention policies defined (Section 7) following the Hot/Warm/Cold/Archive pattern.
- **New reflection triggers**: Accumulated user events crossing the REFLECTION_THRESHOLD (ADR-0008) trigger user-focused re-consolidation.
- **No breaking changes.** Existing consolidation stages, decay formula, and retention tiers operate identically for Event/Entity/Summary nodes.

### ADR-0009 (Multi-Graph Schema)

- **New edge types**: Nine new edge types added to the schema. The intent weight matrix gains three new intent categories (who_is, how_does, personalize) with weights for all edge types.
- **New node types**: Five new node types added to the graph schema.
- **Multi-view extension**: Three new views (V_user, V_behavioral, V_provenance) compose with the existing five views.
- **PROV-DM compatibility**: New edge types documented with PROV-O mappings (Section 14) following the dual-vocabulary approach.
- **No breaking changes to existing types.** All five original edge types (FOLLOWS, CAUSED_BY, SIMILAR_TO, REFERENCES, SUMMARIZES) and three original node types (Event, Entity, Summary) are unchanged.

### ADR-0011 (Ontological Foundation)

- **New ontology module**: `cg-user` added to the module structure. Dependencies on cg-core, cg-entities, cg-retention, cg-events, cg-views, cg-memory documented.
- **Entity type usage**: The existing `entity_type="user"` Entity serves as the anchor point for the entire user subgraph. No changes to the Entity type hierarchy.
- **Event type taxonomy extended**: New event types in the `user.*` namespace (user.preference.stated, user.preference.revoked, user.skill.declared, user.profile.updated) follow the dot-namespaced pattern.
- **PG-Schema extended**: New node type and edge type definitions follow the same PG-Schema notation.
- **No breaking changes.** The cg-user module is additive; existing modules are unchanged.

## Research References

### User Modeling Ontologies
- Heckmann, D., Schwartz, T., et al. (2005). "GUMO -- The General User Model Ontology." UM 2005. https://link.springer.com/chapter/10.1007/11527886_58
- Coutand, O. et al. (2007). "UPOS: User Profile Ontology with Situation-Dependent Preferences Support." IEEE AICT. https://ieeexplore.ieee.org/document/4455987/
- Brickley, D. & Miller, L. "FOAF Vocabulary Specification." http://xmlns.com/foaf/spec/
- schema.org. "Person Type." https://schema.org/Person
- IMS Global. "Learner Information Package Specification." https://www.imsglobal.org/profiles/index.html
- Razmerita, L. (2011). "An Ontology-Based Framework for Modeling User Behavior." https://www.researchgate.net/publication/224238777

### Preference and Interest Modeling
- (2025). "Beyond Explicit and Implicit: How Users Provide Feedback to Shape Personalized Recommendation Content." CHI 2025. https://arxiv.org/html/2502.09869v1
- KGCN-UP (2025). "Knowledge Graph Convolutional Networks with User Preferences." Nature Scientific Reports. https://www.nature.com/articles/s41598-025-14150-5
- PrefPalette (2025). "Personalized Preference Modeling with Latent Attributes." https://arxiv.org/html/2507.13541
- POPI (2025). "Personalizing LLMs via Optimized Preference Inference." https://arxiv.org/html/2510.17881
- (2012). "Ontology-Based Management of Uncertain Preferences." Springer. https://link.springer.com/chapter/10.1007/978-3-642-31715-6_15
- Ciccarese, P. et al. (2013). "PAV Ontology: Provenance, Authoring and Versioning." https://pmc.ncbi.nlm.nih.gov/articles/PMC4177195/

### Production Systems
- Zep/Graphiti. "Temporal Knowledge Graph for Agent Memory." https://help.getzep.com/graphiti/core-concepts/custom-entity-and-edge-types
- Chhikara et al. (2025). "Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory." ECAI. https://arxiv.org/abs/2504.19413
- Khant et al. (2025). "Memoria: A Scalable Agentic Memory Framework for Personalized Conversational AI." https://arxiv.org/abs/2512.12686

### Procedural Memory and Workflow Extraction
- Xu et al. (2025). "MemP: Exploring Agent Procedural Memory." https://arxiv.org/abs/2508.06433
- Microsoft (2025). "LEGOMem: Modular Procedural Memory for Multi-agent LLM Systems." AAMAS 2026. https://arxiv.org/abs/2510.04851
- Wu et al. (2025). "MACLA: Learning Hierarchical Procedural Memory through Bayesian Selection and Contrastive Refinement." https://arxiv.org/html/2512.18950v1

### Personal Knowledge Graphs
- Skjaeveland, Balog et al. (2024). "An Ecosystem for Personal Knowledge Graphs: A Survey and Research Roadmap." AI Open. https://arxiv.org/abs/2304.09572
- Bernard et al. (2024). "PKG API: A Tool for Personal Knowledge Graph Management." WWW 2024. https://arxiv.org/html/2402.07540v1

### Multi-Agent Systems
- AGENTiGraph (CIKM 2025). "A Multi-Agent Knowledge Graph Framework." https://dl.acm.org/doi/10.1145/3746252.3761459
- Jiang et al. (2026). "MAGMA: A Multi-Graph based Agentic Memory Architecture." https://arxiv.org/abs/2601.03236

### Behavior Pattern Detection
- IJCAI 2025. "A Survey on Temporal Interaction Graph Representation Learning." https://www.ijcai.org/proceedings/2025/1166.pdf
- Neo4j (2025). "Discovering Hidden Skills with an Enterprise Knowledge Graph." https://neo4j.com/blog/discovering-hidden-skills-enterprise-knowledge-graph/

### Knowledge Tracing and Skill Modeling
- (2025). "Deep Knowledge Tracing and Cognitive Load Estimation." Nature Scientific Reports. https://www.nature.com/articles/s41598-025-10497-x
- (2021). "Competency Ontology for Learning Environments Personalization." Springer. https://slejournal.springeropen.com/articles/10.1186/s40561-021-00160-z

### Memory Architecture
- Hu et al. (2025). "Memory in the Age of AI Agents: A Survey." https://arxiv.org/abs/2512.13564
- Huang et al. (2026). "Rethinking Memory Mechanisms of Foundation Agents." https://arxiv.org/abs/2602.06052

### Privacy
- GDPR Article 17. "Right to Erasure." https://gdpr-info.eu/art-17-gdpr/
- (2025). "Privacy-Preserving Graph Machine Learning Survey." PMC. https://pmc.ncbi.nlm.nih.gov/articles/PMC12056661/

### Cross-Session Identity
- Halpin, H. et al. (2010). "When owl:sameAs Isn't the Same." https://link.springer.com/chapter/10.1007/978-3-642-17746-0_20
- Solid Project. "Solid Protocol." https://solidproject.org/

### Interest Modeling and Temporal Evolution
- (2025). "Hierarchical Long and Short-term User Preference Modeling." Springer. https://link.springer.com/article/10.1007/s11704-025-41181-y
- (2023). "Multi-scale Temporal Hierarchical Attention for Sequential Recommendation." ScienceDirect. https://www.sciencedirect.com/science/article/abs/pii/S0020025523007119
- Ren, H. et al. (2025). "RecKG: Knowledge Graph for Recommender Systems." https://arxiv.org/html/2501.03598v1

### Provenance Standards
- W3C. "PROV-O: The PROV Ontology." https://www.w3.org/TR/prov-o/
- Belhajjame, K. et al. (2024). "User Modeling and User Profiling: A Comprehensive Survey." https://arxiv.org/pdf/2402.09660
