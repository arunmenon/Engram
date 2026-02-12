# Knowledge Extraction Landscape Analysis

**Date**: 2026-02-12
**Purpose**: Define the extraction problem space and research tracks for building the knowledge extraction pipeline that transforms unstructured conversation text into structured graph nodes conforming to our ontology (ADR-0011, ADR-0012).

---

## 1. Problem Statement

The context-graph system has a well-defined target ontology (ADR-0011 core types + ADR-0012 user personalization types) specifying 8 node types (Event, Entity, Summary, UserProfile, Preference, Skill, Workflow, BehavioralPattern), 16 edge types, and detailed property constraints. The gap is the **extraction pipeline**: how does unstructured conversation text between a user and a conversational AI agent (e.g., a PayPal merchant support agent) get transformed into structured graph nodes conforming to this ontology?

### Use Case: SMB Merchant Conversational Agents

The primary use case is **conversational agents for small and medium business merchants**. These are customer-facing agents that help merchants with tasks like:

- Managing payment settings, invoices, and disputes
- Configuring shipping, inventory, and product listings
- Understanding analytics, reports, and compliance requirements
- Troubleshooting integration issues and account problems

In these conversations, merchants **implicitly and explicitly reveal**:

- **Preferences**: "I always want email notifications for disputes" (explicit), consistently using the mobile app over desktop (implicit)
- **Skills/expertise**: Fluent discussion of API integrations (high technical skill) vs. asking basic questions about CSV exports (low data skill)
- **Behavioral patterns**: Always checking analytics before making pricing changes (routine), escalating quickly when payment issues arise (escalation pattern)
- **Interests**: Frequently asking about international shipping (domain interest), recurring questions about tax compliance (topic interest)

The extraction pipeline must capture these signals from natural language, map them to the correct ontology types, assign appropriate confidence scores, and maintain full provenance back to source events.

### Three-Stage Architecture

Per ADR-0008, extraction maps to the three consolidation stages:

| Stage | Extraction Role | Latency Budget | Input |
|-------|----------------|----------------|-------|
| **Stage 1: Event Projection** | Extract entities mentioned in events, create REFERENCES edges, handle explicit preference statements (`user.preference.stated` events) | Low (< 500ms per event) | Individual events as they arrive |
| **Stage 2: Enrichment** | LLM-based extraction of implicit preferences, skill assessments, interest signals; entity resolution; keyword/embedding generation | Medium (batch, seconds per event) | Accumulated events for a session or user |
| **Stage 3: Re-Consolidation** | Cross-session pattern detection, workflow extraction, preference merging, behavioral pattern identification | High (periodic batch, minutes) | All events for a user across sessions |

The pipeline progressively builds richer user models: Stage 1 captures the explicit and structural, Stage 2 infers the implicit, Stage 3 discovers cross-session patterns.

---

## 2. Technique Categories

Research identifies five major categories of knowledge extraction techniques relevant to our use case:

### 2.1 LLM-Based Extraction (Generative)

The dominant paradigm in 2025-2026. LLMs reframe information extraction as a generative task -- given conversation text and a schema definition, the model generates structured output conforming to the schema.

**Key approaches**:

- **Structured output / JSON mode**: Models like GPT-4o, Claude, and Gemini support constrained JSON output. Pydantic schemas can be passed directly, and the model generates conforming objects. Accuracy varies: GPT-4o achieves ~76% on structured output benchmarks (StructEval 2025), with field-level confidence extractable from token log probabilities.
- **Function calling / tool use**: The model is given function signatures matching ontology types (e.g., `extract_preference(category, key, polarity, strength, source)`) and invokes them against conversation text. This naturally maps to our Pydantic models.
- **Few-shot prompting**: Providing 3-5 examples of conversation-to-extraction mappings significantly improves accuracy. Few-shot prompting with frontier models achieves accuracy comparable to fully supervised traditional models without requiring labeled training data.
- **Multi-step extraction (ChatIE pattern)**: Decompose extraction into sequential LLM calls -- first extract entities, then extract relations, then validate. KGGEN (2025) demonstrates this two-phase approach (entities first, then relations) improves consistency.
- **Batch vs. per-turn extraction**: Per-turn extraction captures real-time signals but is expensive. Batch extraction over session transcripts is more token-efficient and enables cross-utterance reasoning. The optimal strategy depends on latency requirements (Stage 1 vs. Stage 2).

