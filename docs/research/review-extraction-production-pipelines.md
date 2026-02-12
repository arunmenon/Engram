# Review: Production Knowledge Extraction Pipelines

**Reviewer**: reviewer-2
**Date**: 2026-02-12
**Reviewed Document**: `docs/research/extraction-production-pipelines.md` (researcher-2)
**Context Documents**: ADR-0011 (Ontological Foundation), ADR-0012 (User Personalization Ontology), `docs/research/extraction-landscape.md`

---

## Summary of Key Findings

The research report analyzes five production and near-production agent memory systems (Mem0, Zep/Graphiti, Memoria, A-MEM, MAGMA) and one supplementary system (Cognee). The key claims are:

- All production systems use LLM-based extraction with structured JSON output; no system relies solely on NER or rule-based methods.
- Conflict resolution is the hardest unsolved problem, with each system taking a fundamentally different approach (LLM-decided CRUD, temporal edge invalidation, exponential decay, bidirectional note evolution, query-time intent weighting).
- Entity resolution universally uses a hybrid of embedding similarity + LLM verification.
- MAGMA's dual-stream (fast path + slow path consolidation) maps directly to our Stage 1 / Stage 2-3 architecture.
- Graphiti's bi-temporal model is the most sophisticated temporal tracking, and is recommended for our Preference nodes.
- No production system maintains event-level provenance (DERIVED_FROM edges), which the report identifies as our system's key differentiator.
- Approximate per-turn extraction costs range from $0.001 (Mem0) to $0.010 (Graphiti) using GPT-4o-mini pricing.

---

## Strengths of the Research

### 1. Exceptional Depth on Source Code and Prompt Internals

The report goes beyond paper summaries to analyze actual source code (Mem0's `prompts.py`, Graphiti's `extract_nodes.py` and `extract_edges.py`). The detailed prompt descriptions -- including Mem0's seven extraction categories, Graphiti's reflexion loops, and the specific JSON output formats -- are directly actionable for designing our extraction prompts. This level of source-code grounding is rare in survey-style research and significantly increases the credibility of the claims.

### 2. Well-Structured Cross-System Comparison

The comparison matrices in Section 6 (Sections 6.1 through 6.5) systematically compare all five systems across six dimensions: extraction architecture, conflict resolution, extraction triggers, entity resolution, cost/latency. The consistent dimensionality enables direct apples-to-apples comparison. The "Common Patterns" section (7) correctly distills the six universal patterns and four divergent design choices, which is a valuable synthesis for the ADR.

### 3. Strong Alignment with Our ADR Architecture

The report consistently maps findings to our system's ADR decisions:
- MAGMA's four-graph design to ADR-0009's five views
- Graphiti's bi-temporal model to our Preference temporal tracking needs (ADR-0012)
- Mem0's CRUD decision model to our Stage 1 explicit preference handling
- MAGMA's dual-stream to our Stage 1 / Stage 2-3 consolidation pipeline (ADR-0008)
- Memoria's EWA to our Ebbinghaus decay model (ADR-0008)

This is not a detached literature review; it is targeted analysis that directly serves the design.

### 4. Honest Treatment of Benchmark Controversies

Section 10 acknowledges the Zep/Mem0 benchmark disputes, the limitations of LLM-as-Judge evaluation, the absence of personalization-specific benchmarks, and the task-specific performance variation. This intellectual honesty prevents the ADR from being built on inflated accuracy claims and correctly calibrates expectations.

### 5. Graphiti's Bi-Temporal Model Analysis

The explanation of Graphiti's four-timestamp bi-temporal model (Section 2.3) is thorough and clearly articulated. The mapping table distinguishing transactional timeline (when the system learned a fact) from event timeline (when the fact became true) is directly applicable to our Preference node design. The temporal edge invalidation mechanism (Section 2.6) is explained with enough specificity to implement.

### 6. Actionable "Implications for Our System" Section

Section 8 provides concrete, numbered recommendations for patterns to adopt (6 items), patterns to avoid (3 items), and open questions (5 items). This is the most valuable section for the ADR author. The recommendations are well-justified by the preceding analysis.

---

## Gaps and Weaknesses Identified

### 1. Cost and Latency Figures May Be Unreliable or Fabricated

**Issue**: The cost estimates in Section 6.5 ("Approximate cost per turn") present precise-looking figures ($0.001-0.003 for Mem0, $0.003-0.010 for Graphiti, etc.) attributed to "GPT-4o-mini pricing." However:

- The Mem0 cost is derived from the paper's token counts, which is reasonable.
- The Graphiti cost range ($0.003-0.010) is not directly reported in the Graphiti paper or documentation. The paper reports LLM call counts (5-8 per episode) but not token usage per call. The cost figure appears to be the researcher's own estimate, which should be clearly labeled as such.
- The A-MEM cost ($0.002-0.005) and MAGMA cost ("Variable (async)") appear similarly inferred rather than reported.
- Memoria's cost ($0.001-0.002) is not sourced from the paper.

Mixing reported figures with researcher estimates in the same table without distinguishing them is misleading.

**Correction needed**: Clearly mark which cost figures are reported by the original systems and which are the researcher's estimates. For estimated figures, show the calculation (e.g., "5-8 LLM calls x estimated 2K tokens per call x GPT-4o-mini pricing = $X"). This is particularly important because the ADR will use these figures for capacity planning.

### 2. Graphiti's Bulk Processing Limitation Is Understated

**Issue**: Section 2.8 contains a critical caveat buried in a note: "Bulk episode processing (`add_episode_bulk`) optimizes throughput but skips edge invalidation and temporal contradiction detection." This is a fundamental limitation -- bulk processing disables the very feature (temporal conflict resolution) that makes Graphiti distinctive. For our system, if we adopt Graphiti's temporal model but need batch processing for Stage 3 re-consolidation, we cannot rely on Graphiti's off-the-shelf bulk path.

This caveat appears only once, in small text at the end of the performance section, rather than being prominently flagged as a design constraint.

**Correction needed**: Promote this limitation to the "Patterns to Avoid" section (8.2) or add it as item 4: "Graphiti's bulk processing path disables temporal conflict resolution. If adopting Graphiti's bi-temporal model, the batch path must implement its own invalidation logic." This has direct implications for our Stage 3 design.

### 3. Missing: How Systems Handle Extraction Failures

**Issue**: The report describes the happy path for each system -- how extraction works when it succeeds. It does not discuss:

- What happens when the LLM returns malformed JSON (all systems use JSON extraction).
- How systems handle extraction timeouts (Graphiti's 5-8 LLM calls per episode could time out mid-pipeline).
- Whether extraction is atomic per episode or allows partial extraction (e.g., entity extraction succeeds but edge extraction fails).
- Retry strategies and error budgets.

For a production system handling thousands of conversations, failure modes are as important as the nominal design. Graphiti's source code has retry logic and error handling that would be valuable to document.

**Addition needed**: A section (or subsection per system) on error handling and failure modes, including how each system handles JSON parse failures, LLM timeouts, and partial extraction states.

### 4. Incomplete Treatment of Entity Resolution at Scale

**Issue**: Section 6.4 compares entity resolution approaches across systems, but the analysis stays at the algorithmic level without discussing scalability:

- **Mem0**: Embedding similarity search against all entities with threshold 0.7. What happens when the entity store has 100K+ entities? Is the search O(N) or indexed?
- **Graphiti**: Three-tier approach (cosine + BM25 + MinHash + LLM). The LLM verification step is expensive -- how does Graphiti decide *which* candidates need LLM verification? The heuristic is important.
- **MAGMA**: "Entity graph with persistent entity nodes" -- what is the entity resolution threshold? How are entity merges handled (merge into one node, or SAME_AS edges)?

For our system serving SMB merchants, a single merchant may reference dozens of entities per session across hundreds of sessions. The entity resolution approach must scale to tens of thousands of entities per merchant.

**Correction needed**: Add scalability analysis for entity resolution. Document the indexing strategies (vector indices, BM25 indices) each system uses and at what entity count the naive approaches break down. This directly informs our ADR-0011 entity resolution tier thresholds.

### 5. A-MEM's Conflict Resolution Limitation Is Identified But Not Sufficiently Analyzed

**Issue**: Section 4.4 correctly notes that A-MEM "does not explicitly address how contradictory facts are handled." The example given -- "I prefer Python" followed by "I prefer Rust" -- is exactly our use case (Preference evolution via `superseded_by`). The report labels this a "Limitation" but does not analyze the downstream consequences:

- If A-MEM cannot resolve contradictions, what happens to retrieval quality when contradictory notes exist?
- Does the bidirectional evolution in practice degrade to noise when many contradictions accumulate?
- The A-MEM paper's LoCoMo Temporal F1 (45.85%) is actually quite high compared to its Multi-Hop F1 (27.02%) -- does this suggest the evolution mechanism partially compensates for the lack of explicit contradiction resolution?

**Correction needed**: Extend the analysis to discuss whether A-MEM's bidirectional evolution provides *implicit* contradiction resolution (via contextual description updates), and whether this is sufficient for our preference evolution use case. The answer is likely "no" (our ADR-0012 requires explicit `superseded_by` chains), but the analysis should be explicit.

### 6. Missing: Comparison of What Each System Extracts vs. What We Need

**Issue**: The report compares extraction *architectures* but does not systematically compare the *types of knowledge* each system extracts against our target ontology (ADR-0012's 5 node types: UserProfile, Preference, Skill, Workflow, BehavioralPattern). This is a critical gap.

| Knowledge Type | Mem0 | Graphiti | Memoria | A-MEM | MAGMA |
|---------------|------|---------|---------|-------|-------|
| UserProfile | ? | ? | ? | ? | ? |
| Preference | Yes (facts) | Yes (edges) | Yes (triplets) | Yes (notes) | ? |
| Skill | ? | ? | ? | ? | ? |
| Workflow | No | No | No | No | No |
| BehavioralPattern | No | No | No | No | No |

None of the surveyed systems extract Workflow or BehavioralPattern nodes. Most extract some form of preferences and entity relationships. But the report does not make this coverage gap explicit, which could lead the ADR author to assume that production systems provide validated patterns for all five node types.

**Addition needed**: A coverage matrix mapping each system's extraction output types to our ADR-0012 node types. This would clearly show which extraction patterns are production-validated and which require novel design.

### 7. Memoria's Benchmarks Are on a Different Task

**Issue**: Section 3.6 reports Memoria's benchmarks (87.1% single-session accuracy, 80.8% knowledge-update accuracy) alongside benchmarks from other systems that use LoCoMo or LongMemEval. However, Memoria's benchmarks are from a different evaluation methodology -- the paper uses its own proprietary evaluation, not the standardized benchmarks used by the other systems. This makes direct comparison misleading.

The report acknowledges this partially in Section 10 ("Memoria's Session and Knowledge-Update benchmarks are closer to our use case but are proprietary") but the benchmarks in Section 3.6 are presented without this caveat, creating a false impression of comparability.

**Correction needed**: Add a caveat to Section 3.6 noting that Memoria's benchmarks use a different evaluation methodology than LoCoMo/LongMemEval and are not directly comparable to the numbers reported for Mem0, Graphiti, A-MEM, and MAGMA. Alternatively, add a "Benchmark" column to the comparison matrices that identifies which evaluation was used for each system's numbers.

### 8. Graphiti's Reflexion Loop Cost is Not Quantified

**Issue**: The report identifies Graphiti's reflexion loop as a "key differentiator" (Section 2.2) and recommends adopting it (Section 8.1 item 2). However, the reflexion loop adds 1-2 additional LLM calls per extraction phase (one for nodes, one for edges). This means reflexion accounts for roughly 25-40% of Graphiti's total LLM call budget per episode. The report does not quantify this cost or analyze the accuracy-cost tradeoff.

If we adopt reflexion for Stage 2, what is the marginal accuracy improvement per additional LLM call? Graphiti's paper does not provide an ablation study of reflexion specifically. Without this data, the recommendation to adopt reflexion is based on intuition rather than evidence.

**Correction needed**: Note that reflexion's accuracy contribution is not isolated in the Graphiti paper (no ablation study). The recommendation should be conditional: adopt reflexion as an optional enrichment step in Stage 2, with A/B testing to measure the actual accuracy gain versus the ~30% cost increase.

### 9. Missing: Multi-Language and Domain-Specific Extraction

**Issue**: The extraction-landscape.md identifies "merchant domain specificity" and "multi-language support" as cross-cutting concerns. None of the five systems are analyzed for their multi-language capabilities or domain customization mechanisms. Specifically:

- Mem0 supports `custom_fact_extraction_prompt` -- how well does this work for domain-specific extraction?
- Graphiti's `classify_nodes` uses a "configurable taxonomy" -- how is this configured, and how does it perform on domain-specific entity types?
- Do any of the systems support non-English conversation extraction?

For our SMB merchant use case (PayPal), merchants may converse in Spanish, Portuguese, Mandarin, and dozens of other languages. The extraction pipeline must handle multilingual input.

**Addition needed**: A brief assessment of each system's multi-language support and domain customization capabilities. Even if the answer is "none of these systems have been evaluated on non-English text," this should be stated explicitly.

### 10. Cognee Section Is Thin and Could Be Cut or Expanded

**Issue**: Section 9 on Cognee is a brief overview (6 bullet points) that does not include extraction prompts, conflict resolution mechanisms, benchmarks, or any of the depth provided for the other five systems. It contributes little to the analysis beyond noting that Cognee exists and validates the modular pipeline concept.

**Recommendation**: Either expand Cognee to the same depth as the other systems (which may not be possible if the system lacks published papers) or remove it from the main analysis and reference it only in the "Common Patterns" section as additional validation.

---

## Cross-System Comparison Assessment

### Is the Comparison Fair?

The comparison matrices (Section 6.1-6.5) are **mostly fair** but have several asymmetries:

**Fair dimensions**:
- Extraction architecture (6.1) uses consistent categories and all systems are covered.
- Conflict resolution (6.2) is well-structured with consistent dimensions.
- Entity resolution (6.4) uses the same categories for all systems.

**Unfair or incomplete dimensions**:

1. **Cost comparison (6.5)**: The token counts and cost estimates come from different sources and methodologies. Mem0's token count is from the paper; Memoria's is from the paper; others appear estimated. The "Approximate cost per turn" row mixes reported and estimated data without distinguishing them.

2. **Performance benchmarks**: Each system's benchmarks are reported in separate sections (1.6, 2.8, 3.6, 4.6, 5.7) rather than in a unified comparison table. This makes it hard to compare. A unified benchmark table would reveal that different systems are evaluated on different benchmarks (LoCoMo Judge for Mem0/MAGMA, LongMemEval for Graphiti/MAGMA, proprietary for Memoria).

3. **MAGMA's "LLM calls per write"** is listed as "1 (fast) + N (slow)" which is not comparable to the fixed numbers for other systems. The "N" should be estimated or bounded.

4. **Retrieval latency comparison**: Mem0 reports p50/p95 separately; Graphiti reports p95 and "Zep Cloud" latency; Memoria does not report retrieval latency; A-MEM reports query latency (which includes retrieval + LLM); MAGMA reports query latency. These are not the same measurements.

### Recommendation for the Comparison

Add a consolidated benchmark table that normalizes system comparisons:

| System | Benchmark Used | Key Metric | Score | LLM Calls/Write | Retrieval Latency | Cost/Turn (estimated) |
|--------|---------------|-----------|-------|-----------------|-------------------|----------------------|

This would make the asymmetries transparent and allow the ADR author to compare on equal footing.

---

## Recommendations for Our System

Based on the research and the gaps identified, here are my recommendations for which production patterns to adopt, adapt, or avoid:

### Adopt (strong evidence, production-validated)

1. **MAGMA's dual-stream architecture** for Stage 1 (fast path) / Stage 2-3 (slow path). This is the best-validated pattern in the research and maps cleanly to our ADR-0008 consolidation stages. The fast path provides sub-100ms entity extraction; the slow path enables richer LLM-based inference.

2. **Graphiti's bi-temporal model** for Preference temporal tracking. The four-timestamp model (created, expired, valid_at, invalid_at) directly maps to our Preference lifecycle (created, superseded, first_observed_at, last_confirmed_at). This is the only production system with a proper temporal model for fact evolution.

3. **User-message-only extraction** (Mem0 and Memoria pattern) for implicit preference inference in Stage 2. The rationale is sound: extracting from assistant messages causes the system to memorize its own outputs, creating a feedback loop.

4. **No LLM calls at retrieval time** (universal pattern). All five systems perform retrieval via embedding search + graph traversal without LLM calls. This validates our ADR-0009 intent-weighted traversal approach.

5. **Embedding + LLM hybrid entity resolution** (Graphiti pattern). The three-tier approach (embedding similarity + BM25 + LLM verification for ambiguous cases) is the most robust and maps to our ADR-0011 exact/close/related match strategy.

### Adapt (partially applicable, requires modification)

6. **Mem0's LLM-decided CRUD model** for Stage 1 explicit preference handling. Adapt to our ontology: the CRUD operations map to ADD (new Preference node), UPDATE (increase confidence/observation_count), SUPERSEDE (set superseded_by), NOOP. However, Mem0's non-determinism is a concern -- the same conflict may resolve differently across runs. Add deterministic priority rules (explicit > implicit, newer > older) as pre-LLM tiebreakers.

7. **Graphiti's reflexion loops** for Stage 2 extraction verification. Adopt as an optional quality-enhancement step, not as a mandatory pipeline phase. A/B test the reflexion's accuracy improvement against its ~30% cost increase before committing to it for all extractions.

8. **Memoria's exponential weighted average** as a validation that our Ebbinghaus decay model is on the right track. Our model is already richer (per-item stability, reinforcement-based adjustment), so this is more a confidence signal than a pattern to adopt directly.

### Avoid (poor fit or insufficient evidence)

9. **A-MEM's schema-free approach**. Our ontology (ADR-0011/0012) defines a precise target schema with 5 node types, 16 edge types, and detailed property constraints. Schema-free extraction would require a post-extraction mapping layer, adding complexity and error surface. A-MEM's bidirectional evolution concept is interesting for preference reinforcement but does not justify abandoning schema-guided extraction.

10. **Graphiti's bulk processing path for batch operations**. As noted in Gap #2, bulk processing disables temporal conflict resolution. Our Stage 3 re-consolidation requires conflict detection. If we implement batch processing, we must build our own invalidation logic rather than relying on Graphiti's `add_episode_bulk`.

11. **MAGMA's query-time-only conflict resolution**. While elegant, deferring all conflict resolution to query time means the graph accumulates unbounded contradictions. For user preferences, contradictions should be resolved at write time (via `superseded_by` chains) to keep the preference subgraph clean. Query-time weighting is complementary but not a substitute for write-time resolution.

12. **Single-timestamp approaches** (Mem0, A-MEM). Our preference evolution model requires at minimum `first_observed_at`, `last_confirmed_at`, and `superseded_by`. Systems with only a creation timestamp lose critical temporal information.

---

## Additional Observations

### Systems Compared to Our Three-Stage Architecture

A mapping the report could have made more explicit:

| Our Stage | Closest System Pattern | Key Difference |
|-----------|----------------------|----------------|
| Stage 1 (Event Projection, <500ms) | MAGMA fast path | MAGMA does event segmentation + vector indexing; we also need entity extraction + REFERENCES edges |
| Stage 2 (Enrichment, async batch) | Mem0 extraction + update pipeline; Graphiti entity/edge extraction | We need Preference/Skill/Interest extraction, not just generic facts. No production system extracts our full ADR-0012 schema |
| Stage 3 (Re-Consolidation, periodic) | MAGMA slow path; A-MEM bidirectional evolution | No production system does cross-session Workflow extraction or BehavioralPattern detection |

This mapping reveals that our Stage 1 is well-served by existing patterns, Stage 2 partially covered, and Stage 3 is largely novel.

### The Provenance Gap Is Real and Significant

The report correctly identifies that no production system maintains DERIVED_FROM provenance chains. This claim is verifiable from the source code: Mem0 stores memories without source event references; Graphiti creates episodic edges (`E_e`) that link episodes to entities but these are adjacency links, not derivation provenance; Memoria embeds triplets in ChromaDB without event-level backlinks; A-MEM stores raw content in notes but does not model derivation. This validates DERIVED_FROM as a genuine differentiator.

### Missing Production Systems

The report covers the major open-source and published systems. Notable omissions:

- **MemGPT/Letta**: An earlier agent memory system that influenced Mem0 and A-MEM. While superseded by newer systems, its tiered memory architecture (main context, archival storage) is relevant to our memory tier design.
- **LangMem**: LangChain's memory management library. Production-deployed at scale via the LangSmith platform. While less architecturally sophisticated than Graphiti or MAGMA, it represents a significant share of real-world agent memory deployments and may have relevant patterns for simple preference tracking.
- **Nemori**: Referenced in the MAGMA comparison table (0.590 Judge score) but not analyzed. If MAGMA compares against it as a baseline, it may contain relevant extraction patterns.

These omissions do not invalidate the analysis but would strengthen it.

---

## Overall Assessment

The research report is **thorough, well-organized, and directly relevant** to our extraction pipeline design. The five-system survey with cross-cutting comparison matrices provides a solid foundation for the ADR-0013 synthesis. The source-code-level analysis of extraction prompts and conflict resolution mechanisms goes beyond typical survey depth and produces actionable insights.

The primary weaknesses are:

1. **Cost/latency figures need sourcing discipline** -- clearly distinguish reported metrics from researcher estimates.
2. **Knowledge type coverage gap** -- the report does not map each system's extraction outputs to our specific ADR-0012 node types, making it unclear which of our five node types have production-validated extraction patterns (answer: roughly Preference only).
3. **Missing operational concerns** -- error handling, extraction failures, multi-language support, and domain customization are not addressed.
4. **Benchmark comparability** -- different systems use different evaluation methodologies, which the comparison tables do not make sufficiently transparent.

These gaps are addressable as refinements and do not require fundamental restructuring of the research. The "Implications for Our System" section (Section 8) is the strongest part of the report and provides clear, well-justified recommendations.

**Rating**: 8/10 -- High quality and directly actionable, with identifiable gaps in operational coverage and metric sourcing that should be addressed before the ADR synthesis.
