# Context Graph — Video Narration Script (v5)

**Format:** Animated React presentation (screen record at 1920x1080)
**Duration:** ~15-16 minutes (15 slides)
**Audience:** Stakeholders / Investors / Technical Leadership
**Tone:** Professional and composed, with a clear narrative arc — authoritative but accessible

---

## Slide 1: Title (0:00 – 0:40)

**[NARRATION]**

> "Welcome. Today I want to walk you through something we have been building — a system called Context Graph. At its core, Context Graph provides structured, traceable memory for AI agents. Not the kind of memory that relies on dumping information into a vector database. This is memory with provenance — memory that records *why* something happened, *who* was involved, and can trace every piece of context back to the event that produced it."

**[SPEAKER NOTES]**
- Allow the title animation to fully resolve before speaking
- Tone: confident and composed — you are introducing a serious piece of infrastructure
- Pause briefly after "memory with provenance" for emphasis
- The three tags (Traceable, Immutable, Intelligent) should be visible by the time you finish

---

## Slide 2: The Problem (0:40 – 1:30)

**[NARRATION]**

> "To understand why we built this, consider a pattern that is remarkably common across every AI agent on the market today."

> "When a user starts a new session with an agent — a chatbot, a copilot, a support assistant — the agent has no recollection of prior interactions. All of the context from previous sessions is effectively lost."

> "But the problem runs deeper than session continuity. Even *within* a single session, when an agent retrieves context to generate a response, there is no way to trace where that context originated. No provenance chain. No audit trail back to the source event."

> "And then there is personalization. The agent interacts with Sarah — an engineering lead who prefers concise, technical communication — in exactly the same way it interacts with a first-time user. It does not learn preferences. It does not adapt."

> "We set out to solve all three of these problems. Not with workarounds, but with a well-considered architecture."

**[SPEAKER NOTES]**
- Each card animates in — time your words to match
- "Agents Forget" card appears first — address session amnesia
- "No Traceability" card — pivot to the provenance gap
- "No Personalization" card — ground it with the Sarah example (she is a character in the demo)
- Close with the architectural commitment to create narrative tension
- This is the *empathy* slide — the audience should be recognizing these problems from their own experience

---

## Slide 3: Research Foundations (1:30 – 3:15)

**[NARRATION]**

> "Before writing any code, we conducted an extensive review of the research literature. What we found was striking — there has been a significant acceleration in agent memory research, particularly from late 2025 into early 2026. Twelve papers ultimately shaped nearly every design decision in this system."

> *[gesture toward first column]*
> "The first cluster addresses graph-based memory. Chang Yang and eighteen co-authors published a comprehensive survey in February 2026 identifying five distinct graph structures and a four-stage memory lifecycle. MAGMA, by Jiang et al., was perhaps the most directly influential — they constructed a multi-graph architecture with four orthogonal views (temporal, causal, semantic, entity) and demonstrated a 45% improvement in reasoning accuracy. A-MEM, presented at NeurIPS, introduced a Zettelkasten-inspired approach to memory notes that evolve bidirectionally."

> *[gesture toward second column]*
> "The second cluster covers broader agent memory architectures. Hu et al. assembled a 102-page survey with forty-seven contributing authors — they developed a unified framework organized around memory Forms, Functions, and Dynamics. Huang et al., with sixty co-authors, derived what became the foundation of our scoring system: recency, importance, and relevance as the three primary retrieval factors."

> *[gesture toward third column]*
> "The third cluster draws from neuroscience. Liang et al. established a direct bridge between cognitive neuroscience and AI agent design. The central concept is Complementary Learning Systems theory — CLS — which describes how the brain maintains two fundamentally different memory systems that work in concert. We will examine this in detail on the next slide. HiMeS demonstrated that a dual-memory architecture outperforms single-store systems by 55%."

> *[gesture toward fourth column]*
> "Finally, there are the production systems — Zep, Mem0, Memoria — that validated these patterns at scale. Zep achieves P95 retrieval latency under 300 milliseconds. Memoria reaches 87% accuracy."

