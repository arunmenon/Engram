# User Modeling Ontologies and Standards: Discovery Catalog

**Purpose:** Survey and catalog existing ontologies and standards for user modeling, personalization, and preference representation, assessed for relevance to the context-graph `cg-user` module extension.

**Context:** The context-graph project is a traceability-first context graph for AI agents, grounded in PROV-O (ADR-0011), with 5 edge types, 3 node types, a modular ontology (cg-core, cg-events, cg-entities, cg-memory, cg-views, cg-retention), and a dual-store architecture (Redis + Neo4j). We need a `cg-user` module to model user preferences, interests, behavior patterns, and personalization state, with full provenance tracing back to source events.

---

## 1. User Model Ontologies

### 1.1 GUMO (General User Model Ontology)

**What it covers:**
GUMO is a comprehensive ontology for representing distributed user models in semantic web environments. Developed at DFKI (German Research Center for Artificial Intelligence) by Heckmann, Schwartz, et al. (2005), it defines ~1000 groups of auxiliaries, predicates, and ranges organized under a `BasicUserDimensions` class hierarchy:

- **Demographic dimensions:** age, gender, birthplace, current location
- **Physiological state:** heart rate, body temperature, physical capabilities (subclass of BasicUserDimensions)
- **Emotional state:** current emotional state with temporal decay (15-minute default expiry)
- **Personality traits:** long-lived characteristics (months-level expiry)
- **Knowledge and skills:** domain knowledge, abilities (e.g., "ability to swim")
- **Interests and preferences:** recreational activities, consumption preferences (e.g., "reading poems", "French Bordeaux wines")
- **Goals and plans:** user intentions and planned activities

GUMO uses an `expiry` attribute on user model statements, providing built-in temporal validity -- emotional states expire in ~15 minutes while personality traits persist for months. This temporal decay model is directly analogous to our retention tier system (ADR-0008).

GUMO is tightly coupled with **UserML**, a markup language for serializing user model statements that separates syntax (UserML) from semantics (GUMO ontology).

**Maturity level:** Academic (published at UM 2005, maintained by DFKI). OWL-based. No W3C standardization. The ontology was browsable at www.gumo.org (now offline), and academic usage has declined since ~2012.

**Relevance to context-graph:** **HIGH**

**What it could contribute to cg-user:**
- The `BasicUserDimensions` hierarchy provides a well-organized taxonomy of user properties we could adapt
- The `expiry` / temporal decay concept maps directly to our retention tiers
- The distinction between short-lived (emotional state) and long-lived (personality) dimensions maps to our hot/warm/cold/archive tiers
- The predicate structure (hasInterest, hasKnowledge, hasSkill) suggests a property-based approach for REFERENCES edge roles on user entity nodes

**Gaps:**
- No provenance model -- user model statements have no source tracing
- No context-dependence -- preferences are global, not situation-specific
- No confidence/uncertainty model for preference strength
- No cross-session or cross-agent user identity model
- Academic-only; no industry adoption or active maintenance

---

### 1.2 UPO (User Profile Ontology) and UPOS (User Profile Ontology with Situation-Dependent Preferences)

**What it covers:**

**UPO** was developed as an extension of OntoNav's User Navigation Ontology (UNO) to emphasize context-awareness and user dimension modeling. It includes:
- A **User Modeling** component with user profiles and context information
- **User group classification** via a Reasoner and Rule Engine
- **Contextual Path-Finding** for personalized navigation based on user preferences
- **Fuzzy membership functions** where each concept in the ontology is a fuzzy set and users belong to the set to a certain degree (modeling preference strength)

**UPOS** (Coutand et al., 2007) extends this with situation-dependent preferences:
- Introduces a **Situation** as a ternary relation: `(Person, Context, SituationalProfileSubset)`
- Users can have different preference profiles for different contexts (e.g., "at work" vs. "at home")
- Sub-profiles are activated/deactivated based on the current situation
- Designed for context-aware mobile communication and information services

The key architectural insight from UPOS is that preferences are not global constants -- they are conditional on the user's current situation. This maps well to our session-based context model where different agent interactions may represent different user contexts.