**Confidence scoring**: A critical gap. LLM extractions need confidence signals to populate the `confidence` field on Preference/Skill/BehavioralPattern nodes. Approaches include: token log-probability aggregation per field (Cleanlab TLM), self-consistency sampling (extract N times, measure agreement), and calibrated verbalized confidence ("How confident are you in this extraction? Rate 0-1").

### 2.2 Production Agent Memory Pipelines

Several production systems have solved this extraction problem for conversational agents. Their architectures provide concrete implementation patterns:

- **Zep/Graphiti**: Temporally-aware knowledge graph engine. Extracts entities and "episodic facts" (relationship triples with timestamps) from conversations using LLM prompting. Employs hyper-edges for multi-entity facts. Performs entity deduplication through embedding similarity. Achieves P95 retrieval latency of 300ms via hybrid search (semantic + BM25 + graph traversal) with zero LLM calls at retrieval time. Published benchmarks show F1/J scores exceeding Mem0.
- **Mem0**: Scalable long-term memory with graph-based user modeling. Extracts user preferences and facts from conversations, stores in a knowledge graph. Recent graph memory implementation (January 2026) focuses on entity extraction and relationship mapping. Production-deployed at scale.
- **Memoria**: Hybrid architecture combining session-level summarization with a weighted knowledge graph for user modeling. Incrementally captures user traits, preferences, and behavioral patterns as structured entities/relationships. Achieves 87.1% accuracy on benchmarks with 38.7% latency reduction vs. full-context prompting. Token usage drops from ~115K to ~400 tokens per retrieval.
- **A-MEM**: Zettelkasten-inspired interconnected note network. Organizes knowledge into linked notes with bidirectional evolution tracking. Relevant for our `superseded_by` preference chain pattern.
- **MAGMA**: Multi-graph architecture (semantic, temporal, causal, entity graphs) with policy-guided traversal. The architecture is directly aligned with our ADR-0009 multi-view design. MAGMA's extraction prompts explicitly define extraction targets to ensure graph integrity.
- **Cognee**: Modular extraction pipeline with 30+ data source connectors. Composes custom extraction, enrichment, and retrieval workflows.

### 2.3 Ontology-Guided Extraction (OBIE)

Ontology-Based Information Extraction (OBIE) uses ontology schemas to guide and constrain LLM extraction. This is directly relevant because our ontology (ADR-0011/0012) defines the target schema.

**Key approaches**:

- **Schema-as-prompt (SPIRES/OntoGPT)**: The SPIRES method feeds ontology schemas directly into LLM prompts as extraction templates. Given a schema and input text, it recursively performs prompt interrogation to extract conforming instances. Zero-shot, no training data required. Available as the open-source OntoGPT package.
- **ODKE+ (Apple, 2025)**: Dynamically generates ontology snippets tailored to each entity type, aligning extractions with schema constraints. Supports 195 predicates across open-domain extraction. Employs ontology-guided workflow coupling schema supervision with instance-level corroboration.
- **RELATE (2025)**: Three-stage pipeline for ontology-constrained predicate mapping -- ontology-driven preprocessing, vector search for candidate predicates, LLM reranking for final selection. Converts free-text relations into ontology-aligned edges.
- **OmEGa**: Task-centric ontology-based extraction from documents using LLMs, specifically designed for manufacturing domain.
- **AutoSchemaKG**: Induces schemas from corpora via unsupervised clustering, then uses multi-stage prompts for extraction. Represents the emerging "dynamic schema" paradigm where ontology evolves with data.

### 2.4 Entity Resolution and Graph Integration

Extracted knowledge must be reconciled with existing graph nodes. Entity resolution is critical for preventing node duplication and maintaining graph integrity.

**Key approaches**:

- **Deterministic normalization**: Lowercase, strip whitespace, canonicalize names. Handles exact matches (ADR-0011 Tier 1). Simple, fast, used at Stage 1.
- **Embedding-based similarity**: Generate embeddings for entity names/descriptions, compute cosine similarity. Handles close matches (ADR-0011 Tier 2, threshold > 0.9). Used at Stage 2.
- **LLM-based resolution**: Ask the LLM "Are entity A and entity B the same?" with context. Most accurate but most expensive. Used for ambiguous cases.
- **Semantic aggregation**: iText2KG (2024) calculates similarity scores combining label similarity, entity type similarity, and description similarity, aggregating entities above threshold. Applicable to our three-tier resolution strategy.
- **Temporal deduplication**: Zep/Graphiti's approach -- when the same fact is extracted multiple times, temporal metadata determines which is canonical. Critical for our `superseded_by` preference chains.

### 2.5 Validation and Quality Assurance

Extracted knowledge needs validation before graph insertion to maintain ontology conformance.