> "What ultimately motivated us to build Context Graph is a clear gap in this landscape: *no existing system* combines immutable event sourcing with graph-based lineage and provenance-annotated retrieval. Individual systems implement one or two of these capabilities. None implement all three."

**[SPEAKER NOTES]**
- This is the longest narration section — you are telling a story of rigorous investigation
- Do not rush the paper references. The audience needs to appreciate the depth of the research foundation
- The "forty-seven authors" and "sixty co-authors" details should register as notable — they convey the maturity of this field
- When mentioning MAGMA's influence, maintain a measured tone — share it as a considered assessment
- The concluding gap analysis should feel like an evidence-based finding, not a sales pitch
- If the audience is non-technical, abbreviate the paper details and focus on the findings
- Pacing: approximately 20 seconds per cluster, 15 seconds for the summary

---

## Slide 4: Neuroscience Foundation (3:15 – 5:15)

**[NARRATION]**

> "Let me elaborate on the neuroscience mapping, because it is not merely an analogy. The correspondence between biological memory systems and our architecture is surprisingly precise."

> "The hippocampus is the brain's fast-learning system. When an experience occurs, the hippocampus encodes it almost instantly. What is often underappreciated is that it does not store the complete memory — it stores *pointers*. Sparse indices that can reactivate patterns across other brain regions. This is precisely what Redis does in our system. When an event arrives, Redis appends it to a stream in sub-millisecond time. The stream entry ID serves as the sparse pointer. The full event payload resides in a JSON document. It is fast, append-only, and it never modifies what has already been written."

> "The neocortex operates differently — it is slow, deliberate, and focused on constructing stable long-term knowledge. It takes individual experiences and consolidates them into general understanding: entities, relationships, patterns. That is our Neo4j graph. It does not attempt to store every raw event. It stores the *meaning* that emerges from events over time."

> "The critical process occurs between these two systems. In neuroscience, it is called *systems consolidation* — the hippocampus replays memories, gradually transferring structure to the neocortex. In our architecture, this role is filled by four consumer workers that continuously read from Redis Streams and project, enrich, extract, and consolidate into Neo4j. This is not a batch ETL process — it is continuous replay, directly paralleling the biological mechanism."

> "We also adopted the Ebbinghaus forgetting curve — published in 1885 — where R equals e to the negative t over S, and S represents stability. Each time a memory is accessed, S increases. The memory becomes more resistant to decay. Our default configuration uses a 168-hour base stability — one week — with a 24-hour boost per retrieval. A piece of context accessed daily will effectively persist indefinitely."

> "There is one additional mapping worth highlighting. Kapoor et al. traced the hippocampal circuit — the four regions EC, DG, CA3, and CA1 — to specific software operations. Grid-cell encoding corresponds to our event ingestion. Pattern separation, the mechanism by which the brain ensures distinct memories remain distinct, corresponds to our UUIDs and rich provenance metadata. Pattern completion, where a partial cue triggers full recall, corresponds to our lineage queries. Given a single node, we can traverse the graph to reconstruct the complete context."

**[SPEAKER NOTES]**
- This slide carries the most conceptual depth — maintain a measured, explanatory pace
- Open with "not merely an analogy" to address any skepticism directly
- The hippocampus/pointer correspondence is the single most important concept — ensure it is clearly communicated
- When explaining Redis as hippocampus, gesture toward the left side of the screen where the mapping appears
- The Ebbinghaus formula: allow it to remain on screen. Convey the intuition rather than explaining every variable
- The hippocampal circuit mapping (EC, DG, CA3, CA1) is detailed — for non-technical audiences, gauge engagement and consider abbreviating
- Vocal quality should convey intellectual engagement — this is the section where the depth of the research becomes evident

---

## Slide 5: Industry Gap Analysis (5:15 – 6:30)

**[NARRATION]**