**Maturity level:** Academic (UPO from multiple groups; UPOS published at IEEE AICT 2007). OWL-based. No standardization.

**Relevance to context-graph:** **HIGH**

**What it could contribute to cg-user:**
- The **situation-dependent preference model** is directly relevant -- in our system, a user's preferences when interacting with a coding agent differ from preferences with a research agent
- The **fuzzy membership** concept maps to preference strength/confidence scores
- The **sub-profile** concept could map to session-scoped or agent-scoped user preference views
- The ternary `(Person, Context, Preferences)` pattern could be encoded as REFERENCES edges with context metadata

**Gaps:**
- No provenance tracing for preference origins
- No temporal evolution model (when/how preferences change)
- No integration with event-sourced architectures
- Limited to human-designed situation categories (not learned from behavior)

---

### 1.3 PersonLink

**What it covers:**
PersonLink is a multilingual and multicultural ontology for representing **family relationships**, developed for the CAPTAIN MEMO memory prosthesis (assisting elderly individuals in remembering personal information). It:
- Defines family relationship types across cultures
- Handles cultural differences in kinship terminology
- Supports multilingual relationship descriptions
- Was validated against DBpedia and Freebase linked datasets

**Important clarification:** Despite its name suggesting cross-platform identity linking, PersonLink focuses on **kinship/family relationship modeling**, not cross-platform digital identity resolution. Cross-platform user identity linking is a separate research area (see Section 3.3).

**Maturity level:** Academic (published 2015). Available on TriplyDB. Narrow scope.

**Relevance to context-graph:** **LOW**

**What it could contribute to cg-user:**
- Limited direct applicability; family relationships are outside our domain
- The multilingual/multicultural approach to relationship naming could inform internationalization of user-facing concepts

**Gaps:**
- Does not address digital identity linking
- No preference or behavior modeling
- No relevance to AI agent interactions

---

### 1.4 FOAF (Friend of a Friend)

**What it covers:**
FOAF is one of the most widely adopted Semantic Web ontologies, created by Dan Brickley and Libby Miller (~2000). It provides an RDF/OWL vocabulary (19 classes, 44 object properties, 27 datatype properties) for describing:

- **Person identity:** `foaf:Person`, `foaf:name`, `foaf:mbox`, `foaf:homepage`
- **Social relationships:** `foaf:knows` (generic bidirectional social link)
- **Interests:** `foaf:interest` (links to a document about the interest), `foaf:topic_interest` (links to the topic itself)
- **Online accounts:** `foaf:OnlineAccount`, `foaf:accountName`, `foaf:accountServiceHomepage`
- **Groups:** `foaf:Group`, `foaf:member`
- **Organizations:** `foaf:Organization`
- **Projects:** `foaf:Project`, `foaf:currentProject`, `foaf:pastProject`

Key design decisions:
- `foaf:knows` is intentionally vague ("some kind of relationship") to maximize adoption
- Decentralized by design: users publish FOAF files on their own servers
- The `foaf:OnlineAccount` class enables cross-platform identity linking by associating multiple accounts with a single Person

**Maturity level:** De facto standard for Semantic Web social data. Widely adopted (millions of FOAF profiles). Not a W3C Recommendation but referenced in many W3C documents. Maintained informally. Last major spec update was 2014 but remains in active use.

**Relevance to context-graph:** **MEDIUM**

**What it could contribute to cg-user:**
- `foaf:Person` as the base class for our `cg:UserEntity` (or mapping via `rdfs:subClassOf`)
- `foaf:interest` / `foaf:topic_interest` pattern for linking users to interest entities
- `foaf:OnlineAccount` for cross-platform identity linking (a user interacting through multiple AI agents/tools)
- `foaf:knows` as a pattern for user-to-user relationships if our system tracks collaborative contexts
- Namespace alignment would give us interoperability with the large existing FOAF ecosystem

**Gaps:**
- No preference strength, polarity, or confidence
- No temporal evolution of interests
- No context-dependent preferences
- No behavior modeling
- `foaf:knows` is too vague for meaningful relationship typing
- No provenance for how/when interest associations were established

---

### 1.5 schema.org Person

