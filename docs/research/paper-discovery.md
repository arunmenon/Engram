# Paper Discovery: Context Graphs, Agent Memory, and Neuroscience-Inspired AI

**Date**: 2026-02-11
**Scope**: Dec 2025 -- Feb 2026
**Purpose**: Identify foundational research to inform the design of a memory layer for the context-graph service.

---

## Cluster 1: Context Graphs and Graph-Based Memory for Agents

### 1.1 Graph-based Agent Memory: Taxonomy, Techniques, and Applications

- **Authors**: Chang Yang et al. (18 authors)
- **Date**: February 5, 2026
- **Link**: https://arxiv.org/abs/2602.05665
- **Summary**: A comprehensive survey of graph-based memory architectures for LLM agents covering knowledge graphs, temporal graphs, hypergraphs, hierarchical trees, and hybrid graphs. Decomposes the memory lifecycle into extraction, storage, retrieval, and evolution stages. Directly relevant to our graph-projection architecture -- validates the decision to use graph structures for agent memory and provides a taxonomy we can align our schema to.

### 1.2 MAGMA: A Multi-Graph based Agentic Memory Architecture for AI Agents

- **Authors**: Dongming Jiang, Yi Li, Guanpeng Li, Bingzhe Li
- **Date**: January 6, 2026
- **Link**: https://arxiv.org/abs/2601.03236
- **Summary**: Proposes representing each memory item across orthogonal semantic, temporal, causal, and entity graphs, with retrieval formulated as policy-guided traversal. Achieves up to 45.5% higher reasoning accuracy on long-context benchmarks while reducing token consumption by over 95%. Highly relevant to our dual-store architecture -- the multi-graph decomposition maps naturally onto our Neo4j projection layer.

### 1.3 A-MEM: Agentic Memory for LLM Agents

- **Authors**: Wujiang Xu, Zujie Liang, Kai Mei et al.
- **Date**: February 17, 2025 (revised through 2026)
- **Link**: https://arxiv.org/abs/2502.12110
- **Summary**: Introduces a Zettelkasten-inspired agentic memory system that dynamically organizes memories through interconnected knowledge networks with structured attributes (contextual descriptions, keywords, tags). Memory evolution allows new memories to trigger updates to existing ones. Relevant to our design for how memories should be linked and evolved in the graph -- provides a concrete model for memory interconnection beyond simple retrieval.

---

## Cluster 2: Agent Memory Architectures -- Tiers, Types, Decay

### 2.1 Memory in the Age of AI Agents: A Survey

- **Authors**: Yuyang Hu et al. (47 authors)
- **Date**: December 15, 2025
- **Link**: https://arxiv.org/abs/2512.13564
- **Summary**: A 102-page survey introducing a unified framework for agent memory through three lenses: Forms (token-level, parametric, latent), Functions (factual, experiential, working memory), and Dynamics (formation, evolution, retrieval). Proposes a finer-grained taxonomy beyond simple short/long-term distinctions. Essential reference for our memory tier design -- the Forms/Functions/Dynamics framework provides the conceptual scaffolding for our memory architecture ADRs.

### 2.2 Rethinking Memory Mechanisms of Foundation Agents in the Second Half: A Survey

- **Authors**: Wei-Chieh Huang et al. (60 authors)
- **Date**: January 14, 2026 (revised February 9, 2026)
- **Link**: https://arxiv.org/abs/2602.06052
- **Summary**: Examines agent memory along three dimensions: memory substrate (internal/external), cognitive mechanism (episodic, semantic, sensory, working, procedural), and memory subject (agent-centric vs. user-centric). Addresses context explosion and the need for selective reuse across extended interactions. Directly informs how we should categorize memory types in our event schema and which cognitive mechanisms to prioritize.

### 2.3 Position: Episodic Memory is the Missing Piece for Long-Term LLM Agents

- **Authors**: Mathis Pink, Qinyuan Wu, Vy Ai Vo, Javier Turek, Jianing Mu, Alexander Huth, Mariya Toneva
- **Date**: February 10, 2025
- **Link**: https://arxiv.org/abs/2502.06975
- **Summary**: A position paper arguing that episodic memory -- supporting single-shot learning of instance-specific contexts -- is critical for long-term agents. Defines five key properties of episodic memory that underlie adaptive, context-sensitive behavior. Relevant to our event-ledger design: our immutable event records are essentially episodic memories, and this paper provides the theoretical grounding for why that approach is sound.

---

## Cluster 3: Neuroscience-Inspired Memory Patterns for AI

### 3.1 AI Meets Brain: A Unified Survey on Memory Systems from Cognitive Neuroscience to Autonomous Agents

- **Authors**: (Multiple authors, collaborative survey)
- **Date**: December 29, 2025
- **Link**: https://arxiv.org/abs/2512.23343
- **Summary**: Systematically synthesizes interdisciplinary knowledge connecting cognitive neuroscience with LLM-driven agents. Covers memory taxonomy, storage mechanisms, and the complete management lifecycle from both biological and artificial perspectives. Describes hippocampal-neocortical consolidation where new information converges in the hippocampus for integration before gradually consolidating to neocortical networks. Foundational reference for bridging neuroscience memory models to our graph-based architecture.

### 3.2 HiMeS: Hippocampus-inspired Memory System for Personalized AI Assistants

- **Authors**: Hailong Li, Feifei Li, Wenhui Que, Xingyu Fan
- **Date**: January 6, 2026
- **Link**: https://arxiv.org/abs/2601.06152
- **Summary**: An AI-assistant architecture fusing short-term and long-term memory inspired by hippocampus-neocortex mechanisms. Uses reinforcement learning to train a short-term memory extractor that compresses recent dialogue and proactively pre-retrieves documents, emulating hippocampus-prefrontal cortex cooperation. Directly applicable to our projection worker design -- the hippocampal model maps to our Postgres-to-Neo4j consolidation pipeline.

### 3.3 HiCL: Hippocampal-Inspired Continual Learning

- **Authors**: (Research team, 2025)
- **Date**: August 2025
- **Link**: https://arxiv.org/abs/2508.16651
- **Summary**: A dual-memory continual learning architecture mitigating catastrophic forgetting using hippocampal circuitry: grid-cell-like encoding, sparse pattern separation via a dentate gyrus-inspired module, and episodic memory traces in a CA3-like autoassociative memory. Cortical outputs consolidated using Elastic Weight Consolidation weighted by inter-task similarity. Provides concrete mechanisms for memory consolidation and decay that we can adapt for our memory evolution strategies.

---

## Cross-Cutting Themes

1. **Multi-graph decomposition**: Multiple papers (MAGMA, Graph-based Agent Memory survey) converge on using orthogonal graph views (semantic, temporal, causal, entity) rather than a monolithic graph.
2. **Memory lifecycle**: Consistent decomposition into formation/extraction, storage/organization, retrieval, and evolution/consolidation stages.
3. **Episodic vs. semantic memory**: Strong consensus that both are needed -- episodic for context-specific recall, semantic for generalized knowledge.
4. **Hippocampal-cortical consolidation**: The biological model of fast hippocampal encoding followed by slow neocortical consolidation maps naturally onto event-ledger (fast write) to graph-projection (consolidated query store).
5. **Active forgetting**: Memory decay is not passive loss but active pruning based on relevance, recency, and utility -- directly applicable to graph node lifecycle management.
