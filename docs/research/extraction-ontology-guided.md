# Ontology-Guided Extraction and Validation Patterns

**Date**: 2026-02-12
**Author**: researcher-3
**Task**: Research Track 3 -- How to use our ontology schema to guide extraction and validate results
**Status**: Complete

---

## Executive Summary

This document investigates how our ontology (ADR-0011 core types + ADR-0012 cg-user module) can **drive** knowledge extraction from merchant-agent conversations, not merely validate results after the fact. We examine the academic field of Ontology-Based Information Extraction (OBIE), modern schema-as-prompt patterns, validation pipelines, entity resolution during extraction, confidence calibration, incremental ontology evolution, and SHACL-based graph validation.

**Key finding**: Ontology-as-extraction-schema is not merely theoretically appealing -- it demonstrably works with current LLMs, achieving 65-90% semantic accuracy and 80-90% schema compliance when combined with two-stage validation. However, the approach requires careful prompt engineering: raw ontology serialization into prompts is insufficient. The most effective systems (ODKE+, SPIRES, Graphiti) all pre-process ontology definitions into targeted extraction templates with concrete examples, value constraints, and negative examples. Our cg-user ontology with its rich property constraints (9 properties on Preference, enum values, float ranges) is an ideal candidate for this approach.

**Use case reminder**: Our target domain is **conversational agents for SMB merchants** (PayPal-style payment/commerce platform). The extraction pipeline must capture preferences, skills, behavioral patterns, and interests from merchant-agent conversations about payment settings, invoicing, disputes, shipping, analytics, and compliance.

---

## 1. Ontology-Based Information Extraction (OBIE): The Academic Field

### 1.1 Historical Foundation