**What it covers:**
schema.org `Person` is part of the schema.org vocabulary (maintained by Google, Microsoft, Yahoo, Yandex). It extends `schema:Thing` and provides:

- **Basic identity:** `name`, `givenName`, `familyName`, `email`, `telephone`, `url`, `image`
- **Professional:** `jobTitle`, `worksFor`, `colleague`, `alumniOf`
- **Expertise:** `knowsAbout` (areas/topics the person is knowledgeable about), `knowsLanguage`
- **Relationships:** `knows` (generic), `relatedTo`, `spouse`, `children`, `parent`, `sibling`
- **Cross-platform identity:** `sameAs` (URLs of profiles on other platforms -- Twitter, LinkedIn, etc.)
- **Interaction tracking:** `interactionStatistic` uses `InteractionCounter` to count actions like shares, comments, likes

The `InteractionCounter` type is particularly relevant:
- `interactionType` references a schema.org `Action` subtype (e.g., `LikeAction`, `DislikeAction`, `CommentAction`, `ShareAction`)
- `userInteractionCount` provides the count
- `interactionService` identifies the platform
- This enables structured tracking of user engagement behavior

**Maturity level:** **Industry standard** (W3C Community Group). Supported by all major search engines. Actively maintained with frequent releases. The most widely deployed structured data vocabulary on the web.

**Relevance to context-graph:** **HIGH**

**What it could contribute to cg-user:**
- `schema:Person` as an interoperable identity type (aligns with our existing schema.org Action role vocabulary in ADR-0011)
- `schema:knowsAbout` for user expertise/knowledge modeling
- `schema:sameAs` for cross-platform identity linking
- `schema:InteractionCounter` + `Action` subtypes for behavior pattern tracking
- `LikeAction` / `DislikeAction` provide a built-in preference polarity model
- Already partially integrated via ADR-0011's schema.org Action role alignment

**Gaps:**
- No preference strength quantification (only count-based interaction tracking)
- No temporal preference evolution
- No context-dependent preferences
- Designed for SEO/web indexing, not for AI agent personalization
- No provenance model

---

## 2. Preference and Interest Standards

### 2.1 Ontology-Based Preference Modeling (Research Patterns)

There is no single dominant standard for preference modeling, but research converges on several patterns:

**Preference representation dimensions:**
| Dimension | Description | Formalization Approaches |
|-----------|-------------|--------------------------|
| **Strength/Degree** | How much the user prefers something | Numeric scale (0-1 float), fuzzy membership, ordinal (high/medium/low) |
| **Polarity** | Like vs. dislike | Binary (like/dislike), ternary (like/neutral/dislike), continuous (-1 to +1) |
| **Context-dependence** | Preferences that vary by situation | UPOS situation-dependent sub-profiles, context attributes on preference edges |
| **Temporal evolution** | How preferences change over time | Timestamp + decay function, versioned preference snapshots, event-sourced changes |
| **Confidence** | How certain the system is about the preference | Bayesian confidence, observation count, explicit vs. implicit signal |
| **Source** | Where the preference was inferred from | Explicit (stated by user), implicit (inferred from behavior), inherited (from group) |

**Key research findings for preference modeling:**
- **Long-term vs. short-term preferences** (IEEE ICWS 2011): Systems that model both long-term stable preferences and short-term contextual interests outperform single-model approaches
- **Dynamic preferences via spatiotemporal knowledge graphs** (Complex & Intelligent Systems, 2024): User preferences are modeled as dynamic entities influenced by temporal, spatial, and situational contexts
- **Fuzzy preference modeling** (multiple papers): Preferences as fuzzy set memberships allow partial and uncertain preference representation
- **Ontology evolution for preference tracking** (University of Vigo, 2024): Ontology evolution techniques update the preference model as user behavior changes over social media

**Relevance to context-graph:** **HIGH** -- these patterns directly inform the design of preference edges and properties in our cg-user module.

