# Review: Ontology-Guided Extraction and Validation Patterns

**Reviewer**: reviewer-3
**Date**: 2026-02-12
**Reviewed Document**: `docs/research/extraction-ontology-guided.md` (researcher-3)
**Context Documents**: ADR-0011 (Ontological Foundation), ADR-0012 (User Personalization Ontology)

---

## Summary of Key Findings

The research report investigates how our cg-user ontology (ADR-0011 core types + ADR-0012 user personalization module) can drive knowledge extraction from merchant-agent conversations. The key findings are:

- **Ontology-Based Information Extraction (OBIE)** has shifted from rule-based systems to LLM-era "schema-as-prompt" paradigms, where ontology definitions are serialized into prompts to guide structured extraction.
- **Schema-as-prompt works with current LLMs** when ontology definitions are translated into targeted extraction templates with concrete examples and constraints -- raw OWL/RDF serialization does not work.
- **Three serialization approaches** are compared: Pydantic + Instructor (recommended), Natural Language descriptions, and ODKE+-style per-type snippets.
- **Four-layer validation pipeline** proposed: Schema Validation (Pydantic) -> Ontology Constraint -> Graph Consistency -> Confidence Gating.
- **Entity resolution during extraction** via known-entity injection into prompts follows the Graphiti/Zep pattern, with a three-tier strategy (exact, close, related match).
- **Confidence calibration** requires external mechanisms (logprobs, self-consistency sampling, Cleanlab TLM) since LLMs do not produce well-calibrated confidence natively.
- **Ontology evolution** should be human-in-the-loop: automated gap detection proposes changes; humans approve schema modifications.
- **SHACL validation** is recommended as a periodic batch audit mechanism, not on the hot path, consistent with ADR-0011's deferred SHACL strategy.

---

## Strengths of the Research

### 1. Strong Alignment with Our Architecture

The report consistently maps recommendations back to ADR-0011 and ADR-0012. The four-layer validation pipeline mirrors ADR-0011 Section 7's layered enforcement strategy. The Pydantic extraction models map 1:1 to ADR-0012 node schemas. The three-tier entity resolution directly references ADR-0011 Section 3. This is not theoretical research disconnected from our system -- it reads as a practical implementation guide.

### 2. Honest, Nuanced Assessment of LLM-Based Extraction

Section 1.4 ("Honest Assessment") is the strongest section of the report. Rather than overselling the approach, it clearly delineates what works well (enum constraints, nested schema extraction, value ranges), what requires careful handling (raw ontology serialization, edge endpoint constraints, confidence calibration, entity resolution), and why our specific system is well-suited (moderately sized ontology, specific property constraints, bounded merchant domain). The 65-90% semantic accuracy and 80-90% schema compliance figures with two-stage validation are cited with appropriate sourcing.

### 3. Concrete, Executable Examples

The Pydantic extraction model for Preference (Section 2.2, Approach A) is directly usable code. The end-to-end merchant conversation example (Section 9) walks through extraction output and Cypher operations. The entity resolution examples (Section 4.6) use merchant-domain entities (USPS, QuickBooks, CSV export). This concreteness significantly increases the report's practical value.

### 4. Comprehensive Literature Coverage

The reference list spans 35+ sources across six domains (OBIE, schema-as-prompt, entity resolution, confidence calibration, ontology evolution, SHACL). The OBIE coverage bridges the classical Wimalasuriya & Dou (2010) foundation to the 2025 LLM-era systems (ODKE+, RELATE, SPIREX, AutoSchemaKG). The SPIRES/OntoGPT analysis is particularly well done, showing how LinkML-style schemas translate to our Pydantic approach.

### 5. Sound Recommendation for Pydantic as Schema Bridge

The recommendation to use Pydantic models as a triple-duty bridge (extraction target, LLM output validation, graph operation mapping) is architecturally elegant and well-justified. It leverages our existing Pydantic v2 stack, integrates with the Instructor library for automatic retry on validation failure, and avoids introducing a separate schema language (like LinkML or OWL) that the team would need to learn.

---

## Gaps and Weaknesses Identified

### 1. Missing: Embedding-Based and Graph Neural Network Approaches

The report focuses almost exclusively on LLM-based extraction with structured output. There is no discussion of:

- **Graph Neural Networks (GNNs) for extraction**: Systems like R-GCN and CompGCN have been used for relation extraction guided by ontology structure. For our entity-rich merchant domain, GNN-based link prediction could complement LLM extraction, especially for inferring INTERESTED_IN and ABOUT edges from graph structure rather than conversation text alone.
- **KG embedding methods**: TransE, RotatE, and more recent embedding-based methods for knowledge graph completion could serve as a complementary signal for entity resolution and relation prediction. These are well-suited for Stage 3 re-consolidation where cross-session patterns are detected.
- **Non-LLM extraction baselines**: For high-volume, low-complexity extraction tasks (e.g., detecting tool usage frequency for implicit preferences), simpler NER/regex-based extractors may be more cost-effective and faster than full LLM calls. The report does not discuss when NOT to use LLMs.

**Impact**: The absence of these approaches means the pipeline design is over-reliant on LLMs for all extraction stages. A production system should use LLMs for complex semantic extraction (Stage 2) but consider cheaper alternatives for Stage 1 rule-based extraction and Stage 3 graph-structural inference.

### 2. Latency Analysis of the Validation Pipeline is Absent

The four-layer validation pipeline (Section 3.1) is architecturally sound but the report does not estimate latency impact. Each layer adds processing time:

- **Layer 1 (Pydantic)**: Negligible (<1ms)
- **Layer 2 (Ontology constraint)**: Low (~1-5ms) for application-level rule checks
- **Layer 3 (Graph consistency)**: Potentially high -- requires Neo4j queries to check duplicate preferences, entity existence, supersession. Each query could be 10-50ms depending on graph size and whether the graph store connection is warm.
- **Layer 4 (Confidence gating)**: Negligible if using source-type priors only; significant if using self-consistency (N * LLM call latency)

For the Stage 2 enrichment path (batch, async), total latency is acceptable. But if any validation is needed on the real-time ingestion path (Stage 1 explicit preferences), the graph consistency layer (Layer 3) could add unacceptable latency. The report should have recommended which layers apply to which stages.

**Recommendation**: Layer 3 (Graph Consistency) should be async-only, never on the Stage 1 hot path. Stage 1 should only apply Layers 1-2 synchronously, with Layer 3 deferred to a validation queue.

### 3. Entity Resolution Scalability Concern

The known-entity injection approach (Section 4.3) injects up to 100 entities into the extraction prompt. This is practical for early-stage systems with few entities per user, but:

- **Context window pressure**: At 100 entities with name, type, and ID, this consumes ~2K tokens. Combined with the extraction schema, system prompt, and conversation text, this may push total prompt size above 8K tokens, limiting the conversation window available for extraction.
- **Entity growth**: A merchant active for 6 months may reference 500+ entities across sessions. The `limit=100` is a hard cutoff with no stated ranking strategy. Which 100 entities are included? Most recent? Most referenced? Most relevant to the current conversation topic?
- **Missing: vector similarity retrieval for entity candidates**: Rather than injecting a flat list, the system should embed the conversation text and retrieve the top-k most relevant existing entities via vector similarity. This is how Graphiti actually works -- the report describes Graphiti's entropy-gated fuzzy matching but omits its retrieval-augmented entity resolution.

**Recommendation**: Use embedding-based retrieval to select the most relevant entities for injection, not a fixed limit of the most recent N entities.

### 4. Confidence Calibration Approach is Under-Specified

Section 6 presents three calibration approaches (logprobs, self-consistency, Cleanlab TLM) and recommends a hybrid. However:

- **The hybrid formula (Section 6.3) has arbitrary weights**: The 0.7/0.3 split for logprobs and 0.6/0.4 split for consistency have no empirical justification. These should be treated as hyperparameters to be tuned, not hard-coded decisions.
- **Anthropic Claude does not expose logprobs**: Since our system may use Claude models (given this project's context), the logprob approach is unavailable for a significant model family. The report acknowledges this ("Anthropic does not as of 2025") but still recommends logprobs as a primary signal.
- **Self-consistency is too expensive for real-time**: At N=5 samples, self-consistency multiplies LLM cost by 5x. The report correctly flags this for batch processing only, but the recommended confidence formula does not clearly distinguish the real-time vs. batch paths.
- **Missing: calibration dataset and evaluation methodology**: The report mentions "after 1000 extractions, compute actual precision per confidence bucket" (Section 6.4) but provides no methodology for creating ground truth labels. In our merchant-agent domain, who labels the ground truth? How is inter-annotator agreement measured?

**Recommendation**: Start with source-type priors only (no logprobs, no self-consistency) for MVP. Add calibration mechanisms incrementally once production data is available for tuning.

### 5. SHACL Analysis is Thorough but Overly Optimistic About n10s

Section 8 provides a detailed SHACL shape definition and a useful comparison table (Section 8.3). However:

- **n10s has significant limitations**: The Neosemantics (n10s) plugin translates between Neo4j's property graph model and RDF. This translation is lossy for edge properties (Neo4j edge properties must be reified as intermediate RDF nodes), and n10s does not support all SHACL features (notably `sh:sparql` constraints require a SPARQL endpoint that n10s does not fully provide).
- **SHACL validation under graph updates (Section 8.5)**: The cited paper is about incremental RDF validation, not Neo4j property graph validation. Applying its delta-validation approach to Neo4j via n10s would require significant engineering.

**Impact**: Low for MVP (SHACL is deferred). But the report should note these limitations to prevent over-optimism about SHACL's near-term viability for Neo4j property graphs.

### 6. Missing: Error Recovery and Partial Extraction

The report describes what happens when extraction succeeds (validation, entity resolution, graph insertion) and when it fails validation (retry via Instructor). But it does not address:

- **Partial extraction**: What if the LLM correctly extracts 3 out of 4 preferences from a conversation but hallucinates the 4th? The pipeline should be able to accept the 3 valid extractions while rejecting the hallucinated one. The current design validates the entire extraction batch as a unit.
- **Extraction failure modes**: What if the LLM times out? What if it returns structurally valid but semantically nonsensical output (e.g., strength=0.99 for a weakly stated preference)? The report addresses schema validation but not semantic plausibility checking.
- **Retry budget**: The Instructor library supports `max_retries=3`, but what if all retries fail? The report does not define a fallback strategy (skip, alert, degrade to simpler extraction).

**Recommendation**: Design the pipeline to validate and accept individual extractions independently, not as a batch. Add a semantic plausibility checker (possibly a second, cheaper LLM call or rule-based heuristics) between Layers 2 and 3.

### 7. Ontology Evolution is Under-Developed

Section 7 proposes a gap detection mechanism and human-in-the-loop review workflow. This is directionally correct but lacks:

- **Concrete thresholds**: "min_occurrences = 10, window_days = 30" is arbitrary. What if a critical new entity type appears 5 times in 3 days?
- **Schema migration strategy**: Adding a new enum value (e.g., "pricing" to PreferenceCategory) requires updating Pydantic models, extraction prompts, and validation rules. The report says "no graph migration needed (Neo4j is derived; re-project with new rules)" but does not address backward compatibility of API responses -- existing clients may not handle new enum values.
- **Missing: automated ontology alignment**: When the unconstrained extraction discovers a new type, the system could automatically propose alignment to existing types via embedding similarity (e.g., "Is 'pricing strategy' a subtype of 'domain' or does it warrant a new category?"). This is a lighter-weight approach than full human review for every candidate.

---

## Specific Examples: How Our cg-user Ontology Works as Extraction Schema

To evaluate whether the ontology-as-extraction-schema approach actually works for our system, I traced through several concrete scenarios:

### Example 1: Preference Extraction from Explicit Statement

**Input**: "I always want email notifications for disputes, not those in-app popups."

**ADR-0012 Preference schema maps to extraction targets:**
- `category`: "communication" (from the 6-value enum -- correctly constrained)
- `key`: "dispute_notification_method" (free-form string -- LLM must generate this)
- `polarity`: "positive" (from the 3-value enum -- correctly constrained)
- `strength`: 0.95 (float 0.0-1.0 -- "always" maps to high strength, as the extraction prompt instructs)
- `confidence`: 0.9 (float 0.0-1.0 -- explicit statement = high confidence per ADR-0012 Section 5)
- `source`: "explicit" (from the 4-value enum -- correctly constrained)
- `context`: "dispute_management" (free-form string -- LLM must infer scope)
- `scope`: "global" (from the 3-value enum -- correctly constrained)

**Verdict**: This works well. The constrained fields (category, polarity, source, scope) are finite enums that LLMs handle reliably in structured output mode. The free-form fields (key, context, about_entity) require LLM judgment but are bounded by the merchant domain.

### Example 2: Skill Extraction from Behavioral Evidence

**Input**: "I've done a bunch of API integrations for my store. I connected Shopify, our shipping provider, and a couple of payment gateways."

**ADR-0012 Skill schema + HAS_SKILL edge:**
- Skill node: `name`: "API integration", `category`: "tool_proficiency"
- HAS_SKILL edge: `proficiency`: 0.8, `confidence`: 0.75, `source`: "declared"

**Verdict**: This works but the `proficiency` estimate is subjective. The merchant said "a bunch" and listed examples, which suggests competence but not expert-level. The LLM must map qualitative language to a 0.0-1.0 quantitative scale. The extraction prompt's guidance ("0.8=advanced") helps, but different LLMs will produce different proficiency estimates for the same input. This is an area where self-consistency sampling (Section 6, Approach 2) would add value -- if 4/5 runs estimate proficiency as 0.75-0.85, the estimate is robust.

### Example 3: Implicit Preference from Behavioral Pattern (Stage 2)

**Input**: Merchant has used the mobile app for 15 of 17 recent sessions (behavioral data, not conversation text).

**Challenge**: This is not extractable from conversation text. The extraction pipeline needs access to session metadata (device type, session count). The report's Pydantic extraction model assumes conversation text as input but does not address extraction from structured behavioral data.

**Verdict**: The ontology schema (Preference with source="implicit_unintentional") correctly models the output, but the extraction mechanism needs a separate path for behavioral data (frequency analysis, not LLM extraction). The report mentions this in Section 10.1 (Stage 1 = rule-based) but the extraction models in Section 2 are all LLM-oriented.

### Example 4: Entity Resolution for "QuickBooks" vs. "Quickbooks Online" vs. "QB"

**Input**: Different sessions reference "QuickBooks", "Quickbooks Online", and "QB" -- all the same service.

**ADR-0011 Entity resolution strategy:**
- "QuickBooks" -> "quickbooks" (normalized) -> exact match if Entity exists
- "Quickbooks Online" -> "quickbooks online" -> close match: embedding similarity with "quickbooks" likely > 0.9 -> SAME_AS edge
- "QB" -> "qb" -> exact match fails; embedding similarity with "quickbooks" likely < 0.8 (short acronym, low entropy per Graphiti's approach); requires alias table or LLM reasoning

**Verdict**: The three-tier resolution works for common variations but struggles with short acronyms. The Graphiti entropy-gating approach (Section 4.4) correctly identifies "QB" as a low-entropy string unsuitable for fuzzy matching. The practical solution is an alias table for common domain abbreviations. The report should have recommended maintaining a merchant-domain alias dictionary for high-frequency abbreviations.

### Example 5: Edge Endpoint Constraint Enforcement

**Extracted**: Preference("bookkeeping_tool") -[ABOUT]-> Entity("QuickBooks", type="service")

**ADR-0012 PG-Schema**: `ABOUT` is defined as `FROM Preference TO Entity` with no type constraint on the target Entity. This is correct -- a preference can be about any entity type (service, tool, concept, resource).

**But**: The extraction model includes `about_entity_type` as a field the LLM must fill. This creates a potential inconsistency -- the LLM might assign `about_entity_type: "tool"` while the existing Entity("QuickBooks") has `entity_type: "service"`. The validation pipeline (Layer 2, ontology constraints) should flag this mismatch.

**Verdict**: The schema is correct, but the extraction model needs a post-processing step to reconcile extracted entity types with existing entity types in the graph.

---

## Recommendation for Validation Pipeline Design

Based on the analysis above, I recommend the following validation pipeline architecture:

### Stage 1 (Hot Path -- Explicit Preference Events)

```
Event (user.preference.stated)
  |
  v
[Layer 1: Pydantic Validation]  -- Immediate, synchronous
  |
  v
[Layer 2: Ontology Constraints]  -- Immediate, synchronous
  |
  v
Graph Insertion (with optimistic entity creation)
  |
  v
[Layer 3: Graph Consistency]  -- Async, queued within 30 seconds
  |                             -- Deduplicate, supersede, reconcile entities
  v
[Layer 4: Confidence Adjustment]  -- Async, on next Stage 2 batch
```

**Rationale**: Stage 1 must be fast. Layers 1-2 are in-process and add <5ms. Graph insertion is optimistic (insert, then reconcile). Layers 3-4 run asynchronously to avoid blocking event ingestion.

### Stage 2 (Batch Path -- LLM Extraction)

```
Conversation Text + Known Entities (embedding-retrieved, top-50)
  |
  v
[LLM Extraction (Pydantic + Instructor, max_retries=2)]
  |
  v
[Layer 1: Pydantic Validation]  -- Automatic via Instructor
  |
  v
[Per-extraction filtering]  -- Accept individual valid extractions, reject invalid ones
  |
  v
[Layer 2: Ontology Constraints]  -- Per-extraction
  |
  v
[Layer 3: Graph Consistency]  -- Batch: deduplicate, entity resolution, supersession
  |
  v
[Layer 4: Confidence Gating]  -- Source-type priors for MVP; add calibration later
  |
  v
Graph Insertion
```

**Rationale**: Stage 2 is async and batch-oriented. Full four-layer validation is applied. Individual extractions are validated independently (not as a batch) to allow partial acceptance. Entity retrieval uses embedding similarity rather than a fixed limit.

### Stage 3 (Background -- Cross-Session Patterns)

```
User Session History + Existing User Subgraph
  |
  v
[LLM-based Pattern Detection OR Graph-structural Analysis]
  |
  v
[Full Four-Layer Validation]
  |
  v
[Self-Consistency Sampling (N=3) for confidence]  -- Only for behavioral patterns
  |
  v
Graph Insertion
```

**Rationale**: Stage 3 has no latency constraints. Self-consistency sampling is justified here because behavioral patterns have high downstream impact (they influence agent behavior across sessions) and the marginal cost is acceptable for batch processing.

### Key Design Principles

1. **Per-extraction validation, not per-batch**: Each extracted preference/skill/interest is validated independently. A hallucinated preference should not invalidate co-extracted valid preferences.
2. **Async graph consistency**: Never block event ingestion on graph queries. Optimistic insertion + async reconciliation.
3. **Source-type priors for MVP confidence**: Do not invest in logprobs or self-consistency until production data enables calibration tuning.
4. **Embedding-based entity retrieval**: Replace fixed-limit entity injection with vector similarity retrieval for prompt context.
5. **Alias dictionary for low-entropy entities**: Maintain a domain-specific alias table for common abbreviations (QB -> QuickBooks, PP -> PayPal, etc.).
6. **Separate extraction paths for text vs. behavioral data**: LLM extraction for conversation text; rule-based/statistical extraction for behavioral patterns (tool usage frequency, session metadata).

---

## Overall Assessment

The research report is **strong and well-suited to guide our implementation**, with the caveats noted above. The core recommendation (Pydantic models as extraction schema, Instructor for structured output, four-layer validation, known-entity injection) is architecturally sound and directly executable on our stack.

The most significant gap is the absence of non-LLM extraction approaches and the over-reliance on LLMs for all stages. A production system should be hybrid: LLMs for complex semantic extraction, rule-based extractors for structured signals, and graph-structural methods for relationship inference.

The entity resolution approach is directionally correct but needs embedding-based retrieval and a domain alias dictionary to be production-ready. The confidence calibration recommendation is reasonable for MVP (source-type priors) but needs a concrete plan for post-MVP calibration with ground truth labels.

**Initial Rating**: 8/10 -- High quality, directly actionable, with identifiable gaps that should be addressed before implementation.

---

## Post-Revision Assessment (v2)

Researcher-3 addressed all seven identified gaps in a document revision. Each gap was verified as resolved:

1. **Non-LLM approaches (Gap 1)**: New Section 9 covers rule-based, statistical, and graph-structural methods. The hybrid pipeline table (Section 9.4) estimates ~40-60% LLM cost reduction. **Resolved well.**
2. **Latency analysis (Gap 2)**: Section 3.6 provides per-layer latency estimates and stage-specific validation paths. Stage 1 hot path uses only Layers 1-2 synchronously. **Resolved well.**
3. **Entity resolution scalability (Gap 3)**: Section 4.3 rewritten with embedding-based retrieval (top-50 similarity + top-20 frequency) and a DOMAIN_ALIAS_DICT for merchant abbreviations. **Resolved well.**
4. **Confidence calibration (Gap 4)**: Phased approach (MVP: source-type priors only; post-MVP: tunable hyperparameters). Claude logprob unavailability explicitly noted. Ground-truth labeling methodology with 200-sample calibration dataset, 2 reviewers, Cohen's kappa target. **Resolved well.**
5. **Partial extraction (Gap 5)**: Section 3.8 with per-item validation, semantic plausibility checks, and retry budget exhaustion strategy. **Resolved well.**
6. **SHACL/n10s limitations (Gap 6)**: Section 8.4 covers edge property reification, sh:sparql limitations, and version compatibility. Section 8.6 caveats the incremental validation paper as RDF-specific. **Resolved.**
7. **API backward compatibility (Gap 7)**: Section 7.4 covers additive-only enum policy, versioned schemas, deprecation lifecycle. **Resolved.**

Additional improvements beyond the requested fixes: new Section 2.2 (zero-shot vs. few-shot extraction guidance) and Section 2.3 (unified vs. per-type prompts with hybrid two-phase recommendation) strengthen the document significantly.

**Updated Rating**: 9/10 -- Comprehensive and implementation-ready. The remaining area for future validation is the hybrid pipeline's estimated 40-60% LLM cost reduction, which is plausible but unverified until production data is available.