**Key approaches**:

- **Schema validation**: Pydantic v2 strict mode for structural conformance (property types, required fields, enum values). Already planned per ADR-0011 Section 7.
- **Ontology constraint checking**: Validate edge endpoint types, value ranges, enum membership. Application-level enforcement per ADR-0011.
- **Cross-reference validation**: Check extracted entities against known entities in the graph. Flag novel entities for review.
- **Confidence thresholds**: Gate graph insertion on minimum confidence. Implicit preferences with confidence < 0.3 should not be persisted (per ADR-0012 warm tier policy).
- **Human-in-the-loop**: Semi-automated pipelines with periodic human review for schema refinement and anomaly correction. Recommended for initial calibration.
- **Competency question testing**: Validate the extraction pipeline against known-answer queries ("Does the system correctly extract that User X prefers Python?").

---

## 3. Mapping to Our Pipeline Stages

| Technique Category | Stage 1 (Event Projection) | Stage 2 (Enrichment) | Stage 3 (Re-Consolidation) |
|---|---|---|---|
| **LLM-Based Extraction** | Minimal -- only for explicit `user.preference.stated` events | Primary -- per-session extraction of implicit preferences, skills, interests | Batch -- cross-session pattern summarization |
| **Production Pipelines** | Zep-style entity extraction from event payloads | Memoria-style weighted KG construction; Mem0-style preference inference | MAGMA-style multi-graph pattern discovery; A-MEM-style evolution tracking |
| **Ontology-Guided** | Schema validation of explicit events | SPIRES-style schema-as-prompt for extraction; ODKE+-style ontology snippet generation | AutoSchemaKG-style schema evolution for new pattern types |
| **Entity Resolution** | Exact match (deterministic normalization) | Close match (embedding similarity > 0.9) | Cross-session entity merging; SAME_AS edge creation |
| **Validation** | Pydantic v2 + Neo4j constraints | Confidence thresholds; cross-reference checks | Competency question testing; human-in-the-loop calibration |

### Critical Design Decisions for Our System

1. **Schema-first extraction**: Our ontology (ADR-0011/0012) provides a well-defined target schema. We should use schema-as-prompt patterns (SPIRES approach) rather than open-ended extraction followed by schema mapping.

2. **Confidence-native design**: Every node type in ADR-0012 carries a `confidence` field. The extraction pipeline must produce calibrated confidence scores from day one, not add them as an afterthought.

3. **Provenance-first extraction**: Every extracted node must have a DERIVED_FROM edge to source events. This is our differentiator over Zep, Mem0, and Memoria, which lack event-level provenance.

4. **Conversation-optimized, not document-optimized**: Most KG construction literature targets documents. Our input is multi-turn conversations between merchants and agents, which have different characteristics (informal language, context-dependent references, preference signals embedded in task-oriented dialogue).

---

## 4. Recommended Research Tracks

Based on the landscape analysis, three parallel research tracks are needed:

### Track 1: LLM-Based Extraction Techniques (researcher-1)

**Focus**: How to use LLMs to extract structured knowledge from merchant-agent conversations.

**Key questions**:
- What prompting strategies work best for extracting preferences, skills, and interests from conversational text?
- How should extraction be structured: single-pass vs. multi-step (entities first, then relations)?
- How to generate calibrated confidence scores for extractions?
- What are the trade-offs between per-turn extraction (Stage 1/2) vs. batch session extraction (Stage 2/3)?
- Which models offer the best accuracy/cost/latency trade-offs for extraction at scale?
- How does structured output (JSON mode, function calling) compare to free-form extraction + parsing?

**Systems/papers to investigate**: StructEval benchmarks, Cleanlab TLM confidence scoring, ChatIE multi-turn extraction, KGGEN two-phase extraction, SLOT structured output framework, token log-probability confidence methods.

### Track 2: Production Extraction Pipelines (researcher-2)

**Focus**: How existing agent memory systems actually extract knowledge from conversations in production.

**Key questions**:
- What is Zep/Graphiti's exact extraction pipeline (prompts, entity resolution, deduplication, temporal handling)?
- How does Mem0 extract and persist user preferences at scale?
- What is Memoria's incremental knowledge graph construction approach?
- How does A-MEM handle knowledge evolution and contradiction detection?
- What extraction prompts does MAGMA use to populate its multi-graph architecture?
- What are the common failure modes and how do production systems handle extraction errors?

**Systems to investigate**: Zep/Graphiti (open source, GitHub), Mem0 (paper + open source), Memoria (paper), A-MEM (paper), MAGMA (paper), Cognee (open source).