> "We conducted a systematic review of every major agent framework currently available — LangSmith, CrewAI, AutoGen, OpenAI's Agents SDK, Semantic Kernel — and evaluated each against three criteria."

> "Does it maintain an immutable event ledger — a true append-only source of truth? None of them do."

> "Does it annotate retrieved context with provenance, enabling traceability back to the original event? No."

> "Does it support graph-based lineage queries, allowing questions like 'why did this happen?' to be answered through causal chain traversal? Also no."

> "What these frameworks *do* provide is observability — and they provide it well. Run trees, spans, metrics, trace visualization. But observability and memory are fundamentally different capabilities. Observability tells you what happened in the past. Memory uses the past to improve the future. That distinction defines the gap we are addressing."

> "On the right side of the slide, you can see our alignment with established standards. We have not invented proprietary conventions. We use OpenTelemetry for span semantics, W3C PROV for provenance modeling, event sourcing patterns from the Axon and Marten ecosystem, and SKOS for entity resolution taxonomies. The benchmarks from architecturally adjacent systems are also encouraging — MAGMA's 45% reasoning improvement, Memoria's 87% retrieval accuracy."

**[SPEAKER NOTES]**
- The comparison table is the focal point of this slide. Allow the audience time to read it.
- Deliver the three "no" answers with measured emphasis — factual, not dismissive of competitors
- The distinction between observability and memory is a KEY INSIGHT — slow down here
- "Observability tells you what happened. Memory uses the past to improve the future." — This is the most quotable line in the presentation. Pause after it.
- Do not spend excessive time on standards — they are present for credibility, not excitement
- The benchmarks provide validation — mention them concisely

---

## Slide 6: The Solution (6:30 – 7:15)

**[NARRATION]**

> "With that research and gap analysis as context, let me describe what we built."

> "Context Graph operates in four stages, each mapping directly to the research we have just discussed."

> "Stage one: Capture. Every action an agent takes — a user message, a tool invocation, a decision — becomes an immutable event. It enters Redis, receives a global position, and is never modified."

> "Stage two: Project. Those events are projected into a knowledge graph comprising eight node types — Events, Entities, Summaries, User Profiles, Preferences, Skills, Workflows, and Behavioral Patterns — connected by sixteen edge types."

> "Stage three: Enrich. This is where the consumer workers operate. Entities are extracted, embedding vectors are computed, semantic similarity edges form, and user preferences and skills are identified."

> "Stage four: Retrieve. When an agent requires context, the system classifies the intent of the query — is it asking 'why?', 'when?', 'what?', 'who?' — and traverses the graph with edge weights tuned to that intent. Every node returned carries full provenance."

**[SPEAKER NOTES]**
- This should feel like a deliberate pivot from research to implementation — the energy becomes more concrete
- "With that research and gap analysis as context" — acknowledge the deep dive and signal the transition
- If recording video, count the stages with your hand
- The four animated rows slide in from the left — time each explanation to match the animation
- "And is never modified" — brief pause for emphasis
- Counter animations on the right (8, 16, 8, 4) should be resolving as you conclude

---

## Slide 7: Cognitive Memory Architecture (7:15 – 8:30)

**[NARRATION]**

> "Let me now show how the five cognitive memory types from the research map to concrete system components. This is where the neuroscience becomes engineering."

> "Sensory memory is the initial capture buffer. In the brain, sensory information persists for a fraction of a second before being processed or discarded. In our system, it corresponds to the Redis Streams XADD pipeline. Events arrive, are deduplicated by a Lua script, and are either processed into the next stage or not. This operates at millisecond latency."

> "Working memory is what you are actively processing at any given moment. George Miller's well-known capacity limit of seven items, plus or minus two. Our equivalent is the Neo4j hot tier — everything from the last 24 hours, at full detail, with all edges intact. When an agent is in a conversation, this is the context pool it draws from. We enforce bounded queries — a maximum of 100 nodes at depth 3 — which mirrors that cognitive constraint."

