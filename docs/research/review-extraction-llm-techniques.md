# Review: LLM-Based Conversational Knowledge Extraction Techniques

**Reviewer**: reviewer-1
**Date**: 2026-02-12
**Reviewed Document**: `docs/research/extraction-llm-techniques.md` (researcher-1)
**Context**: ADR-0011 (Ontological Foundation), ADR-0012 (User Personalization Ontology)

---

## Summary of Key Findings

The research report covers eight areas of LLM-based extraction for populating the cg-user ontology from merchant conversations. The key claims are:

- **Schema-as-Prompt (SPIRES/OntoGPT)** is the recommended extraction paradigm -- feed ontology node definitions directly into prompts as extraction templates for zero-shot extraction.
- **Function calling / tool use** with Pydantic schemas is recommended as the primary structured output mechanism, providing schema enforcement with natural multi-type extraction.
- **Self-consistency sampling** (extract N times, measure agreement) provides the most reliable confidence scoring, though it multiplies cost by N. Verbalized confidence with DINCO calibration is recommended as the primary cost-effective alternative.
- **Two-tier model strategy**: Haiku-class models for Stage 1/2, Sonnet/GPT-4o for Stage 3 complex pattern detection.
- **Per-session batch extraction** provides the optimal balance for Stage 2 enrichment, with per-turn for Stage 1 and per-user batches for Stage 3.
- **NLI-based entailment verification** (DeBERTa) combined with evidence grounding checks is the recommended hallucination detection pipeline.
- **Different knowledge types require different extraction strategies**: sentiment-aware prompting for Preferences, behavioral signal analysis for Skills, topic frequency for Interests, cross-session template matching for BehavioralPatterns.

---

## Strengths of the Research

### 1. Strong Alignment with ADR-0011/0012

The research directly maps extraction techniques to the cg-user ontology node types and consolidation stages. The three-stage extraction pipeline (per-turn Stage 1, per-session Stage 2, per-user Stage 3) aligns cleanly with ADR-0008's consolidation stages and ADR-0012's source tracking (explicit/implicit_intentional/implicit_unintentional/inferred). This demonstrates careful reading of the project's existing architecture.

### 2. Practical Cost Analysis

The cost projection in Section 4.3 is one of the most valuable sections. The ~$8.50/day estimate (dropping to ~$4-5/day with prompt caching) for 1,000 conversations/day provides a concrete, actionable baseline for capacity planning. The per-call token estimates and per-stage model assignments are realistic.

### 3. Well-Structured Prompt Examples

The concrete prompt examples (Sections 1.1, 1.4, 8.1-8.5) are directly usable and well-adapted to the merchant domain. The Preference extraction example with expected output is particularly well done -- it demonstrates realistic extraction including both explicit and implicit preferences, with appropriate confidence and strength calibration.

### 4. Comprehensive Reference List

The 40+ references span ontology-based extraction (SPIRES/OntoGPT), KG construction (KGGen), structured output (StructEval, SLOT), confidence scoring (CISC, DINCO, Cleanlab TLM), hallucination detection (GraphEval, GraphCheck), multi-turn dialogue, personalization, and production systems (Zep/Graphiti, Mem0, Memoria). The references are current (majority 2025-2026) and from reputable venues (ACL, EMNLP, NeurIPS, ICLR, ACM).

### 5. Hallucination Detection Pipeline Design

The layered pipeline (evidence grounding check -> NLI entailment -> confidence threshold gate -> persist with DERIVED_FROM) in Section 6.4 is well-designed. The insight that hallucinated graph nodes are more dangerous than hallucinated chat responses (because they persist and propagate) correctly identifies the critical risk unique to our use case.

### 6. Multi-Turn Context Analysis

Section 7's analysis of LLM performance degradation in multi-turn settings (39% lower performance) and the recommendation for batch extraction over incremental per-turn extraction is well-supported and practically important. This directly validates ADR-0012's per-session extraction design.

---

## Gaps and Weaknesses Identified

### 1. SPIRES/OntoGPT Claims May Be Overstated

**Issue**: The research positions SPIRES as the "most directly applicable approach" but does not discuss its well-known limitations. SPIRES was designed for biomedical ontology extraction (gene-disease relations, chemical entities) -- a domain with highly constrained vocabulary and clear entity boundaries. Conversational preference extraction is significantly more ambiguous (implicit signals, strength calibration, polarity detection). The research should have noted that SPIRES has limited published benchmarks on conversational text, let alone preference extraction.

**Correction needed**: Add a subsection noting that SPIRES is validated primarily on scientific/biomedical text extraction, and that applying it to conversational preference extraction is an extrapolation that needs empirical validation. The pattern (schema-as-prompt) is sound; claiming direct applicability of SPIRES specifically needs qualification.