Ontology-Based Information Extraction (OBIE) emerged as a distinct subfield of information extraction in the mid-2000s. The foundational survey by [Wimalasuriya and Dou (2010)](https://journals.sagepub.com/doi/abs/10.1177/0165551509360123) defined OBIE as "a subfield of IE where ontologies are used by the information extraction process and the output is generally presented through an ontology." Their classification identified a common OBIE architecture:

1. **Input**: Unstructured/semi-structured text + domain ontology
2. **Processing**: NLP pipeline guided by ontology concepts and relations
3. **Output**: Instances conforming to the ontology schema (new individuals, property assertions, relation instances)

Early OBIE systems (SROIE, AeroDAML, CREAM, KIM) relied on hand-crafted extraction rules mapped to ontology classes. The ontology served dual roles: defining the target schema and constraining the extraction search space. For example, if the ontology defined a `Preference` class with a `polarity` property restricted to `{positive, negative, neutral}`, the extraction system would only search for signals matching those three values.

### 1.2 The LLM Paradigm Shift (2023-2026)

The advent of LLMs fundamentally changed OBIE. Instead of hand-crafted rules, the ontology is now **serialized into prompts** that guide LLM-based extraction. This creates a new OBIE paradigm:

- **Classical OBIE**: Ontology -> Extraction Rules -> Rule Engine -> Instances
- **LLM-era OBIE**: Ontology -> Prompt Template -> LLM -> Structured Output -> Validation -> Instances

The [LLM-empowered KG construction survey (ICAIS 2025)](https://arxiv.org/abs/2510.20345) identifies this as the dominant paradigm, analyzing how LLMs reshape the three-layered pipeline of ontology engineering, knowledge extraction, and knowledge fusion. The survey distinguishes:

- **Schema-based paradigms**: Emphasize structure and consistency; use predefined ontologies to constrain extraction (our approach)
- **Schema-free paradigms**: Emphasize flexibility; induce schemas dynamically from data (relevant for ontology evolution, Section 7)

Research in 2024-2025 demonstrates that [injecting ontological axioms into prompts improves response accuracy](https://ceur-ws.org/Vol-4079/paper10.pdf) and reduces hallucinations. Two-stage validation combining LLM-based semantic verification with rule-based audits achieves 65-90% semantic accuracy and 80-90% schema compliance.

### 1.3 Key OBIE Systems Relevant to Our Use Case

| System | Year | Approach | Domain | Relevance to Our System |
|--------|------|----------|--------|------------------------|
| [SPIRES/OntoGPT](https://github.com/monarch-initiative/ontogpt) | 2023-2025 | Schema-as-prompt via LinkML; recursive extraction | Biomedical | Direct model for serializing our PG-Schema into extraction prompts |
| [ODKE+ (Apple)](https://machinelearning.apple.com/research/odke) | 2025 | Ontology snippets per entity type; 5-stage pipeline | Open-domain KG | Production-grade template for our multi-stage enrichment |
| [RELATE](https://arxiv.org/abs/2509.19057) | 2025 | Three-stage ontology-constrained predicate mapping | Biomedical | Model for mapping free-text relations to our edge types |
| [OmEGa](https://www.sciencedirect.com/science/article/abs/pii/S1474034624006529) | 2024 | Task-Centric Ontology for domain-specific extraction | Manufacturing | Demonstrates ontology-guided extraction in structured domain |
| [SPIREX](https://vldb.org/workshops/2024/proceedings/LLM+KG/LLM+KG-12.pdf) | 2024 | Schema-constrained prompts + graph ML validation | RNA biology | Combines extraction with graph-based plausibility checking |
| [AutoSchemaKG](https://arxiv.org/abs/2505.23628) | 2025 | Dynamic schema induction from web corpora | Open-domain | Model for ontology evolution when extraction discovers new types |

### 1.4 Honest Assessment: Does Ontology-as-Extraction-Schema Actually Work?

**Yes, but with caveats.** The evidence from production systems and benchmarks is clear:

**What works well:**
- Defining the **set of target types** (node types and edge types) in the prompt dramatically reduces hallucinated entity types. ODKE+ achieves 98.8% precision by constraining extraction to known predicates.
- Providing **enum constraints** in the prompt (e.g., `polarity must be one of: positive, negative, neutral`) leads to near-perfect enum compliance in structured output mode.
- **Nested schema extraction** (SPIRES pattern) handles our complex types -- a Preference node with 9+ properties can be recursively populated.
- **Value range constraints** (e.g., `strength: float 0.0 to 1.0`) are respected by LLMs in structured output mode ~95% of the time.

**What requires careful handling:**
- **Raw ontology serialization is insufficient.** Dumping OWL axioms or full PG-Schema into a prompt confuses LLMs. The schema must be translated into natural-language-augmented templates with examples.
- **Edge endpoint constraints are hard for LLMs.** Telling an LLM "HAS_PREFERENCE only goes from Entity(type=user) to Preference" is less effective than showing concrete examples.
- **Confidence calibration is not built-in.** LLMs do not natively produce well-calibrated confidence scores. External mechanisms are required (Section 6).
- **Entity resolution requires graph access.** The LLM cannot resolve "USPS" to an existing Entity node without being given the current graph context (Section 4).

**Bottom line for our system:** The ontology-as-extraction-schema approach is well-suited to our use case because:
1. Our ontology is moderately sized (8 node types, 16 edge types) -- small enough to fit in context windows
2. Property constraints are specific and enumerable (enum values, float ranges, required fields)
3. The merchant domain is bounded -- extraction targets are predictable
4. We control both the ontology and the extraction pipeline -- no cross-organization schema alignment needed

---

## 2. Schema-as-Prompt Patterns

### 2.1 The SPIRES Approach (OntoGPT)

[SPIRES (Structured Prompt Interrogation and Recursive Extraction of Semantics)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10924283/) is the foundational schema-as-prompt method, published in Bioinformatics 2024.

**How it works:**

1. Define a schema in [LinkML](https://linkml.io/) (YAML-based ontology language)
2. For each class in the schema, generate a prompt template:
   ```
   GeneratePrompt(Schema, Class, Text) =
     Instructions() +
     AttributeTemplate(Schema, Class, Text) +
     TextIntro() +
     Text +
     Break()
   ```
3. For each attribute, the template writes: `Name(attribute) + ": " + Prompt(attribute)`
4. For nested classes (inlined), recursively call SPIRES on the nested type
5. For non-inlined classes, perform **ontology grounding** -- map extracted strings to known ontology terms

**Key insight for our system:** SPIRES demonstrates that LinkML-style YAML schemas translate effectively into extraction prompts. Our PG-Schema can be similarly serialized.

**Accuracy on benchmarks:**
- BioCreative Chemical-Disease-Relation: F-score 41.16% (zero-shot, no training data)
- Entity grounding accuracy: 97-100% for well-defined ontologies
- Major advantage: zero-shot, no labeled training data required

### 2.2 Zero-Shot vs. Few-Shot Ontology-Guided Extraction

A critical design question: should we provide extraction examples in the prompt (few-shot) or rely on schema definitions alone (zero-shot)?

**Zero-shot** (schema only, no examples):
- SPIRES achieves F-score 41.16% on BioCreative CDR with zero-shot extraction. This is impressive for zero training data, but low for production use.
- [Ontology-aware zero-shot LLM prompting (ACM 2024)](https://dl.acm.org/doi/10.1145/3716554.3716603) demonstrates that even small LLMs perform well when given ontology-structured prompts, especially for enum-constrained fields.
- Works best when: property constraints are tight (enums, ranges), the target schema is simple, or labeled examples are unavailable.
- Fails when: the extraction target is ambiguous (e.g., distinguishing "explicit" vs. "implicit_intentional" source types requires nuanced understanding that examples convey better than definitions).

**Few-shot** (schema + 3-5 examples):
- [Testing prompt engineering methods for KE (SWJ 2025)](https://journals.sagepub.com/doi/10.3233/SW-243719) found that incorporating a task demonstration with three examples selected via a retrieval mechanism significantly enhances performance across models (Mistral 7B, Llama 3, GPT-4).
- The [LLM-empowered KG construction survey (ICAIS 2025)](https://arxiv.org/abs/2510.20345) confirms: few-shot prompting with frontier models achieves accuracy comparable to fully supervised traditional models without requiring labeled training data.
- Works best when: extraction requires nuanced judgment (confidence calibration, source type classification), the domain has conventions not obvious from schema alone, or you need consistent formatting.

**Recommendation for our system:**

| Extraction Target | Approach | Rationale |
|-------------------|----------|-----------|
| Preference properties (category, polarity, scope) | Zero-shot sufficient | Tight enums; schema constraints carry the signal |
| Preference strength/confidence calibration | Few-shot required | Nuanced judgment (e.g., "always" = 0.95 strength) requires examples |
| Source type classification (explicit vs. implicit_intentional) | Few-shot required | The CHI 2025 trichotomy distinction is subtle; examples are essential |
| Skill proficiency estimation | Few-shot required | Mapping conversation fluency to 0.0-1.0 proficiency is subjective |
| Entity type assignment (tool vs. service) | Few-shot recommended | The distinction is domain-specific (see Section 5.1) |
| Behavioral patterns (Stage 3) | Few-shot required | Pattern types like "delegation" vs. "escalation" need concrete examples |

**Practical approach:** Use a **few-shot prompt with dynamically selected examples**. Maintain a curated set of 15-20 extraction examples per node type. For each extraction call, select the 3-5 most relevant examples using embedding similarity between the input text and the example conversation contexts. This balances accuracy (few-shot) with prompt efficiency (not including all examples every time).

### 2.3 Unified Prompt vs. Per-Type Extraction Prompts

Should we use a single unified extraction prompt that extracts all types simultaneously, or separate per-type prompts?

**Unified prompt** (extract Preferences + Skills + Interests in one call):
- Pros: Lower cost (one LLM call vs. N calls); cross-type context (seeing a skill signal may inform confidence on a related preference); simpler orchestration.
- Cons: Larger prompt; cognitive overload for the LLM when schema is complex; harder to tune per-type; failure in one type can affect others.
- Used by: Graphiti (unified entity+relation extraction), Memoria (unified trait extraction).

**Per-type prompts** (separate calls for Preferences, Skills, Interests):
- Pros: Focused attention per type; easier to iterate and debug; per-type few-shot examples; per-type token/cost tracking; failure isolation.
- Cons: Higher cost (multiple LLM calls); potential cross-type inconsistency; orchestration complexity.
- Used by: ODKE+ (generates ontology snippets per entity type), KGGEN (entity extraction first, then relation extraction), ChatIE (decomposed multi-turn extraction).

**Hybrid approach** (recommended for our system):

Following the [AutoRE/KGGEN two-phase pattern](https://arxiv.org/abs/2502.09956):

```
Phase 1: Unified entity + signal extraction (single LLM call)
  Input: Conversation text + known entities
  Output: List of entities mentioned, list of signal types detected
          (e.g., "explicit preference about notifications", "skill signal for API integration")

Phase 2: Per-type detail extraction (per-type LLM calls, parallelizable)
  For each signal detected in Phase 1:
    Input: Original text + signal context + type-specific schema + few-shot examples
    Output: Fully structured node (e.g., complete ExtractedPreference with all 9 properties)
```

This hybrid approach:
- Minimizes redundant processing (Phase 1 identifies what to extract)
- Maximizes accuracy per type (Phase 2 uses focused, type-specific prompts)
- Enables parallelization (Phase 2 calls are independent)
- Naturally maps to our Stage 2 enrichment pipeline

**Cost comparison** (estimated for a typical 500-token merchant conversation):

| Strategy | LLM Calls | Input Tokens | Output Tokens | Relative Cost |
|----------|-----------|-------------|---------------|---------------|
| Unified (all types) | 1 | ~2000 | ~500 | 1.0x |
| Per-type (4 types) | 4 | ~4000 | ~800 | 1.9x |
| Hybrid (1 triage + 2 detail) | 3 | ~3000 | ~600 | 1.4x |

The hybrid approach is ~40% more expensive than unified but provides significantly better per-type accuracy and debuggability.

### 2.4 How to Serialize Our cg-user Ontology as an Extraction Prompt

Here is a concrete example of how the Preference node type from ADR-0012 would be serialized as an extraction prompt schema for a merchant-agent conversation:

#### Approach A: Pydantic Model as Schema (recommended for our stack)

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum

class PreferenceCategory(str, Enum):
    tool = "tool"
    workflow = "workflow"
    communication = "communication"
    domain = "domain"
    environment = "environment"
    style = "style"

class PreferencePolarity(str, Enum):
    positive = "positive"
    negative = "negative"
    neutral = "neutral"

class PreferenceSource(str, Enum):
    explicit = "explicit"
    implicit_intentional = "implicit_intentional"
    implicit_unintentional = "implicit_unintentional"
    inferred = "inferred"

class PreferenceScope(str, Enum):
    global_scope = "global"
    agent = "agent"
    session = "session"

class ExtractedPreference(BaseModel):
    """A user preference extracted from conversation text."""

    category: PreferenceCategory = Field(
        description="The category of preference: 'tool' for tool/feature preferences, "
                    "'workflow' for process preferences, 'communication' for interaction "
                    "style preferences, 'domain' for topic/subject preferences, "
                    "'environment' for setting preferences, 'style' for coding/work style"
    )
    key: str = Field(
        description="A concise key describing the preference, e.g., "
                    "'notification_method', 'payment_view', 'report_format'"
    )
    value_description: str = Field(
        description="What the user prefers or avoids, e.g., "
                    "'email notifications for disputes', 'mobile app over desktop'"
    )
    polarity: PreferencePolarity = Field(
        description="Whether this is a positive preference (user wants this), "
                    "negative (user wants to avoid this), or neutral"
    )
    strength: float = Field(
        ge=0.0, le=1.0,
        description="How strongly the user feels: 0.0 (slight) to 1.0 (absolute). "
                    "Strong language like 'always' or 'never' = 0.9-1.0. "
                    "Mild language like 'usually' or 'prefer' = 0.5-0.7."
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Your confidence in this extraction: "
                    "0.9 if user explicitly stated it, "
                    "0.7 if clearly implied by deliberate behavior, "
                    "0.5 if inferred from patterns, "
                    "0.3 if weakly suggested"
    )
    source: PreferenceSource = Field(
        description="How this preference was identified: "
                    "'explicit' if user directly stated it, "
                    "'implicit_intentional' if user deliberately demonstrated it, "
                    "'implicit_unintentional' if inferred from passive behavior, "
                    "'inferred' if derived from other knowledge"
    )
    context: Optional[str] = Field(
        default=None,
        description="The situational context where this preference applies, "
                    "e.g., 'dispute_management', 'invoice_creation'. "
                    "Omit if the preference is general."
    )
    scope: PreferenceScope = Field(
        default=PreferenceScope.global_scope,
        description="Visibility scope: 'global' applies everywhere, "
                    "'agent' applies only to this agent, "
                    "'session' applies only to this session"
    )
    about_entity: Optional[str] = Field(
        default=None,
        description="The entity this preference concerns, e.g., "
                    "'email', 'USPS', 'CSV format', 'dark mode'. "
                    "Used to create the ABOUT edge."
    )
    about_entity_type: Optional[str] = Field(
        default=None,
        description="Type of the about entity: 'tool', 'service', 'concept', 'resource'"
    )
    source_quote: str = Field(
        description="The exact quote from the conversation that supports this extraction"
    )
```

This Pydantic model directly maps to our ADR-0012 Preference node schema. Using the [Instructor library](https://python.useinstructor.com/) (11k+ GitHub stars, 3M+ monthly downloads), this model can be passed directly to any LLM:

```python
import instructor
from openai import OpenAI

client = instructor.from_openai(OpenAI())

preferences = client.chat.completions.create(
    model="gpt-4o",
    response_model=list[ExtractedPreference],
    messages=[
        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": conversation_text},
    ],
    max_retries=3,  # automatic retry on validation failure
)
```

The Instructor library automatically:
1. Generates a JSON Schema from the Pydantic model
2. Passes it as a structured output constraint to the LLM
3. Validates the response against the Pydantic model
4. Retries with the validation error message if validation fails

#### Approach B: Natural Language Schema Description

For models that perform better with natural language than JSON Schema:

```
Extract user preferences from the following merchant support conversation.

For each preference found, provide:
- category: one of [tool, workflow, communication, domain, environment, style]
- key: short identifier (e.g., "notification_method", "payment_view")
- value_description: what the user prefers or avoids
- polarity: "positive" (wants), "negative" (avoids), or "neutral"
- strength: 0.0-1.0 (how strongly they feel; "always/never"=0.9+, "prefer/usually"=0.5-0.7)
- confidence: 0.9 (explicit statement), 0.7 (deliberate behavior), 0.5 (pattern inference), 0.3 (weak signal)
- source: "explicit" (stated directly), "implicit_intentional" (deliberate action), "implicit_unintentional" (passive behavior), "inferred" (derived)
- context: situational scope if applicable (e.g., "dispute_management"), or null
- scope: "global" (default), "agent", or "session"
- about_entity: the entity this preference concerns (e.g., "email", "USPS")
- about_entity_type: one of [tool, service, concept, resource]
- source_quote: exact quote supporting this extraction

IMPORTANT: Only extract preferences that are clearly supported by the text.
Do NOT hallucinate preferences not present in the conversation.
```

#### Approach C: ODKE+-Style Ontology Snippets

Following Apple's ODKE+ pattern, generate a tailored snippet per node type being extracted:

```
You are extracting structured knowledge from a merchant support conversation.

TARGET TYPE: Preference
DESCRIPTION: A user preference represents something the merchant likes, dislikes, or is neutral about.

REQUIRED PROPERTIES:
- category (enum): tool | workflow | communication | domain | environment | style
- key (string): concise preference identifier
- polarity (enum): positive | negative | neutral
- strength (float 0.0-1.0): intensity of preference
- confidence (float 0.0-1.0): extraction certainty
- source (enum): explicit | implicit_intentional | implicit_unintentional | inferred

OPTIONAL PROPERTIES:
- context (string): situational scope
- scope (enum, default "global"): global | agent | session
- about_entity (string): entity the preference concerns

EXAMPLES:
Input: "I always want email notifications for disputes"
Output: {category: "communication", key: "dispute_notification_method", polarity: "positive",
         strength: 0.95, confidence: 0.9, source: "explicit", context: "dispute_management",
         about_entity: "email notifications", about_entity_type: "concept"}

Input: [Merchant has used the mobile app for 15 of their last 17 sessions]
Output: {category: "environment", key: "preferred_interface", polarity: "positive",
         strength: 0.7, confidence: 0.5, source: "implicit_unintentional",
         about_entity: "mobile app", about_entity_type: "tool"}

CONSTRAINTS:
- Extract ONLY preferences supported by the text
- strength > 0.8 requires strong language ("always", "never", "must")
- confidence should reflect source type (explicit=0.9, implicit_intentional=0.7, implicit_unintentional=0.5, inferred=0.3)
- about_entity should match existing entities where possible (see KNOWN ENTITIES below)
```

### 2.5 Comparison of Schema Serialization Approaches

| Approach | Pros | Cons | Best For |
|----------|------|------|----------|
| **Pydantic + Instructor** | Type-safe; automatic validation and retry; enum enforcement via JSON Schema; integrates with our Python stack | Requires structured output support from LLM; JSON Schema can be verbose | Stage 2 enrichment (batch extraction with validation) |
| **Natural Language** | Works with any LLM; human-readable; easy to modify | No automatic validation; parsing required; enum violations possible | Few-shot examples in prompts; documentation |
| **ODKE+ Snippets** | Focused per-type; includes examples and constraints; balances structure with readability | More prompt engineering needed per type; not automatically generated | Stage 2/3 where different types need different extraction strategies |

**Recommendation for our system:** Use **Pydantic + Instructor** as the primary mechanism for Stage 2 enrichment. The Pydantic models defined for extraction map 1:1 to our ADR-0012 node type schemas, the validation/retry loop handles most extraction errors automatically, and our stack is already Pydantic v2.

### 2.6 Full Extraction Schema for All cg-user Node Types

Beyond Preference, here is how each cg-user node type maps to an extraction schema:

**Skill extraction:**
```python
class ExtractedSkill(BaseModel):
    """A skill or competency area observed for the user."""
    name: str = Field(description="Skill name, e.g., 'Python', 'SQL', 'API integration'")
    category: Literal["programming_language", "tool_proficiency",
                       "domain_knowledge", "workflow_skill"]
    proficiency: float = Field(ge=0.0, le=1.0,
        description="Estimated proficiency: 0.2=novice, 0.5=intermediate, "
                    "0.8=advanced, 0.95=expert. Base on language fluency, "
                    "question complexity, and error recovery in conversation.")
    confidence: float = Field(ge=0.0, le=1.0)
    source: Literal["observed", "declared", "inferred"]
    evidence_quote: str
```

**Interest extraction:**
```python
class ExtractedInterest(BaseModel):
    """A topic or domain the user shows interest in."""
    topic: str = Field(description="The topic of interest, e.g., 'international shipping', 'tax compliance'")
    entity_type: Literal["concept", "tool", "service", "resource"]
    weight: float = Field(ge=0.0, le=1.0,
        description="Interest strength: 0.3=passing mention, 0.6=repeated questions, 0.9=active focus")
    source: Literal["explicit", "implicit", "inferred"]
    evidence_quote: str
```

**Behavioral Pattern extraction (Stage 3):**
```python
class ExtractedBehavioralPattern(BaseModel):
    """A recurring behavioral pattern detected across sessions."""
    pattern_type: Literal["delegation", "escalation", "routine",
                          "avoidance", "exploration", "specialization"]
    description: str = Field(description="Human-readable pattern description")
    confidence: float = Field(ge=0.0, le=1.0)
    involved_agents: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(
        description="List of session IDs or event summaries supporting this pattern")
```

### 2.7 Context-Dependent Multi-Type Extraction

A single utterance can simultaneously reveal multiple extraction targets. For example:

> "I've done a bunch of API integrations for my store. I connected Shopify, our shipping provider, and a couple of payment gateways. I'm pretty comfortable with that stuff."

This single passage contains:
- **Skill signal**: API integration proficiency (advanced level, declared)
- **Interest signal**: E-commerce integrations (implicit)
- **Entity references**: Shopify (service), shipping provider (service), payment gateways (concept)
- **Preference signal** (weak): Comfort with technical work (implicit_unintentional)

The **hybrid Phase 1/Phase 2 approach** (Section 2.3) handles this naturally:

**Phase 1** identifies all signals: `["skill:api_integration", "interest:ecommerce_integrations", "entities:shopify,shipping_provider,payment_gateways"]`

**Phase 2** runs separate type-specific extractions for each signal, allowing focused few-shot examples per type. Crucially, the Phase 2 prompts can **cross-reference signals from the same utterance**: the Skill extraction prompt can note that the same utterance also mentions specific services (Shopify, payment gateways), which helps calibrate proficiency (mentioning multiple specific integrations suggests higher proficiency than a vague claim).

**Deduplication across types**: When multiple type extractors reference the same entity (e.g., "Shopify" appears in both the Skill evidence and the Interest evidence), the entity resolution layer (Section 4) ensures a single Entity node is created with REFERENCES edges from both the Skill and Interest extraction events.

---

## 3. Validation Pipelines

### 3.1 Multi-Layer Validation Architecture

Extracted knowledge must be validated before graph insertion. Following ADR-0011 Section 7's layered enforcement strategy, we propose a four-layer validation pipeline:

```
LLM Extraction
    |
    v
[Layer 1: Schema Validation]     -- Pydantic v2 strict mode
    |
    v
[Layer 2: Ontology Constraint]   -- Application-level rules
    |
    v
[Layer 3: Graph Consistency]     -- Cross-reference with existing graph
    |
    v
[Layer 4: Confidence Gating]     -- Minimum confidence thresholds
    |
    v
Graph Insertion (Neo4j)
```

### 3.2 Layer 1: Schema Validation (Pydantic v2)

This is the first line of defense. When using Pydantic models with the Instructor library, validation happens automatically:

```python
from pydantic import BaseModel, Field, field_validator

class ExtractedPreference(BaseModel):
    # ... fields as defined above ...

    @field_validator('strength')
    @classmethod
    def validate_strength_range(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError(f'strength must be 0.0-1.0, got {v}')
        return round(v, 2)  # normalize to 2 decimal places

    @field_validator('confidence')
    @classmethod
    def validate_confidence_consistency(cls, v, info):
        """Confidence should be consistent with source type."""
        source = info.data.get('source')
        if source == 'explicit' and v < 0.7:
            raise ValueError(
                f'explicit source should have confidence >= 0.7, got {v}')
        if source == 'inferred' and v > 0.5:
            raise ValueError(
                f'inferred source should have confidence <= 0.5, got {v}')
        return round(v, 2)
```

**What Layer 1 catches:**
- Wrong types (string where float expected)
- Invalid enum values (e.g., `polarity: "kind of positive"`)
- Out-of-range values (e.g., `strength: 1.5`)
- Missing required fields
- Cross-field consistency violations

**What Layer 1 misses:**
- Hallucinated extractions (preference not actually in text)
- Wrong entity resolution (linking to wrong graph node)
- Duplicate extractions (same preference extracted twice)

### 3.3 Layer 2: Ontology Constraint Validation

Application-level validation enforcing constraints from ADR-0011/0012 that cannot be expressed in Pydantic alone:

```python
class OntologyConstraintValidator:
    """Validates extracted knowledge against ontology rules."""

    def validate_edge_endpoints(self, edge_type: str, source_node: dict, target_node: dict) -> bool:
        """Enforce PG-Schema endpoint constraints."""
        rules = {
            "HAS_PREFERENCE": lambda s, t: s.get("entity_type") == "user" and t.get("node_type") == "Preference",
            "HAS_SKILL": lambda s, t: s.get("entity_type") == "user" and t.get("node_type") == "Skill",
            "ABOUT": lambda s, t: s.get("node_type") == "Preference" and t.get("node_type") == "Entity",
            "DERIVED_FROM": lambda s, t: s.get("node_type") in {"Preference", "BehavioralPattern", "Skill", "Workflow"} and t.get("node_type") == "Event",
            "INTERESTED_IN": lambda s, t: s.get("entity_type") == "user" and t.get("entity_type") == "concept",
        }
        validator = rules.get(edge_type)
        if validator is None:
            return True  # unknown edge type, pass through
        return validator(source_node, target_node)

    def validate_source_confidence_alignment(self, preference: dict) -> list[str]:
        """Validate that confidence aligns with source type (ADR-0012 Section 5)."""
        warnings = []
        source = preference.get("source")
        confidence = preference.get("confidence", 0)

        expected_ranges = {
            "explicit": (0.7, 1.0),
            "implicit_intentional": (0.5, 0.9),
            "implicit_unintentional": (0.3, 0.7),
            "inferred": (0.1, 0.5),
        }
        low, high = expected_ranges.get(source, (0, 1))
        if not low <= confidence <= high:
            warnings.append(
                f"Confidence {confidence} unusual for source '{source}' "
                f"(expected {low}-{high})")
        return warnings
```

### 3.4 Layer 3: Graph Consistency Validation

Before inserting extracted knowledge, validate against the existing graph state:

- **Duplicate detection**: Check if a semantically equivalent Preference already exists for this user (same category + key + about_entity). If so, update rather than create.
- **Entity existence**: If the extraction references an `about_entity`, verify it exists in the graph or create it.
- **Supersession check**: If a new preference contradicts an existing active preference for the same key, set `superseded_by` on the old preference.
- **Cardinality constraints**: Enforce "one UserProfile per user Entity" (ADR-0012 Section 1.1).

### 3.5 Layer 4: Confidence Gating

Following ADR-0012's retention tier policies:

| Extraction Type | Minimum Confidence for Insertion | Rationale |
|----------------|----------------------------------|-----------|
| Explicit preference (`source=explicit`) | 0.5 | Explicit statements are high-signal; even low-confidence extraction is worth persisting |
| Implicit preference (`source=implicit_*`) | 0.4 | Implicit signals need moderate confidence to justify graph insertion |
| Inferred preference (`source=inferred`) | 0.3 | Inferred preferences below 0.3 are too speculative (ADR-0012 warm tier pruning) |
| Skill assessment | 0.4 | Skills need at least moderate evidence |
| Behavioral pattern | 0.5 | Patterns require higher confidence due to cross-session scope |

Extractions below the confidence threshold are logged but not inserted into the graph. They can be revisited during Stage 3 re-consolidation if additional evidence accumulates.

### 3.6 Latency Analysis by Stage

**Added per reviewer feedback.** The four-layer validation pipeline has different latency characteristics per layer, and not all layers should run on every stage's hot path:

| Layer | Estimated Latency | Stage 1 (Hot Path) | Stage 2 (Batch) | Stage 3 (Background) |
|-------|------------------|-------------------|-----------------|---------------------|
| Layer 1: Pydantic | <1ms | Synchronous | Synchronous | Synchronous |
| Layer 2: Ontology Constraints | 1-5ms | Synchronous | Synchronous | Synchronous |
| Layer 3: Graph Consistency | 10-50ms (Neo4j queries) | **Async only** | Synchronous | Synchronous |
| Layer 4: Confidence Gating | <1ms (priors) or N*LLM_cost (consistency) | Source-type priors only | Source-type priors + optional logprobs | Self-consistency (N=3) |

**Stage 1 validation path** (must complete in <5ms for the event projection hot path):
```
Event -> Layer 1 (Pydantic) -> Layer 2 (Ontology) -> Optimistic Graph Insert
                                                        |
                                                        v (async, within 30s)
                                                   Layer 3 (Graph Consistency: dedup, supersede)
                                                        |
                                                        v (async, on next Stage 2 batch)
                                                   Layer 4 (Confidence adjustment)
```

**Stage 2 validation path** (batch, latency budget: seconds per event):
```
LLM Extraction -> Layer 1 -> Layer 2 -> Layer 3 -> Layer 4 -> Graph Insert
                   (all synchronous, full validation)
```

Layer 3 is the bottleneck because it requires Neo4j queries (duplicate check, entity existence, supersession). On the Stage 1 hot path, this must be deferred to async processing. Optimistic insertion with async reconciliation ensures event ingestion is never blocked.

### 3.7 Handling Validation Failures

When an extraction fails validation, the system must decide: reject, flag for review, or accept with modifications? The strategy depends on which layer caught the failure and the severity.

**Decision matrix:**

| Failure Layer | Failure Type | Action | Rationale |
|---------------|-------------|--------|-----------|
| Layer 1 (Schema) | Wrong type, missing required field | **Retry with Instructor** | Instructor automatically re-prompts the LLM with the validation error; works for structural failures |
| Layer 1 (Schema) | Invalid enum value (e.g., `polarity: "somewhat"`) | **Retry with Instructor** | LLM often self-corrects enum values on retry when shown the valid options |
| Layer 1 (Schema) | Retry exhausted (3 attempts) | **Reject and log** | Structural failures after retry indicate the LLM cannot extract this pattern from this input |
| Layer 2 (Ontology) | Edge endpoint violation | **Reject** | This indicates a fundamental extraction error (wrong relationship type); cannot be auto-fixed |
| Layer 2 (Ontology) | Source-confidence misalignment | **Accept with adjusted confidence** | Override confidence to match source-type expected range; log the adjustment |
| Layer 3 (Graph) | Duplicate preference detected | **Merge** | Update existing preference's `last_confirmed_at`, `observation_count`, `stability` |
| Layer 3 (Graph) | Contradicting preference detected | **Accept and supersede** | Create new preference, set `superseded_by` on old one |
| Layer 3 (Graph) | Entity not found in graph | **Create new entity** | New entities are expected; entity resolution may link it later |
| Layer 4 (Confidence) | Below minimum threshold | **Log to staging table** | Store in a "pending extractions" table for batch review at Stage 3 |

**Retry mechanism with Instructor:**

```python
import instructor
from tenacity import retry, stop_after_attempt

client = instructor.from_openai(OpenAI())

# Instructor automatically retries on Pydantic validation failure
# On each retry, the validation error is injected into the prompt
# so the LLM can see exactly what went wrong
preferences = client.chat.completions.create(
    model="gpt-4o",
    response_model=list[ExtractedPreference],
    messages=[...],
    max_retries=3,  # 3 retries = 4 total attempts
)
```

**Staging table for low-confidence extractions:**

Extractions that pass schema validation but fall below confidence thresholds are stored in a staging table rather than discarded entirely. During Stage 3 re-consolidation, the system:
1. Checks if multiple low-confidence extractions for the same preference key have accumulated
2. If yes, computes aggregate confidence (N independent observations increase confidence)
3. If aggregate confidence exceeds the threshold, promotes to the graph
4. If not, purges after a configurable retention period (default: 14 days)

This prevents loss of weak signals that collectively represent strong evidence.

### 3.8 Partial Extraction and Per-Item Validation

**Added per reviewer feedback.** A critical design principle: validate and accept individual extractions independently, not as a batch. When the LLM extracts 4 preferences from a conversation, 3 may be valid and 1 may be hallucinated. The pipeline must accept the 3 valid ones while rejecting the hallucinated one.

```python
async def validate_extraction_batch(
    extractions: list[ExtractedPreference],
    user_id: str,
    source_event_id: str,
) -> tuple[list[ExtractedPreference], list[dict]]:
    """Validate each extraction independently. Return (accepted, rejected)."""
    accepted = []
    rejected = []

    for extraction in extractions:
        try:
            # Layer 1: Pydantic already validated by Instructor
            # Layer 2: Ontology constraints
            warnings = ontology_validator.validate(extraction)
            if any(w.severity == "error" for w in warnings):
                rejected.append({"extraction": extraction, "reason": "ontology_constraint", "warnings": warnings})
                continue

            # Layer 3: Graph consistency (per-extraction)
            duplicate = await graph_store.find_duplicate_preference(
                user_id=user_id,
                category=extraction.category,
                key=extraction.key,
                about_entity=extraction.about_entity,
            )
            if duplicate:
                # Merge: reinforce existing preference instead of creating duplicate
                await graph_store.reinforce_preference(duplicate.preference_id)
                continue

            # Layer 4: Confidence gating
            if extraction.confidence < CONFIDENCE_THRESHOLDS[extraction.source]:
                rejected.append({"extraction": extraction, "reason": "below_confidence_threshold"})
                continue

            accepted.append(extraction)

        except Exception as e:
            rejected.append({"extraction": extraction, "reason": "unexpected_error", "error": str(e)})

    return accepted, rejected
```

**Semantic plausibility checking**: Beyond schema validation, add heuristic checks for semantically nonsensical extractions:
- `strength > 0.8` requires strong language evidence ("always", "never", "must", "absolutely") -- if the `source_quote` contains only mild language ("sometimes", "might prefer"), flag for review
- `source = "explicit"` requires a direct statement in the `source_quote` -- if the quote contains only behavioral description, downgrade to `implicit_intentional`
- `confidence > 0.8` with `source = "inferred"` is contradictory -- auto-cap inferred confidence at 0.5

**Retry budget exhaustion**: When Instructor's `max_retries=3` is exhausted:
1. Log the failed extraction attempt with the full prompt, response, and validation errors
2. Skip this extraction (do not block the pipeline)
3. Increment a per-session failure counter; if failures exceed 30% of extraction attempts, flag the session for manual review
4. The failed extraction is not retried -- downstream Stage 3 can potentially recover the signal from cross-session analysis

---

## 4. Entity Resolution During Extraction

### 4.1 The Core Challenge

When the LLM extracts a preference like "prefers USPS for shipping," it produces a string "USPS." This string must be resolved to an existing Entity node in the graph (if one exists) or used to create a new Entity node. This is where extraction meets the existing graph.

Entity resolution during extraction is fundamentally different from post-extraction resolution:
- **Post-extraction**: Extract freely, then reconcile with the graph (batch, can be expensive)
- **During extraction**: Provide the LLM with graph context so it can reference existing entities (real-time, requires graph access in the extraction loop)

### 4.2 Our Three-Tier Resolution Strategy (from ADR-0011)

| Tier | Condition | When Used | Method | Confidence |
|------|-----------|-----------|--------|------------|
| **Exact match** | Normalized name + entity_type match | Stage 1 + Stage 2 | Deterministic string normalization: lowercase, strip whitespace, canonicalize aliases | 1.0 |
| **Close match** | Embedding similarity > 0.9 | Stage 2 | Generate embedding for extracted entity name, compare with existing entity embeddings via cosine similarity | 0.9+ |
| **Related match** | Family/version relationship | Stage 3 | LLM-based reasoning: "Are 'PayPal Business' and 'PayPal' related?" | Variable |

### 4.3 Practical Implementation: Injection of Known Entities into Extraction Prompts

The most effective approach for entity resolution during extraction is to inject a list of known entities into the extraction prompt. This follows the [Graphiti/Zep pattern](https://github.com/getzep/graphiti):

```python
async def build_extraction_prompt(session_id: str, user_id: str, conversation_text: str) -> str:
    """Build an extraction prompt with known entities for resolution.

    Uses embedding-based retrieval (not a fixed cutoff) to select the most
    relevant entities for this specific conversation context.
    """

    # Embed the conversation text for similarity retrieval
    conversation_embedding = await embed(conversation_text)

    # Retrieve entities most relevant to this conversation via vector similarity
    # This replaces a naive `LIMIT 100` with semantic ranking
    relevant_entities = await graph_store.get_entities_by_embedding_similarity(
        user_id=user_id,
        query_embedding=conversation_embedding,
        top_k=50,  # semantic top-50 is more targeted than random top-100
    )

    # Also include high-frequency entities regardless of embedding match
    # (common services like "PayPal" may not appear in every conversation embedding)
    frequent_entities = await graph_store.get_most_referenced_entities(
        user_id=user_id, limit=20,
    )

    # Merge and deduplicate, prioritizing semantic matches
    all_entities = {e.entity_id: e for e in frequent_entities}
    all_entities.update({e.entity_id: e for e in relevant_entities})

    # Expand with domain alias dictionary for low-entropy entities
    entity_section = "KNOWN ENTITIES (use these exact names when matching):\n"
    for entity in all_entities.values():
        aliases = DOMAIN_ALIAS_DICT.get(entity.name.lower(), [])
        alias_str = f" (also known as: {', '.join(aliases)})" if aliases else ""
        entity_section += f"- {entity.name} (type={entity.entity_type}, id={entity.entity_id}){alias_str}\n"

    # Also fetch active preferences to avoid duplicates
    active_preferences = await graph_store.get_active_preferences(user_id, limit=30)
    pref_section = "EXISTING PREFERENCES (do not re-extract these unless contradicted):\n"
    for pref in active_preferences:
        pref_section += f"- {pref.key}: {pref.value_description} (confidence={pref.confidence})\n"

    return EXTRACTION_TEMPLATE.format(
        known_entities=entity_section,
        existing_preferences=pref_section,
    )

# Domain alias dictionary for low-entropy entities (common merchant abbreviations)
DOMAIN_ALIAS_DICT = {
    "quickbooks": ["QB", "QBO", "Quickbooks Online"],
    "paypal": ["PP"],
    "usps": ["United States Postal Service", "US Postal Service"],
    "fedex": ["Federal Express", "FedEx Ground", "FedEx Express"],
    "shopify": ["Shopify Plus", "Shopify POS"],
    "stripe": [],
    "csv": ["CSV file", "CSV export", "spreadsheet export"],
    "api": ["REST API", "web API"],
    # ... maintained by domain team, updated as new abbreviations are observed
}
```

This approach:
1. Reduces duplicate entity creation by showing the LLM what entities already exist
2. Prevents re-extraction of known preferences (only extract new or contradicting ones)
3. Enables the LLM to use exact entity names, making exact-match resolution trivial
4. Uses **embedding-based retrieval** (not a fixed cutoff) to select the most relevant entities for each conversation
5. Includes a **domain alias dictionary** for low-entropy entities that embedding similarity handles poorly (e.g., "QB" -> "QuickBooks")

### 4.4 Graphiti's Entropy-Gated Fuzzy Matching

[Graphiti (2025)](https://github.com/getzep/graphiti) introduced an innovative approach to entity deduplication: **entropy-gated fuzzy matching**. The system computes approximate Shannon entropy over characters in normalized entity names. Low-entropy strings (short, repetitive) are unstable for fuzzy matching and are handled differently from high-entropy (long, unique) strings.

For our merchant domain, this is relevant because:
- Low-entropy: "CSV", "PDF", "API" (3-char acronyms, high collision risk)
- High-entropy: "international shipping label generator" (unique, safe for fuzzy matching)

### 4.5 iText2KG's Semantic Aggregation

[iText2KG (WISE 2024)](https://arxiv.org/abs/2409.03284) calculates similarity scores for entity resolution combining three dimensions:

1. **Label similarity**: Cosine similarity between entity name embeddings
2. **Entity type similarity**: Whether both entities share the same type
3. **Description similarity**: Cosine similarity between entity description embeddings

An aggregate score above a calibrated threshold triggers merging. For our system, this maps to:

```python
def compute_entity_similarity(extracted: dict, existing: dict) -> float:
    label_sim = cosine_similarity(embed(extracted["name"]), embed(existing["name"]))
    type_match = 1.0 if extracted["entity_type"] == existing["entity_type"] else 0.0
    desc_sim = cosine_similarity(
        embed(extracted.get("description", "")),
        embed(existing.get("description", ""))
    ) if existing.get("description") else 0.0

    # Weighted aggregate
    return 0.5 * label_sim + 0.3 * type_match + 0.2 * desc_sim
```

### 4.6 Merchant-Domain Entity Resolution Examples

| Extracted Text | Normalization | Resolution | Result |
|---------------|---------------|------------|--------|
| "USPS" | "usps" | Exact match: Entity(name="USPS", type="service") | Merge |
| "United States Postal Service" | "united states postal service" | Close match: embedding similarity 0.95 with "USPS" | SAME_AS edge |
| "PayPal Business app" | "paypal business app" | Close match: 0.92 with "PayPal" | Related match: RELATED_TO edge |
| "that CSV export thing" | "csv export" | Close match: 0.88 with "CSV Export Tool" | Merge (above 0.85 threshold for tool entities) |
| "dark mode" | "dark mode" | No existing entity | Create new Entity(name="dark mode", type="concept") |

---

## 5. Ontology-Guided Entity Linking

### 5.1 Using the Entity Hierarchy for Type Assignment

Our entity hierarchy (ADR-0011 Section 3) provides a two-level type system:

```
prov:Agent
  cg:AgentEntity    (entity_type = "agent")
  cg:UserEntity     (entity_type = "user")
  cg:ServiceEntity  (entity_type = "service")

prov:Entity
  cg:ToolEntity     (entity_type = "tool")
  cg:ResourceEntity (entity_type = "resource")
  cg:ConceptEntity  (entity_type = "concept")
```

When the LLM extracts an entity, it must assign the correct `entity_type`. The ontology hierarchy helps by providing disambiguation rules:

```
ENTITY TYPE ASSIGNMENT RULES:
- "agent": AI agents, LLM-based autonomous agents (e.g., "Claude", "GPT-4", "the support bot")
- "user": Human users (e.g., "the merchant", "John")
- "service": External APIs, platforms, third-party services (e.g., "PayPal", "USPS", "Stripe", "QuickBooks")
  NOTE: Services ACT autonomously (accept requests, produce responses)
- "tool": Instruments used by agents (e.g., "CSV exporter", "invoice generator", "search function")
  NOTE: Tools are USED BY agents, they don't act independently
- "resource": Data sources, documents, artifacts (e.g., "Q4 report", "tax form 1099", "shipping manifest")
- "concept": Abstract ideas, topics, categories (e.g., "international shipping", "tax compliance", "dark mode")
```

**The tool vs. service distinction** is particularly important for merchant conversations:
- "PayPal" is a **service** (it's a platform that acts autonomously)
- "PayPal invoice generator" is a **tool** (it's a feature used by agents/users)
- "PayPal API" could be either -- context determines whether it's treated as a service (external) or tool (integration)

### 5.2 RELATE-Style Predicate Mapping for Edge Types

When the extraction pipeline identifies a relationship between entities, it must map the free-text relation to one of our 16 defined edge types. Following [RELATE's three-stage approach](https://arxiv.org/abs/2509.19057):

**Stage 1: Candidate retrieval** -- Embed the extracted relation text and find the nearest edge type definitions:

```python
EDGE_TYPE_DESCRIPTIONS = {
    "HAS_PREFERENCE": "The user has a preference for or against something",
    "HAS_SKILL": "The user has proficiency in a skill or competency area",
    "INTERESTED_IN": "The user is interested in a topic or domain",
    "ABOUT": "A preference concerns a specific entity",
    "DERIVED_FROM": "Knowledge was derived from a source event",
    "EXHIBITS_PATTERN": "The user exhibits a behavioral pattern",
    # ... etc
}

# Embed all descriptions once, then similarity search for each extracted relation
```

**Stage 2: LLM reranking** -- Given the top-k candidate edge types and the full extraction context, the LLM selects the best match:

```
Given the relationship: "merchant frequently asks about"
Between: Entity(type=user, "merchant_123") and Entity(type=concept, "tax compliance")
Top candidates: INTERESTED_IN, HAS_PREFERENCE, REFERENCES
Select the most appropriate edge type: INTERESTED_IN
```

### 5.3 The ABOUT Edge: Linking Preferences to Entities

The `ABOUT` edge (Preference -> Entity) is critical for making preferences queryable. During extraction, the LLM should identify both the preference and what it's about:

```
Conversation: "I always want email notifications for disputes"

Extracted:
- Preference(key="dispute_notification_method", polarity="positive", about_entity="email notifications")
- Edges:
  - HAS_PREFERENCE: User -> Preference
  - ABOUT: Preference -> Entity("email notifications", type="concept")
  - DERIVED_FROM: Preference -> Source Event
```

This triple-path structure (who/what/why) from ADR-0012 Section 4 is the extraction target.

---

## 6. Confidence Calibration

### 6.1 The Calibration Problem

LLMs do not natively produce well-calibrated confidence scores. When asked "how confident are you?", LLMs tend to overestimate confidence (calibration studies show systematic overconfidence). Our system requires the `confidence` field on Preference, Skill, and BehavioralPattern nodes to be meaningful for downstream decisions (retention tier pruning, conflict resolution, context ranking).

### 6.2 Three Approaches to Confidence

#### Approach 1: Token Log-Probability Aggregation

Use [token logprobs](https://ericjinks.com/blog/2025/logprobs/) from the LLM response to compute field-level confidence:

```python
# With OpenAI API
response = client.chat.completions.create(
    model="gpt-4o",
    logprobs=True,
    top_logprobs=5,
    # ... structured output request
)

# Aggregate logprobs for the "confidence" field tokens
field_logprobs = extract_field_logprobs(response, field_name="strength")
field_confidence = math.exp(sum(field_logprobs) / len(field_logprobs))
```

**Pros**: Most accurate single-signal method; per-field granularity possible.
**Cons**: Not all providers expose logprobs for structured output tokens (OpenAI does for JSON mode; Anthropic does not as of 2025); logprobs for JSON structural tokens (braces, commas) dilute signal.

#### Approach 2: Self-Consistency Sampling

Extract N times (e.g., N=5) with temperature > 0, measure agreement:

```python
extractions = []
for _ in range(N):
    result = extract_preferences(conversation, temperature=0.7)
    extractions.append(result)

# For each unique preference key, count how many extractions found it
for key in all_extracted_keys:
    agreement = count_extractions_with_key(extractions, key) / N
    # agreement = 1.0 means all 5 runs extracted it
    # agreement = 0.2 means only 1 run found it
```

[Confidence-Informed Self-Consistency (CISC, ACL 2025)](https://arxiv.org/abs/2502.06233) demonstrates that weighted voting based on confidence scores reduces required samples by 40%+ while maintaining accuracy. For our extraction use case, self-consistency can determine whether a preference extraction is robust or spurious.

**Pros**: Model-agnostic; works with any LLM; no logprobs needed.
**Cons**: Expensive (N x cost per extraction); increases latency; best for batch Stage 2/3.

#### Approach 3: Cleanlab TLM (Trustworthy Language Model)

[Cleanlab's TLM](https://cleanlab.ai/detect/) provides per-field trustworthiness scores for structured outputs:

> "TLM can assign a trustworthiness score to structured outputs from any LLM, and to each field within a structured output."

TLM reduces incorrect responses: GPT-4o by 27%, Claude 3.5 Sonnet by 20%. Per-field trust scores point reviewers directly to specific fields warranting attention.

**Pros**: Turnkey solution; per-field scores; works with any base LLM.
**Cons**: External dependency; API cost; adds latency.

### 6.3 Recommended Confidence Strategy for Our System

**Updated per reviewer feedback.** We recommend a **phased approach**, starting with source-type priors only for MVP and adding extraction-time signals incrementally.

#### Phase 1: MVP -- Source-Type Priors Only

For initial deployment, use only the source-type priors from ADR-0012 Section 5. This requires no additional infrastructure, works with any LLM (including Claude, which does not expose logprobs), and provides a reasonable baseline:

```python
def compute_mvp_confidence(extraction: ExtractedPreference) -> float:
    """MVP confidence: source-type priors only. No logprobs, no self-consistency."""

    source_priors = {
        "explicit": 0.9,
        "implicit_intentional": 0.7,
        "implicit_unintentional": 0.5,
        "inferred": 0.3,
    }
    base = source_priors.get(extraction.source, 0.5)

    # Use LLM's self-reported confidence only as a downward adjustment
    # (never trust the LLM to increase confidence above the source prior)
    llm_confidence = extraction.confidence * 0.8  # 20% skepticism discount
    return round(min(base, llm_confidence) if llm_confidence < base else base, 2)
```

**Rationale for MVP-first**: Logprob-based approaches are unavailable for Anthropic Claude models. Self-consistency sampling multiplies LLM cost by N (expensive for Stage 2 batch processing). Source-type priors are grounded in the ADR-0012 design and provide a principled starting point.

#### Phase 2: Post-MVP -- Add Extraction-Time Signals

Once production data is available for calibration tuning:

```python
def compute_calibrated_confidence(
    extraction: ExtractedPreference,
    logprob_confidence: float | None,
    consistency_score: float | None,
    # Weights are configurable hyperparameters, NOT hard-coded
    w_logprob: float = 0.3,   # tuned via calibration dataset
    w_consistency: float = 0.4,  # tuned via calibration dataset
) -> float:
    """Post-MVP confidence with extraction-time signals.

    NOTE: w_logprob and w_consistency are HYPERPARAMETERS to be tuned
    on a labeled calibration dataset, not fixed design decisions.
    The default values (0.3, 0.4) are starting points only.
    """
    source_priors = {
        "explicit": 0.9,
        "implicit_intentional": 0.7,
        "implicit_unintentional": 0.5,
        "inferred": 0.3,
    }
    base = source_priors.get(extraction.source, 0.5)

    if logprob_confidence is not None:
        adjusted = (1 - w_logprob) * base + w_logprob * logprob_confidence
    elif consistency_score is not None:
        adjusted = (1 - w_consistency) * base + w_consistency * consistency_score
    else:
        adjusted = min(base, extraction.confidence * 0.8)

    return round(max(0.0, min(1.0, adjusted)), 2)
```

**Important**: The blending weights (`w_logprob`, `w_consistency`) are **hyperparameters to be tuned**, not hard-coded design decisions. They should be optimized on a calibration dataset via grid search or Bayesian optimization. The values 0.3 and 0.4 are starting points only, with no empirical basis until production data is available.

**Model-specific considerations**: Logprob availability varies by provider:
- **OpenAI (GPT-4o)**: Logprobs available for structured output tokens, including JSON mode
- **Anthropic (Claude)**: Logprobs NOT available as of early 2026; use self-consistency or source-type priors only
- **Google (Gemini)**: Logprobs available via Vertex AI API
- **Open-source (Llama, Mistral)**: Logprobs always available locally

**Key insight**: The source type is the strongest prior for confidence. An explicit statement ("I always want email notifications") should start at 0.9 confidence regardless of extraction signals. The extraction-time signals (logprobs, consistency) serve as **adjustments**, not replacements.

### 6.4 Calibration Over Time

Confidence calibration should be treated as a continuous process:

1. **Initial deployment (MVP)**: Use source-type priors only (see Phase 1 above)
2. **After 1000 extractions**: Build a calibration dataset:
   - Sample 200 extractions across confidence buckets (50 per quartile)
   - Have a domain expert (merchant support team member) label each as correct/incorrect
   - Compute actual precision per confidence bucket
   - Track inter-annotator agreement (2 reviewers per sample, Cohen's kappa target > 0.7)
3. **After calibration dataset**: Apply isotonic regression or Platt scaling to map raw confidence scores to calibrated probabilities
4. **Ongoing**: Weekly audit of ~100 randomly sampled extractions (following ODKE+'s practice of regular human audits), updating the calibration model monthly

**Ground truth labeling methodology**: The calibration dataset requires human labels. For our merchant domain:
- **Labelers**: Merchant support team members who understand the domain vocabulary
- **Task**: Given the source conversation text and the extracted preference/skill/interest, label as "correct extraction", "partially correct" (right concept, wrong property value), or "incorrect" (hallucinated or misinterpreted)
- **Quality control**: Two independent labels per extraction; disagreements resolved by a third reviewer
- **Cost**: ~200 labeled samples for initial calibration, ~100 per month for ongoing monitoring

---

## 7. Incremental Ontology Evolution

### 7.1 The Evolution Problem

What happens when extraction consistently produces knowledge that does not fit the current ontology? For example:

- Merchants consistently express preferences about **pricing strategies** (not covered by current preference categories)
- A new behavioral pattern emerges: **seasonal_adjustment** (merchants who change settings seasonally)
- An entity type gap: **regulatory_body** ("IRS", "FDA", "FTC") does not fit neatly into `service` or `concept`

### 7.2 Detection Mechanisms

#### Extraction Rejection Monitoring

Track extractions that fail validation or require forced categorization:

```python
class OntologyGapDetector:
    def __init__(self):
        self.rejection_log = []
        self.forced_categorization_log = []

    def log_rejection(self, extraction: dict, reason: str):
        self.rejection_log.append({"extraction": extraction, "reason": reason, "timestamp": now()})

    def log_forced_categorization(self, extraction: dict, intended_value: str, forced_to: str):
        """When LLM wanted a value outside the enum but we forced it to nearest match."""
        self.forced_categorization_log.append({
            "extraction": extraction,
            "intended": intended_value,
            "forced_to": forced_to,
            "timestamp": now()
        })

    def detect_gaps(self, min_occurrences: int = 10, window_days: int = 30) -> list[dict]:
        """Identify repeated ontology gaps that suggest schema evolution."""
        # Cluster rejections by reason
        # If same reason appears > min_occurrences in window, flag for review
        ...
```

#### AutoSchemaKG-Inspired Dynamic Schema Detection

[AutoSchemaKG (2025)](https://arxiv.org/abs/2505.23628) simultaneously extracts knowledge triples and induces schemas from text. While our system uses a predefined ontology, we can borrow the **schema gap detection** mechanism:

1. Run unconstrained extraction alongside constrained extraction (10% sample)
2. Compare unconstrained output types against our ontology
3. Types that appear repeatedly in unconstrained output but not in our ontology are candidate extensions

### 7.3 Ontology Extension Workflow

When a gap is detected:

```
1. Gap Detection (automated)
   -> "Preference category 'pricing' appeared 47 times in 30 days, forced to 'domain'"

2. Proposal Generation (LLM-assisted)
   -> Generate an ADR amendment: "Add 'pricing' to PreferenceCategory enum"
   -> Include: examples, frequency data, impact on existing data

3. Human Review (manual)
   -> Domain expert reviews proposal
   -> Approves, modifies, or rejects

4. Schema Update (controlled)
   -> Update Pydantic models
   -> Update extraction prompts
   -> Run migration on existing data if needed
   -> No graph migration needed (Neo4j is derived; re-project with new rules)
```

**Critical principle**: Ontology evolution is a **human-in-the-loop** process. Automated detection proposes; humans decide. This prevents semantic drift where the schema silently expands beyond its intended scope.

**Adaptive gap detection thresholds**: Rather than fixed thresholds (`min_occurrences=10, window_days=30`), use frequency-weighted alerting:
- **Critical gaps** (> 5 occurrences in 3 days): Immediate notification -- a rapidly emerging pattern may indicate a new product feature or regulatory change
- **Moderate gaps** (> 10 occurrences in 14 days): Weekly review batch
- **Low-priority gaps** (> 20 occurrences in 30 days): Monthly review batch

**Automated ontology alignment for candidate types**: Before escalating to human review, the system should attempt automated alignment:
```python
async def propose_alignment(candidate_type: str, existing_types: list[str]) -> dict:
    """Check if a candidate type is a subtype of an existing type."""
    candidate_embedding = await embed(candidate_type)
    similarities = {
        t: cosine_similarity(candidate_embedding, await embed(t))
        for t in existing_types
    }
    best_match = max(similarities, key=similarities.get)
    best_score = similarities[best_match]

    if best_score > 0.85:
        return {"action": "map_to_existing", "target": best_match, "confidence": best_score}
    elif best_score > 0.6:
        return {"action": "propose_subtype", "parent": best_match, "confidence": best_score}
    else:
        return {"action": "propose_new_type", "confidence": 1 - best_score}
```

### 7.4 API Backward Compatibility for Schema Changes

**Added per reviewer feedback.** Adding new enum values (e.g., "pricing" to `PreferenceCategory`) is an API-breaking change if existing clients do not handle unknown values gracefully. The ontology evolution workflow must include backward compatibility planning:

**Strategy: Additive-only enum evolution with "unknown" tolerance**

1. **API contract**: Document that enum fields may gain new values in minor versions. Clients MUST treat unknown enum values as valid (log a warning, do not reject).
2. **Versioned schemas**: Extraction Pydantic models carry a `schema_version` field. When a new enum value is added:
   - Increment `schema_version` from `1.0` to `1.1`
   - Old extraction prompts continue to work (the new value simply does not appear in their enum list)
   - New extraction prompts include the new value
   - API responses include `schema_version` in metadata
3. **Deprecation, not removal**: Existing enum values are never removed. If a value becomes obsolete, it is deprecated (extraction prompts stop producing it) but validation still accepts it for historical data.
4. **Graph migration**: Neo4j is a derived projection (ADR-0003). Adding a new enum value requires no graph migration -- the next re-projection with updated rules naturally produces the new values. Existing nodes with old values remain valid.

```python
# Example: PreferenceCategory evolution
class PreferenceCategory(str, Enum):
    tool = "tool"
    workflow = "workflow"
    communication = "communication"
    domain = "domain"
    environment = "environment"
    style = "style"
    pricing = "pricing"        # Added in schema_version 1.1
    # compliance = "compliance"  # Proposed for schema_version 1.2, pending review

# API response validation allows unknown values for forward compatibility
class PreferenceResponse(BaseModel):
    category: str  # NOT PreferenceCategory enum -- accepts any string
    # Validation logs a warning for unknown values but does not reject
```

### 7.4 Handling the Schema-Free Paradigm

[Recent research on schema-adaptable KG construction](https://www.emergentmind.com/topics/schema-adaptable-knowledge-graph-construction) shows three trends:

1. Static schemas -> dynamic induction
2. Pipeline modularity -> generative unification
3. Symbolic rigidity -> semantic adaptability

For our system, we adopt a **schema-primary with evolution hooks** approach:
- The predefined ontology (ADR-0011/0012) is authoritative and constrains all extraction
- Evolution is incremental and controlled (not automatic schema induction)
- The "semantic adaptability" comes from the LLM's ability to map novel concepts to existing types, with gap detection for cases where mapping fails

---

## 8. SHACL and Graph Validation

### 8.1 SHACL Overview

[SHACL (Shapes Constraint Language)](https://www.w3.org/TR/shacl/) is a W3C standard for validating RDF graphs against a set of conditions (shapes). While our system uses Neo4j property graphs (not RDF), SHACL is relevant because:

1. [Neosemantics (n10s)](https://neo4j.com/labs/neosemantics/) enables SHACL validation on Neo4j graphs
2. SHACL can express constraints that Neo4j's native constraint system cannot (edge endpoint types, value ranges, pattern matching, closed shapes)
3. ADR-0011 Section 7 explicitly defers SHACL to a future phase

### 8.2 SHACL Shapes for Our Ontology

Here is how our cg-user ontology constraints would be expressed as SHACL shapes:

```turtle
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix cg: <http://context-graph.io/ontology/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# Preference node shape
cg:PreferenceShape a sh:NodeShape ;
    sh:targetClass cg:Preference ;

    # Required properties
    sh:property [
        sh:path cg:preference_id ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
    ] ;
    sh:property [
        sh:path cg:category ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
        sh:in ("tool" "workflow" "communication" "domain" "environment" "style") ;
    ] ;
    sh:property [
        sh:path cg:polarity ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
        sh:in ("positive" "negative" "neutral") ;
    ] ;
    sh:property [
        sh:path cg:strength ;
        sh:datatype xsd:float ;
        sh:minCount 1 ;
        sh:minInclusive 0.0 ;
        sh:maxInclusive 1.0 ;
    ] ;
    sh:property [
        sh:path cg:confidence ;
        sh:datatype xsd:float ;
        sh:minCount 1 ;
        sh:minInclusive 0.0 ;
        sh:maxInclusive 1.0 ;
    ] ;
    sh:property [
        sh:path cg:source ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
        sh:in ("explicit" "implicit_intentional" "implicit_unintentional" "inferred") ;
    ] ;
    sh:property [
        sh:path cg:scope ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
        sh:in ("global" "agent" "session") ;
    ] .

# Edge endpoint constraint: HAS_PREFERENCE
cg:HasPreferenceShape a sh:NodeShape ;
    sh:targetClass cg:Entity ;
    sh:property [
        sh:path cg:HAS_PREFERENCE ;
        sh:class cg:Preference ;
        sh:message "HAS_PREFERENCE must target a Preference node" ;
    ] ;
    # Constraint: only user entities can have preferences
    sh:sparql [
        sh:select """
            SELECT $this
            WHERE {
                $this cg:HAS_PREFERENCE ?pref .
                FILTER NOT EXISTS { $this cg:entity_type "user" }
            }
        """ ;
        sh:message "Only Entity(type=user) can have HAS_PREFERENCE edges" ;
    ] .
```

### 8.3 SHACL vs. Application-Level Validation

| Concern | Application Code (Current) | SHACL (Future) | Winner |
|---------|--------------------------|----------------|--------|
| Property existence (NOT NULL) | Pydantic validators | `sh:minCount 1` | Tie |
| Enum values | Pydantic Literal/Enum | `sh:in (...)` | Tie |
| Value ranges (0.0-1.0) | Pydantic `ge`/`le` | `sh:minInclusive` / `sh:maxInclusive` | Tie |
| Edge endpoint types | Custom validator code | `sh:class`, SPARQL constraints | SHACL (declarative, auditable) |
| Cross-property constraints | Custom `@field_validator` | `sh:sparql` | Application code (more flexible) |
| Machine-readable reports | Custom logging | SHACL validation reports (standardized) | SHACL (standard format) |
| Runtime performance | Fast (in-process) | Slower (n10s plugin, RDF translation) | Application code |
| Development effort | Code per constraint | Turtle per constraint | Similar |

### 8.4 n10s Limitations and Practical Concerns

**Added per reviewer feedback.** While SHACL via neosemantics (n10s) is the most viable path for Neo4j graph validation, several significant limitations should be noted:

1. **Edge property reification**: Neo4j natively supports properties on relationships (e.g., `HAS_SKILL` has `proficiency`, `confidence`, `source` properties). RDF does not support edge properties directly. n10s must **reify** these as intermediate RDF nodes, which:
   - Increases graph complexity during validation
   - May cause shape definitions to not match the intuitive graph structure
   - Makes writing SHACL shapes for edge-property validation non-trivial

2. **Limited `sh:sparql` support**: n10s provides a SPARQL-like interface, but it is not a full SPARQL endpoint. Complex `sh:sparql` constraints (like the HAS_PREFERENCE endpoint type check in Section 8.2) may not execute correctly in all n10s versions. The `sh:sparql` constraint in the example above should be tested against the specific n10s version before relying on it.

3. **Version compatibility**: n10s releases are tied to Neo4j versions. Upgrading Neo4j may require waiting for a compatible n10s release. Some community-reported issues (e.g., [GitHub issue #232](https://github.com/neo4j-labs/neosemantics/issues/232)) indicate SHACL validation regressions between versions.

4. **Performance overhead**: SHACL validation via n10s requires translating Neo4j property graph data to RDF representation in-memory. For large graphs (millions of nodes), this translation is the bottleneck, not the validation itself.

**Bottom line**: n10s SHACL validation is viable for periodic batch audits on subsets of the graph but should NOT be treated as a runtime validation mechanism. For our system, Pydantic + application-level validation remains the production path; SHACL serves as a compliance auditing layer.

### 8.5 Recommendation

**For MVP**: Continue with Pydantic v2 + application-level validation as specified in ADR-0011. This is faster, integrates with our Python stack, and handles all our current constraints.

**For production audit/compliance**: Add SHACL validation as a periodic batch process (not on the hot path). Run SHACL shapes against a representative sample of the Neo4j graph weekly to produce machine-readable validation reports. This aligns with ADR-0011's deferred SHACL adoption strategy.

**Specific SHACL value-add**: The main advantage of SHACL over application code is **auditability**. SHACL shapes are declarative, machine-readable constraint definitions that can be versioned, shared, and validated independently. For a system processing user personal data (GDPR scope), having a formal, auditable constraint definition is valuable for compliance reporting.

### 8.6 SHACL Validation Under Graph Updates

Recent research on [SHACL validation under graph updates (2025)](https://arxiv.org/abs/2508.00137) addresses the question of whether a graph will remain valid after applying an update sequence. **Important caveat (per reviewer feedback)**: This paper addresses incremental RDF validation, not Neo4j property graph validation. Applying its delta-validation approach to Neo4j via n10s would require significant engineering to translate Neo4j graph deltas into RDF representation before running incremental SHACL validation. This is a research direction, not a near-term implementation option.

For practical delta validation on our system, the application-level validation in the projection worker (which already validates each batch of new/modified nodes) is the more effective approach.

---

## 9. Non-LLM Extraction Approaches

**Added per reviewer feedback.** The preceding sections focus on LLM-based extraction. A production system should be hybrid, using LLMs for complex semantic extraction but cheaper alternatives where appropriate. This section covers non-LLM methods and where they fit in our pipeline.

### 9.1 Rule-Based Extraction (Stage 1)

For the Stage 1 hot path, LLM calls are too slow and expensive. Rule-based extractors handle structured signals:

```python
# Rule-based extraction for explicit preference events
EXPLICIT_PREFERENCE_PATTERNS = [
    # "I always want X" / "I never want X"
    (r"I\s+(always|never)\s+want\s+(.+)", lambda m: {
        "polarity": "positive" if m.group(1) == "always" else "negative",
        "strength": 0.95,
        "source": "explicit",
    }),
    # "I prefer X over Y"
    (r"I\s+prefer\s+(.+?)\s+over\s+(.+)", lambda m: {
        "polarity": "positive",
        "strength": 0.7,
        "source": "explicit",
    }),
    # "Please use X" / "Don't use X"
    (r"(please|don't)\s+use\s+(.+)", lambda m: {
        "polarity": "positive" if m.group(1) == "please" else "negative",
        "strength": 0.6,
        "source": "explicit",
    }),
]
```

**When to use**: Stage 1 for `user.preference.stated` events where the event payload already contains structured preference data. Also for entity mention detection in event payloads (fast NER for creating REFERENCES edges).

**When NOT to use**: Implicit preferences, skill assessment, behavioral patterns -- these require semantic understanding that rules cannot provide.

### 9.2 Statistical/Frequency-Based Extraction (Stage 2/3)

For implicit preferences inferred from behavioral data (not conversation text), frequency analysis is more appropriate than LLM extraction:

```python
async def extract_tool_preferences_from_usage(
    user_id: str, window_days: int = 30
) -> list[ExtractedPreference]:
    """Extract implicit tool preferences from usage frequency.
    No LLM required -- pure statistical analysis."""

    tool_usage = await graph_store.get_tool_usage_frequency(
        user_id=user_id, window_days=window_days
    )

    preferences = []
    for tool_name, usage_count, success_rate in tool_usage:
        if usage_count >= 3 and success_rate > 0.7:
            preferences.append(ExtractedPreference(
                category="tool",
                key=f"tool_usage_{normalize(tool_name)}",
                value_description=f"frequently uses {tool_name}",
                polarity="positive",
                strength=min(0.9, 0.3 + (usage_count / 20)),  # scales with frequency
                confidence=0.5,  # implicit_unintentional
                source="implicit_unintentional",
                about_entity=tool_name,
                about_entity_type="tool",
                source_quote=f"Used {usage_count} times in {window_days} days (success rate: {success_rate:.0%})",
            ))
    return preferences
```

**When to use**: Stage 2 for tool usage frequency, session device patterns (mobile vs. desktop), time-of-day patterns. Stage 3 for cross-session behavioral pattern detection.

### 9.3 Graph-Structural Methods (Stage 3)

For Stage 3 re-consolidation, graph structure itself can reveal patterns without additional LLM calls:

- **KG embedding methods** (TransE, RotatE): Train embeddings on the existing user subgraph. Missing edges (e.g., predicted INTERESTED_IN links) can be inferred from embedding proximity without LLM calls. Useful for interest propagation along the concept hierarchy.
- **Graph pattern matching**: Detect recurring subgraph patterns (e.g., `User -> tool.execute -> Entity(type=tool) -> FOLLOWED_BY -> tool.execute -> same Entity`) to identify routine behavioral patterns without LLM interpretation.
- **Link prediction for entity resolution**: GNN-based link prediction (R-GCN, CompGCN) can predict SAME_AS edges between entities based on graph neighborhood structure, complementing embedding similarity for close-match entity resolution.

**When to use**: Stage 3 where cross-session graph structure is available and inference costs must be controlled. Graph-structural methods are especially useful for INTERESTED_IN edge inference (propagating interest along concept hierarchies) and SAME_AS prediction.

### 9.4 Recommended Hybrid Pipeline

| Extraction Task | Method | Stage | Rationale |
|----------------|--------|-------|-----------|
| Explicit preference parsing | Rule-based (regex + structured event parsing) | Stage 1 | Fast, deterministic, no LLM cost |
| Entity mention detection | NER (spaCy or similar) + exact-match resolution | Stage 1 | Sub-millisecond, high precision for known entities |
| Implicit preference from conversation text | LLM-based (Pydantic + Instructor) | Stage 2 | Requires semantic understanding |
| Skill assessment from conversation text | LLM-based (Pydantic + Instructor) | Stage 2 | Requires nuanced proficiency judgment |
| Tool preference from usage frequency | Statistical (frequency analysis) | Stage 2 | No semantic understanding needed, cheaper |
| Interest inference from concept co-occurrence | Statistical + KG embeddings | Stage 3 | Graph-structural, no LLM needed |
| Behavioral pattern detection | LLM (for description) + graph pattern matching (for detection) | Stage 3 | Pattern detection is structural; LLM generates human-readable description |
| Cross-session entity resolution | Embedding similarity + optional LLM reasoning | Stage 3 | Embedding handles most cases; LLM for ambiguous ones only |

This hybrid approach reduces LLM dependency by ~40-60% compared to an all-LLM pipeline, with the largest savings at Stages 1 and 3.

---

## 10. End-to-End Extraction Example

### 9.1 Merchant Conversation Input

```
Agent: Welcome back! How can I help you today?

Merchant: Hey, I need to change my dispute notification settings.
I always want email notifications for disputes, not those in-app
popups. They're easy to miss.

Agent: Got it! I'll update your notification preferences for disputes
to email only. Anything else?

Merchant: Yeah, actually. Can you also set up automatic invoice
reminders? I've been using QuickBooks for my bookkeeping and I'd
love if the invoices could sync there automatically.

Agent: I can enable automatic invoice reminders for you. For the
QuickBooks integration, I'll need to set up the API connection.
Have you worked with API integrations before?

Merchant: Oh yeah, I've done a bunch of API integrations for my store.
I connected Shopify, our shipping provider, and a couple of payment
gateways. I'm pretty comfortable with that stuff.
```

### 9.2 Extraction Output (Stage 2 Enrichment)

```json
{
  "preferences": [
    {
      "category": "communication",
      "key": "dispute_notification_method",
      "value_description": "email notifications for disputes instead of in-app popups",
      "polarity": "positive",
      "strength": 0.95,
      "confidence": 0.9,
      "source": "explicit",
      "context": "dispute_management",
      "scope": "global",
      "about_entity": "email notifications",
      "about_entity_type": "concept",
      "source_quote": "I always want email notifications for disputes, not those in-app popups"
    },
    {
      "category": "communication",
      "key": "in_app_popups",
      "value_description": "dislikes in-app popup notifications",
      "polarity": "negative",
      "strength": 0.8,
      "confidence": 0.85,
      "source": "explicit",
      "context": "dispute_management",
      "scope": "global",
      "about_entity": "in-app popups",
      "about_entity_type": "concept",
      "source_quote": "not those in-app popups. They're easy to miss."
    },
    {
      "category": "tool",
      "key": "bookkeeping_tool",
      "value_description": "uses and prefers QuickBooks for bookkeeping",
      "polarity": "positive",
      "strength": 0.7,
      "confidence": 0.8,
      "source": "explicit",
      "context": null,
      "scope": "global",
      "about_entity": "QuickBooks",
      "about_entity_type": "service",
      "source_quote": "I've been using QuickBooks for my bookkeeping"
    },
    {
      "category": "workflow",
      "key": "invoice_sync_automation",
      "value_description": "wants automatic invoice syncing with QuickBooks",
      "polarity": "positive",
      "strength": 0.75,
      "confidence": 0.85,
      "source": "explicit",
      "context": "invoicing",
      "scope": "global",
      "about_entity": "QuickBooks invoice sync",
      "about_entity_type": "tool",
      "source_quote": "I'd love if the invoices could sync there automatically"
    }
  ],
  "skills": [
    {
      "name": "API integration",
      "category": "tool_proficiency",
      "proficiency": 0.8,
      "confidence": 0.75,
      "source": "declared",
      "evidence_quote": "I've done a bunch of API integrations for my store. I connected Shopify, our shipping provider, and a couple of payment gateways. I'm pretty comfortable with that stuff."
    }
  ],
  "interests": [
    {
      "topic": "workflow automation",
      "entity_type": "concept",
      "weight": 0.6,
      "source": "implicit",
      "evidence_quote": "Can you also set up automatic invoice reminders?"
    }
  ],
  "entities_referenced": [
    {"name": "QuickBooks", "type": "service"},
    {"name": "Shopify", "type": "service"},
    {"name": "email notifications", "type": "concept"},
    {"name": "in-app popups", "type": "concept"},
    {"name": "API integration", "type": "concept"}
  ]
}
```

### 9.3 Graph Operations Generated

After validation, the following graph operations would be executed:

```cypher
// 1. Resolve or create entities
MERGE (quickbooks:Entity {name: "QuickBooks", entity_type: "service"})
  ON CREATE SET quickbooks.entity_id = $qb_id, quickbooks.first_seen = datetime(),
                quickbooks.last_seen = datetime(), quickbooks.mention_count = 1
  ON MATCH SET quickbooks.last_seen = datetime(),
               quickbooks.mention_count = quickbooks.mention_count + 1

// 2. Create preference nodes with DERIVED_FROM provenance
CREATE (p1:Preference {
  preference_id: $pref_id_1,
  category: "communication",
  key: "dispute_notification_method",
  polarity: "positive",
  strength: 0.95,
  confidence: 0.9,
  source: "explicit",
  context: "dispute_management",
  scope: "global",
  observation_count: 1,
  first_observed_at: datetime(),
  last_confirmed_at: datetime(),
  stability: 720.0
})

// 3. Create edges: User -> Preference -> Entity, Preference -> Event
MATCH (u:Entity {entity_id: $user_id, entity_type: "user"})
MATCH (email:Entity {name: "email notifications"})
MATCH (event:Event {event_id: $source_event_id})
CREATE (u)-[:HAS_PREFERENCE]->(p1)
CREATE (p1)-[:ABOUT]->(email)
CREATE (p1)-[:DERIVED_FROM {derivation_method: "llm_extraction", derived_at: datetime()}]->(event)
```

---

## 11. Recommendations for Our System

### 11.1 Extraction Architecture Summary

| Stage | Extraction Method | Schema Mechanism | Entity Resolution | Confidence |
|-------|------------------|------------------|-------------------|------------|
| **Stage 1** | Rule-based (explicit events only) | Pydantic validation of event payload | Exact match (deterministic normalization) | Source-type prior |
| **Stage 2** | LLM-based (Pydantic + Instructor) | ODKE+-style ontology snippets per type | Exact + Close match (embedding similarity) | Hybrid (prior + logprobs) |
| **Stage 3** | LLM-based (batch, cross-session) | Full schema for pattern detection | Close + Related match (LLM reasoning) | Self-consistency sampling |

### 11.2 Priority Implementation Order

1. **Pydantic extraction models** for all cg-user node types (maps directly to ADR-0012 schema)
2. **Instructor integration** for automatic structured output + validation + retry
3. **Entity resolution with known-entity injection** into extraction prompts
4. **Confidence calibration** with source-type priors (defer logprobs/consistency to optimization phase)
5. **Ontology gap detection** (monitor forced categorizations and rejections)
6. **SHACL validation** as periodic batch audit (defer to post-MVP)

### 11.3 Key Design Decisions

1. **Schema-first extraction**: Use our ontology (ADR-0011/0012) to drive extraction prompts, not open-ended extraction followed by mapping.
2. **Pydantic as the schema bridge**: Pydantic models serve triple duty: (a) defining the extraction target, (b) validating LLM output, (c) mapping to graph operations.
3. **Known-entity injection**: Include existing entities in extraction prompts to enable resolution during extraction, not just after.
4. **Conservative confidence**: Use source-type priors as the confidence floor; extraction signals can only adjust within bounds.
5. **Human-in-the-loop for ontology evolution**: Detect gaps automatically, propose changes, but require human approval before schema changes.

---

## References

### OBIE and Ontology-Guided Extraction
- [Wimalasuriya & Dou (2010). "Ontology-based information extraction: An introduction and a survey." JIST.](https://journals.sagepub.com/doi/abs/10.1177/0165551509360123)
- [Caufield et al. (2024). "Structured prompt interrogation and recursive extraction of semantics (SPIRES)." Bioinformatics.](https://pmc.ncbi.nlm.nih.gov/articles/PMC10924283/)
- [SPIRES/OntoGPT GitHub Repository](https://github.com/monarch-initiative/ontogpt)
- [LinkML: Linked Data Modeling Language](https://linkml.io/)
- [Khorshidi et al. (2025). "ODKE+: Ontology-Guided Open-Domain Knowledge Extraction with LLMs." Apple ML Research.](https://machinelearning.apple.com/research/odke)
- [RELATE (2025). "Relation Extraction in Biomedical Abstracts with LLMs and Ontology Constraints."](https://arxiv.org/abs/2509.19057)
- [OmEGa (2024). "Ontology-based task-centric KG construction from manufacturing documents." Adv. Eng. Informatics.](https://www.sciencedirect.com/science/article/abs/pii/S1474034624006529)
- [SPIREX (2024). "Schema-constrained prompts + graph ML validation." VLDB LLM+KG Workshop.](https://vldb.org/workshops/2024/proceedings/LLM+KG/LLM+KG-12.pdf)
- [Ceur-WS (2025). "Beyond Statistical Parroting: Hard-Coding Truth into LLMs via Ontologies."](https://ceur-ws.org/Vol-4079/paper10.pdf)

### Schema-as-Prompt and Structured Output
- [Pydantic for LLMs: Schema, Validation & Prompts](https://pydantic.dev/articles/llm-intro)
- [Instructor: Multi-Language Library for Structured LLM Outputs](https://python.useinstructor.com/)
- [StructEval: Benchmarking LLM Structured Outputs (2025)](https://arxiv.org/html/2505.20139v1)
- [SLOT: Structuring LLM Outputs (EMNLP 2025)](https://aclanthology.org/2025.emnlp-industry.32.pdf)

### Entity Resolution
- [Graphiti/Zep: Temporal Knowledge Graph for Agent Memory (2025)](https://arxiv.org/abs/2501.13956)
- [Graphiti GitHub Repository](https://github.com/getzep/graphiti)
- [iText2KG: Incremental KG Construction with Entity Resolution (WISE 2024)](https://arxiv.org/abs/2409.03284)
- [KGGen: Knowledge Graph Generation with Entity Clustering (NeurIPS 2025)](https://arxiv.org/abs/2502.09956)
- [Neo4j: Entity Resolved Knowledge Graphs Tutorial](https://neo4j.com/blog/developer/entity-resolved-knowledge-graphs/)
- [The Rise of Semantic Entity Resolution (2025)](https://towardsdatascience.com/the-rise-of-semantic-entity-resolution/)

### Confidence Calibration
- [Jinks (2025). "Estimating LLM classification confidence with log probabilities."](https://ericjinks.com/blog/2025/logprobs/)
- [Cleanlab TLM: Trustworthy Language Model](https://cleanlab.ai/detect/)
- [Cleanlab TLM Structured Outputs Benchmark](https://cleanlab.ai/blog/tlm-structured-outputs-benchmark/)
- [Confidence Improves Self-Consistency in LLMs (ACL 2025)](https://arxiv.org/abs/2502.06233)
- [VATBox/llm-confidence Python Package](https://github.com/VATBox/llm-confidence)

### Ontology Evolution and Schema Induction
- [AutoSchemaKG: Dynamic Schema Induction from Web-Scale Corpora (2025)](https://arxiv.org/abs/2505.23628)
- [LLM-empowered KG Construction: A Survey (ICAIS 2025)](https://arxiv.org/abs/2510.20345)
- [Schema-Adaptable Knowledge Graph Construction (EmergenTMind)](https://www.emergentmind.com/topics/schema-adaptable-knowledge-graph-construction)
- [Ontology Learning and KG Construction: Comparison of Approaches (2025)](https://arxiv.org/html/2511.05991v1)

### SHACL and Graph Validation
- [W3C SHACL Specification](https://www.w3.org/TR/shacl/)
- [Neosemantics (n10s): Neo4j RDF & Semantics Toolkit](https://neo4j.com/labs/neosemantics/)
- [SHACL Validation under Graph Updates (2025)](https://arxiv.org/abs/2508.00137)
- [Validating Neo4j Graphs against SHACL](https://neo4j.com/labs/neosemantics/4.0/validation/)
- [Learning SHACL Shapes from Knowledge Graphs (SWJ)](https://www.semantic-web-journal.net/system/files/swj3063.pdf)
- [SHACTOR: Validating Shapes for Large-Scale KGs (SIGMOD 2023)](https://dl.acm.org/doi/10.1145/3555041.3589723)

### Production Systems
- [Zep: Temporal Knowledge Graph Architecture for Agent Memory](https://arxiv.org/abs/2501.13956)
- [Mem0: Production-Ready AI Agents with Scalable Long-Term Memory (ECAI 2025)](https://arxiv.org/abs/2504.19413)
- [Memoria: Scalable Agentic Memory for Personalized Conversational AI](https://arxiv.org/abs/2512.12686)

### LLM Extraction Surveys
- [Large Language Models for Generative Information Extraction: A Survey (Frontiers CS 2025)](https://link.springer.com/article/10.1007/s11704-024-40555-y)
- [A Survey on Open Information Extraction from Rule-based to LLM (EMNLP 2024)](https://aclanthology.org/2024.findings-emnlp.560.pdf)