> "Episodic memory is the most significant mapping. It is your autobiography — specific events, in chronological order, with full context. The Redis event ledger is precisely this: append-only, immutable, ordered by global position. Every event carries a timestamp, session ID, agent ID, and trace ID. Any session can be replayed from the beginning."

> "Semantic memory represents what you *know* — facts, relationships, concepts — independent of the specific experience where you acquired them. That is the Neo4j graph after consolidation. Entities exist independently of the events that created them. Summaries abstract the underlying detail."

> "Procedural memory encompasses what you know how to *do* without conscious effort. For agents, these are Workflow nodes and BehavioralPattern nodes — recurring sequences detected across sessions and stored as first-class graph objects."

> "What is particularly compelling about this mapping is that it was not imposed. We did not begin by attempting to replicate the brain. We began with engineering requirements, built the system, and subsequently discovered that the neuroscience literature was describing almost exactly what we had arrived at independently. The research validated the architecture."

**[SPEAKER NOTES]**
- Walk through each row as the animations play
- Miller's "seven plus or minus two" is widely recognized — mention it with confidence, without over-explaining
- The episodic memory section should be the most deliberate — it represents the core differentiator
- The final paragraph about independent convergence is important for credibility — it demonstrates intellectual rigor rather than post-hoc narrative construction
- Direct attention to the bottom bar showing Redis = Hippocampus, Neo4j = Neocortex, Workers = Consolidation

---

## Slide 8: Memory Consolidation Pipeline (8:30 – 10:00)

**[NARRATION]**

> "Let me now walk through how memories actually *form* within the system. This is not a simple event-in, graph-out process. There are four distinct stages, each running as an independent process."

> "Consumer 1 is the foundation — Graph Projection. It operates in real time, processing every event as it arrives. An event enters through Redis, and within milliseconds, a corresponding node exists in Neo4j. It creates FOLLOWS edges for temporal ordering and CAUSED_BY edges when explicit causality is present. No language model is required. This is pure structural projection."

> "Consumer 3 — and I am presenting these out of numerical order because this reflects the actual pipeline flow — handles Enrichment. It operates in batches, extracting keywords from event payloads, computing 384-dimensional embedding vectors, and creating SIMILAR_TO edges between events whose cosine similarity exceeds 0.85. It also identifies entity mentions and creates REFERENCES edges. This is the stage where the graph becomes considerably more valuable, because events from entirely separate sessions can now be connected semantically."

> "Consumer 2 is the LLM-powered stage — Session Extraction. It triggers when a session concludes. The language model examines the full conversation and extracts entities, preferences, skills, and interests. It then executes three-tier entity resolution to determine whether 'QuickBooks,' 'QB,' and 'QBO' refer to the same thing — we will examine that process in detail shortly. Every extracted node receives a DERIVED_FROM edge back to its source events, maintaining the provenance chain."

> "Consumer 4 handles Re-Consolidation. It runs on a six-hour schedule, grouping events into episodes using 30-minute gap detection, creating hierarchical summaries, and recomputing importance based on graph centrality. It also performs what we call active forgetting — it removes low-importance, rarely-accessed nodes. Not because of storage constraints, but because a pruned graph produces higher-quality results. Less noise, higher signal."

> "Two additional details are worth noting. Consolidation does not operate on a fixed timer — it triggers when accumulated importance crosses a threshold, approximately 15 high-importance events. This approach comes directly from Park et al.'s Generative Agents paper. And when a node is *retrieved* — when it is used to generate a response — its stability increases. The act of remembering strengthens the memory. That is biological reconsolidation, and we implement it in the system."

**[SPEAKER NOTES]**
- This is the most technically dense slide. Guide the audience through it deliberately.
- Acknowledge the out-of-order numbering explicitly so it does not appear to be a mistake
- "The graph becomes considerably more valuable" — this is the moment to show measured enthusiasm
- The "active forgetting" concept should register as unexpected. Pause briefly before and after introducing it.
- The reconsolidation insight at the close connects back to the neuroscience foundation — this is the intellectual payoff
- If the audience appears fatigued, abbreviate Consumers 2 and 4 and focus on the reconsolidation insight

