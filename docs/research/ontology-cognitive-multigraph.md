# Cognitive Memory Ontologies and Multi-Graph Formalisms

Date: 2026-02-11
Status: Research deliverable for ADR-0011 (Task #4)

## Purpose

This document provides a deep dive into two interconnected areas that are critical for formalizing the context-graph project's cognitive architecture as an ontology:

1. **Cognitive and memory ontologies** -- formal representations of memory types, consolidation, decay, and forgetting that ground our 5-tier memory architecture (ADR-0007) in established knowledge representation standards.

2. **Multi-graph formalisms** -- techniques for representing multiple overlapping relational views on the same node set, which is exactly the pattern our 5 edge types (FOLLOWS, CAUSED_BY, SIMILAR_TO, REFERENCES, SUMMARIZES) impose on our 3 node types (Event, Entity, Summary).

The goal is to determine: (a) which existing cognitive ontologies can formally ground our memory tier names and transitions, (b) whether CLS (Complementary Learning Systems) theory has been formalized as an ontology, and (c) what multi-graph formalisms best capture our architecture where the same events participate in temporal, causal, semantic, entity, and hierarchical relationship layers simultaneously.

---

## 1. Cognitive and Memory Ontologies

### 1.1 Mental Functioning Ontology (MFO)

**Source**: https://github.com/jannahastings/mental-functioning-ontology
**OBO Foundry**: https://obofoundry.org/ontology/mf.html
**BioPortal**: https://bioportal.bioontology.org/ontologies/MF
**Format**: OWL, built on BFO (Basic Formal Ontology)
**Last updated**: September 2025 (BioPortal)

#### What MFO Provides

MFO is the most formally rigorous OWL ontology covering mental functioning. It is built on BFO 2.0 (ISO/IEC 21838-2), which provides the upper-level class hierarchy:

```
BFO:entity
  BFO:continuant
    BFO:independent_continuant        (things that exist)
    BFO:dependent_continuant
      BFO:quality                     (measurable attributes)
      BFO:realizable_entity
        BFO:disposition               (inherent capacities)
        BFO:role                      (socially grounded)
  BFO:occurrent
    BFO:process                       (things that happen)
    BFO:temporal_region               (time intervals)
```

Within this BFO framework, MFO positions memory as a **mental process** (subclass of `BFO:process`). The MFO hierarchy for memory-related concepts includes:

```
mf:mental_process
  mf:cognitive_process
    mf:memory
      mf:episodic_memory              (instance-specific recall)
      mf:semantic_memory              (factual knowledge retrieval)
      mf:procedural_memory            (skill execution)
      mf:working_memory               (active manipulation)
    mf:learning
      mf:memory_encoding              (formation)
      mf:memory_consolidation         (stabilization)
      mf:memory_retrieval             (recall)
```

MFO also represents memory-related **dispositions** (capacities that exist even when not being exercised):

```
mf:mental_disposition
  mf:cognitive_disposition
    mf:memory_capacity                (ability to store/retrieve)
```

#### What MFO Lacks

MFO models human mental functioning, not computational systems. Key gaps for our use case:

- **No sensory memory class.** MFO's taxonomy starts at working memory. Sensory memory (sub-second perceptual buffering) is treated as a perceptual process, not a memory type. This aligns with our ADR-0007 decision to treat sensory memory as implicit (API ingestion buffer, not a persistent store).

- **No memory tier transitions.** MFO defines memory types as static process categories but does not model transitions between them (e.g., working -> episodic -> semantic consolidation). The consolidation lifecycle is absent.

- **No decay or forgetting processes.** MFO has no classes for memory decay, forgetting curves, or retention scoring. Forgetting is not modeled as an active process.

- **No computational analogy framework.** MFO describes biological memory literally. Using MFO terms for computational systems requires explicit analogical qualification.

#### Relevance Assessment

MFO provides the best available formal OWL taxonomy for naming our memory tiers. The mapping is:

| Our Tier (ADR-0007) | MFO Class | Qualification |
|---------------------|-----------|---------------|
| Sensory (Tier 1) | (no direct mapping -- see `mf:perception`) | Analogical: API buffer ~ perceptual transient |
| Working (Tier 2) | `mf:working_memory` | Analogical: context assembly ~ active manipulation |
| Episodic (Tier 3) | `mf:episodic_memory` | Analogical: Redis event ledger ~ instance-specific recall |
| Semantic (Tier 4) | `mf:semantic_memory` | Analogical: Neo4j graph ~ factual knowledge retrieval |
| Procedural (Tier 5) | `mf:procedural_memory` | Analogical: workflow patterns ~ skill execution |

**Recommendation**: Reference MFO as the formal grounding for tier names, with explicit `cg:analogicallyGroundedIn` annotation linking our tier classes to MFO classes. Do not import MFO wholesale -- it drags in the entire BFO/OGMS stack, which is irrelevant to our domain. Instead, create our own lightweight tier classes and annotate them with `rdfs:seeAlso` or `skos:closeMatch` pointing to MFO IRIs.

### 1.2 Cognitive Atlas (CogAt)

**Source**: https://cognitiveatlas.org/
**Format**: Web-based knowledge graph with OWL serialization
**PMC**: https://pmc.ncbi.nlm.nih.gov/articles/PMC3167196/

#### What Cognitive Atlas Provides

Cognitive Atlas is a collaborative knowledge base built on two fundamental categories:

1. **Mental concepts** -- unobservable psychological constructs (e.g., "episodic memory", "working memory", "attention", "decision-making")
2. **Mental tasks** -- observable operations used to measure those constructs (e.g., Stroop task, N-back task)

Concepts are linked by three core relationships:
- `is_a` -- taxonomic subsumption
- `is_part_of` -- mereological containment
- `is_measured_by` -- operationalization link from concept to task

The memory-related concept taxonomy in Cognitive Atlas includes:

```
memory
  episodic memory
    episodic encoding
    episodic retrieval
    prospective memory (memory for future intentions)
  semantic memory
    semantic encoding
    semantic retrieval
  working memory
    phonological loop
    visuospatial sketchpad
    central executive
  procedural memory
    motor learning
    skill acquisition
  sensory memory
    iconic memory (visual)
    echoic memory (auditory)
  long-term memory
  short-term memory
```

#### What Cognitive Atlas Lacks

- **Not a formal OWL ontology.** CogAt is primarily a web knowledge base with informal ontological structure. It has been exported to OWL but the export is a lightweight SKOS-style taxonomy, not an axiomatized OWL 2 DL ontology.
- **No process modeling.** CogAt defines memory types as static concepts, not processes with temporal dynamics. There is no model for consolidation, decay, or retrieval mechanics.
- **No computational mapping vocabulary.** No mechanism for annotating that a software component "implements" or "is analogous to" a cognitive concept.

#### Relevance Assessment

CogAt provides the most comprehensive vocabulary of memory-type names. It is the best source for ensuring our tier naming is consistent with established cognitive science terminology. Its `is_measured_by` relationship is conceptually interesting -- it formalizes how abstract cognitive constructs are operationalized through observable tasks, which parallels how our memory tiers are operationalized through system metrics (e.g., episodic memory is "measured by" event ledger completeness).

**Recommendation**: Use CogAt concept URIs as `skos:exactMatch` annotations on our tier classes where alignment is clear (episodic, semantic, procedural, working, sensory). Reference the CogAt taxonomy as the normative vocabulary source.

### 1.3 Cognitive Paradigm Ontology (CogPO)

**Source**: http://www.cogpo.org/
**BioPortal**: https://bioportal.bioontology.org/ontologies/COGPO
**Format**: OWL, BFO-compliant
**Reference**: Turner & Laird (2012). "The Cognitive Paradigm Ontology: Design and Application." Neuroinformatics.

#### What CogPO Provides

CogPO models experimental conditions in cognitive neuroscience through three dimensions:
- **Stimulus presented** -- what the subject perceives
- **Instructions given** -- task demands
- **Response requested** -- expected behavioral output

CogPO is harmonized with BFO, RadLex, NeuroLex, and OBI (Ontology for Biomedical Investigations).

#### What CogPO Lacks for Our Use Case

CogPO is specifically designed for fMRI/neuroimaging experiment classification. Its primary value is labeling brain activation data with experimental conditions, not modeling computational memory systems. The stimulus/instruction/response pattern is conceptually interesting (maps loosely to input/context/output in agent behavior) but too domain-specific for direct adoption.

**Recommendation**: May reference for background. CogPO's stimulus/instruction/response decomposition provides a useful conceptual frame for thinking about agent event cycles, but it is not worth importing or formally aligning with.

### 1.4 Neural ElectroMagnetic Ontology (NEMO)

**Source**: https://bioportal.bioontology.org/ontologies/NEMO
**NITRC**: https://www.nitrc.org/projects/nemo
**Format**: OWL, OBO-compliant

#### What NEMO Provides

NEMO is an NIH-funded ontology for EEG/MEG (Event-Related Potential) data. Its three pillars are:
- **DATA**: Raw EEG, averaged ERPs, analysis results
- **ONTOLOGY**: Concepts for ERP data features (spatial, temporal), data provenance, and cognitive paradigms
- **DATABASE**: Semantically-based reasoning over annotated ERP data

NEMO uses a combined top-down (knowledge-driven) and bottom-up (data-driven) approach.

#### What NEMO Lacks for Our Use Case

NEMO is entirely focused on neural electromagnetic data analysis. It does not model memory processes as computational patterns. Its cognitive paradigm coverage overlaps with CogPO and is limited to the experimental context of ERP studies.

**Recommendation**: Not relevant for direct adoption. NEMO's domain (electromagnetic brain signals) does not intersect with our computational memory architecture.

### 1.5 Has CLS Theory Been Formalized as an Ontology?

**Finding: No formal CLS ontology exists.**

Complementary Learning Systems theory (McClelland, McNaughton & O'Reilly, 1995; updated by Kumaran, Hassabis & McClelland, 2016) describes the interplay between hippocampal fast learning and neocortical slow consolidation. Despite being one of the most influential theories in computational neuroscience, it has not been formalized as an OWL or RDF ontology.

The closest formalizations are:

1. **Computational models** -- CLS has been implemented as neural network models (e.g., HiCL's hippocampal circuit mapping, HiMeS's dual-memory system), but these are programmatic implementations, not ontological formalizations. They define algorithms, not classes and relationships.

2. **Agent memory architectures** -- Papers like MAGMA (Jiang et al., 2026) and "AI Meets Brain" (Liang et al., 2025) map CLS concepts to software architectures, but again as informal analogies in prose, not as formal ontology statements.

3. **MFO partial coverage** -- MFO defines `memory_consolidation` and `memory_encoding` as process classes, which are components of the CLS lifecycle, but MFO does not model the dual-system interplay (fast system vs. slow system) that is CLS's defining feature.

**This represents an opportunity for the context-graph project.** We could define a lightweight CLS vocabulary as part of our ontology:

```
cg:ComplementaryLearningSystem
  cg:FastLearningSystem       # rapid, detailed, interference-prone
    cg:hasImplementation -> cg:RedisEventStore
  cg:SlowLearningSystem       # gradual, abstract, stable
    cg:hasImplementation -> cg:Neo4jGraphProjection
  cg:ConsolidationProcess      # transfers knowledge from fast to slow
    cg:hasImplementation -> cg:ProjectionWorker
```

This would be the first formal ontological representation of CLS theory, scoped specifically to our computational analogy. The vocabulary would use `cg:analogicallyGroundedIn` annotations pointing to the relevant neuroscience literature.

### 1.6 Formal Models for Memory Consolidation, Replay, and Forgetting

No standalone ontology exists for memory consolidation, replay, or forgetting. However, several relevant formalisms exist:

#### Ontology Design Patterns for Temporal Change

The ODP (Ontology Design Patterns) community has developed patterns relevant to modeling memory lifecycle:

- **Temporal Indirection Pattern** (WOP 2024): Models entities with time-varying properties by reifying the temporal binding. A memory node's importance score changes over time -- this pattern provides the OWL machinery to represent that.

- **Change Over Time Pattern** (Logical Design Pattern): Uses the 4D (perdurantist) view where objects have temporal parts. Applied to memory: an event node at time T1 has different decay scores than at time T2. The 4D view avoids the complexity of n-ary relations by treating each time-slice as a distinct entity.

- **Recurrent Events Pattern** (WOP 2019): Models events that recur with variations. Relevant to re-consolidation -- the same graph region is re-processed periodically, potentially yielding different enrichments each time.

#### Ebbinghaus Decay as Ontological Constraint

Our decay scoring formula (`score = e^(-t/S)` where S increases on access) could be formalized as an ontological constraint, though OWL's expressiveness is limited for mathematical functions. Two approaches:

1. **SWRL rules**: `MemoryNode(?x) ^ hasElapsedHours(?x, ?t) ^ hasStability(?x, ?s) -> hasRecencyScore(?x, e^(-?t/?s))`. SWRL supports mathematical built-ins but is not widely supported by reasoners.

2. **SHACL constraints**: Define shapes that validate decay-scored nodes have scores within expected ranges. Cannot compute the score but can validate it: `sh:property [sh:path cg:decayScore; sh:minInclusive 0.0; sh:maxInclusive 1.0]`.

3. **Pragmatic approach**: Define the decay formula in documentation and code, not in OWL axioms. Use ontology classes to categorize retention tiers (Hot, Warm, Cold, Archive) as discrete states rather than continuous functions.

**Recommendation**: Model retention tiers as ontology classes with discrete membership criteria. Do not attempt to encode continuous decay functions in OWL. The tier boundaries are the ontologically meaningful concepts:

```
cg:RetentionTier
  cg:HotTier       # < 24 hours, full detail
  cg:WarmTier      # 24h -- 7 days, pruned low-importance edges
  cg:ColdTier      # 7 -- 30 days, importance >= 5 or access >= 3
  cg:ArchiveTier   # > 30 days, removed from Neo4j
```

### 1.7 Formalizing Memory Tier Transitions

The directional flow from ADR-0007 (`Sensory -> Working -> Episodic -> Semantic -> Procedural`) can be formalized as an ontological state transition model:

```
cg:MemoryTier a owl:Class .
cg:SensoryTier rdfs:subClassOf cg:MemoryTier .
cg:WorkingTier rdfs:subClassOf cg:MemoryTier .
cg:EpisodicTier rdfs:subClassOf cg:MemoryTier .
cg:SemanticTier rdfs:subClassOf cg:MemoryTier .
cg:ProceduralTier rdfs:subClassOf cg:MemoryTier .

cg:consolidatesTo a owl:ObjectProperty ;
    rdfs:domain cg:MemoryTier ;
    rdfs:range cg:MemoryTier ;
    rdfs:comment "Directional flow of information during consolidation." .

cg:SensoryTier cg:consolidatesTo cg:WorkingTier .
cg:WorkingTier cg:consolidatesTo cg:EpisodicTier .
cg:EpisodicTier cg:consolidatesTo cg:SemanticTier .
cg:EpisodicTier cg:consolidatesTo cg:ProceduralTier .
```

The consolidation stages from ADR-0008 can similarly be formalized:

```
cg:ConsolidationStage a owl:Class .
cg:EventProjection rdfs:subClassOf cg:ConsolidationStage ;
    rdfs:comment "Stage 1: Fast-path MERGE from Redis to Neo4j." .
cg:Enrichment rdfs:subClassOf cg:ConsolidationStage ;
    rdfs:comment "Stage 2: Derived attributes (keywords, embeddings, importance)." .
cg:ReConsolidation rdfs:subClassOf cg:ConsolidationStage ;
    rdfs:comment "Stage 3: Periodic cross-event relationship discovery." .

cg:EventProjection cg:precedes cg:Enrichment .
cg:Enrichment cg:precedes cg:ReConsolidation .
```

---

## 2. Multi-Graph Formalisms

Our architecture imposes five distinct relational views on the same node set. This is a multi-graph problem: the same Event nodes participate simultaneously in temporal chains (FOLLOWS), causal chains (CAUSED_BY), semantic similarity clusters (SIMILAR_TO), entity attribution networks (REFERENCES), and hierarchical summaries (SUMMARIZES). Each view captures orthogonal information about the same underlying events.

### 2.1 MAGMA: The Agent Memory Multi-Graph Precedent

**Source**: Jiang et al. (2026). "MAGMA: A Multi-Graph based Agentic Memory Architecture." arXiv:2601.03236

MAGMA is the most directly relevant multi-graph formalism for our architecture. It represents memory using four orthogonal graphs over a shared node set:

#### MAGMA's Four Graphs

| Graph | Edge Type | Semantics | Construction |
|-------|-----------|-----------|--------------|
| **Temporal** (E_temp) | Directed, strict ordering | Chronological sequence | Immutable: `(ni, nj)` where `tau_i < tau_j` |
| **Causal** (E_causal) | Directed, logical entailment | Why relationships | LLM-inferred: edge if `S(nj|ni,q) > delta` |
| **Semantic** (E_sem) | Undirected, similarity | Topical relatedness | Embedding: edge if `cos(vi, vj) > theta_sim` |
| **Entity** (E_ent) | Bipartite (event <-> entity) | Actor/object participation | NER extraction from event content |

#### Shared Node Representation

All four graphs share identical event nodes, each defined by:
- `ci` -- content (observations, actions, state changes)
- `tau_i` -- timestamp (discrete time anchor)
- `vi` -- dense embedding (vector index)
- `A_i` -- metadata (structured attributes, entity references)

This is exactly our architectural pattern: Event nodes participate in all five edge types simultaneously.

#### Intent-Aware Query Routing

MAGMA's key innovation is **intent-aware traversal**: the query mechanism classifies query intent (Why? When? Who/What?) and dynamically weights which graph edges to prioritize:

```
transition_score = phi(r, Tq) * sim(v_candidate, v_query)
```

Where `phi(r, Tq)` is a learned weight that varies by edge type `r` and query intent `Tq`. "Why" queries upweight causal edges; "When" queries upweight temporal edges; entity queries upweight entity edges.

#### Dual-Stream Memory Evolution

MAGMA separates ingestion from consolidation:
- **Fast path** (synaptic): Non-blocking event segmentation, vector indexing, and temporal backbone update
- **Slow path** (structural): Asynchronous LLM-based inference of causal and entity edges

This maps directly to our ADR-0008 consolidation stages:
- Fast path = Stage 1 (Event Projection)
- Slow path = Stages 2-3 (Enrichment + Re-Consolidation)

#### Mapping MAGMA to Context-Graph

| MAGMA Graph | Context-Graph Edge Type | Notes |
|-------------|------------------------|-------|
| Temporal (E_temp) | FOLLOWS | Both: strict temporal ordering, immutable |
| Causal (E_causal) | CAUSED_BY | Both: directed logical entailment; ours uses `parent_event_id`, MAGMA uses LLM inference |
| Semantic (E_sem) | SIMILAR_TO | Both: embedding cosine similarity above threshold |
| Entity (E_ent) | REFERENCES | Both: bipartite event-to-entity links |
| (no equivalent) | SUMMARIZES | Our addition: hierarchical summary nodes |

Our SUMMARIZES edge has no MAGMA equivalent. This is our contribution -- the hierarchical summarization layer that creates abstract Summary nodes from clusters of Event nodes, following the hippocampal indexing pattern.

### 2.2 Named Graphs in RDF

**Spec**: W3C RDF 1.1 Datasets (https://www.w3.org/TR/rdf11-datasets/)

Named graphs extend RDF from triples to quads: `(subject, predicate, object, graphName)`. Each named graph is identified by an IRI and contains a set of triples.

#### How Named Graphs Enable Multi-View

A named graph partitions triples into labeled sets. The same entity can appear in multiple named graphs, each representing a different view:

```
:temporalGraph {
    :event1 :follows :event2 .
    :event2 :follows :event3 .
}

:causalGraph {
    :event3 :causedBy :event1 .
}

:semanticGraph {
    :event1 :similarTo :event2 .
}

:entityGraph {
    :event1 :references :toolX .
    :event2 :references :agentY .
}
```

SPARQL 1.1 queries can target specific graphs or query across graphs:

```sparql
# Query only the causal view
SELECT ?effect ?cause WHERE {
    GRAPH :causalGraph { ?effect :causedBy ?cause }
}

# Query across temporal and causal views
SELECT ?event ?next ?cause WHERE {
    GRAPH :temporalGraph { ?event :follows ?next }
    GRAPH :causalGraph { ?next :causedBy ?cause }
}
```

#### Relevance to Context-Graph

Named graphs provide a clean formal model for our multi-view architecture. If we were to export our Neo4j data as RDF, each edge type would naturally map to a named graph:

| Context-Graph Edge | Named Graph IRI | Content |
|-------------------|-----------------|---------|
| FOLLOWS | `cg:temporal` | Temporal ordering triples |
| CAUSED_BY | `cg:causal` | Causal chain triples |
| SIMILAR_TO | `cg:semantic` | Similarity link triples |
| REFERENCES | `cg:entity` | Entity attribution triples |
| SUMMARIZES | `cg:hierarchical` | Summary hierarchy triples |

**However**, we are not using RDF. Our store is Neo4j (property graph model). Named graphs inform the conceptual model but are not directly implementable. The relevant pattern is the concept of "multiple labeled edge sets over shared nodes" -- which Neo4j supports natively through relationship types.

### 2.3 Multi-View Knowledge Graphs (MVKG)

**Source**: Yang et al. (2025). "A Survey on Multi-View Knowledge Graph: Generation, Fusion, Applications and Future Directions." IJCAI 2025.

The MVKG survey provides the first unified formal definition:

```
MVKG = (G, V, f, Theta)
```

Where:
- `G = (E, R, T)` -- base knowledge graph (entities, relations, triples)
- `V = {v1, v2, ..., vk}` -- set of views, each a subset/perspective of G
- `f` -- view generation function
- `Theta` -- fusion parameters

#### View Types (Taxonomy)

The survey classifies views into four types:

1. **Structural views** -- different subgraph topologies (e.g., 1-hop neighborhood vs. 2-hop neighborhood)
2. **Semantic views** -- different relation-type filters (e.g., only causal edges vs. only temporal edges)
3. **Representation views** -- different embedding spaces (e.g., TransE vs. RotatE encodings)
4. **Knowledge & modality views** -- different data sources (e.g., text vs. images vs. structured data)

Our multi-edge-type architecture corresponds to **semantic views** -- each edge type defines a relational filter that produces a distinct view of the same entity set.

#### View Fusion Methods

When querying, views must be fused. The survey identifies three fusion targets:
- **Feature fusion**: Combine node embeddings from different views (concatenation, element-wise addition, attention-weighted pooling)
- **Decision fusion**: Produce separate query results from each view, then merge results
- **Hybrid fusion**: Combine features at intermediate layers

MAGMA's intent-aware traversal is a form of **decision fusion with dynamic weighting** -- each view produces a subgraph, and the results are merged with intent-dependent weights.

#### Relevance to Context-Graph

The MVKG formalism provides the theoretical vocabulary for describing our architecture:

- Our five edge types are five **semantic views** over a shared entity set
- Our intent-aware retrieval (ADR-0009) is a **decision fusion** mechanism
- Our working memory assembly (Tier 2) performs **feature fusion** by combining information from multiple views into a bounded, priority-ranked context

**Recommendation**: Adopt the MVKG vocabulary when describing our multi-view architecture in ADR-0011. Define each edge type as a named semantic view.

### 2.4 Ontology Modularization and OWL Imports

**Key reference**: MODL -- Modular Ontology Design Library (Shimizu et al., 2019)
**Workshop**: 15th Workshop on Ontology Design and Patterns (WOP 2024, colocated with ISWC 2024)

Ontology modularization addresses how to decompose a large ontology into independently maintainable modules that can be imported as needed. This is relevant because our ontology has orthogonal concerns:

- **Provenance vocabulary** (PROV-O core: Entity/Activity/Agent)
- **Event vocabulary** (event types, status, temporal properties)
- **Memory tier vocabulary** (tier classes, consolidation stages)
- **Graph schema vocabulary** (node types, edge types, constraints)

#### Modularization Patterns

1. **OWL imports** (`owl:imports`): One ontology imports another wholesale. Transitively imports all axioms. Good for stable, well-scoped dependencies (e.g., importing PROV-O). Bad for large ontologies where you only need a subset.

2. **Ontology Design Patterns (ODPs)**: Reusable micro-ontologies (10-20 classes) solving specific modeling problems. Published in curated libraries (MODL). Can be composed via OWL imports or by copy-adapt.

3. **OPLa (Ontology Pattern Language Annotations)**: Metadata standard for documenting pattern provenance, version, and relationships between patterns and the ontologies that use them.

4. **Reasonable Ontology Templates (OTTRs)**: OWL macros for instantiating ontology design patterns. Allow parameterized pattern application.

#### Recommended Module Structure for Context-Graph Ontology

```
cg-core.owl          -- Node types, edge types, core properties
  owl:imports prov-o  -- W3C PROV-O for provenance vocabulary

cg-events.owl        -- Event type taxonomy, status values, temporal properties
  owl:imports cg-core

cg-memory.owl        -- Memory tier classes, consolidation stages, CLS vocabulary
  owl:imports cg-core

cg-views.owl         -- Multi-view definitions (temporal, causal, semantic, entity, hierarchical)
  owl:imports cg-core

cg-decay.owl         -- Retention tier classes, decay scoring parameters
  owl:imports cg-memory
```

This separation ensures that consumers who only need the core graph schema do not need to import the cognitive memory vocabulary, and vice versa.

### 2.5 Neo4j and Property Graph Multi-Graph Support

#### Neo4j Native Approach: Relationship Types as Views

Neo4j's property graph model naturally supports multi-graph patterns through relationship types. Each relationship type defines an implicit subgraph:

```cypher
// Temporal view
MATCH (a:Event)-[:FOLLOWS]->(b:Event) RETURN a, b

// Causal view
MATCH (a:Event)-[:CAUSED_BY]->(b:Event) RETURN a, b

// Semantic view
MATCH (a:Event)-[:SIMILAR_TO]-(b:Event) RETURN a, b

// Entity view
MATCH (a:Event)-[:REFERENCES]->(e:Entity) RETURN a, e

// Hierarchical view
MATCH (s:Summary)-[:SUMMARIZES]->(a:Event) RETURN s, a
```

This is the simplest multi-graph pattern: the node set is shared, and relationship types partition the edge set into views. Neo4j's query optimizer handles this efficiently because relationship type filtering is a constant-time operation in the native storage engine.

#### Neo4j Fabric (Multi-Database)

Neo4j Fabric allows querying across multiple databases in a single Cypher query. Each database could hold a different view:

- Database `temporal` -- only FOLLOWS edges
- Database `causal` -- only CAUSED_BY edges
- etc.

**However**, this is overengineering for our case. Fabric is designed for data federation across physically separate databases, not for logical view separation within a single dataset. Our relationship-type-based approach is simpler, more performant, and sufficient.

#### Neo4j Graph Data Science (GDS) Projections

The GDS library creates in-memory graph projections that can filter by relationship type:

```cypher
CALL gds.graph.project(
    'temporalView',
    'Event',
    'FOLLOWS'
)

CALL gds.graph.project(
    'causalView',
    'Event',
    'CAUSED_BY'
)
```

This allows running graph algorithms (PageRank, community detection, centrality) on specific views. Useful for computing importance scores within the causal view vs. the temporal view.

**Recommendation**: Use Neo4j's native relationship types as the multi-graph mechanism. Use GDS projections for view-specific analytics. Do not use Fabric for view separation.

#### TigerGraph MultiGraph (Comparison)

TigerGraph supports overlapping graphs where multiple named graphs share subsets of vertex and edge containers. A graph can be defined as the union of other graphs: `Graph X = Graph Y UNION Graph Z`. Each graph has its own queries and loading jobs.

This is more expressive than Neo4j's approach but adds administrative complexity. For our use case, Neo4j's relationship-type filtering achieves the same result with less overhead.

### 2.6 Category Theory: Useful or Too Academic?

**Key reference**: "Bridging Property Graphs and Knowledge Graphs: A Category Theory Approach to Interoperable Graph Transformation." KGSWC 2025.

Category theory provides a mathematical framework for describing graph transformations through functors (structure-preserving maps between categories). The 2025 KGSWC paper uses functorial transformations to bridge property graphs and RDF-star knowledge graphs.

#### Where Category Theory Applies

- **Formal interoperability**: If we need to export our Neo4j property graph to RDF/OWL for standards compliance, category theory provides the formal foundation for proving that the transformation preserves structure (a functor from the category of property graphs to the category of RDF graphs).

- **Multi-view composition**: Category theory's natural transformations describe how different views (functors) of the same underlying data relate to each other. This provides rigorous vocabulary for saying "the temporal view and the causal view are two different projections of the same event stream."

- **Schema evolution**: Functors can model schema migrations as structure-preserving transformations, ensuring that projected views remain consistent when the underlying schema changes.

#### Where Category Theory Is Overkill

- **Day-to-day development**: Category theory does not help write Cypher queries or design API endpoints. It is a meta-level formalism.

- **Team communication**: The overhead of category-theoretic vocabulary (functors, natural transformations, adjunctions) exceeds its explanatory benefit for a software engineering team.

- **Implementation**: No production graph database provides category-theoretic primitives. The formalism stays on paper.

**Recommendation**: Reference category theory in the ADR as the mathematical foundation that justifies our multi-view design (the claim that "different edge types are independent projections of the same event stream" is a claim about functors). Do not adopt category-theoretic notation or require the team to understand it. Use it for theoretical grounding, not operational guidance.

---

## 3. Bridging Cognitive Tiers to Formal Ontology

### 3.1 Memory Tiers as Ontology Classes

Our five memory tiers can be expressed as ontology classes with formal properties:

```turtle
@prefix cg: <https://context-graph.dev/ontology#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .

# Memory Tier Hierarchy
cg:MemoryTier a owl:Class ;
    rdfs:comment "A cognitive memory tier in the CLS-inspired architecture." .

cg:SensoryTier a owl:Class ;
    rdfs:subClassOf cg:MemoryTier ;
    skos:closeMatch <https://cognitiveatlas.org/concept/id/sensory_memory> ;
    cg:implementedBy cg:APIIngestionBuffer ;
    cg:persistence "transient" ;
    cg:duration "< 1 second" ;
    rdfs:comment "Transient buffering of raw input before validation." .

cg:WorkingTier a owl:Class ;
    rdfs:subClassOf cg:MemoryTier ;
    skos:closeMatch <https://cognitiveatlas.org/concept/id/working_memory> ;
    cg:implementedBy cg:ContextAPIResponse ;
    cg:persistence "session-scoped" ;
    cg:capacityBounded true ;
    rdfs:comment "Bounded, priority-ranked context assembly for the requesting agent." .

cg:EpisodicTier a owl:Class ;
    rdfs:subClassOf cg:MemoryTier ;
    skos:closeMatch <https://cognitiveatlas.org/concept/id/episodic_memory> ;
    cg:implementedBy cg:RedisEventStore ;
    cg:persistence "immutable" ;
    cg:CLSRole cg:FastLearningSystem ;
    rdfs:comment "Immutable, instance-specific event records in Redis." .

cg:SemanticTier a owl:Class ;
    rdfs:subClassOf cg:MemoryTier ;
    skos:closeMatch <https://cognitiveatlas.org/concept/id/semantic_memory> ;
    cg:implementedBy cg:Neo4jGraphProjection ;
    cg:persistence "derived" ;
    cg:CLSRole cg:SlowLearningSystem ;
    rdfs:comment "Derived relational knowledge in Neo4j graph projection." .

cg:ProceduralTier a owl:Class ;
    rdfs:subClassOf cg:MemoryTier ;
    skos:closeMatch <https://cognitiveatlas.org/concept/id/procedural_memory> ;
    cg:implementedBy cg:Neo4jPatternSubgraph ;
    cg:persistence "future" ;
    rdfs:comment "Learned tool-use policies and workflow patterns (future)." .
```

### 3.2 Tier Transitions as Object Properties

The consolidation flow is a directional process. It can be modeled as object properties with domain/range constraints:

```turtle
cg:consolidatesTo a owl:ObjectProperty ;
    rdfs:domain cg:MemoryTier ;
    rdfs:range cg:MemoryTier ;
    owl:propertyChainAxiom ( cg:consolidatesTo cg:consolidatesTo ) ;
    rdfs:comment "Information flows from this tier to the target during consolidation." .

# Specific transitions
cg:SensoryTier cg:consolidatesTo cg:WorkingTier .
cg:WorkingTier cg:consolidatesTo cg:EpisodicTier .
cg:EpisodicTier cg:consolidatesTo cg:SemanticTier .
cg:EpisodicTier cg:consolidatesTo cg:ProceduralTier .
```

The consolidation stages from ADR-0008 mediate these transitions:

```turtle
cg:mediatedBy a owl:ObjectProperty ;
    rdfs:domain cg:MemoryTier ;
    rdfs:range cg:ConsolidationStage .

# Episodic -> Semantic is mediated by all three stages
cg:EpisodicTier cg:mediatedBy cg:EventProjection .
cg:EpisodicTier cg:mediatedBy cg:Enrichment .
cg:EpisodicTier cg:mediatedBy cg:ReConsolidation .
```

### 3.3 Retention Tiers as Ontological Constraints

The retention tiers from ADR-0008 define discrete states with membership criteria:

```turtle
cg:RetentionTier a owl:Class ;
    rdfs:comment "Graph node retention classification based on age and importance." .

cg:HotTier a owl:Class ;
    rdfs:subClassOf cg:RetentionTier ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty cg:ageHours ;
        owl:maxExclusive 24
    ] ;
    cg:retentionPolicy "Full detail: all nodes, all edges, all derived attributes." .

cg:WarmTier a owl:Class ;
    rdfs:subClassOf cg:RetentionTier ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty cg:ageHours ;
        owl:minInclusive 24 ;
        owl:maxExclusive 168
    ] ;
    cg:retentionPolicy "Full nodes; low-importance edges pruned." .

cg:ColdTier a owl:Class ;
    rdfs:subClassOf cg:RetentionTier ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty cg:ageHours ;
        owl:minInclusive 168 ;
        owl:maxExclusive 720
    ] ;
    cg:retentionPolicy "Only importance >= 5 or access >= 3 retained." .

cg:ArchiveTier a owl:Class ;
    rdfs:subClassOf cg:RetentionTier ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty cg:ageHours ;
        owl:minInclusive 720
    ] ;
    cg:retentionPolicy "Removed from Neo4j; retained in Redis cold tier." .
```

### 3.4 Decay Scoring as Annotation, Not Axiom

The Ebbinghaus-inspired decay formula from ADR-0008 is a continuous function:

```
score(node, query, t_now) = w_r * e^(-t_elapsed / S) + w_i * importance/10 + w_v * cosine_similarity
```

OWL 2 DL cannot express this formula as an axiom (no support for exponential functions, floating-point arithmetic, or query-dependent computation). Instead of trying to force it into OWL:

1. **Document the formula** as an `rdfs:comment` annotation on the `cg:decayScore` property.
2. **Define the inputs** as OWL datatype properties: `cg:ageHours`, `cg:stabilityFactor`, `cg:importanceScore`, `cg:accessCount`, `cg:lastAccessedAt`.
3. **Define the output** as a computed property: `cg:decayScore` with `rdfs:comment "Computed at query time. Not stored. See ADR-0008 for formula."`.
4. **Use SHACL** (if adopted) to validate that `cg:decayScore` values fall in `[0.0, 3.0]` (max possible with default weights).

---

## 4. Synthesis: What This Means for ADR-0011

### 4.1 Cognitive Vocabulary Layer

ADR-0011 should define a `cg-memory.owl` module containing:

- **Five MemoryTier classes** with `skos:closeMatch` to Cognitive Atlas concepts and `rdfs:seeAlso` to MFO classes
- **CLS vocabulary** (`FastLearningSystem`, `SlowLearningSystem`, `ConsolidationProcess`) -- the first formal ontological representation of CLS theory for computational systems
- **ConsolidationStage classes** (EventProjection, Enrichment, ReConsolidation)
- **RetentionTier classes** (Hot, Warm, Cold, Archive) with age-based membership criteria
- **Tier transition properties** (`consolidatesTo`, `mediatedBy`, `precedes`)
- **Explicit analogical grounding annotations** (`cg:analogicallyGroundedIn`) pointing to neuroscience literature

### 4.2 Multi-View Graph Layer

ADR-0011 should define a `cg-views.owl` module containing:

- **Five view classes** corresponding to our edge types, using MVKG vocabulary
- **View selection vocabulary** for intent-aware retrieval (following MAGMA's pattern)
- **View composition rules** for working memory assembly (feature fusion from multiple views)
- **Formal statement** that views are independent projections of a shared event set (multi-graph formalism)

### 4.3 What NOT to Formalize

- **Continuous decay functions** -- document in code, not in OWL
- **Embedding computation details** -- implementation concern, not ontological
- **Full MFO/BFO import** -- too heavy; use lightweight alignment annotations instead
- **Category theory notation** -- useful for theoretical grounding but not for the operational ontology

### 4.4 Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Define CLS vocabulary ourselves | No existing ontology formalizes CLS for computational systems |
| Use `skos:closeMatch` not `owl:equivalentClass` | Our tiers are analogical to, not identical with, biological memory types |
| Model retention tiers as discrete classes | OWL cannot express continuous decay; discrete tiers are the actionable boundaries |
| Use MAGMA's multi-graph pattern | Closest existing formalism to our architecture; validates our 5-edge-type design |
| Modularize into separate OWL files | Allows consumers to import only what they need; separates provenance, events, memory, views, and decay concerns |
| Use relationship types as views (Neo4j) | Simplest, most performant multi-graph implementation for property graphs |
| Reference category theory, do not adopt it | Provides theoretical justification without operational overhead |

---

## 5. Comparison of Existing Formalisms

### 5.1 Cognitive Ontology Comparison

| Ontology | Memory Types | Consolidation | Decay | OWL Quality | Our Use |
|----------|-------------|---------------|-------|-------------|---------|
| **MFO** | episodic, semantic, procedural, working | Partial (encoding, consolidation as processes) | None | Rigorous (BFO-based) | Tier name grounding |
| **CogAt** | All 5 including sensory | None | None | Informal (SKOS-like) | Vocabulary source |
| **CogPO** | None (paradigm-focused) | None | None | Good (BFO-based) | Background reference |
| **NEMO** | None (ERP-focused) | None | None | Good (OBO-compliant) | Not relevant |
| **CLS (informal)** | Fast/slow dual system | Central concept | Implicit | Not formalized | We formalize it |

### 5.2 Multi-Graph Formalism Comparison

| Formalism | Shared Nodes | View Definition | Query Support | Implementation | Our Use |
|-----------|-------------|-----------------|---------------|----------------|---------|
| **MAGMA 4-graph** | Event nodes | Edge type + construction rule | Intent-aware routing | Custom Python | Architecture model |
| **RDF Named Graphs** | RDF subjects/objects | Named IRI per graph | SPARQL GRAPH clause | Triple stores | Conceptual model |
| **MVKG (IJCAI 2025)** | Entity set E | View function f over G | Fusion methods | Research | Theoretical vocabulary |
| **Neo4j Rel Types** | Node set | Relationship type filter | Cypher type matching | Neo4j native | Production implementation |
| **TigerGraph MultiGraph** | Shared vertex containers | Named graph definition | Per-graph queries | TigerGraph native | Not adopted |
| **Category Theory** | Objects in a category | Functors between categories | N/A (meta-level) | None (mathematical) | Theoretical grounding |

---

## References

### Cognitive Ontologies
- Hastings et al. (2024). "Development of an ontology to characterize mental functioning." PMC10932805.
- Hastings et al. (2012). "Representing mental functioning: Ontologies for mental health and disease." ICBO 2012.
- Poldrack et al. (2011). "The Cognitive Atlas: Toward a Knowledge Foundation for Cognitive Neuroscience." Frontiers in Neuroinformatics.
- Turner & Laird (2012). "The Cognitive Paradigm Ontology: Design and Application." Neuroinformatics. PMC3682219.
- Frishkoff et al. (2009). "Development of Neural Electromagnetic Ontologies (NEMO)." Nature Precedings.
- McClelland, McNaughton & O'Reilly (1995). "Why There Are Complementary Learning Systems in the Hippocampus and Neocortex." Psychological Review.
- Kumaran, Hassabis & McClelland (2016). "What Learning Systems do Intelligent Agents Need? CLS Theory Updated." Trends in Cognitive Sciences.

### Multi-Graph and Multi-View Formalisms
- Jiang et al. (2026). "MAGMA: A Multi-Graph based Agentic Memory Architecture." arXiv:2601.03236.
- Yang et al. (2025). "A Survey on Multi-View Knowledge Graph: Generation, Fusion, Applications and Future Directions." IJCAI 2025.
- W3C (2014). "RDF 1.1 Datasets." https://www.w3.org/TR/rdf11-datasets/
- Lieber (2023). "RDF named graphs." https://sven-lieber.org/en/2023/06/26/rdf-named-graphs/
- KGSWC (2025). "Bridging Property Graphs and Knowledge Graphs: A Category Theory Approach." Springer.

### Ontology Design and Modularization
- Shimizu et al. (2019). "MODL: A Modular Ontology Design Library." arXiv:1904.05405.
- WOP (2024). 15th Workshop on Ontology Design and Patterns. ISWC 2024.
- Hitzler & Gangemi (2016). "Ontology Engineering with Ontology Design Patterns." IOS Press.
- BFO 2.0: https://basic-formal-ontology.org/

### Project ADRs Referenced
- ADR-0007: Cognitive Memory Tier Architecture
- ADR-0008: Memory Consolidation, Decay, and Active Forgetting
- ADR-0009: Intent-Aware Retrieval (referenced for query routing)
- ADR-0010: Redis Adoption (referenced for event store mapping)
