# LLM-Based Conversational Knowledge Extraction Techniques

**Date**: 2026-02-12
**Author**: researcher-1
**Task**: #2 -- Research LLM-based conversational knowledge extraction techniques
**Context**: Populating the cg-user ontology (ADR-0011, ADR-0012) from conversations between SMB merchants and conversational AI agents (e.g., PayPal merchant support)

---

## Executive Summary

This document presents a comprehensive analysis of LLM-based techniques for extracting structured knowledge from conversational text and populating an ontology-defined knowledge graph. The research covers eight areas: prompt engineering for structured extraction, structured output mechanisms, confidence scoring, model selection, batch vs. per-turn extraction, hallucination detection, multi-turn context handling, and extraction strategies for different knowledge types.

**Key findings**:

1. **Schema-as-prompt** (SPIRES/OntoGPT pattern) is the recommended extraction paradigm -- feed ontology node definitions directly into prompts as extraction templates, achieving zero-shot extraction without labeled training data.
2. **Function calling / tool use** with Pydantic schemas provides the most reliable structured output mechanism for our use case, combining schema enforcement with natural extraction semantics.
3. **Self-consistency sampling** (extract N times, measure agreement) is the most reliable confidence scoring method, though it multiplies cost by N. Verbalized confidence with post-hoc calibration offers a cost-effective alternative.
4. **A two-tier model strategy** is recommended: Haiku-class models ($0.15-$1.00/M input tokens) for Stage 1/2 extraction, Sonnet/GPT-4o-class models for Stage 3 complex pattern detection.
5. **Per-session batch extraction** (not per-turn, not per-user-history) provides the optimal balance of accuracy, cost, and context for Stage 2 enrichment.
6. **NLI-based entailment verification** is the most practical hallucination detection technique for our use case -- decompose each extracted triple into a claim and verify entailment against source conversation text.
7. **Different knowledge types require different extraction strategies**: Preferences benefit from sentiment-aware prompting, Skills from behavioral signal analysis, and BehavioralPatterns from cross-session sequence detection.

---

## 1. Prompt Engineering for Structured Extraction

### 1.1 Schema-as-Prompt (SPIRES Pattern)

The SPIRES (Structured Prompt Interrogation and Recursive Extraction of Semantics) method, implemented in the open-source OntoGPT package, is the most directly applicable approach for our use case. SPIRES feeds ontology schemas directly into LLM prompts as extraction templates, then recursively performs prompt interrogation to extract conforming instances.