---

## Slide 9: Architecture Patterns (10:00 – 11:15)

**[NARRATION]**

> "Let me step back from the specifics and discuss the engineering patterns that underpin the system."

> "We employ hexagonal architecture — also known as ports and adapters. The domain core — scoring, intent classification, lineage traversal, validation — has zero imports from FastAPI or any web framework. Ten of eleven domain modules are pure Python with typing.Protocol interfaces. This means you could replace FastAPI with Django or Flask or any future framework, and the domain layer would require no changes. You could substitute Redis for Postgres or Neo4j for an alternative graph database, and the domain layer would still require no changes. This is not a theoretical benefit — it is a deliberate design constraint."

> "The write path follows pure event sourcing. Events are written to Redis, deduplicated by a Lua script, and that is the end of the write operation. The event is the source of truth. Everything else is derived."

> "The read path follows CQRS — Command Query Responsibility Segregation — and is completely independent. A query passes through intent classification, seed node selection, weighted graph traversal, and decay scoring, then returns an Atlas response with nodes, edges, pagination, and full metadata. The write path and read path share no state."

> "The dual store — Redis plus Neo4j — is not an arbitrary choice. It maps directly to CLS theory. Redis serves as the hippocampus: fast, episodic. Neo4j serves as the neocortex: slow, semantic. The projection workers are systems consolidation."

> "The graph itself is not a single structure — it is five overlapping views. The temporal view operates through FOLLOWS edges. The causal view through CAUSED_BY. Semantic through SIMILAR_TO. Entity through REFERENCES. Hierarchical through SUMMARIZES. The same underlying data, five distinct perspectives. When a query arrives, the intent determines which edges receive amplified weight. A 'why?' question weights CAUSED_BY edges five times higher. A 'when?' question weights FOLLOWS. The same graph produces fundamentally different results depending on how the question is framed."

**[SPEAKER NOTES]**
- "Zero imports from FastAPI" is a strong architectural claim — deliver it with quiet confidence
- The framework substitution example makes the abstraction concrete for non-technical listeners
- CQRS can lose less technical audiences — keep it high-level: "the write path and read path share no state"
- The five graph views section is visually rich — allow the audience to read the visual while you explain
- "The same graph produces fundamentally different results" should be the defining moment of this slide
- Energy level: measured and assured. This is clean engineering and you know it.

---

## Slide 10: Entity Reconciliation (11:15 – 12:15)

**[NARRATION]**

> "One of the most persistent challenges in any knowledge system is determining when two references denote the same entity. When one session mentions 'QuickBooks,' another says 'QB,' and a third says 'QBO' — is that one entity or three?"

> "We address this with a three-tier cascade. Each tier applies progressively more sophisticated matching, and they execute in sequence until a match is found."

> "Tier 1 is straightforward — exact match after normalization. We maintain an alias dictionary. 'QB,' 'QBO,' and 'QuickBooks Online' all resolve to the canonical entity 'QuickBooks.' On an exact hit, confidence is 1.0, and we merge into the existing entity node."

> "Tier 2a engages when exact match fails. It applies fuzzy string comparison using SequenceMatcher at the character level. If 'React.js' versus 'ReactJS' scores above 0.9, we do not merge — we create a SAME_AS edge. This is a softer assertion: 'these are very likely the same entity, at 92% confidence.' If the entity types differ, the relationship becomes RELATED_TO instead."

> "Tier 2b applies semantic matching. We compare embedding vectors. 'Payment processing' and 'billing system' share no character-level similarity but are conceptually proximate. If cosine similarity exceeds 0.90, a SAME_AS edge is created. Above 0.75, RELATED_TO. Semantic matches are designed to never produce a hard merge — the confidence ceiling is intentionally lower."