### Track 3: Ontology-Guided Extraction and Validation (researcher-3)

**Focus**: How to use our ontology schema to guide extraction and validate results.

**Key questions**:
- How to translate our PG-Schema (ADR-0011) into effective extraction prompts (SPIRES/OntoGPT pattern)?
- How to generate ontology snippets per entity type (ODKE+ pattern) for our 8 node types?
- What validation pipeline ensures extracted nodes conform to ontology constraints before graph insertion?
- How to perform entity resolution during extraction (not just post-extraction) to prevent duplicate nodes?
- How to calibrate confidence thresholds for different extraction sources (explicit/implicit/inferred)?
- How to handle schema evolution -- what happens when new preference categories or behavioral pattern types emerge from conversations?

**Systems/papers to investigate**: SPIRES/OntoGPT, ODKE+, RELATE, OmEGa, iText2KG, AutoSchemaKG, Neo4j LLM Knowledge Graph Builder.

---

## 5. Cross-Cutting Concerns

All three tracks should address these shared concerns:

1. **Merchant domain specificity**: Extraction must work well with SMB merchant vocabulary (payment processing, invoicing, shipping, compliance) -- not just generic conversation.

2. **Multi-language support**: Merchants may converse in multiple languages. Extraction should be language-agnostic or explicitly handle the `language` field on UserProfile.

3. **Privacy by design**: Extraction must respect consent boundaries (ADR-0012 Section 10). The pipeline should never extract preferences from conversations where consent has not been granted.

4. **Cost optimization**: LLM calls at extraction time are the primary operational cost. Research should quantify token usage per extraction and identify optimization opportunities (batching, caching, model selection).

5. **Evaluation methodology**: How to measure extraction quality? Precision/recall/F1 on labeled conversation datasets? Competency question pass rates? End-to-end personalization quality metrics?

---

## References

### LLM-Based Knowledge Graph Construction
- [LLM-empowered KG construction survey (ICAIS 2025)](https://arxiv.org/abs/2510.20345)
- [LLM-TEXT2KG 2025 Workshop](https://aiisc.ai/text2kg2025/)
- [Neo4j LLM Knowledge Graph Builder](https://neo4j.com/blog/developer/llm-knowledge-graph-builder-release/)
- [StructEval: Benchmarking LLM Structured Outputs](https://arxiv.org/html/2505.20139v1)
- [SLOT: Structuring LLM Outputs (EMNLP 2025)](https://aclanthology.org/2025.emnlp-industry.32.pdf)
- [Cleanlab TLM Structured Output Confidence](https://cleanlab.ai/blog/tlm-structured-outputs-benchmark/)

### Production Agent Memory Systems
- [Zep/Graphiti: Temporal Knowledge Graph for Agent Memory](https://arxiv.org/abs/2501.13956)
- [Mem0: Production-Ready AI Agents with Scalable Long-Term Memory (ECAI 2025)](https://arxiv.org/abs/2504.19413)
- [Memoria: Scalable Agentic Memory for Personalized Conversational AI](https://arxiv.org/abs/2512.12686)
- [MAGMA: Multi-Graph Agentic Memory Architecture](https://arxiv.org/abs/2601.03236)
- [Graph-based Agent Memory: Taxonomy, Techniques, and Applications](https://arxiv.org/html/2602.05665)
- [Cognee AI Memory Tools Evaluation](https://www.cognee.ai/blog/deep-dives/ai-memory-tools-evaluation)

### Ontology-Guided Extraction
- [SPIRES/OntoGPT: Ontological Extraction Tools](https://github.com/monarch-initiative/ontogpt)
- [ODKE+: Ontology-Guided Open-Domain Knowledge Extraction (Apple)](https://machinelearning.apple.com/research/odke)
- [RELATE: Ontology-Constrained Relation Extraction](https://arxiv.org/html/2509.19057v1)
- [OmEGa: Ontology-based Task-Centric KG Construction](https://www.sciencedirect.com/science/article/abs/pii/S1474034624006529)
- [iText2KG: Incremental KG Construction](https://arxiv.org/html/2409.03284v1)

### Entity Resolution and Validation
- [Neo4j: Text to Knowledge Graph Pipeline](https://neo4j.com/blog/genai/text-to-knowledge-graph-information-extraction-pipeline/)
- [KARMA: Multi-Agent LLMs for KG Enrichment](https://openreview.net/pdf?id=k0wyi4cOGy)
- [KG Construction: Extraction, Learning, and Evaluation](https://www.mdpi.com/2076-3417/15/7/3727)