**How it maps to our system**: Our PG-Schema definitions (ADR-0011 Section 5) and Pydantic models (ADR-0012 node types) serve as the extraction templates. Instead of LinkML schemas (OntoGPT's native format), we pass Pydantic model definitions or simplified schema descriptions.

**Core approach**:
1. Define the target schema in the system prompt (node type properties, valid enum values, value ranges)
2. Present conversation text as input
3. Ask the model to extract all instances conforming to the schema
4. Validate extracted instances against the schema

**Concrete prompt example -- Preference extraction from merchant conversation**:

```
SYSTEM:
You are a knowledge extraction system. Extract user preferences from the
conversation below. Each preference must conform to this schema:

Preference:
  category: one of ["tool", "workflow", "communication", "domain", "environment", "style"]
  key: string describing the preference (e.g., "notification_method", "report_format")
  polarity: one of ["positive", "negative", "neutral"]
  strength: float 0.0-1.0 (how strongly the user feels about this)
  confidence: float 0.0-1.0 (how certain you are this preference exists in the text)
  source: one of ["explicit", "implicit_intentional", "implicit_unintentional"]
  context: optional scope qualifier (e.g., "dispute_management", "invoicing")
  about_entity: the entity this preference concerns (e.g., "email notifications", "PDF format")
  evidence: exact quote from conversation supporting this preference

Rules:
- Only extract preferences that are CLEARLY supported by the conversation text
- Set source="explicit" only when the user directly states a preference
- Set source="implicit_intentional" when the user deliberately chooses/avoids something
- Set source="implicit_unintentional" when preference is inferred from behavior patterns
- The evidence field must contain a direct quote -- do not paraphrase
- If unsure, set lower confidence rather than omitting the preference

USER:
Conversation between merchant and support agent:

Merchant: "Hi, I need help with my dispute notifications. I keep getting them
by text message but I really prefer email for anything dispute-related."
Agent: "I can update that for you. Would you like email for all notifications
or just disputes?"
Merchant: "Just disputes. Text is fine for payment confirmations -- those are
quick and I like seeing them on my phone right away. But disputes need more
detail so email works better."
Agent: "Got it. I'll set dispute notifications to email. Anything else?"
Merchant: "Actually, can you also send me the monthly analytics report as a
PDF? The online dashboard is hard to read on my tablet."

Extract all preferences as a JSON array.
```

**Expected output**:

```json
[
  {
    "category": "communication",
    "key": "dispute_notification_method",
    "polarity": "positive",
    "strength": 0.9,
    "confidence": 0.95,
    "source": "explicit",
    "context": "dispute_management",
    "about_entity": "email notifications",
    "evidence": "I really prefer email for anything dispute-related"
  },
  {
    "category": "communication",
    "key": "payment_notification_method",
    "polarity": "positive",
    "strength": 0.7,
    "confidence": 0.85,
    "source": "explicit",
    "context": "payment_confirmations",
    "about_entity": "text message notifications",
    "evidence": "Text is fine for payment confirmations -- those are quick and I like seeing them on my phone right away"
  },
  {
    "category": "tool",
    "key": "report_format",
    "polarity": "positive",
    "strength": 0.8,
    "confidence": 0.90,
    "source": "explicit",
    "context": "analytics",
    "about_entity": "PDF format",
    "evidence": "can you also send me the monthly analytics report as a PDF"
  },
  {
    "category": "environment",
    "key": "analytics_dashboard_usability",
    "polarity": "negative",
    "strength": 0.6,
    "confidence": 0.75,
    "source": "implicit_intentional",
    "context": "analytics",
    "about_entity": "online dashboard",
    "evidence": "The online dashboard is hard to read on my tablet"
  }
]
```

### 1.2 Zero-Shot vs. Few-Shot Approaches

**Zero-shot**: Provide only the schema definition and extraction rules. Works well with frontier models (Sonnet 4.5, GPT-4o, Gemini Pro) for straightforward extractions. Research shows that even without examples, LLMs can internalize relational structures through guided reasoning and schema prompts.

**Few-shot (3-5 examples)**: Providing concrete examples of conversation-to-extraction mappings significantly improves accuracy and calibration. Research from 2025 confirms that few-shot prompting with frontier models achieves accuracy comparable to fully supervised traditional models without requiring labeled training data. Few-shot is particularly important for:
- Distinguishing `explicit` vs. `implicit_intentional` vs. `implicit_unintentional` source types
- Calibrating `strength` and `confidence` values consistently
- Handling merchant-domain vocabulary (disputes, chargebacks, settlement, compliance)

**Recommendation**: Use few-shot prompting (3-5 examples per knowledge type) for production. Invest in curating a high-quality example set for each extraction target (Preference, Skill, Interest, BehavioralPattern). The examples should cover the merchant domain specifically, including payment processing, invoicing, shipping, and compliance vocabulary.

### 1.3 Chain-of-Thought for Complex Extractions

Chain-of-thought (CoT) prompting improves accuracy for complex extractions where the model needs to reason about implicit preferences or behavioral patterns. This is particularly valuable for:

- **Implicit preferences**: "The merchant asked for PDF format because they mentioned tablet usage -- this suggests an environment preference for offline/portable document access."
- **Skill assessment**: "The merchant used technical terms like 'webhook endpoint' and 'API callback' naturally, suggesting advanced technical skill in API integrations."
- **Behavioral patterns**: "Across three turns, the merchant checked analytics before making a pricing change -- this suggests a 'routine' behavioral pattern."

**CoT extraction prompt pattern**:

```
For each potential preference or skill signal in the conversation:
1. Quote the relevant text
2. Explain your reasoning for why this is a preference/skill/pattern
3. Classify the source type (explicit/implicit_intentional/implicit_unintentional)
4. Assign strength and confidence with justification
5. Output the structured extraction

Think step by step before producing the final JSON.
```

**Trade-off**: CoT increases output tokens (cost) by 2-5x but improves accuracy on ambiguous extractions. The reasoning trace also serves as an auditable justification for the extraction -- valuable for our provenance-first design.

### 1.4 Multi-Step Extraction (ChatIE / KGGen Pattern)

The ChatIE approach decomposes extraction into sequential steps, and KGGen demonstrates a two-phase approach (entities first, then relations) that improves consistency.

**Adapted for our ontology**:

**Phase 1 -- Entity Identification**:
```
Given this merchant-agent conversation, identify all entities mentioned.
For each entity, specify:
- name: canonical name
- entity_type: one of ["user", "tool", "resource", "concept", "service"]
- mentions: list of text spans where this entity appears
```

**Phase 2 -- Knowledge Extraction** (given entities from Phase 1):
```
Given these entities and the conversation, extract:
1. Preferences (user preferences about entities)
2. Skills (user competency signals)
3. Interests (topics the user engages with)

Use the entities identified in Phase 1 as the targets for ABOUT edges.
```

**Phase 3 -- Validation** (given extractions from Phase 2):
```
Review each extraction below against the original conversation text.
For each extraction, verify:
1. Is the evidence quote accurate? (exact match in source text)
2. Is the source type correct? (explicit vs. implicit)
3. Is the confidence justified? (would a human agree?)
Flag any extraction that fails validation.
```

**Trade-offs**:
- Multi-step is more accurate (+10-15% on complex conversations per KGGEN benchmarks)
- Multi-step is more expensive (3 LLM calls vs. 1)
- Multi-step provides better provenance (each phase is auditable)
- Multi-step enables different models per phase (cheap model for Phase 1, expensive for Phase 2)

**Recommendation**: Use multi-step for Stage 2 enrichment (batch processing, cost amortized over session). Use single-step for Stage 1 explicit preference handling (low latency required).

---

## 2. Structured Output Mechanisms

### 2.1 Mechanism Comparison

Four primary mechanisms exist for ensuring LLM outputs conform to our ontology schema:

| Mechanism | Schema Guarantee | Latency Impact | Provider Support | Best For |
|-----------|-----------------|----------------|-----------------|----------|
| **JSON Mode** | Valid JSON, no schema guarantee | Minimal | OpenAI, Anthropic, Google | Simple flat extractions |
| **Structured Outputs** (constrained decoding) | 100% schema conformance | Minimal (< 5% overhead) | OpenAI (gpt-4o+), Google (Gemini), vLLM, Outlines | Complex nested schemas |
| **Function Calling / Tool Use** | Schema-validated parameters | Minimal | OpenAI, Anthropic, Google | Multi-type extraction |
| **Post-processing (SLOT)** | Near-perfect (99.5%) via fine-tuned validator | Additional model call | Any LLM + Mistral-7B/Llama-3.2-1B validator | Vendor-agnostic pipelines |

### 2.2 Constrained Decoding (Outlines, Guidance, XGrammar)

Constrained decoding modifies the probability distribution at each generation step by setting the probability of invalid tokens to zero. The JSON Schema is converted into a context-free grammar (CFG), and at each decoding step, only tokens that would produce valid partial output are allowed.

**Key libraries**:
- **Outlines** (dottxt-ai): Builds a finite state machine (FSM) from JSON Schema or Pydantic models. Masks invalid tokens at each step. Open-source, works with any HuggingFace model.
- **llguidance** (guidance-ai): Enforces arbitrary context-free grammars with ~50us CPU overhead per token and negligible startup costs.
- **XGrammar**: High-performance grammar-guided generation, integrated into vLLM.
- **vLLM structured outputs**: Available since vLLM 0.8.5, supports JSON schemas with minimal overhead.

**For self-hosted models**: Outlines or XGrammar provide the best balance of schema guarantee and performance. The StructEval benchmark (2025) evaluated six frameworks -- Outlines, Guidance, Llamacpp, XGrammar, OpenAI, and Gemini -- and found that constrained decoding achieves near-100% schema adherence.

**For API-based models**: OpenAI's Structured Outputs (with `strict: true`) and Anthropic's tool use with `strict: true` provide guaranteed schema conformance without needing local constrained decoding.

### 2.3 Function Calling / Tool Use for Extraction

Function calling naturally maps to our extraction use case because each ontology node type becomes a "tool" the model can invoke:

```python
# Anthropic Claude tool definition for Preference extraction
tools = [
    {
        "name": "extract_preference",
        "description": "Extract a user preference from conversation text",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["tool", "workflow", "communication",
                             "domain", "environment", "style"]
                },
                "key": {
                    "type": "string",
                    "description": "Preference key, e.g. 'notification_method'"
                },
                "polarity": {
                    "type": "string",
                    "enum": ["positive", "negative", "neutral"]
                },
                "strength": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "How strongly the user feels (0.0-1.0)"
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Your certainty this preference exists (0.0-1.0)"
                },
                "source": {
                    "type": "string",
                    "enum": ["explicit", "implicit_intentional",
                             "implicit_unintentional"]
                },
                "context": {
                    "type": "string",
                    "description": "Optional scope qualifier"
                },
                "about_entity": {
                    "type": "string",
                    "description": "Entity this preference concerns"
                },
                "evidence": {
                    "type": "string",
                    "description": "EXACT quote from conversation"
                }
            },
            "required": ["category", "key", "polarity", "strength",
                         "confidence", "source", "about_entity", "evidence"]
        }
    },
    {
        "name": "extract_skill_signal",
        "description": "Extract a user skill/competency signal from conversation",
        "input_schema": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Skill name, e.g. 'API integration'"
                },
                "category": {
                    "type": "string",
                    "enum": ["programming_language", "tool_proficiency",
                             "domain_knowledge", "workflow_skill"]
                },
                "proficiency_signal": {
                    "type": "string",
                    "enum": ["novice", "intermediate", "advanced", "expert"]
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0
                },
                "evidence": {
                    "type": "string",
                    "description": "EXACT quote from conversation"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Why this text indicates this skill level"
                }
            },
            "required": ["skill_name", "category", "proficiency_signal",
                         "confidence", "evidence", "reasoning"]
        }
    },
    {
        "name": "extract_interest",
        "description": "Extract a topic/domain interest signal from conversation",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic or domain of interest"
                },
                "weight": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0
                },
                "source": {
                    "type": "string",
                    "enum": ["explicit", "implicit", "inferred"]
                },
                "evidence": {
                    "type": "string"
                }
            },
            "required": ["topic", "weight", "source", "evidence"]
        }
    }
]
```

**Advantages of function calling for extraction**:
1. **Natural multi-type extraction**: The model can invoke different tools for different knowledge types in a single pass.
2. **Schema enforcement**: Each tool definition enforces the exact schema. With `strict: true`, the model is constrained to produce valid parameters.
3. **Incremental extraction**: The model can invoke the same tool multiple times to extract multiple instances.
4. **Framework alignment**: Tool use maps directly to our Pydantic model definitions and is supported by both Anthropic (Claude) and OpenAI (GPT-4o).

### 2.4 Pydantic Integration

OpenAI's Python SDK natively supports passing Pydantic models as tool schemas. Anthropic's SDK similarly supports JSON Schema definitions derived from Pydantic models. This means our existing domain model definitions in `domain/models.py` can be directly used (or adapted) as extraction schemas:

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class ExtractedPreference(BaseModel):
    """Schema for LLM-extracted preference from conversation text."""
    category: Literal["tool", "workflow", "communication",
                       "domain", "environment", "style"]
    key: str = Field(description="Preference key, e.g. 'notification_method'")
    polarity: Literal["positive", "negative", "neutral"]
    strength: float = Field(ge=0.0, le=1.0,
        description="How strongly the user feels about this (0.0-1.0)")
    confidence: float = Field(ge=0.0, le=1.0,
        description="Your certainty this preference exists in the text (0.0-1.0)")
    source: Literal["explicit", "implicit_intentional", "implicit_unintentional"]
    context: Optional[str] = Field(None,
        description="Scope qualifier, e.g. 'dispute_management'")
    about_entity: str = Field(
        description="The entity this preference concerns")
    evidence: str = Field(
        description="EXACT quote from conversation supporting this preference")
```

**Recommendation**: Define extraction-specific Pydantic models that are subsets of the full domain models, adding fields like `evidence` and `reasoning` that support provenance and validation but are not persisted to the graph. Use function calling / tool use as the primary structured output mechanism for API-based extraction.

### 2.5 SLOT Post-Processing Approach

The SLOT framework (EMNLP 2025) uses a fine-tuned lightweight language model (Mistral-7B or Llama-3.2-1B) as a post-processing layer to structure free-form LLM outputs into schema-conforming JSON. SLOT achieves 99.5% schema accuracy and 94.0% content similarity, outperforming Claude-3.5-Sonnet by +25 and +20 percentage points respectively.

**When to consider SLOT**: If the extraction pipeline needs to be vendor-agnostic (support multiple LLM providers without relying on provider-specific structured output features), SLOT provides a reliable standardization layer. The fine-tuned 1B-parameter model can run locally with minimal latency overhead.

---

## 3. Confidence Scoring

### 3.1 Why Confidence Matters for Our System

Every node type in ADR-0012 carries a `confidence` field (0.0-1.0). This field gates graph insertion (preferences with confidence < 0.3 are pruned in the warm retention tier), determines conflict resolution priority, and provides transparency for the provenance chain. The extraction pipeline must produce calibrated confidence scores from day one.

### 3.2 Approaches to Confidence Scoring

#### 3.2.1 Verbalized Confidence (Direct Self-Rating)

Ask the LLM to self-rate its confidence as part of the extraction output.

```
For each extracted preference, rate your confidence (0.0-1.0) based on:
- 0.9-1.0: User EXPLICITLY stated this preference in clear terms
- 0.7-0.8: Strong implicit signal from user behavior or language
- 0.5-0.6: Moderate implicit signal, some ambiguity
- 0.3-0.4: Weak signal, significant inference required
- 0.1-0.2: Speculative, minimal textual support
```

**Calibration challenge**: Raw verbalized confidence scores from LLMs are systematically miscalibrated -- they tend to be overconfident, reporting high confidence on instances with low accuracy. Recent research (ACL Findings 2025) addresses this through post-hoc calibration:

- **Isotonic regression**: Fit a monotonic mapping from raw confidence to calibrated confidence using a held-out validation set.
- **DINCO (Distractor-Normalized Coherence)**: Generates self-distractor alternative claims and normalizes confidence by total verbalized confidence across distractors. At 10 inference calls, DINCO outperforms self-consistency at 100. This is the most promising recent technique.
- **Histogram binning**: Group predictions by confidence bin, compute empirical accuracy per bin, and adjust.

**Cost**: 1x LLM call (confidence is part of the extraction output). Calibration requires initial labeled data.

#### 3.2.2 Self-Consistency Sampling

Extract N times with temperature > 0, measure agreement across samples. Fields that are consistent across N extractions receive higher confidence.

```python
def self_consistency_confidence(
    conversation_text: str,
    extraction_prompt: str,
    model: str,
    num_samples: int = 5,
    temperature: float = 0.7
) -> list[dict]:
    """Extract multiple times and score confidence by agreement."""
    extractions = []
    for _ in range(num_samples):
        result = llm_extract(conversation_text, extraction_prompt,
                             model=model, temperature=temperature)
        extractions.append(result)

    # For each unique preference key, count how many samples extracted it
    preference_counts = {}
    for extraction in extractions:
        for pref in extraction.get("preferences", []):
            key = (pref["category"], pref["key"], pref["about_entity"])
            if key not in preference_counts:
                preference_counts[key] = {
                    "count": 0,
                    "strengths": [],
                    "sources": [],
                    "examples": []
                }
            preference_counts[key]["count"] += 1
            preference_counts[key]["strengths"].append(pref["strength"])
            preference_counts[key]["sources"].append(pref["source"])
            preference_counts[key]["examples"].append(pref)

    # Confidence = fraction of samples that extracted this preference
    results = []
    for key, data in preference_counts.items():
        consistency_confidence = data["count"] / num_samples
        median_strength = sorted(data["strengths"])[len(data["strengths"]) // 2]
        majority_source = max(set(data["sources"]),
                             key=data["sources"].count)
        best_example = data["examples"][0]
        best_example["confidence"] = consistency_confidence
        best_example["strength"] = median_strength
        best_example["source"] = majority_source
        results.append(best_example)

    return results
```

**Advantages**:
- Most reliable confidence signal -- agreement across independent samples strongly correlates with correctness
- No calibration data needed
- Works with any model

**Disadvantages**:
- Cost multiplied by N (typically 3-5 samples)
- Latency multiplied by N (unless parallelized)

**CISC optimization**: Confidence-Informed Self-Consistency (ACL Findings 2025) reduces required samples by 40% by weighting votes by verbalized confidence. This combines verbalized confidence with self-consistency for the best of both approaches.

#### 3.2.3 Token Log-Probability Aggregation

Aggregate token-level log probabilities across each extracted field to estimate per-field confidence.

**Limitations**:
- Anthropic does not expose token log-probabilities, ruling out this approach for Claude models
- Log probabilities capture aleatoric uncertainty (known unknowns) but miss epistemic uncertainty (unknown unknowns) -- an LLM may confidently hallucinate with high token probabilities
- Per-field confidence requires decomposing the JSON output into field-level token sequences, which is complex

**When to use**: Only if using OpenAI models (which expose logprobs) and cost constraints prevent self-consistency sampling.

#### 3.2.4 Cleanlab TLM (Trustworthiness Scoring)

Cleanlab's Trustworthy Language Model (TLM) provides a trustworthiness score for any LLM output, including per-field confidence for structured outputs. TLM additionally quantifies epistemic uncertainty (unknown unknowns), which token probabilities miss.

**Key advantages**:
- Works with any base LLM model
- Can score per-field within structured outputs
- Handles both aleatoric and epistemic uncertainty
- Highest AUROC across all benchmarks tested (Cleanlab 2025)

**Key disadvantages**:
- Requires Cleanlab API access (commercial product)
- Additional API call overhead
- May not be necessary if self-consistency provides sufficient calibration

### 3.3 Recommended Confidence Strategy

**For production deployment**:

1. **Primary**: Verbalized confidence with DINCO calibration for per-extraction confidence scoring (cost: 1x base extraction + ~10 distractor evaluations per batch)
2. **Validation**: Self-consistency sampling (N=3) on a random 10% sample of extractions, used to monitor and recalibrate the verbalized confidence model
3. **Override**: Map source type to minimum confidence floors:
   - `explicit` source -> confidence >= 0.7 (raise if lower)
   - `implicit_intentional` -> confidence >= 0.4
   - `implicit_unintentional` -> confidence >= 0.3
   - `inferred` -> confidence >= 0.15

---

## 4. Model Selection for Extraction

### 4.1 Model Tiers and Pricing (as of February 2026)

| Model | Class | Input $/M tokens | Output $/M tokens | Tokens/sec | Structured Output | Best For |
|-------|-------|------------------|--------------------|------------|-------------------|----------|
| GPT-4o-mini | Small | $0.15 | $0.60 | ~150 | JSON mode, Structured Outputs | High-volume Stage 1/2 extraction |
| Gemini 2.0 Flash | Small | $0.10 | $0.40 | ~250 | JSON mode, function calling | High-volume, cost-sensitive extraction |
| Gemini 3 Flash | Small | $0.05 | $0.20 | ~300 | JSON mode, function calling | Lowest-cost extraction |
| Claude Haiku 4.5 | Small+ | $1.00 | $5.00 | ~150 | Tool use, strict mode | Quality-sensitive extraction |
| GPT-4o | Medium | $2.50 | $10.00 | ~100 | JSON mode, Structured Outputs | Complex pattern detection |
| Claude Sonnet 4.5 | Medium | $3.00 | $15.00 | ~80 | Tool use, strict mode | Complex reasoning, few-shot |
| Claude Opus 4.6 | Large | $15.00 | $75.00 | ~40 | Tool use, strict mode | Most complex, highest accuracy |

**Note**: Prices fluctuate. Batch API discounts (50% for OpenAI, 50% for Anthropic) and prompt caching (90% savings for Anthropic on repeated context) significantly reduce effective costs.

### 4.2 Cost-Accuracy Analysis for Extraction

Research from 2025 (StructEval benchmark) shows GPT-4o achieves only 76% average accuracy on structured output tasks. Smaller models lag further. However, extraction accuracy depends heavily on task complexity:

| Task Complexity | Recommended Model | Rationale |
|----------------|-------------------|-----------|
| **Simple entity extraction** (Stage 1) | GPT-4o-mini / Gemini Flash | Low-cost, high-throughput. Entities are named in text. |
| **Explicit preference extraction** (Stage 1) | GPT-4o-mini / Gemini Flash | User directly states preferences -- minimal inference. |
| **Implicit preference extraction** (Stage 2) | Claude Haiku 4.5 / GPT-4o-mini | Moderate inference. Haiku outperforms on nuanced text. |
| **Skill assessment** (Stage 2) | Claude Haiku 4.5 | Requires reasoning about technical vocabulary. |
| **Cross-session pattern detection** (Stage 3) | Claude Sonnet 4.5 / GPT-4o | Complex reasoning over long context. |
| **Preference conflict resolution** (Stage 3) | Claude Sonnet 4.5 / GPT-4o | Requires understanding temporal and semantic relationships. |

### 4.3 Cost Projection

For a merchant support agent handling ~1000 conversations/day, with an average of 8 turns per conversation:

| Stage | Model | Calls/day | Avg tokens/call | Daily cost |
|-------|-------|-----------|-----------------|------------|
| Stage 1 (entity extraction) | GPT-4o-mini | 8,000 (per-turn) | ~500 in + ~200 out | ~$0.96 |
| Stage 2 (preference/skill extraction) | Claude Haiku 4.5 | 1,000 (per-session) | ~2,000 in + ~500 out | ~$4.50 |
| Stage 3 (pattern detection) | Claude Sonnet 4.5 | 100 (per-user-batch) | ~5,000 in + ~1,000 out | ~$3.00 |
| **Total** | | | | **~$8.50/day** |

With prompt caching (90% savings on system prompt + schema, ~60% of input tokens): effective daily cost drops to ~$4-5/day.

### 4.4 Model Selection Recommendation

**Two-tier strategy**:
- **Tier 1 (Workhorse)**: GPT-4o-mini or Gemini Flash for Stage 1 and simple Stage 2 extractions. Optimize for cost and throughput.
- **Tier 2 (Quality)**: Claude Haiku 4.5 for nuanced Stage 2 extractions (implicit preferences, skill assessment). Claude Sonnet 4.5 or GPT-4o for Stage 3 complex pattern detection.

**Routing logic**: Start all extractions with Tier 1. If the extraction confidence is below a threshold (e.g., 0.5) or the conversation contains complex reasoning signals, escalate to Tier 2.

---

## 5. Batch vs. Per-Turn Extraction

### 5.1 Trade-off Matrix

| Strategy | Latency | Cost | Context Quality | Use Case |
|----------|---------|------|-----------------|----------|
| **Per-turn** | Low (< 500ms) | High (LLM call per turn) | Low (no cross-turn context) | Stage 1: explicit events, entity extraction |
| **Per-session** (batch) | Medium (seconds, async) | Medium (1 call per session) | High (full conversation context) | Stage 2: implicit preference/skill extraction |
| **Per-user** (batch) | High (minutes, periodic) | Low (1 call per user per cycle) | Highest (cross-session patterns) | Stage 3: behavioral patterns, workflow extraction |

### 5.2 Per-Turn Extraction (Stage 1)

**When**: Event arrives, extract immediately.

**What to extract**:
- Entities mentioned in the event payload (tool names, services, concepts)
- Explicit preference statements (detected by `user.preference.stated` event type)
- Direct skill declarations (`user.skill.declared` event type)

**How**: Lightweight regex/NER for entity extraction, no LLM needed for most cases. LLM only for `user.preference.stated` events that need schema mapping.

**Latency budget**: < 500ms per event (per ADR-0008 Stage 1 requirements).

### 5.3 Per-Session Batch Extraction (Stage 2)

**When**: Session ends or reaches a configurable turn count threshold (e.g., every 10 turns).

**What to extract**:
- Implicit preferences (from behavioral signals across the session)
- Skill/competency assessments (from how the user discusses technical topics)
- Topic interests (from entity co-occurrence and discussion depth)

**How**: Concatenate all session turns into a single extraction prompt. This is the optimal unit for LLM extraction because:

1. **Cross-turn context**: Preferences that emerge across multiple turns (e.g., "I mentioned I prefer email for disputes, and later confirmed I want all dispute-related communications by email") can be captured.
2. **Token efficiency**: A single call over the full session is cheaper than per-turn calls (amortized prompt/schema overhead).
3. **LLM performance**: Research from 2025 shows LLMs exhibit 39% lower performance in multi-turn conversations vs. single-turn when processing turns independently. Batch extraction avoids this degradation by providing full context.

**Session extraction prompt structure**:

```
SYSTEM:
You are analyzing a complete conversation between a merchant and a support
agent. Extract all knowledge signals from the full conversation.

[Schema definitions for Preference, Skill, Interest]

IMPORTANT: Consider the FULL conversation context. A preference may be
stated in one turn and confirmed/elaborated in a later turn. Extract the
strongest, most complete version of each preference.

USER:
Complete conversation transcript:
[Turn 1]: Merchant: "..."
[Turn 2]: Agent: "..."
[Turn 3]: Merchant: "..."
...

Extract all preferences, skill signals, and interest signals.
```

### 5.4 Per-User Batch Extraction (Stage 3)

**When**: Periodic batch job (e.g., daily or after N new sessions for a user).

**What to extract**:
- Cross-session behavioral patterns (delegation, escalation, routine, avoidance, exploration, specialization)
- Workflow sequences (recurring action patterns)
- Preference conflict resolution (contradictory preferences across sessions)
- Interest evolution (changing topic weights over time)

**How**: Aggregate session summaries (not raw turns) for the user and run pattern detection. This avoids context window limitations and focuses the LLM on higher-level patterns.

### 5.5 Recommendation

**Hybrid strategy**: Per-turn for Stage 1 (explicit/structural), per-session for Stage 2 (implicit extraction), per-user for Stage 3 (pattern detection). This aligns with the three-stage consolidation pipeline in ADR-0008.

---

## 6. Hallucination Detection

### 6.1 The Critical Risk

When an LLM extracts knowledge that is NOT present in the conversation text, it creates a false node in the knowledge graph. Unlike hallucinations in chat responses (which are ephemeral), hallucinated graph nodes persist and propagate -- downstream queries and agent behaviors will be influenced by fabricated preferences, skills, or patterns. This makes hallucination detection a critical quality gate for the extraction pipeline.

### 6.2 Types of Extraction Hallucinations

| Type | Description | Example | Risk Level |
|------|-------------|---------|------------|
| **Fabricated preference** | LLM invents a preference not in the text | Text: "Send me reports by email" -> Extraction: "User prefers dark mode" | High |
| **Exaggerated strength** | LLM overestimates preference intensity | Text: "I guess email is fine" -> strength: 0.95 | Medium |
| **Wrong source type** | LLM classifies implicit as explicit (or vice versa) | Behavioral pattern classified as explicit statement | Medium |
| **Invented entity** | LLM creates an entity not mentioned in conversation | "User prefers Stripe" when Stripe was never mentioned | High |
| **Over-inference** | LLM draws conclusions beyond what the text supports | "Uses mobile app" -> "Prefers mobile-first design" | Medium |

### 6.3 Detection Techniques

#### 6.3.1 Evidence-Grounding Verification (Primary)

The most effective technique for our use case: require every extraction to include an `evidence` field with an exact quote from the source text, then verify the quote exists.

```python
def verify_evidence_grounding(
    extraction: dict,
    source_text: str,
    fuzzy_threshold: float = 0.85
) -> tuple[bool, float]:
    """Verify that the extraction's evidence quote exists in source text."""
    evidence = extraction.get("evidence", "")
    if not evidence:
        return False, 0.0

    # Exact substring match
    if evidence.lower() in source_text.lower():
        return True, 1.0

    # Fuzzy match for minor LLM paraphrasing
    from difflib import SequenceMatcher
    # Check against sliding windows of source text
    evidence_len = len(evidence)
    best_ratio = 0.0
    for i in range(len(source_text) - evidence_len + 1):
        window = source_text[i:i + evidence_len + 20]
        ratio = SequenceMatcher(None, evidence.lower(),
                                window.lower()).ratio()
        best_ratio = max(best_ratio, ratio)

    return best_ratio >= fuzzy_threshold, best_ratio
```

**Limitation**: This catches fabricated evidence but not over-inference (where the evidence exists but does not support the extraction).

#### 6.3.2 NLI-Based Entailment Verification

Decompose each extraction into a natural language claim and verify entailment against the source text using an NLI model.

```python
from transformers import pipeline

nli_model = pipeline("text-classification",
                     model="microsoft/deberta-v3-large-mnli")

def verify_extraction_entailment(
    extraction: dict,
    source_text: str
) -> tuple[str, float]:
    """Verify extraction is entailed by source text using NLI."""
    # Convert extraction to natural language claim
    claim = extraction_to_claim(extraction)
    # e.g., "The user prefers email notifications for dispute-related
    #         communications with high strength."

    result = nli_model(
        {"text": source_text, "text_pair": claim},
        top_k=3
    )

    # Parse NLI result
    entailment_score = next(
        (r["score"] for r in result if r["label"] == "ENTAILMENT"), 0.0
    )
    contradiction_score = next(
        (r["score"] for r in result if r["label"] == "CONTRADICTION"), 0.0
    )

    if entailment_score > 0.7:
        return "entailed", entailment_score
    elif contradiction_score > 0.5:
        return "contradicted", contradiction_score
    else:
        return "neutral", max(entailment_score, 1 - contradiction_score)


def extraction_to_claim(extraction: dict) -> str:
    """Convert a structured extraction to a natural language claim."""
    category = extraction.get("category", "unknown")
    key = extraction.get("key", "unknown")
    polarity = extraction.get("polarity", "positive")
    about = extraction.get("about_entity", "unknown")
    source = extraction.get("source", "unknown")

    polarity_text = {
        "positive": "prefers",
        "negative": "dislikes",
        "neutral": "has no strong feeling about"
    }[polarity]

    source_text = {
        "explicit": "explicitly stated that they",
        "implicit_intentional": "deliberately indicated that they",
        "implicit_unintentional": "implicitly showed that they"
    }.get(source, "indicated that they")

    return f"The user {source_text} {polarity_text} {about} for {key}."
```

**GraphEval pattern** (Amazon Science, 2025): Extract atomic claims from the LLM output as a sub-graph, then compare each triple's entailment to the source text. This is the most thorough approach but also the most expensive (NLI call per extraction).

#### 6.3.3 Cross-Extraction Consistency Check

If using self-consistency sampling (Section 3.2.2), extractions that appear in fewer than 50% of samples are flagged as potential hallucinations.

#### 6.3.4 LLM-as-Judge Verification

Use a separate LLM call (potentially a different model) to verify each extraction:

```
Given the conversation text below, verify whether this extraction is
accurate:

Extraction: {extraction_json}

Conversation: {source_text}

Answer these questions:
1. Is the evidence quote present in the conversation? (yes/no)
2. Does the evidence support the extracted preference? (yes/no)
3. Is the source type (explicit/implicit) correct? (yes/no)
4. Is the confidence level appropriate? (too_high/appropriate/too_low)

Return your assessment as JSON.
```

**Trade-off**: Adds one LLM call per extraction. Useful as a quality gate for high-stakes extractions (e.g., explicit preferences that will be used to override defaults).

### 6.4 Recommended Hallucination Detection Pipeline

```
Extraction -> Evidence Grounding Check (fast, regex-based)
    |
    |-- FAIL -> Reject extraction
    |
    v
    NLI Entailment Verification (medium cost, DeBERTa-based)
    |
    |-- CONTRADICTED -> Reject extraction
    |-- NEUTRAL -> Flag for review, reduce confidence by 0.2
    |
    v
    Confidence Threshold Gate
    |
    |-- confidence < 0.3 -> Do not persist to graph
    |
    v
    Persist to graph with DERIVED_FROM edge to source event
```

**Cost**: The NLI model (DeBERTa-v3-large) runs locally at ~5ms per claim, adding negligible latency. The evidence grounding check is pure string matching. This pipeline adds minimal cost while catching the most common hallucination types.

---

## 7. Multi-Turn Context Handling

### 7.1 The Challenge

Preferences and skills often emerge across multiple conversation turns, not in a single statement:

```
Turn 1: Merchant: "I need to update my shipping settings"
Turn 3: Merchant: "We mainly ship to Canada and Mexico"
Turn 5: Merchant: "Do you support real-time rate calculations for
                   international shipments?"
Turn 7: Merchant: "Great, let's enable that. We've been calculating
                   rates manually and it's been a pain."
```

**Aggregated signal**: The merchant has domain knowledge in international shipping (skill), a preference for automated rate calculations (preference, implicit_intentional), and an interest in international commerce (interest).

No single turn contains the full picture. The extraction system must synthesize across turns.

### 7.2 Approaches

#### 7.2.1 Full-Session Batch (Recommended for Stage 2)

As described in Section 5.3, concatenating the full session transcript and extracting once provides the best context for cross-turn synthesis. The prompt should explicitly instruct the model to consider the full conversation:

```
IMPORTANT: Preferences and skills may be spread across multiple turns.
Look for signals that build on each other across the conversation.
For example, if the user asks a basic question in one turn but then
uses advanced terminology in a later turn, consider the overall
skill signal across all turns.
```

#### 7.2.2 Sliding Window with State Accumulation

For long conversations that exceed the context window, use a sliding window approach:

1. Process turns 1-N with the extraction prompt, producing `state_1`
2. Process turns (N/2)-2N with `state_1` as prior context, producing `state_2`
3. Continue with overlapping windows until all turns are processed
4. Merge extracted knowledge across all windows

```python
def sliding_window_extraction(
    turns: list[str],
    window_size: int = 20,
    overlap: int = 5,
    prior_state: dict = None
) -> dict:
    """Extract knowledge using sliding windows for long conversations."""
    accumulated_knowledge = prior_state or {
        "preferences": [],
        "skills": [],
        "interests": []
    }

    for start in range(0, len(turns), window_size - overlap):
        window = turns[start:start + window_size]

        prompt = build_extraction_prompt(
            turns=window,
            prior_knowledge=accumulated_knowledge,
            instruction="Update and refine the prior knowledge based "
                        "on this conversation segment. Add new "
                        "extractions and adjust confidence of existing "
                        "ones if confirmed or contradicted."
        )

        new_knowledge = llm_extract(prompt)
        accumulated_knowledge = merge_knowledge(
            accumulated_knowledge, new_knowledge
        )

    return accumulated_knowledge
```

#### 7.2.3 Turn-Level Signal Accumulation (for Stage 1)

For per-turn processing at Stage 1, accumulate lightweight signals and defer synthesis to Stage 2:

```python
# Stage 1: Accumulate signals per turn (no LLM needed)
turn_signals = []
for turn in conversation_turns:
    signals = {
        "turn_id": turn.id,
        "entities_mentioned": extract_entities_fast(turn.text),
        "has_explicit_preference": matches_preference_pattern(turn.text),
        "technical_vocabulary_level": count_technical_terms(turn.text),
        "sentiment": quick_sentiment(turn.text)
    }
    turn_signals.append(signals)

# Stage 2: Synthesize accumulated signals with LLM
session_summary = {
    "total_turns": len(turn_signals),
    "entities_across_turns": aggregate_entities(turn_signals),
    "preference_turns": [s for s in turn_signals
                        if s["has_explicit_preference"]],
    "avg_technical_level": mean(s["technical_vocabulary_level"]
                               for s in turn_signals)
}
# Feed summary + full transcript to LLM for extraction
```

### 7.3 Research Context

2025 research (ACM survey on multi-turn dialogue systems) identifies three memory layers for multi-turn LLM interactions:

1. **Turn memory**: Within-turn context (individual message)
2. **Conversational memory**: Cross-turn context within a session
3. **Persistent memory**: Cross-session context (our user profile)

Our three-stage extraction pipeline maps naturally to these layers:
- Stage 1 -> Turn memory (per-turn entity/explicit extraction)
- Stage 2 -> Conversational memory (per-session implicit extraction)
- Stage 3 -> Persistent memory (cross-session pattern detection)

### 7.4 LLM Performance Degradation in Multi-Turn

Critical finding: Research shows LLMs exhibit 39% lower performance in multi-turn conversations compared to single-turn tasks. When models "take a wrong turn" early in a conversation, they tend not to recover. This argues strongly for:

1. **Batch extraction over per-turn extraction** for implicit signals -- the LLM sees the complete picture rather than building incrementally
2. **Independent extraction calls** rather than maintaining extraction state across turns within an LLM conversation
3. **Session-end extraction** over mid-session extraction to avoid early-turn biases

---

## 8. Extraction Strategies for Different Knowledge Types

### 8.1 Preferences

**Characteristics**: Preferences have polarity (like/dislike), strength, temporal evolution, and context-dependency. They are the most common extraction target.

**Strategy**: Sentiment-aware prompting with explicit polarity detection.

```
SYSTEM:
Extract user preferences. Pay attention to:
- POSITIVE signals: "I prefer", "I like", "I want", "I always use",
  "that works well", "I'd rather", positive comparative language
- NEGATIVE signals: "I don't like", "I avoid", "that's frustrating",
  "stop doing", negative comparative language
- STRENGTH indicators: "always", "never" (strong, 0.8-1.0);
  "usually", "often" (medium, 0.5-0.7);
  "sometimes", "I guess" (weak, 0.2-0.4)
- CONTEXT: Note when a preference applies only in certain situations
  (e.g., "for disputes" vs. "for everything")
```

**Merchant-specific signals**:
```
Merchant preference signals to watch for:
- Notification preferences: email vs. text vs. push vs. in-app
- Report preferences: PDF vs. dashboard vs. CSV vs. email summary
- Communication style: detailed vs. concise, formal vs. casual
- Tool preferences: mobile app vs. desktop, API vs. UI
- Workflow preferences: manual review vs. auto-approve, batch vs. real-time
- Domain preferences: domestic vs. international, B2B vs. B2C
```

### 8.2 Skills/Competencies

**Characteristics**: Skills are inferred from behavioral signals, not directly stated. Technical vocabulary usage, question complexity, and tool interaction patterns indicate proficiency levels.

**Strategy**: Behavioral signal analysis with explicit proficiency calibration.

```
SYSTEM:
Assess the user's skill levels based on their conversation behavior.
Look for these signals:

EXPERT indicators (proficiency 0.8-1.0):
- Uses specialized technical terminology correctly
- References specific API endpoints, configurations, or parameters
- Diagnoses issues without prompting
- Suggests solutions before the agent does

ADVANCED indicators (proficiency 0.6-0.8):
- Understands technical concepts when explained
- Asks specific, well-formed questions
- Knows what they want but may not know exact steps

INTERMEDIATE indicators (proficiency 0.3-0.6):
- Asks for explanations of concepts
- Uses some technical terms but may misuse them
- Needs guidance on multi-step processes

NOVICE indicators (proficiency 0.0-0.3):
- Asks basic "what is" questions
- Needs step-by-step instructions
- Uses non-technical language for technical concepts
- Expresses confusion about fundamental features

Skill categories for merchant context:
- Payment processing (disputes, refunds, chargebacks, settlements)
- Technical integration (APIs, webhooks, SDKs, testing)
- Financial reporting (analytics, reconciliation, tax compliance)
- Business operations (inventory, shipping, multi-currency)
- Platform navigation (dashboard, settings, configuration)
```

**Concrete example prompt**:

```
USER:
Conversation:

Merchant: "My webhook endpoint keeps returning 502 on the IPN callback.
I checked the nginx error logs and it looks like the upstream timeout is
set to 30s but your payload processing takes about 45s for batch IPNs.
Can I increase the timeout or is there an async callback option?"

Extract skill signals.
```

**Expected output**:
```json
[
  {
    "skill_name": "API integration",
    "category": "tool_proficiency",
    "proficiency_signal": "expert",
    "confidence": 0.90,
    "evidence": "My webhook endpoint keeps returning 502 on the IPN callback. I checked the nginx error logs and it looks like the upstream timeout is set to 30s",
    "reasoning": "User correctly identifies the 502 error, knows to check nginx logs, understands upstream timeout configuration, and identifies the root cause (processing time exceeds timeout). This indicates expert-level proficiency in API integration and server administration."
  },
  {
    "skill_name": "Server administration",
    "category": "tool_proficiency",
    "proficiency_signal": "advanced",
    "confidence": 0.80,
    "evidence": "I checked the nginx error logs and it looks like the upstream timeout is set to 30s",
    "reasoning": "User knows how to read nginx error logs and understands timeout configuration, indicating advanced server administration skills."
  }
]
```

### 8.3 Interests/Topics

**Characteristics**: Interests are topic-level engagement signals. They differ from preferences in that they represent what the user engages with, not what they like/dislike.

**Strategy**: Topic frequency analysis + depth-of-engagement scoring.

```
SYSTEM:
Identify topics the user shows interest in based on:
- Topics they ask questions about (engagement signal)
- Topics they discuss in depth vs. briefly mention
- Topics they return to across multiple turns
- Topics they ask for more information about

Weight signals:
- Asking a detailed question (weight 0.7-0.9): "How do I set up
  multi-currency pricing for my Shopify integration?"
- Mentioning in passing (weight 0.2-0.4): "I also sell on eBay sometimes"
- Requesting documentation (weight 0.8-1.0): "Can you send me the guide
  for international tax compliance?"
- Expressing frustration about a topic (weight 0.5-0.7 -- indicates
  engagement even if negative): "I never understand these chargeback reports"
```

### 8.4 Behavioral Patterns

**Characteristics**: Behavioral patterns are cross-session, cross-interaction patterns that require analysis over multiple conversations. They are the most complex extraction target.

**Strategy**: Session summary analysis with pattern template matching.

```
SYSTEM:
Given summaries of the user's recent sessions, identify behavioral
patterns. Look for:

DELEGATION pattern: User routes specific task types to specific agents
- Signal: "For X tasks, I always use [agent]"
- Signal: Consistent agent choice by task category across sessions

ESCALATION pattern: User switches agents or asks for human help when blocked
- Signal: Session starts with one agent, transfers to another
- Signal: "Can I talk to someone else?" or "This isn't working"

ROUTINE pattern: User follows consistent step sequences
- Signal: Same sequence of actions across multiple sessions
- Signal: "I always do X before Y"

AVOIDANCE pattern: User consistently avoids certain features/tools
- Signal: Never uses a feature that was offered
- Signal: "I don't use X" or consistently chooses alternatives

EXPLORATION pattern: User frequently tries new features
- Signal: Asks about features not previously used
- Signal: High variety in tool usage across sessions

SPECIALIZATION pattern: User develops deep expertise in a domain
- Signal: Increasing technical depth in a topic over time
- Signal: Shifts from asking basic questions to advanced questions

For each pattern, provide:
- pattern_type: one of the above types
- description: what the specific pattern is
- confidence: 0.0-1.0
- supporting_sessions: which session summaries support this pattern
```

### 8.5 Entity Extraction

**Characteristics**: Entities are mentioned by name in conversation text. They map to the Entity node type with entity_type discrimination.

**Strategy**: Named Entity Recognition (NER) enhanced with domain-specific entity types.

For Stage 1, a lightweight NER approach (spaCy or regex-based) is sufficient:

```python
# Domain-specific entity patterns for merchant context
MERCHANT_ENTITIES = {
    "service": [
        r"PayPal|Stripe|Square|Shopify|WooCommerce|BigCommerce|eBay|Amazon",
        r"QuickBooks|Xero|FreshBooks|Wave"
    ],
    "tool": [
        r"dashboard|API|webhook|SDK|plugin|extension|widget",
        r"invoice generator|report builder|analytics tool"
    ],
    "concept": [
        r"chargeback|dispute|refund|settlement|reconciliation",
        r"PCI compliance|tax compliance|KYC|AML",
        r"multi-currency|cross-border|international shipping"
    ]
}
```

For Stage 2, LLM-based entity extraction with disambiguation:

```
Given this conversation, identify all entities mentioned:
- Services: payment platforms, e-commerce platforms, SaaS tools
- Tools: specific features, plugins, integrations
- Concepts: business concepts, compliance topics, financial terms
- Resources: documents, reports, guides

For each entity:
- name: canonical name (e.g., "PayPal" not "paypal" or "PP")
- entity_type: service | tool | concept | resource
- mentions: list of text spans where this entity appears
```

### 8.6 Summary: Strategy per Knowledge Type

| Knowledge Type | Stage | Model Tier | Prompting Strategy | Key Challenge |
|---------------|-------|------------|-------------------|---------------|
| Preference | 1+2 | Small (explicit), Medium (implicit) | Sentiment-aware, polarity detection | Strength calibration |
| Skill | 2 | Small+ (Haiku-class) | Behavioral signal analysis, proficiency rubric | Distinguishing genuine expertise from surface knowledge |
| Interest | 2 | Small | Topic frequency + engagement depth | Separating genuine interest from transactional mentions |
| BehavioralPattern | 3 | Medium (Sonnet/GPT-4o) | Cross-session template matching | Requires sufficient session history; cold-start |
| Entity | 1 | None (regex/NER) or Small | Domain-specific NER | Entity resolution / deduplication |
| Workflow | 3 | Medium | Sequence pattern detection | Distinguishing recurring workflows from coincidence |

---

## 9. Implementation Architecture Recommendations

### 9.1 Extraction Pipeline Design

```
Conversation Event
    |
    v
Stage 1: Per-Turn Processing (< 500ms)
    |-- Entity extraction (regex/NER, no LLM)
    |-- Explicit preference detection (pattern match)
    |-- If explicit preference: LLM extraction (GPT-4o-mini)
    |       -> Schema validation (Pydantic)
    |       -> Evidence grounding check
    |       -> Persist Preference + DERIVED_FROM edge
    |
    v
Stage 2: Per-Session Enrichment (async, seconds)
    |-- Triggered at session end or every N turns
    |-- Full session transcript -> LLM extraction (Haiku 4.5)
    |       -> Tool use: extract_preference, extract_skill, extract_interest
    |       -> Multi-step: entities first, then knowledge types
    |       -> Schema validation (Pydantic)
    |       -> Evidence grounding check
    |       -> NLI entailment verification
    |       -> Confidence threshold gate (>= 0.3)
    |       -> Persist nodes + DERIVED_FROM edges
    |
    v
Stage 3: Per-User Re-Consolidation (periodic batch)
    |-- Triggered daily or after N sessions per user
    |-- Session summaries -> LLM pattern detection (Sonnet 4.5)
    |       -> BehavioralPattern extraction
    |       -> Workflow detection
    |       -> Preference conflict resolution
    |       -> Cross-session preference merging
    |-- Confidence threshold gate (>= 0.5 for patterns)
    |-- Persist patterns + DERIVED_FROM edges
```

### 9.2 Prompt Caching Strategy

With Anthropic's prompt caching (90% savings on cached input tokens):

- **Cache the system prompt + schema definitions**: These are identical across all extraction calls. Cache breakpoint after the schema section.
- **Cache few-shot examples**: If using 3-5 examples, cache them as part of the system prompt.
- **Only the conversation text varies per call**.

For a typical extraction call:
- System prompt + schema + examples: ~1,500 tokens (cached at 90% discount)
- Conversation text: ~500-2,000 tokens (not cached)
- Effective input cost: ~150 cached tokens + 500-2,000 new tokens

### 9.3 Quality Monitoring

```python
# Metrics to track for extraction quality
EXTRACTION_METRICS = {
    # Grounding rate: % of extractions with verified evidence
    "grounding_rate": "extractions_with_verified_evidence / total_extractions",

    # NLI pass rate: % of extractions that pass entailment check
    "nli_pass_rate": "entailed_extractions / total_extractions",

    # Consistency rate: for self-consistency sampled extractions,
    # average agreement across samples
    "consistency_rate": "mean(agreement_scores)",

    # Confidence calibration: correlation between reported confidence
    # and actual accuracy (measured against human labels)
    "calibration_error": "expected_calibration_error(confidence, accuracy)",

    # Extraction yield: average extractions per session
    "yield_per_session": "total_extractions / total_sessions",

    # Rejection rate: % of extractions rejected by validation pipeline
    "rejection_rate": "rejected_extractions / total_extractions",
}
```

---

## 10. Conversation-Specific Extraction Challenges

This section addresses challenges unique to extracting knowledge from multi-turn merchant-agent conversations, as opposed to extraction from documents or single-turn queries.

### 10.1 Negation and Correction Handling

Merchants frequently negate, retract, or correct statements during conversations. The extraction pipeline must handle these patterns correctly to avoid persisting outdated or reversed preferences.

**Common negation/correction patterns**:

```
Pattern 1 -- Direct negation:
  "I don't want text notifications for disputes."
  -> Preference(polarity="negative", about_entity="text notifications",
     context="disputes")

Pattern 2 -- Correction of prior statement:
  Turn 3: "Send me reports by email."
  Turn 7: "Actually, wait -- can you do PDF attachments instead of
           just an email link?"
  -> First preference is superseded by second. Extract both:
     Pref1(key="report_delivery", about="email", superseded_by=Pref2.id)
     Pref2(key="report_format", about="PDF attachment")

Pattern 3 -- Hedged negation:
  "I'm not really a fan of the dashboard, but I guess it's fine for
   quick checks."
  -> Preference(polarity="negative", strength=0.4, about="dashboard",
     context="general") AND
     Preference(polarity="neutral", strength=0.3, about="dashboard",
     context="quick_checks")

Pattern 4 -- Mind change within session:
  Turn 2: "Let's set up weekly reports."
  Turn 8: "Actually, I changed my mind. Monthly is enough."
  -> Only the final state should be the active preference.
     Weekly preference gets superseded_by monthly preference.
```

**Extraction prompt guidance for negation**:

```
IMPORTANT: Handle negations and corrections carefully.
- "don't", "not", "never", "stop", "avoid" -> set polarity="negative"
- "Actually", "wait", "I changed my mind", "instead" -> the NEW
  statement supersedes the PREVIOUS one. Extract both and mark the
  earlier one as superseded.
- "I guess", "it's fine", "I suppose" -> weak positive (strength 0.2-0.4),
  NOT a strong preference
- If the user corrects themselves, ONLY the corrected version should have
  high confidence. The retracted statement gets confidence reduced to 0.2.
```

**Implementation pattern**: When the extraction pipeline detects a correction pattern (keywords: "actually", "wait", "instead", "changed my mind", "never mind"), it should:
1. Extract both the original and corrected preference
2. Mark the original with `superseded_by` pointing to the corrected version
3. Set the original's confidence to 0.2 (retracted)
4. Create DERIVED_FROM edges from both to their respective source events

### 10.2 Coreference Resolution

Conversations contain frequent pronoun references and elliptical constructions that obscure what the user is referring to:

```
Turn 1: Merchant: "I've been using the analytics dashboard."
Turn 2: Agent: "How do you find it?"
Turn 3: Merchant: "It's great for daily sales, but it's slow when I
                   pull monthly reports."
Turn 4: Agent: "Would you like to try the new reporting API?"
Turn 5: Merchant: "Maybe. Is it faster?"
```

**Coreference challenges**:
- "It" in Turn 3 refers to "analytics dashboard" from Turn 1
- "it" in Turn 5 refers to "reporting API" from Turn 4
- The preference signal ("it's great for daily sales, but it's slow for monthly reports") must be linked to "analytics dashboard", not to "reporting API"

**Approaches**:

1. **Full-session batch extraction (recommended)**: Providing the full conversation context allows the LLM to naturally resolve coreferences. Frontier models handle conversational coreference well when the full transcript is available.

2. **Explicit coreference instruction**:
```
When extracting preferences, resolve all pronouns and references to
their specific antecedents. For example:
- "it" -> identify what "it" refers to in context
- "that feature" -> identify the specific feature
- "the same thing" -> identify the referent

In the about_entity field, always use the FULL entity name, not a
pronoun. If you cannot determine the referent, set confidence lower.
```

3. **Pre-processing step**: Run a coreference resolution model (e.g., spaCy's neuralcoref or a dedicated coref model) before LLM extraction. Replace pronouns with their antecedents. This adds complexity but improves extraction accuracy for per-turn processing where full context is not available.

**Recommendation**: Full-session batch extraction at Stage 2 avoids most coreference issues. For Stage 1 per-turn processing, use the explicit coreference instruction in the extraction prompt. Reserve dedicated coreference resolution pre-processing for high-volume deployments where per-session batch is too expensive.

### 10.3 Merchant Domain Vocabulary

SMB merchant conversations use domain-specific terminology that general-purpose LLMs may misinterpret or fail to recognize as knowledge signals.

**Domain vocabulary categories for merchant support**:

| Domain | Key Terms | Extraction Relevance |
|--------|-----------|---------------------|
| **Payment processing** | chargeback, dispute, refund, settlement, authorization hold, PCI DSS, tokenization, gateway, acquirer, issuer | Preference contexts (e.g., "dispute notification preferences"), Skill signals (understands PCI compliance) |
| **Invoicing** | net-30, net-60, recurring invoice, proforma, credit memo, dunning, AR aging | Workflow preferences (invoice timing), Domain knowledge (accounting familiarity) |
| **Shipping/Fulfillment** | drop shipping, 3PL, tracking number, customs declaration, HS code, incoterm, FOB, DDP | Interest signals (international shipping), Skill signals (logistics expertise) |
| **Tax/Compliance** | nexus, sales tax, VAT, 1099-K, threshold, exemption certificate, resale certificate | Interest signals, Skill signals (compliance knowledge level) |
| **E-commerce platform** | SKU, variant, listing, catalog sync, inventory buffer, oversell protection | Tool preferences, Platform skill level |
| **Analytics** | GMV, AOV, conversion rate, cohort, attribution, funnel, churn | Domain knowledge signals, Report preferences |

**Prompt enhancement for merchant domain**:

```
MERCHANT DOMAIN CONTEXT:
You are extracting knowledge from a conversation between a merchant (small
business owner) and a support agent for a payment/commerce platform.

Domain-specific skill indicators:
- Knowing terms like "chargeback ratio", "authorization rate", "BIN" indicates
  ADVANCED payment processing knowledge
- Asking "what's a chargeback?" indicates NOVICE payment processing knowledge
- Using terms like "net-30 terms" or "dunning schedule" correctly indicates
  ADVANCED invoicing knowledge
- Discussing "nexus" or "exemption certificates" indicates ADVANCED
  tax compliance knowledge

Domain-specific preference contexts:
- "for disputes" -> context="dispute_management"
- "for invoices" -> context="invoicing"
- "for shipping" -> context="fulfillment"
- "for reports" -> context="analytics"
- "for my store" -> context="ecommerce_storefront"
```

### 10.4 Distinguishing Transactional Mentions from Genuine Signals

In merchant support conversations, many entity mentions are transactional (the merchant is asking about something as part of a task) rather than indicating a genuine preference, skill, or interest:

```
Transactional (NOT a preference):
  "How do I process a refund?" -> Merchant is asking for help, not
  expressing a preference about refunds.

Genuine preference signal:
  "I always process refunds as store credit first -- it keeps my
  chargeback rate lower." -> Indicates a workflow preference AND
  domain knowledge about chargeback management.
```

**Distinguishing heuristics**:

1. **Task-oriented questions** ("How do I...?", "Can you help me...?", "Where is...?") are typically transactional unless they reveal a preference about how the task should be done.
2. **Repeated engagement** with a topic across turns or sessions indicates genuine interest (vs. a one-off question).
3. **Evaluative language** ("I like", "I prefer", "it works well", "that's frustrating") signals genuine preference.
4. **Technical depth** in discussion indicates skill, regardless of whether the mention is transactional.

**Extraction prompt guidance**:

```
IMPORTANT: Distinguish between transactional mentions and genuine signals.
- A merchant asking "How do I export to CSV?" is asking for help (transactional)
  -- do NOT extract this as a preference for CSV.
- A merchant saying "I always export to CSV because it's easier to process
  in my accounting software" IS a preference for CSV with context.
- A merchant asking basic questions about a topic indicates NOVICE-level
  knowledge (which IS a skill signal).
- Only extract an interest signal when the topic is discussed with engagement
  beyond task completion (follow-up questions, depth, return visits).
```

### 10.5 Agent Utterance Handling

In our extraction pipeline, agent utterances (the support agent's responses) provide important context but are NOT sources of user preferences. However, agent utterances can:

1. **Confirm user preferences** -- "So you'd like email notifications for disputes?" followed by "Yes" confirms the preference.
2. **Present options that reveal implicit preferences** -- If the agent offers "A or B?" and the merchant chooses A, that is an `implicit_intentional` preference signal.
3. **Provide context for coreference** -- Agent utterances often name things explicitly that the merchant subsequently references with pronouns.

**Extraction rule**: Extract knowledge only from merchant (user) utterances. Use agent utterances for context and confirmation but never attribute a preference to the user based solely on what the agent said.

```
RULES:
- Extract preferences ONLY from merchant utterances, not agent utterances.
- If an agent says "I've set your notifications to email" and the merchant
  says "Great, thanks" -- this confirms the preference stated earlier, but
  the confirmation source is the merchant's "Great, thanks", not the agent's
  statement.
- If an agent offers options and the merchant selects one, the preference
  source is "implicit_intentional" (the merchant made a deliberate choice).
```

---

## 11. Open Questions and Future Work

1. **Calibration data collection**: How to efficiently collect human-labeled extraction samples for confidence calibration? Consider a human-in-the-loop workflow where a random sample of extractions is reviewed monthly.

2. **Domain adaptation**: The merchant domain has specific vocabulary (disputes, chargebacks, settlements) that general-purpose models may not handle optimally. Fine-tuning a small extraction model on merchant conversation data could improve accuracy.

3. **Multilingual extraction**: Merchants may converse in multiple languages. The extraction pipeline should handle this transparently -- frontier models support multilingual extraction natively, but confidence calibration may need per-language adjustment.

4. **Preference contradiction handling**: When a new extraction contradicts an existing preference, the pipeline must decide whether to supersede the old preference or treat the new signal as noise. The `superseded_by` chain in ADR-0012 provides the mechanism, but the decision logic (when to supersede vs. when to ignore) needs policy definition.

5. **Feedback loops**: Can agent outcomes (did the personalized response succeed?) be used to refine extraction confidence post-hoc? This would close the loop between extraction and personalization quality.

6. **Schema evolution**: When new preference categories or behavioral pattern types emerge from conversations that do not fit existing enums, how should the pipeline handle them? Options: flag for human review, auto-extend with low confidence, or reject.

---

## References

### Ontology-Based Extraction
- [SPIRES/OntoGPT: LLM-based ontological extraction tools](https://github.com/monarch-initiative/ontogpt) (Caufield et al., Bioinformatics 2024)
- [ODKE+: Ontology-Guided Open-Domain Knowledge Extraction](https://machinelearning.apple.com/research/odke) (Apple, 2025)
- [Testing prompt engineering methods for knowledge extraction](https://journals.sagepub.com/doi/10.3233/SW-243719) (Polat, Tiddi & Groth, Semantic Web 2025)

### Knowledge Graph Construction
- [KGGen: Extracting Knowledge Graphs from Plain Text with Language Models](https://arxiv.org/abs/2502.09956) (NeurIPS 2025)
- [LLM-empowered Knowledge Graph Construction: A Survey](https://arxiv.org/abs/2510.20345) (ICAIS 2025)
- [Extract, Define, Canonicalize: An LLM-based Framework for KG Construction](https://arxiv.org/html/2404.03868v1) (2024)

### Structured Output
- [StructEval: Benchmarking LLMs' Capabilities to Generate Structural Outputs](https://arxiv.org/abs/2505.20139) (2025)
- [SLOT: Structuring the Output of Large Language Models](https://aclanthology.org/2025.emnlp-industry.32/) (EMNLP 2025)
- [OpenAI Structured Outputs](https://openai.com/index/introducing-structured-outputs-in-the-api/) (2024)
- [Claude Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) (Anthropic, 2025)
- [Outlines: Structured Outputs via Constrained Decoding](https://github.com/dottxt-ai/outlines)
- [llguidance: Super-fast Structured Outputs](https://github.com/guidance-ai/llguidance)
- [Generating Structured Outputs from Language Models: Benchmark and Studies](https://arxiv.org/html/2501.10868v1) (2025)

### Confidence Scoring
- [Confidence Improves Self-Consistency in LLMs](https://aclanthology.org/2025.findings-acl.1030/) (ACL Findings 2025)
- [Calibrating Verbalized Confidence with Self-Generated Distractors (DINCO)](https://arxiv.org/abs/2509.25532) (2025)
- [Systematic Evaluation of Uncertainty Estimation Methods in LLMs](https://arxiv.org/html/2510.20460v1) (2025)
- [Cleanlab TLM: Real-Time Error Detection for Structured Outputs](https://cleanlab.ai/blog/tlm-structured-outputs-benchmark/) (2025)
- [NAACL: Noise-Aware Verbal Confidence Calibration for LLMs in RAG Systems](https://arxiv.org/html/2601.11004) (2026)

### Hallucination Detection
- [GraphEval: A Knowledge-Graph Based LLM Hallucination Evaluation Framework](https://www.amazon.science/publications/grapheval-a-knowledge-graph-based-llm-hallucination-evaluation-framework) (Amazon Science, 2025)
- [GraphCheck: Knowledge Graph-Powered Fact-Checking](https://arxiv.org/html/2502.16514) (2025)
- [Knowledge Graphs, LLMs, and Hallucinations: An NLP Perspective](https://arxiv.org/html/2411.14258v1) (ScienceDirect, 2024)
- [Hallucination Detection and Mitigation in Large Language Models](https://arxiv.org/pdf/2601.09929) (2026)
- [FACTS Grounding Benchmark](https://deepmind.google/blog/facts-grounding-a-new-benchmark-for-evaluating-the-factuality-of-large-language-models/) (Google DeepMind, 2024)
- [FaithJudge: Benchmarking LLM Faithfulness in RAG](https://arxiv.org/html/2505.04847) (Vectara, 2025)

### Multi-Turn Conversation
- [LLMs Get Lost In Multi-Turn Conversation](https://arxiv.org/abs/2505.06120) (2025)
- [Beyond Single-Turn: A Survey on Multi-Turn Interactions with LLMs](https://arxiv.org/html/2504.04717v1) (2025)
- [A Survey on Recent Advances in LLM-based Multi-turn Dialogue Systems](https://dl.acm.org/doi/pdf/10.1145/3771090) (ACM, 2025)

### Personalization and Preference Extraction
- [PersonalLLM: Benchmark for Personalized LLMs](https://openreview.net/pdf?id=QWunLKbBGF) (ICLR 2025)
- [Do LLMs Recognize Your Latent Preferences? PrefEval Benchmark](https://arxiv.org/html/2510.17132v1) (2025)
- [Extracting Implicit User Preferences in Conversational Recommender Systems Using LLMs](https://www.mdpi.com/2227-7390/13/2/221) (Mathematics, 2025)
- [A Survey of Personalized Large Language Models](https://arxiv.org/html/2502.11528v2) (2025)
- [Towards Personalized Conversational Sales Agents](https://arxiv.org/html/2504.08754) (2025)

### Model Selection and Pricing
- [LLM API Pricing Comparison 2025](https://intuitionlabs.ai/articles/llm-api-pricing-comparison-2025) (IntuitionLabs)
- [2026 LLM Leaderboard](https://klu.ai/llm-leaderboard) (Klu)
- [Complete LLM Pricing Comparison 2026](https://www.cloudidr.com/blog/llm-pricing-comparison-2026) (CloudIDR)
- [Cost-Aware Model Selection for Text Classification](https://arxiv.org/html/2602.06370) (2026)
- [Choosing LLMs for AI Agents: Cost, Latency, Intelligence](https://softcery.com/lab/ai-agent-llm-selection) (Softcery)

### Production Systems
- [Zep/Graphiti: Temporal Knowledge Graph for Agent Memory](https://arxiv.org/abs/2501.13956) (2025)
- [Mem0: Production-Ready AI Agents with Scalable Long-Term Memory](https://arxiv.org/abs/2504.19413) (ECAI 2025)
- [Memoria: Scalable Agentic Memory for Personalized Conversational AI](https://arxiv.org/abs/2512.12686) (2025)
- [KARMA: Multi-Agent LLMs for KG Enrichment](https://openreview.net/pdf?id=k0wyi4cOGy) (2025)