**What this contributes to cg-user:**
- A preference should be modeled as an edge (or qualified edge) with properties: `strength` (float), `polarity` (positive/negative/neutral), `confidence` (float), `source` (explicit/implicit/inferred), `context` (session/agent/situation metadata)
- Preferences need temporal tracking -- provenance events record when a preference was stated or inferred, and the preference edge carries `first_observed`, `last_observed`, `observation_count`
- This maps naturally to our event-sourced architecture: preference changes are events, and the current preference state is a projection

---

### 2.2 IMS Learner Information Package (LIP)

**What it covers:**
IMS LIP (1EdTech/IMS Global) is a specification for representing learner profile data with 12 core components:
1. **Identification** -- name, contact, demographics
2. **Goals** -- learning objectives
3. **Qualifications** -- certifications, degrees, licenses
4. **Activity** -- learning activities undertaken
5. **Interest** -- hobbies and recreational activities
6. **Competency** -- skills, knowledge, abilities (cognitive, affective, psychomotor)
7. **Accessibility** -- learning preferences (cognitive, physical, technological)
8. **Transcript** -- academic records
9. **Affiliation** -- organizational memberships
10. **Security** -- authentication keys
11. **Relationship** -- links between LIP components
12. **Content Type** -- media type preferences

The **Competency** and **Interest** components are most relevant:
- Competency captures skills/knowledge/abilities with formal taxonomies
- Interest captures recreational and personal interest areas
- Accessibility/Preferences distinguishes cognitive preferences (learning style), physical preferences (display), and technological preferences (platform)

**Maturity level:** **Industry standard** (1EdTech/IMS Global). XML-based. Widely adopted in educational technology. Well-maintained.

**Relevance to context-graph:** **MEDIUM**

**What it could contribute to cg-user:**
- The competency model (skills/knowledge/abilities with levels) maps well to tracking user expertise with AI tools
- The distinction between cognitive, physical, and technological preferences is useful for multi-modal AI agent interactions
- The interest taxonomy pattern (hierarchical categorization of interests) is reusable
- The OntobUMf framework (which extends IMS LIP) adds behavior modeling with activity levels and user stereotypes

**Gaps:**
- Designed for educational/learner contexts, not general AI agent interactions
- XML-based schema, not OWL/RDF
- No temporal evolution tracking
- No provenance model
- No preference strength/confidence
- No context-dependent preferences

---

### 2.3 Knowledge Graph Embedding Approaches for User Interest Modeling

**What it covers:**
Modern recommendation systems increasingly use knowledge graph embeddings to model user interests:

- **Embedding-based methods**: Translate user preferences and item properties into a shared vector space. KG entities (items, attributes, categories) are embedded alongside user representations.
- **Propagation-based methods**: User preferences propagate through the knowledge graph via entity relationships, enabling multi-hop interest discovery.
- **Neuro-symbolic approaches**: Combine KG embeddings with first-order logic rules for explainable preference modeling.

Key architectural patterns:
- **RecKG** (2025): A knowledge graph specifically designed for recommender systems that unifies user-item interactions, item metadata, and user profiles into a single graph
- **User embeddings evolve**: As new interactions are observed, user embedding representations are updated to reflect preference changes
- **Cold-start handling**: KG embeddings help model preferences for new users by leveraging item-side knowledge

**Maturity level:** Active research area (2023-2026). No single standard. Multiple frameworks (DKN, KGAT, KGCN, etc.).

**Relevance to context-graph:** **HIGH**

**What it could contribute to cg-user:**
- Our SIMILAR_TO edges (cosine similarity > threshold) already implement a form of embedding-based similarity. Extending this to user-item similarity is natural.
- User preference embeddings could be stored as node properties (we already store event embeddings)
- Preference propagation through our entity graph (via REFERENCES edges) could discover implicit interests
- The RecKG pattern of unifying interactions, metadata, and profiles in a single graph aligns with our architecture

**Gaps:**
- No standardized ontology -- each system defines its own schema
- Embedding approaches are opaque (no provenance for why a preference was inferred)
- Our system prioritizes traceability, which requires explicit provenance that embedding-only approaches lack

---

## 3. Behavior Pattern and Identity Models

### 3.1 Ontology-Based User Behavior Modeling (OntobUMf and Related)

**What it covers:**
The Ontology-based User Modeling framework (OntobUMf) provides a generic framework for behavior modeling and user classification:

- Extends IMS LIP with a **Behavior** concept defining interaction characteristics
- Models `level_of_activity` (very active, active, passive, inactive)
- Models `type_of_activity` (reading, writing, sharing, etc.)
- Models `level_of_knowledge_sharing` as a behavioral indicator
- Classifies users into **stereotypes** (readers, writers, lurkers) based on observed behavior patterns
- Uses ontology-based reasoning to infer user categories from behavior

Research patterns for behavior modeling include:
- **Browsing habit monitoring**: Automatically constructing user ontologies from semantic sessions where each session updates the user model
- **Behavior sequence classification**: Categorizing behavior sequences based on interest patterns
- **Driver behavior ontology**: DriverOntology as an example of domain-specific behavior modeling with fuzzy rule-based classification

**Maturity level:** Academic. Multiple independent research groups. No single standard.

**Relevance to context-graph:** **HIGH**

**What it could contribute to cg-user:**
- User activity stereotypes (power user, casual user, explorer, etc.) derived from interaction event patterns
- Activity level tracking from event frequency and type distribution
- Behavior-based user segmentation using our existing event data
- The "semantic session" concept maps directly to our session model -- each session contributes behavioral signals
- Stereotypes could be modeled as Entity nodes (type=concept, subtype=user_stereotype) with REFERENCES edges linking users to their inferred stereotypes

**Gaps:**
- No standardized behavior taxonomy for AI agent interactions
- Existing behavior ontologies are domain-specific (knowledge management, driving, education)
- No model for skill progression or learning curves
- No integration with event-sourced architectures

---

### 3.2 schema.org Action Hierarchy for Interaction Tracking

**What it covers:**
schema.org defines a rich hierarchy of user interaction types under the `Action` class:

- **AssessAction** > `ReactAction` > `LikeAction`, `DislikeAction`, `AgreeAction`, `DisagreeAction`
- **InteractAction** > `CommunicateAction` > `AskAction`, `ReplyAction`, `CommentAction`, `ShareAction`
- **ConsumeAction** > `ReadAction`, `ViewAction`, `ListenAction`, `WatchAction`, `UseAction`
- **CreateAction** > `WriteAction`, `DrawAction`, `CookAction`, `PhotographAction`
- **OrganizeAction** > `BookmarkAction`, `PlanAction`
- **SearchAction** -- represents searching

Combined with `InteractionCounter`:
```
InteractionCounter {
  interactionType: Action (e.g., LikeAction)
  userInteractionCount: Integer
  interactionService: WebSite | SoftwareApplication
}
```

This provides a built-in vocabulary for:
- What the user did (Action type)
- How often (count)
- Where (service/platform)

**Maturity level:** **Industry standard** (schema.org). Widely deployed.

**Relevance to context-graph:** **HIGH** -- already partially adopted via ADR-0011's schema.org Action roles.

**What it could contribute to cg-user:**
- Action type hierarchy for classifying user interactions with AI agents
- `LikeAction` / `DislikeAction` for explicit preference signals
- `UseAction` for tool/feature usage tracking
- `SearchAction` for interest signal inference
- `InteractionCounter` pattern for aggregate behavior metrics on user nodes
- Extends our existing schema.org alignment (REFERENCES edge roles use schema.org Action vocabulary)

**Gaps:**
- No temporal granularity (counts, not time series)
- No context-dependent action semantics
- No preference inference from actions
- Counter-based, not event-sourced

---

### 3.3 Cross-Platform Identity: WebID, owl:sameAs, and Solid

**What it covers:**

**WebID** (W3C WebID Community Group):
- A URI-based identity system where each user has a WebID (a dereferenceable URI)
- The WebID Profile Document (RDF) contains identity assertions
- Used as the universal username in the Solid ecosystem
- Supports `owl:sameAs` declarations linking multiple identities

**owl:sameAs in practice:**
- The standard mechanism for asserting two URIs refer to the same entity
- Extensively used in Linked Data for cross-dataset identity linking
- Known problems: "the sameAs problem" -- owl:sameAs is frequently misused for partial overlap rather than true identity, leading to incorrect inferences
- Research proposes weaker alternatives: `skos:closeMatch`, `skos:exactMatch`, or custom similarity predicates with confidence scores

