# ADR-0001 Industry Precedents Research Report

**Date:** 2026-02-07
**Status:** Complete
**Purpose:** Validate and inform ADR-0001 (Traceability-First Context Graph) by surveying industry standards, tools, and patterns for traceability, provenance, event sourcing, and agent observability.

---

## Table of Contents

1. [OpenTelemetry and Distributed Tracing](#1-opentelemetry-and-distributed-tracing)
2. [W3C PROV Standard](#2-w3c-prov-standard)
3. [Event Sourcing Systems](#3-event-sourcing-systems)
4. [AI/ML Lineage Tools](#4-aiml-lineage-tools)
5. [Agent-Specific Observability](#5-agent-specific-observability)
6. [Cross-Cutting Themes](#6-cross-cutting-themes)
7. [Recommendations for ADR-0001](#7-recommendations-for-adr-0001)

---

## 1. OpenTelemetry and Distributed Tracing

### Overview

OpenTelemetry (OTel) is the dominant open standard for distributed tracing, providing a vendor-neutral framework for collecting traces, metrics, and logs. Its data model is directly relevant to ADR-0001's event schema design.

### Data Model

OTel structures observability data around three core concepts:

- **Trace**: Represents the full journey of a request/transaction across services. Identified by a unique `trace_id`.
- **Span**: A timed unit of work within a trace. Each span has a `span_id`, optional `parent_span_id`, `trace_id`, start/end timestamps, attributes (key-value metadata), events (timestamped log entries within the span), and status.
- **Context Propagation**: The mechanism that correlates spans across service boundaries. Uses W3C TraceContext headers (`traceparent`, `tracestate`) by default. Involves injection (serializing context into outbound headers) and extraction (deserializing from inbound requests).

### GenAI Semantic Conventions (Development Status)

OTel has introduced GenAI-specific semantic conventions that are directly relevant:

- **`create_agent` span**: Documents agent creation (typically for remote agent services like OpenAI Assistants, AWS Bedrock Agents).
- **`invoke_agent` span**: Captures agent invocation with attributes for `gen_ai.agent.name`, `gen_ai.agent.id`, `gen_ai.conversation.id` (session/thread), `gen_ai.data_source.id` (RAG sources), and token usage metrics.
- **Tool execution**: Captured as child spans within agent invocation spans.
- **Content recording**: Optional attributes for `gen_ai.input.messages`, `gen_ai.output.messages`, `gen_ai.system_instructions`, and `gen_ai.tool.definitions` -- flagged as potentially containing PII.

### Comparison to ADR-0001 Event Schema

| OTel Concept | ADR-0001 Equivalent | Notes |
|---|---|---|
| `trace_id` | `trace_id` | Direct mapping |
| `span_id` | `event_id` | ADR-0001 uses UUIDs; OTel uses 16-byte hex |
| `parent_span_id` | `parent_event_id` | Direct mapping for causal chains |
| Span `start_time`/`end_time` | `occurred_at`/`ended_at` | Direct mapping |
| Span `attributes` | `payload_ref` + event fields | ADR-0001 separates structured fields from payload |
| Span `status` | `status` | Direct mapping |
| Span `events` | N/A | OTel embeds sub-events in spans; ADR-0001 uses flat event list |
| `service.name` | `agent_id` | Analogous: identifies the emitting entity |
| N/A | `session_id` | ADR-0001 adds session-level grouping |
| N/A | `global_position` (BIGSERIAL) | ADR-0001 adds total ordering for replay |
| N/A | `schema_version` | ADR-0001 adds explicit schema versioning |

### Key Takeaways

1. **ADR-0001's event schema is well-aligned with OTel's span model** -- the core fields (`trace_id`, `parent_event_id`, timestamps, status) map directly.
2. **ADR-0001 goes beyond OTel** by adding `global_position` for deterministic replay ordering and `schema_version` for evolution -- these are essential for event sourcing that OTel does not require.
3. **OTel's GenAI conventions are still in Development status**, meaning ADR-0001 has an opportunity to define a stable schema for agent traceability before OTel finalizes theirs. However, the project should track OTel GenAI conventions and aim for compatibility.
4. **Context propagation is a solved problem** in OTel. ADR-0001 should adopt the `trace_id` / `parent_event_id` pattern and consider W3C TraceContext-compatible header propagation for agents that communicate over HTTP.

---

## 2. W3C PROV Standard

### Overview

The W3C Provenance Data Model (PROV-DM) is a W3C Recommendation that defines a standard vocabulary for provenance -- "information about entities, activities, and people involved in producing a piece of data or thing, which can be used to form assessments about its quality, reliability or trustworthiness."

### Core Concepts

PROV-DM defines three core types and a set of relationships:

**Types:**
- **Entity**: A thing with fixed aspects (physical, digital, conceptual). Can be real or imaginary.
- **Activity**: Something that occurs over a period of time and acts upon or with entities (consuming, processing, transforming, generating).
- **Agent**: Something that bears responsibility for an activity or entity's existence.

**Key Relations:**
- `wasGeneratedBy`: Entity was produced by an Activity
- `used`: Activity consumed an Entity
- `wasDerivedFrom`: Entity was transformed from another Entity
- `wasAttributedTo`: Entity was ascribed to an Agent
- `wasAssociatedWith`: Activity was driven by an Agent
- `wasInformedBy`: Activity was informed by another Activity (communication)
- `actedOnBehalfOf`: Agent delegation

**Advanced Concepts:**
- **Bundle**: A named set of provenance descriptions -- enables "provenance of provenance"
- **Alternate / Specialization**: Links between entities that refer to the same thing at different levels of detail

### Mapping to Context Graph

| PROV-DM Concept | Context Graph Equivalent | Notes |
|---|---|---|
| Entity | Graph Node (artifact, document, decision) | Outputs produced by agent actions |
| Activity | Event record | Agent/tool actions captured as events |
| Agent | `agent_id` in event schema | The agent or tool performing the action |
| `wasGeneratedBy` | Edge: artifact -> event | Links outputs to producing events |
| `used` | Edge: event -> input entity | Links events to their inputs |
| `wasDerivedFrom` | Edge: output -> input | Transitive derivation chain |
| `wasAssociatedWith` | `agent_id` field on event | Agent responsible for the activity |
| Bundle | Session or trace grouping | A set of provenance for one agent run |

### Key Takeaways

1. **PROV-DM provides a strong conceptual vocabulary** for ADR-0001's provenance goals. The Entity/Activity/Agent triple maps cleanly to the context graph's nodes, events, and agent identifiers.
2. **ADR-0001 should adopt PROV-DM terminology** in its graph projection -- using edge types like `GENERATED_BY`, `USED`, `DERIVED_FROM`, `ATTRIBUTED_TO` rather than inventing ad-hoc relationship names. This aids interoperability and clarity.
3. **The Bundle concept** is relevant for session-level provenance grouping and could support "provenance of provenance" for debugging the system itself.
4. **Full PROV-DM compliance is not necessary for MVP** -- the standard is broad and includes concepts (Alternate, Specialization, Influence) that add complexity. ADR-0001 should adopt the core vocabulary and relations selectively.
5. **PROV-DM validates ADR-0001's approach**: the W3C standard was designed precisely for the use case ADR-0001 targets -- tracking what happened, by whom, and from what sources. This is strong evidence that a traceability-first approach is well-grounded.

---

## 3. Event Sourcing Systems

### Overview

Event sourcing is an architectural pattern where every change to application state is stored as an immutable event in an append-only log. The current state is derived by replaying events. This is directly aligned with ADR-0001's dual-store architecture (Postgres as immutable event ledger, Neo4j as derived projection).

### Key Systems Analyzed

**EventStoreDB**: A purpose-built database for event sourcing. Events are stored in streams (logical groupings), are immutable and append-only, and are ordered by position within their stream and globally. Supports built-in projections that create read models from event streams.

**Axon Framework**: A Java framework for CQRS + event sourcing. Separates command handling (writes) from query handling (reads). Provides built-in support for aggregates (consistency boundaries), event handlers, and sagas (long-running processes).

**Marten (PostgreSQL-based)**: A .NET library that uses PostgreSQL as both event store and document database, demonstrating that Postgres is a viable event store -- directly relevant to ADR-0001's choice of Postgres.

### Patterns for Replay and Projection

1. **Event replay / hydration**: Rebuilding state by sequentially applying all past events. ADR-0001's projection worker (polling Postgres events and UNWIND+MERGE into Neo4j) follows this pattern exactly.
2. **Catch-up subscriptions**: Clients subscribe to an event stream from a given position and receive all subsequent events. ADR-0001's `cursor.py` (tracking the last-processed `global_position`) implements this pattern.
3. **Projection rebuilding**: If the read model is corrupted or schema changes, it can be rebuilt by replaying all events from scratch. ADR-0001's principle that "Neo4j is disposable and rebuildable from Postgres events" directly implements this.

### Schema Evolution Patterns

The industry has converged on several strategies for evolving event schemas without breaking immutability:

1. **Upcasting**: Transform old event formats to new formats at read time. Pure functions without side effects. Run on every deserialization -- simple but can have performance cost for high-volume reads.
2. **Versioned events**: Include a version field (`schema_version` in ADR-0001) and maintain handlers for each version. ADR-0001 already includes this.
3. **Weak schema**: Use a flexible payload format (JSON) that tolerates missing/extra fields. Combined with explicit schema_version for breaking changes.
4. **Copy-and-transform**: Replay old events through a transformer into a new stream. Useful for major migrations but requires downtime or dual-write period.
5. **In-place transformation**: Direct database updates to event payloads -- violates immutability principle and is generally discouraged, but sometimes used for GDPR compliance.

### Key Takeaways

1. **ADR-0001's architecture is a textbook implementation of event sourcing + CQRS**: immutable append-only ledger (Postgres), derived read model (Neo4j), cursor-based projection worker. This is a well-proven pattern.
2. **The `global_position` BIGSERIAL** is critical and well-established -- it provides total ordering across all event types, enabling deterministic replay. EventStoreDB uses the same concept (`$all` stream position).
3. **Schema evolution via `schema_version` + upcasting** is the industry standard. ADR-0001 should plan for an upcasting middleware layer between Postgres reads and application logic.
4. **Idempotent projection** (`ON CONFLICT DO NOTHING` for Postgres, MERGE-based Cypher for Neo4j) is a best practice that ADR-0001 already mandates.
5. **Projection lag is expected and acceptable** -- the read model will always be slightly behind the write model. ADR-0001 should define SLAs for acceptable projection lag (e.g., < 1 second).

---

## 4. AI/ML Lineage Tools

### Overview

ML experiment tracking tools have been solving lineage and provenance problems for years, tracking the chain from data sources through transformations and training to model artifacts and predictions.

### Key Systems Analyzed

**MLflow**:
- Model Registry provides model lineage with automatic linking of model versions to the producing run (experiment + run + artifacts).
- Dataset tracking with `DatasetSource` component providing linked lineage to original data sources.
- Separation of concerns: metadata in backend store, binary artifacts in artifact store.
- Relevant pattern: run-centric logging where every experiment run captures parameters, metrics, tags, and artifact references.

**DVC (Data Version Control)**:
- Versions data and pipelines alongside code in git, ensuring reproducibility.
- Every input and transformation is tied to a git commit.
- Acquired by lakeFS in November 2025; continues as open-source.
- Relevant pattern: pipeline DAG definition that explicitly declares data dependencies and transformations.

**Weights & Biases**:
- Artifact tracking with dependency graphs between datasets, models, and pipeline steps.
- Automatic lineage visualization showing how artifacts flow through ML pipelines.
- Relevant pattern: artifact versioning with type system (dataset, model, code) and dependency edges.

### Patterns Relevant to ADR-0001

| Pattern | ML Tool | Context Graph Application |
|---|---|---|
| Run-centric logging | MLflow | Map to session/trace-centric event capture |
| Artifact lineage graph | W&B, MLflow | Map to entity derivation chains in Neo4j |
| Pipeline DAG | DVC | Map to agent workflow graphs |
| Metadata/artifact separation | MLflow | Map to event metadata in Postgres + payload refs |
| Immutable experiment records | All | Directly aligned with immutable event ledger |

### Key Takeaways

1. **The metadata/artifact separation pattern** (MLflow) validates ADR-0001's `payload_ref` field -- storing structured metadata in the event record while referencing large payloads externally.
2. **Run-centric lineage** (MLflow linking model versions to producing runs) is analogous to ADR-0001's approach of linking graph nodes back to source events via provenance pointers.
3. **The artifact dependency graph** (W&B) is a direct precedent for ADR-0001's Neo4j projection -- both represent derivation chains as directed graphs for lineage queries.
4. **Automatic lineage capture** (MLflow's `autolog`) is a relevant pattern -- ADR-0001 should consider how agent frameworks can automatically emit events without manual instrumentation.

---

## 5. Agent-Specific Observability

### Overview

A new category of observability platforms has emerged specifically for AI agent systems. These are the closest precedents for ADR-0001's target use case.

### Key Platforms Analyzed

**LangSmith** (LangChain ecosystem):
- Uses a "Run Tree" model where each trace is composed of nested runs (spans).
- Parent-child hierarchy: a parent run (e.g., full agent execution) contains child runs for tool calls, LLM calls, prompt formatting, and output parsing.
- Functions decorated with `@traceable` automatically log inputs, outputs, execution time, and position in the call hierarchy.
- Near-zero overhead (0% measurable) in production.
- Proprietary tracing layer, tightly coupled to LangChain/LangGraph.

**Arize Phoenix** (Open-source):
- Built on OpenTelemetry + OpenInference instrumentation standards.
- Provides visibility into LLM calls, tool executions, retrieval operations, and agent reasoning loops.
- Open-source and framework-agnostic.
- Uses OTel export pipeline, making it interoperable with other OTel-compatible systems.

**Langfuse** (Open-source):
- Built on OpenTelemetry with GenAI semantic conventions.
- Data model: Traces contain Observations (generations, spans, events) in a hierarchical tree.
- Supports session grouping for multi-turn conversations.
- Self-hostable with OpenTelemetry-native ingestion.
- SDK is a thin layer on top of official OTel client, converting spans to Langfuse observations.

**AgentOps**:
- Tracks 400+ LLM providers.
- Features: time-travel debugging, multi-agent workflow visualization, session replay.
- Claims 25x reduction in fine-tuning costs through cost optimization.
- 12% overhead reported.

**OpenInference** (Specification by Arize):
- Defines 10 span kinds: LLM, EMBEDDING, CHAIN, RETRIEVER, RERANKER, TOOL, AGENT, GUARDRAIL, EVALUATOR, PROMPT.
- Extends OTel with AI-specific semantics (model name, token counts, document scores, tool parameters).
- Transport and file-format agnostic.
- Used by Arize Phoenix and compatible with the broader OTel ecosystem.

### Comparison of Tracing Data Models

| Feature | LangSmith | Langfuse | Arize Phoenix | ADR-0001 |
|---|---|---|---|---|
| Trace concept | Run Tree | Trace + Observations | OTel Trace | Session + Event chain |
| Span/run types | chain, tool, llm, retriever | generation, span, event | 10 OTel span kinds | Dot-namespaced event_type |
| Parent-child | parent_run_id | observation hierarchy | parent_span_id | parent_event_id |
| Session grouping | Project/session | Session | N/A (via attributes) | session_id |
| Immutability | Not explicit | Not explicit | Not explicit | Core principle (append-only) |
| Replay/rebuild | No | No | No | Yes (from event ledger) |
| Schema versioning | No | No | No | schema_version field |
| Graph projection | No (flat trace view) | No (tree view) | No (tree view) | Yes (Neo4j graph) |
| Provenance in responses | No | No | No | Yes (core feature) |

### Key Takeaways

1. **ADR-0001 occupies a unique position**: existing agent observability tools focus on debugging and monitoring (trace viewing), while ADR-0001 focuses on provenance-annotated context retrieval for agents. No existing tool provides provenance pointers in context responses.
2. **The immutable event ledger with replay capability** is a differentiator -- existing platforms store traces but do not guarantee immutability, total ordering, or rebuild capability.
3. **OpenInference's span kinds** (especially AGENT, TOOL, LLM, CHAIN, RETRIEVER) provide a useful taxonomy for ADR-0001's `event_type` namespace. Consider adopting compatible naming: `agent.invoke`, `tool.execute`, `llm.generate`, `retriever.query`.
4. **Session-level grouping** is a common pattern across all platforms. ADR-0001's `session_id` is well-aligned.
5. **The trend toward OTel-native architectures** (Langfuse, Phoenix) suggests ADR-0001 should ensure OTel compatibility for event ingestion -- allowing agents that already emit OTel spans to feed into the context graph.
6. **Graph projection is novel**: none of the existing tools project traces into a queryable graph. ADR-0001's Neo4j projection for lineage queries and subgraph retrieval is a genuine innovation over the trace-tree views offered by existing platforms.

---

## 6. Cross-Cutting Themes

### Theme 1: The Trace/Span Model is Universal

Every system analyzed -- OTel, LangSmith, Langfuse, Phoenix, OpenInference -- uses some form of trace/span hierarchy with parent-child relationships. ADR-0001's `trace_id` + `parent_event_id` pattern is well-validated.

### Theme 2: Immutability and Append-Only are Proven

Event sourcing (EventStoreDB, Axon) has demonstrated that immutable, append-only event stores are viable at scale. ML experiment tracking (MLflow) independently converged on the same pattern. ADR-0001's commitment to immutable events is strongly supported.

### Theme 3: Derived Read Models are Standard Practice

CQRS/event sourcing separates write and read models. MLflow separates metadata and artifacts. OTel separates collection from analysis. ADR-0001's dual-store (Postgres write / Neo4j read) follows an established pattern.

### Theme 4: Schema Evolution is Inevitable

Every event sourcing system has converged on the need for schema versioning and upcasting. ADR-0001's `schema_version` field is necessary but not sufficient -- an upcasting strategy should be defined early.

### Theme 5: The Provenance Gap in Agent Observability

Current agent observability tools capture traces for human debugging but do not return provenance-annotated context to agents. This is the gap ADR-0001 fills. The traceability-first approach is validated by the existence of mature standards (PROV-DM) and tools (MLflow lineage) that solve the same problem in adjacent domains.

### Theme 6: Convergence on OpenTelemetry

The agent observability space is rapidly converging on OTel as the instrumentation standard (Langfuse, Phoenix, and even LangSmith now support OTel export). ADR-0001 should ensure compatibility with OTel for event ingestion.

---

## 7. Recommendations for ADR-0001

### R1: Adopt PROV-DM Vocabulary for Graph Edge Types

Use W3C PROV-DM relationship names for Neo4j edge types: `GENERATED_BY`, `USED`, `DERIVED_FROM`, `ATTRIBUTED_TO`, `INFORMED_BY`. This provides semantic clarity and alignment with an established standard.

**Effort**: Low (naming convention choice)
**Impact**: High (interoperability, clarity)

### R2: Align Event Types with OpenInference Span Kinds

Structure the `event_type` namespace to be compatible with OpenInference's span kind taxonomy:
- `agent.create`, `agent.invoke` (maps to AGENT span kind)
- `tool.execute` (maps to TOOL)
- `llm.generate` (maps to LLM)
- `retriever.query` (maps to RETRIEVER)
- `chain.start`, `chain.end` (maps to CHAIN)

**Effort**: Low (naming convention choice)
**Impact**: Medium (ecosystem compatibility)

### R3: Support OTel-Compatible Event Ingestion

Provide an ingestion adapter that accepts OTel spans (via OTLP/gRPC or OTLP/HTTP) and transforms them into context graph events. This allows agents already instrumented with OTel to feed into the system without custom integration.

**Effort**: Medium (adapter development)
**Impact**: High (adoption, ecosystem integration)

### R4: Plan Schema Evolution Strategy Early

Define an upcasting middleware layer between event deserialization and application logic. Use `schema_version` for explicit version tracking. Start with a "weak schema" approach (tolerant JSON payloads) combined with upcasting for breaking changes.

**Effort**: Medium (design + implementation)
**Impact**: High (long-term maintainability)

### R5: Maintain the Immutable Event Ledger as Core Differentiator

No existing agent observability tool provides immutable event storage with deterministic replay. This is ADR-0001's strongest architectural advantage. Do not compromise on this for short-term convenience.

**Effort**: N/A (architectural commitment)
**Impact**: Critical (differentiation and trust model)

### R6: Ensure Provenance Pointers in All Context Responses

This is the feature gap no current tool fills. Every context retrieval response must include provenance metadata linking back to source events. This is what makes the context graph trustworthy for agents.

**Effort**: Medium (API design)
**Impact**: Critical (core value proposition)

### R7: Define Projection Lag SLAs

Event sourcing systems accept that read models lag behind the write model. Define acceptable lag bounds for the Neo4j projection (e.g., p99 < 1 second) and instrument monitoring for projection health.

**Effort**: Low (operational definition)
**Impact**: Medium (operational reliability)

### R8: Consider Bundle/Session Provenance

Adopt W3C PROV-DM's Bundle concept for session-level provenance grouping. This supports "provenance of provenance" -- being able to explain not just what happened in an agent session, but how the context graph itself was constructed.

**Effort**: Low-Medium (model extension)
**Impact**: Medium (advanced debugging, trust)

---

## Sources

### OpenTelemetry
- [OpenTelemetry Traces Concepts](https://opentelemetry.io/docs/concepts/signals/traces/)
- [Context Propagation](https://opentelemetry.io/docs/concepts/context-propagation/)
- [GenAI Agent Spans Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/)
- [GenAI Semantic Conventions Overview](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- [OTel Specification Overview](https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/overview.md)
- [Tracing API Specification](https://opentelemetry.io/docs/specs/otel/trace/api/)

### W3C PROV
- [PROV-DM: The PROV Data Model](https://www.w3.org/TR/prov-dm/)
- [PROV-O: The PROV Ontology](https://www.w3.org/TR/prov-o/)
- [W3C Prov Wikipedia](https://en.wikipedia.org/wiki/W3C_Prov)
- [PROV Tutorial (GitHub)](https://github.com/pgroth/PROVTutorial)

### Event Sourcing
- [Simple Patterns for Events Schema Versioning (Event-Driven.io)](https://event-driven.io/en/simple_events_versioning_patterns/)
- [Projections and Read Models in Event-Driven Architecture](https://event-driven.io/en/projections_and_read_models_in_event_driven_architecture/)
- [Event Sourcing Explained (BayTech Consulting)](https://www.baytechconsulting.com/blog/event-sourcing-explained-2025)
- [Axon Framework](https://www.axoniq.io/products/axon-framework)
- [Marten Events Versioning](https://martendb.io/events/versioning.html)
- [EventStoreDB Event Sourcing Sample (GitHub)](https://github.com/eugene-khyst/eventstoredb-event-sourcing)

### AI/ML Lineage
- [MLflow Dataset Tracking](https://mlflow.org/docs/latest/ml/dataset/)
- [MLflow Model Registry](https://mlflow.org/docs/latest/model-registry/)
- [Model Versioning Strategies: DVC vs MLflow vs W&B](https://mljourney.com/model-versioning-strategies-dvc-vs-mlflow-vs-weights-biases/)
- [26 MLOps Tools for 2026 (lakeFS)](https://lakefs.io/mlops/mlops-tools/)

### Agent Observability
- [Top 5 AI Agent Observability Platforms 2026 Guide](https://o-mega.ai/articles/top-5-ai-agent-observability-platforms-the-ultimate-2026-guide)
- [8 AI Observability Platforms Compared (Softcery)](https://softcery.com/lab/top-8-observability-platforms-for-ai-agents-in-2025)
- [Phoenix: Open-Source LangSmith Alternative](https://vap1231.medium.com/phoenix-open-source-langsmith-alternative-platform-for-ai-agent-observability-and-evaluation-b22618219e3d)
- [LangSmith Tracing Deep Dive](https://medium.com/@aviadr1/langsmith-tracing-deep-dive-beyond-the-docs-75016c91f747)
- [Langfuse Tracing Data Model](https://langfuse.com/docs/observability/data-model)
- [OpenInference Semantic Conventions](https://arize-ai.github.io/openinference/spec/semantic_conventions.html)
- [OpenInference Tracing Specification](https://arize-ai.github.io/openinference/spec/)
- [Arize Phoenix (GitHub)](https://github.com/Arize-ai/phoenix)
- [15 AI Agent Observability Tools in 2026](https://research.aimultiple.com/agentic-monitoring/)
- [LangSmith and AgentOps](https://www.akira.ai/blog/langsmith-and-agentops-with-ai-agents)