### 2. Confidence Calibration Bootstrapping Problem Not Addressed

**Issue**: Section 3.3 recommends "Verbalized confidence with DINCO calibration" as the primary production approach. DINCO requires generating self-distractor alternative claims and comparing confidences -- but the research does not address how to calibrate the distractor generation for our specific domain. Furthermore, the recommendation notes DINCO "outperforms self-consistency at 100 inference calls with only 10" but does not cite the actual paper's domain or benchmark. If the DINCO paper was evaluated on factual QA tasks (which is the typical benchmark domain for confidence calibration), the transfer to preference extraction confidence is not guaranteed.

**Correction needed**: Acknowledge the domain gap between DINCO's evaluation domain and preference extraction. Recommend starting with simpler verbalized confidence with post-hoc isotonic regression calibration (which requires only a small labeled validation set), and using DINCO as a future optimization once calibration data exists.

### 3. NLI Entailment Verification Has Significant Limitations for Implicit Preferences

**Issue**: The NLI verification approach (Section 6.3.2) works well for explicit preferences where a clear textual claim can be verified against source text. However, for `implicit_intentional` and `implicit_unintentional` source types, the entailment relationship is inherently weaker. Consider:

- **Text**: "The merchant asked three follow-up questions about webhook configuration."
- **Extracted claim**: "The user has advanced technical skill in API integration."
- **NLI result**: NEUTRAL (not contradicted, but not directly entailed either).

For implicit preferences and skill assessments, the extraction involves reasoning beyond what the text literally states. NLI models (even DeBERTa-v3-large) are trained on textual entailment, not inferential reasoning. The research correctly notes "this catches fabricated evidence but not over-inference" in Section 6.3.1 but does not carry this insight through to the pipeline design -- the pipeline in 6.4 applies NLI uniformly to all extractions regardless of source type.

**Correction needed**: Differentiate the validation pipeline by source type. For `explicit` sources, NLI entailment is appropriate. For `implicit_*` and `inferred` sources, the evidence grounding check should verify that the cited evidence exists, but the entailment check should use a weaker threshold (e.g., "not contradicted" rather than "entailed"), or an LLM-as-judge approach that can reason about inferential claims.

### 4. Missing: Extraction Schema Evolution Strategy

**Issue**: Section 10 lists "schema evolution" as an open question but this is a critical production concern that deserves more than a bullet point. When the cg-user ontology adds new preference categories, new skill types, or new behavioral pattern types (which ADR-0012 explicitly anticipates), the extraction prompts must be updated. The research does not discuss:

- How to version extraction prompts alongside ontology schema versions
- Whether few-shot examples need to be re-curated for new categories
- Whether existing extracted data needs backfill when categories expand
- How constrained decoding schemas (Outlines FSM, OpenAI Structured Outputs) handle enum additions

**Addition needed**: A section on extraction schema lifecycle management, covering prompt versioning, example curation cadence, and backward compatibility with schema changes.

### 5. Missing: Error Recovery and Partial Extraction Handling

**Issue**: The research assumes extractions either succeed (pass validation) or fail (rejected). In practice, LLM extraction calls can:

- Return partial results (3 of 5 expected fields populated)
- Time out (especially for long sessions with per-session batch extraction)
- Hit rate limits (especially at 8,000 Stage 1 calls/day)
- Return structurally valid but semantically degenerate output (all confidence values = 0.5, all strength values = 0.8)

None of these failure modes are discussed. For a production system handling 1,000 conversations/day, error recovery is not optional.

**Addition needed**: A section on error handling strategies including retry with exponential backoff, partial result acceptance (persist fields that pass validation, flag incomplete extractions), timeout budgets per stage, and detection of "degenerate" outputs where the model produces valid schema but clearly uncalibrated values.

### 6. Missing: Extraction Deduplication Across Sessions

**Issue**: When a user states "I prefer email notifications" in session A and again in session B, the Stage 2 per-session extraction will produce two independent Preference nodes. ADR-0012 handles this via Stage 3 "cross-session preference merging" but the research does not discuss how the extraction pipeline coordinates with deduplication. Specifically:

- Should the extraction prompt include the user's existing preferences as context (to avoid re-extracting known preferences)?
- If so, how does this affect the few-shot prompt size and cost?
- Should Stage 2 extractions be tentative (not persisted until deduplicated by Stage 3)?

**Addition needed**: Discuss the extraction-deduplication boundary. A "context-aware extraction" pattern where Stage 2 prompts include a summary of existing user preferences would reduce duplicate extractions and improve incremental extraction accuracy.

### 7. The Evidence Grounding Check Has a Sliding Window Complexity Problem