**Solid Protocol:**
- Decentralized personal data stores (Pods) where users control their data
- WebID + OIDC for authentication
- RDF/Linked Data for data representation
- Users choose where to store data and grant access per-application
- Relevant model for agent-mediated personalization where the user owns their preference data

**Maturity level:** WebID is a W3C Community Group specification. owl:sameAs is part of OWL (W3C Recommendation). Solid is actively developed (solidproject.org) with multiple implementations.

**Relevance to context-graph:** **MEDIUM**

**What it could contribute to cg-user:**
- Our existing entity resolution strategy (ADR-0011 Section 3) already uses a three-tier approach (exact/close/related) that parallels the owl:sameAs problem's solutions
- For user identity: a `cg:UserEntity` could have a `SAME_AS` edge to other user entities across sessions/agents, using our existing `SAME_AS` edge type with confidence
- The Solid Pod concept is relevant if users want to own/control their personalization data
- WebID as a stable user identifier across agent interactions

**Gaps:**
- WebID/Solid are infrastructure standards, not user modeling ontologies
- No preference or behavior modeling
- owl:sameAs semantics are too strong for probabilistic identity linking (our SAME_AS with confidence is better)

---

## 4. Provenance Integration: PROV-O for User Model Provenance

Our existing PROV-O foundation (ADR-0011) provides the provenance framework that **none** of the above ontologies include natively. This is our key differentiator.

**How PROV-O enables traceable user modeling:**

| User Model Concept | PROV-O Mapping | Implementation |
|-------------------|----------------|----------------|
| User states a preference | `prov:Activity` (event) that `prov:wasAssociatedWith` user and `prov:generated` the preference entity | Event with `event_type=user.preference.stated` |
| System infers a preference | `prov:Activity` that `prov:used` behavioral events and `prov:generated` the preference entity | Enrichment pipeline event with `wasDerivedFrom` linking to source events |
| Preference changes | New event `prov:wasRevisionOf` the previous preference entity | Immutable event records preference change; old preference retained |
| Confidence in preference | `prov:qualifiedGeneration` with confidence attribute | Confidence metadata on the REFERENCES edge between user and preference |

The **PAV (Provenance, Authoring and Versioning) ontology** extends PROV-O with:
- `pav:authoredBy` / `pav:curatedBy` for distinguishing who created vs. who validated
- `pav:version` / `pav:previousVersion` for tracking preference evolution
- `pav:createdOn` / `pav:lastUpdateOn` for temporal tracking

**Relevance to context-graph:** **HIGH** -- PAV's versioning vocabulary could directly inform our preference evolution model.

---

## 5. Summary Assessment Matrix

| Ontology/Standard | Domain | Maturity | Relevance | Key Contribution | Primary Gap |
|-------------------|--------|----------|-----------|------------------|-------------|
| **GUMO** | User dimensions | Academic | HIGH | Dimension taxonomy, temporal decay | No provenance |
| **UPO/UPOS** | Context-aware preferences | Academic | HIGH | Situation-dependent sub-profiles | No event sourcing |
| **PersonLink** | Family relationships | Academic | LOW | None for our domain | Wrong domain |
| **FOAF** | Social identity | De facto standard | MEDIUM | Person identity, interest linking, accounts | No preference strength |
| **schema.org Person** | Web identity | Industry standard | HIGH | Identity, knowsAbout, sameAs, InteractionCounter | Not for AI personalization |
| **IMS LIP** | Learner profiles | Industry standard | MEDIUM | Competency model, interest taxonomy | Educational focus |
| **Preference Research** | Recommendation | Research | HIGH | Strength/polarity/confidence patterns | No single standard |
| **OntobUMf** | Behavior modeling | Academic | HIGH | Activity stereotypes, behavior classification | Domain-specific |
| **schema.org Action** | Interaction tracking | Industry standard | HIGH | Action type hierarchy, interaction counters | Count-based, not event-sourced |
| **WebID/Solid** | Decentralized identity | W3C Community | MEDIUM | User-owned data, stable identifiers | Not user modeling |
| **KG Embeddings** | Interest modeling | Research | HIGH | Embedding-based similarity, propagation | No provenance |
| **PAV** | Provenance versioning | Academic/W3C | HIGH | Version tracking, authoring attribution | Not user-specific |