> "If all three tiers fail to find a match, we create a new entity. And — this is a point I want to emphasize — every entity, whether merged, linked, or newly created, carries a DERIVED_FROM edge back to its source events. You can always trace an entity to the moment it was first mentioned."

**[SPEAKER NOTES]**
- Open with the problem statement ("QuickBooks vs QB") — it is immediately relatable
- The alias dictionary examples should feel drawn from real usage scenarios
- "Straightforward" for Tier 1 demonstrates that you value simplicity where it is appropriate
- "A softer assertion" for SAME_AS clearly explains the distinction from MERGE
- The provenance point at the close reinforces the central theme of the entire presentation
- Allow the audience to trace the cascade flow diagram at the bottom of the slide

---

## Slide 11: FE Shell Demo (12:15 – 13:30)

*Click through 6 sub-steps at a measured pace*

**[NARRATION]**

> "With the architecture covered, let me demonstrate what this looks like in operation."

> "This is the FE Shell — our demonstration interface. It is organized as three panels: chat on the left, graph visualization in the center, and contextual insights on the right."

> *[Click step 1]*
> "Sarah initiates a support conversation, reporting a duplicate charge. The first Event node appears in the graph — a blue circle. An Entity node for Sarah appears as a green triangle."

> *[Click step 2]*
> "The agent performs a billing lookup. A second Event node appears, connected by a FOLLOWS edge representing temporal sequence. A Billing entity appears, linked by a REFERENCES edge."

> *[Click step 3]*
> "Sarah provides additional details about the charges. The graph continues expanding. On the right, the Context panel now displays which nodes were retrieved for this response: Sarah Chen at relevance 0.95, billing lookup at 0.91, each tagged with a retrieval reason — 'direct,' 'causal,' 'referenced.'"

> *[Click step 4]*
> "The agent initiates a refund. A Refund entity appears, connected to Billing by a RELATED_TO edge. Note the context node count increasing — four nodes contributed to this response."

> *[Click step 5]*
> "Sarah mentions that she prefers email communication. This is where personalization becomes visible. Switch to the User tab — you can observe her profile forming in real time. Preferences: email communication. Skills: engineering lead. Patterns: deep work blocks."

> *[Click step 6]*
> "On the Scores tab, the radar chart displays how each context node scored across the four factors: recency 92, importance 78, relevance 88, user affinity 65. This is the decay scoring system we discussed, operating in real time."

**[SPEAKER NOTES]**
- "With the architecture covered" signals a clear transition — the audience should feel the shift to demonstration
- Click each step deliberately. Allow the animation to resolve before narrating.
- For each step, direct attention explicitly: "note the Context panel...", "switch to the User tab..."
- The preference capture at step 5 is the emotional highlight — this is where memory *visibly functions*
- The radar chart at step 6 closes the loop back to the scoring formula from earlier slides
- Allow 2-3 seconds of silence between clicks for the visuals to register

---

## Slide 12: Persona Simulations (13:30 – 14:15)

**[NARRATION]**

> "Sarah is one of three personas we developed for the demonstration. Each illustrates a different dimension of how context accumulates and shapes agent behavior."

> "Sarah Chen, engineering lead — the system learns that she prefers email over phone, works in focused blocks, and does not require detailed explanations of technical concepts. By her third session, the agent is already adjusting tone, channel, and depth accordingly."

> "Mike Torres, product manager — he works in Kanban, communicates asynchronously, and consistently requests data to support decisions. The system begins proactively surfacing metrics and prior feature decisions during his planning conversations."

> "Lisa Park, customer success — her interactions tend to involve urgency. The system detects an escalation pattern across sessions and begins fast-tracking her responses and flagging potential incidents earlier."

> "The key insight: the same system, the same graph, the same scoring — but the context retrieved is entirely different for each person, because their graph profiles are different."