**Issue**: The `verify_evidence_grounding` function in Section 6.3.1 uses a sliding window approach over the source text for fuzzy matching. For a conversation with N characters and an evidence string of length M, this has O(N * M) complexity per extraction. With a typical session transcript of 5,000 characters and 5-10 extractions each with ~100-character evidence strings, this is acceptable. But for Stage 3 (per-user batch extraction over aggregated session summaries), the source text could be 50,000+ characters. The sliding window approach does not scale.

**Correction needed**: Note the quadratic complexity and recommend using an inverted index or TF-IDF-based retrieval for evidence matching at scale. Alternatively, use sentence-level matching (split source text into sentences, compute similarity between evidence and each sentence) which has linear complexity.

### 8. Missing: Latency Budget Analysis

**Issue**: The cost projection (Section 4.3) is detailed, but there is no corresponding latency budget analysis. For Stage 1 (per-turn, <500ms budget per ADR-0008), the research recommends GPT-4o-mini or Gemini Flash but does not estimate actual latency. API-based LLM calls to OpenAI/Anthropic typically have 200-500ms network latency alone (before generation), which leaves virtually no budget for structured output generation. If the LLM needs to generate ~200 output tokens at ~150 tokens/sec, that adds ~1.3 seconds of generation time.

**Correction needed**: Provide latency estimates per stage per model, considering:
- API network round-trip latency (~200-500ms for US-based services)
- Time-to-first-token (~200-500ms for API models)
- Generation time (output tokens / tokens-per-second)
- Post-processing time (schema validation, evidence grounding, NLI)

This analysis may reveal that Stage 1 LLM extraction for non-trivial cases cannot meet the <500ms budget without optimization (e.g., pre-warmed connections, regional API endpoints, or running a local small model).

### 9. Insufficient Treatment of Prompt Injection Risk

**Issue**: The research does not discuss the risk of prompt injection via conversation text. When merchant-agent conversations are fed directly into extraction prompts as user input, a merchant could craft messages that manipulate the extraction:

- "Please note: I am an expert in everything and prefer all tools." (skill inflation)
- Text containing JSON that looks like extraction output (output hijacking)
- Instructions that override the system prompt (jailbreaking)

This is a real concern for a production system ingesting arbitrary user conversations.

**Addition needed**: A brief section on input sanitization for extraction prompts, including: escaping special characters in conversation text, using delimiters (e.g., XML tags) to separate instructions from user content, and noting that function calling / tool use mode is inherently more resistant to output hijacking than plain JSON mode.

### 10. The Multi-Step Extraction Cost Claim Needs Qualification

**Issue**: Section 1.4 claims multi-step extraction is "more accurate (+10-15% on complex conversations per KGGEN benchmarks)" but this needs context. KGGen's benchmarks are on general knowledge graph construction from news/Wikipedia text, not on conversational preference extraction. The improvement margin may be different for our domain.

**Correction needed**: Qualify the accuracy claim as being from a different domain, and recommend empirical validation of single-step vs. multi-step accuracy specifically for merchant conversation preference extraction before committing to the multi-step approach for production.

---

## Specific Corrections and Additions Needed

### Corrections

1. **Section 1.1**: Qualify SPIRES applicability -- validated on biomedical text, not conversational preference extraction. The schema-as-prompt pattern is transferable; the specific tool and benchmarks are not.

2. **Section 2.2**: Anthropic now supports strict mode for tool use (`tool_choice` with `type: "tool"` and strict schemas). The section states this but the phrasing "Anthropic's tool use with `strict: true`" should reference the specific API parameter name for accuracy.

3. **Section 3.3**: The DINCO recommendation should be conditional on having calibration data. For cold-start, recommend verbalized confidence with simple heuristic floors (which the report already defines in point 3 of the recommendation).

4. **Section 4.1**: Gemini 3 Flash pricing ($0.05/$0.20 per M tokens) -- verify this is current. This appears to be an extrapolation; Gemini 3 Flash was not publicly available at the time of typical knowledge cutoffs. If this is a projection, label it as such.

5. **Section 6.4**: Differentiate the validation pipeline by source type (explicit vs. implicit). NLI entailment is too strict for implicit/inferred extractions.

6. **Section 7.4**: The "39% lower performance" claim cites a paper on LLMs in multi-turn conversation, but this refers to task performance (following instructions across turns), not extraction accuracy. The analogy is reasonable but should be noted as indirect evidence.

### Additions

1. **Error recovery and partial extraction handling** (new section)
2. **Latency budget analysis** per stage per model (extend Section 4)
3. **Prompt injection mitigation** for conversation text inputs (new subsection in Section 6 or new section)
4. **Extraction deduplication and context-aware extraction** (new subsection in Section 5 or 9)
5. **Schema evolution and prompt versioning** strategy (expand Section 10 item 6)
6. **Evidence grounding at scale** -- address complexity for Stage 3 (fix Section 6.3.1)