---

## 6. Architectural Implications for cg-user Module

Based on this survey, the `cg-user` module should:

### 6.1 Adopt from existing standards
- **schema.org Person** as the interoperable grounding for UserEntity (extends our existing schema.org alignment)
- **schema.org Action hierarchy** for classifying user interaction events
- **FOAF interest/topic_interest** pattern for linking users to interest entities
- **GUMO's temporal decay** concept (already aligned with our retention tiers)
- **UPOS's situation-dependent sub-profiles** mapped to session/agent-scoped preferences
- **PAV's versioning vocabulary** for preference evolution tracking

### 6.2 Design new vocabulary for
- **Preference edges** with properties: strength, polarity, confidence, source, context
- **User behavior stereotypes** derived from event pattern analysis
- **Skill/expertise levels** for user-tool interactions (inspired by IMS LIP competency but adapted for AI agents)
- **Preference provenance** tracing every preference to its source events (our unique differentiator)

### 6.3 Preserve core principles
- Every preference/interest/behavior pattern must trace back to source events (traceability-first)
- User model state is a projection, not a source of truth (derived from immutable events)
- Preferences are entities with provenance, not opaque embeddings
- Cross-session user identity uses our existing SAME_AS edge type with confidence scores

---

## References

### User Model Ontologies
- Heckmann, D., Schwartz, T., et al. (2005). [GUMO - The General User Model Ontology](https://link.springer.com/chapter/10.1007/11527886_58). UM 2005.
- Coutand, O. et al. (2007). [UPOS: User Profile Ontology with Situation-Dependent Preferences Support](https://ieeexplore.ieee.org/document/4455987/). IEEE AICT.
- Brickley, D. & Miller, L. [FOAF Vocabulary Specification](http://xmlns.com/foaf/spec/).
- schema.org. [Person Type](https://schema.org/Person).
- Djaghloul, Y. et al. (2015). [PersonLink: An Ontology Representing Family Relationships](https://link.springer.com/chapter/10.1007/978-3-319-25747-1_1).

### Preference and Interest Modeling
- IMS Global. [Learner Information Package Specification](https://www.imsglobal.org/profiles/index.html).
- schema.org. [InteractionCounter](https://schema.org/InteractionCounter).
- schema.org. [Action](https://schema.org/Action).
- Ren, H. et al. (2025). [RecKG: Knowledge Graph for Recommender Systems](https://arxiv.org/html/2501.03598v1).
- Sieg, A. et al. (2007). [Ontology-Based Recommendation with Long-Term and Short-Term Preferences](https://ieeexplore.ieee.org/document/5772322/).
- Chen, Y. et al. (2024). [Dynamic Preference Recommendation Based on Spatiotemporal Knowledge Graphs](https://link.springer.com/article/10.1007/s40747-024-01658-y).

### Behavior and Identity
- Razmerita, L. (2011). [An Ontology-Based Framework for Modeling User Behavior](https://www.researchgate.net/publication/224238777_An_Ontology-Based_Framework_for_Modeling_User_Behavior-A_Case_Study_in_Knowledge_Management).
- Solid Project. [Solid Protocol](https://solidproject.org/).
- W3C. [WebID Profile](https://solid.github.io/webid-profile/).
- Halpin, H. et al. (2010). [When owl:sameAs Isn't the Same](https://link.springer.com/chapter/10.1007/978-3-642-17746-0_20).

### Provenance
- W3C. [PROV-O: The PROV Ontology](https://www.w3.org/TR/prov-o/).
- Ciccarese, P. et al. (2013). [PAV Ontology: Provenance, Authoring and Versioning](https://pmc.ncbi.nlm.nih.gov/articles/PMC4177195/).
- Belhajjame, K. et al. (2024). [User Modeling and User Profiling: A Comprehensive Survey](https://arxiv.org/pdf/2402.09660).