**[SPEAKER NOTES]**
- Allocate approximately equal time to each persona (~15 seconds each)
- The concluding insight ("same system, different context") is the statement that should resonate
- For an investor audience, emphasize the *scalability* of personalization — this approach works for thousands of users
- Gesture toward each persona card as you discuss them

---

## Slide 13: Decay & Forgetting (14:15 – 15:00)

**[NARRATION]**

> "Let me conclude the technical discussion by showing how memory ages within the system. On the left, the Ebbinghaus curve in action. The blue line represents natural decay with a 168-hour half-life — after one week without access, a memory retains approximately 37% of its strength. The green dashed line shows the effect of re-access: the stability parameter increases and the curve resets at a higher level."

> "Below that, the retention tier architecture. There are *two independent systems* operating in parallel. Neo4j maintains four tiers — hot, warm, cold, archive — each with distinct pruning rules. Redis maintains three — hot, cold, expired. They operate on different timelines because they serve different purposes. Neo4j optimizes for query performance. Redis optimizes for durability."

> "On the right, the composite scoring formula. Four factors, each weighted: recency, importance, and relevance at weight 1.0; user affinity at 0.5 as the differentiating factor — the factor that determines relevance *to a specific individual*. Together, they produce the single score that determines which context surfaces."

**[SPEAKER NOTES]**
- The decay curve should remain visible throughout — reference specific portions as you explain
- "Two independent systems" is an architectural subtlety that conveys sophistication — do not skip it
- The formula displayed in monospace is present for credibility. There is no need to read each variable.
- Pacing: this is a concluding section — slightly calmer, wrapping up the technical narrative

---

## Slide 14: Differentiators (15:00 – 15:30)

**[NARRATION]**

> "Let me summarize the six capabilities that distinguish Context Graph from the existing landscape."

> "Full provenance — every context node traces back to its source event. Immutable ledger — the event store is append-only, and the graph is a disposable, rebuildable projection. Framework agnostic — zero coupling to any specific AI framework. Proactive context — the system surfaces relevant information *before* it is requested. GDPR ready — user data export and deletion are built in from the foundation. And intent-weighted retrieval — 'why?' and 'when?' queries follow entirely different paths through the graph."

**[SPEAKER NOTES]**
- This is delivered at a brisk pace — one sentence per differentiator
- The six cards are already on screen. Reference each one briefly.
- "Disposable, rebuildable projection" — that phrase consistently generates interest. Allow it to land.
- "Before it is requested" for proactive context is the compelling detail
- Do not linger — the closing follows immediately

---

## Slide 15: Closing (15:30 – 16:00)

**[NARRATION]**

> "Context Graph provides AI agents with the memory they deserve. Traceable. Intelligent. Personalized."

> "We built it on a foundation of twelve research papers, grounded in cognitive science, and engineered for production. This is not a prototype. This is not a proof of concept. This is a system designed to scale."

> "Thank you. I would welcome your questions."

**[SPEAKER NOTES]**
- Slow down. This is the conclusion.
- "Traceable. Intelligent. Personalized." — three beats, three pauses
- "This is not a prototype" should convey measured conviction
- "I would welcome your questions" — direct eye contact with camera or audience
- Allow the slide to remain on screen for 3-5 seconds after you stop speaking

---

## Complete Slide Inventory

| # | Slide | Duration | Type | Energy |
|---|-------|----------|------|--------|
| 1 | Title | 40s | Intro | Composed, confident |
| 2 | The Problem | 50s | Motivation | Measured empathy |
| 3 | **Research Foundations** | 105s | **Research** | Intellectual rigor |
| 4 | **Neuroscience Foundation** | 120s | **Research** | Engaged expertise |
| 5 | **Industry Gap Analysis** | 75s | **Research** | Analytical, evidence-based |
| 6 | The Solution | 45s | Overview | Clear pivot to implementation |
| 7 | Memory Types | 75s | Architecture | Explanatory, authoritative |
| 8 | Consolidation | 90s | Architecture | Technically precise, guided |
| 9 | Architecture Patterns | 75s | Architecture | Quiet confidence |
| 10 | Entity Resolution | 60s | Architecture | Methodical problem-solving |
| 11 | FE Shell Demo | 75s | Demo (6 steps) | Purposeful demonstration |
| 12 | Personas | 45s | Use Cases | Practical impact |
| 13 | Decay & Forgetting | 45s | Architecture | Composed wrap-up |
| 14 | Differentiators | 30s | Summary | Brisk, confident |
| 15 | Closing | 30s | CTA | Measured conviction |