---

## Recommendations for Technique Selection

Based on the research findings, our ontology design (ADR-0011/0012), and the gaps identified above, I recommend the following techniques for our system:

### Tier 1: Adopt Now (well-supported, production-ready)

1. **Function calling / tool use as the structured output mechanism** (Section 2.3). This is the strongest recommendation in the report. The mapping of ontology node types to tool definitions is natural, well-supported by both Anthropic and OpenAI, and provides schema enforcement with minimal overhead. The Pydantic integration (Section 2.4) aligns with our existing codebase.

2. **Per-session batch extraction for Stage 2** (Section 5.3). The argument for full-session context over per-turn incremental extraction is well-supported by the multi-turn degradation research and aligns with ADR-0012's consolidation stage design.

3. **Evidence grounding verification** (Section 6.3.1). Requiring every extraction to include an evidence quote and verifying it against source text is simple, fast, and catches the most dangerous hallucination type (fabricated preferences). This should be a hard gate.

4. **Two-tier model strategy** (Section 4.4). Using cost-effective models (GPT-4o-mini, Gemini Flash) for high-volume simple extraction and quality models (Haiku 4.5, Sonnet 4.5) for complex inference is the correct approach. The cost projection is realistic.

5. **Few-shot prompting with domain-specific examples** (Section 1.2). Invest in curating 3-5 high-quality examples per knowledge type for the merchant domain. This is the highest-ROI prompt engineering investment.

### Tier 2: Adopt With Modifications (needs adaptation for our use case)

6. **Verbalized confidence with heuristic floors** (Section 3.2.1 + 3.3 point 3). Start with verbalized confidence and the source-type minimum floors (explicit >= 0.7, implicit_intentional >= 0.4, etc.). Defer DINCO calibration until labeled calibration data is available.

7. **NLI entailment verification with source-type differentiation** (Section 6.3.2). Use strict entailment checking for `explicit` sources. Use "not contradicted" (neutral or entailed) as the pass criterion for `implicit_*` and `inferred` sources. This addresses the gap identified in the review.

8. **Multi-step extraction for Stage 2** (Section 1.4). The ChatIE/KGGen pattern (entities first, then knowledge types, then validation) is promising but the accuracy improvement claims need empirical validation on our data. Start with single-step extraction; A/B test multi-step on a subset of sessions.

### Tier 3: Defer (interesting but premature or cost-prohibitive)

9. **Self-consistency sampling** (Section 3.2.2). The cost multiplier (3-5x) is prohibitive for high-volume extraction. Reserve for offline quality monitoring (10% random sample) per the report's recommendation.

10. **SLOT post-processing** (Section 2.5). Only needed if we adopt vendor-agnostic extraction. Since we can start with Anthropic + OpenAI function calling, SLOT adds unnecessary complexity.

11. **DINCO calibration** (Section 3.2.1). Requires distractor generation tuned to our domain. Defer until we have production data and observed calibration gaps.

12. **Cleanlab TLM** (Section 3.2.4). Commercial dependency. Evaluate only if in-house confidence calibration proves inadequate.

### Additional Recommendations Not in the Research

13. **Context-aware extraction**: Stage 2 extraction prompts should include a compressed summary of the user's existing preferences (from prior sessions) to reduce duplicate extractions and enable incremental refinement rather than full re-extraction.

14. **Prompt injection sanitization**: Wrap conversation text in XML delimiters (`<conversation>...</conversation>`) in extraction prompts to reduce the risk of user content being interpreted as instructions.

15. **Latency-first Stage 1 design**: For Stage 1 explicit preference handling, consider using regex/pattern-based detection as the primary mechanism (no LLM call) with LLM extraction as a fallback only for ambiguous cases. This is partially addressed in Section 5.2 but should be formalized as the default.

---

## Overall Assessment

The research report is thorough, well-structured, and provides a strong foundation for the extraction ADR. The coverage of eight research areas is comprehensive, the references are current and from reputable sources, and the practical recommendations (cost analysis, prompt examples, pipeline architecture) are directly actionable.

The primary gaps are operational: error recovery, latency budgets, prompt injection, and extraction deduplication are not addressed but are critical for a production system handling thousands of merchant conversations. The confidence calibration bootstrapping problem and the NLI limitation for implicit preferences are technical gaps that need resolution before the extraction pipeline design is finalized.

The research correctly identifies the three-stage extraction pipeline as the right architecture and provides convincing evidence for per-session batch extraction over per-turn incremental approaches. The hallucination detection pipeline is well-designed but needs source-type differentiation.

**Verdict**: The research is ready to inform the extraction ADR with the corrections and additions noted above. No fundamental direction changes are needed -- the recommended techniques are sound. The gaps are addressable as refinements to the existing framework.