**Total: ~15-16 minutes with pauses and breathing room**

---

## Papers Referenced

**Slide 3 — Research Foundations:**
- Yang et al. (Feb 2026) — Graph-based Agent Memory Survey [2602.05665]
- Jiang et al. (Jan 2026) — MAGMA [2601.03236]
- Xu et al. (Feb 2025) — A-MEM, NeurIPS [2502.12110]
- Hu et al. (Dec 2025) — Memory in the Age of AI Agents (102pp, 47 authors) [2512.13564]
- Huang et al. (Feb 2026) — Rethinking Memory Mechanisms (60 authors) [2602.06052]
- Pink et al. (Feb 2025) — Episodic Memory is the Missing Piece [2502.06975]
- Liang et al. (Dec 2025) — AI Meets Brain [2512.23343]
- Li et al. (Jan 2026) — HiMeS [2601.06152]
- Kapoor et al. (Aug 2025) — HiCL [2508.16651]
- Zep/Graphiti (Jan 2025) [2501.13956]
- Mem0 (ECAI 2025) [2504.19413]
- Memoria (Dec 2025) [2512.12686]

**Slide 4 — Neuroscience Foundation:**
- Complementary Learning Systems (CLS) theory
- Ebbinghaus Forgetting Curve (1885)
- Hippocampal circuit: EC → DG → CA3 → CA1 (Kapoor et al.)
- Park et al. 2023 — Generative Agents reflection threshold

**Slide 5 — Industry Gap:**
- OpenTelemetry GenAI conventions
- W3C PROV-DM
- SKOS / SSSOM entity resolution standards

---

## Recording Guide

### Setup
1. **Resolution:** 1920x1080 minimum. 2560x1440 if your monitor supports it.
2. **Browser:** Chrome, full-screen (F11). Hide bookmarks bar.
3. **Audio:** External microphone recommended. Record in a quiet room. Pop filter helps.
4. **Lighting:** If recording face, soft front light. Avoid overhead fluorescents.

### Controls
- **Arrow keys / Spacebar:** Advance slides
- **'A' key:** Toggle auto-play (useful for rehearsal, not recommended for final recording)
- **Slide 11 (Demo):** Has 6 sub-steps. Click through each one deliberately.

### Recording Strategy
- **Option A (Recommended):** Screen record with OBS Studio (free). Record narration as a separate audio track. Mix in post with Audacity or DaVinci Resolve.
- **Option B:** Use Loom or ScreenFlow for simultaneous screen + voiceover. Simpler but less control.
- **Option C:** Record screen silently, then record voiceover to the playback in a second pass.

### Pacing Advice
- **Slides 1-2:** Composed warmth. Establish the context.
- **Slides 3-5 (Research):** This is the conceptual foundation. Take your time. The audience needs to appreciate the depth of research before seeing the system.
- **Slides 6-10 (Architecture):** Explanatory mode. Be the guide. Direct attention to specific elements on screen.
- **Slide 11 (Demo):** Let the visuals carry the weight. 2-3 seconds of silence between clicks is appropriate.
- **Slides 12-15:** Concluding energy. Slightly brisker pace, building to a composed, confident close.

### Post-Production
- Add subtle ambient music under slides 1-5 (research section). Fade out for demo.
- Consider lower-third titles for paper citations on slides 3-4.
- Trim any dead air over 3 seconds.
- Add a 2-second black fade at the end.
