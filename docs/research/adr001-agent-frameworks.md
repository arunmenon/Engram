# ADR-0001 Research: Agent Framework Traceability Landscape

**Date:** 2026-02-07
**Scope:** Survey of agent framework tracing/context patterns and their alignment with the proposed event schema

---

## Executive Summary

The agent framework ecosystem is converging on OpenTelemetry as the observability backbone, but **no framework provides a unified, immutable, provenance-annotated context graph** that spans across frameworks. Each framework captures traces optimized for its own debugging and monitoring needs, leaving significant gaps in cross-framework lineage, causal provenance, and deterministic replay. The proposed context graph fills a distinct niche: a framework-agnostic, append-only event ledger with graph projection for traceability that sits *downstream* of framework-native telemetry.

---

## 1. LangChain / LangSmith

### How It Works

LangSmith organizes tracing into three tiers:
- **Runs** (spans): Individual steps -- LLM calls, tool invocations, chain executions, retrievers, embeddings, parsers
- **Traces**: A tree of runs representing one end-to-end agent execution
- **Threads**: A collection of traces forming a full conversation

LangChain instruments via a callback system (`LangChainTracer`) that sends runs to an async trace collector in LangSmith.

### Key Schema Fields

| LangSmith Field | Type | Description |
|---|---|---|
| `id` | UUID | Unique run identifier |
| `trace_id` | UUID | Groups all runs in a single trace |
| `parent_run_id` | UUID | Parent run for nesting |
| `run_type` | enum | `llm`, `chain`, `tool`, `retriever`, `embedding`, `prompt`, `parser` |
| `name` | string | Human-readable run name |
| `start_time` / `end_time` | datetime | Execution timestamps |
| `inputs` / `outputs` | dict | Run input/output data |
| `error` | string | Error info if failed |
| `tags` | list[str] | Categorization tags |
| `dotted_order` | string | `{time}{run-uuid}` for ordering |
| `events` | list | Event data within the run |
| `session_name` / `session_id` | string | Project identification |
| `attachments` | list | `(mime_type, bytes)` tuples |

### Mapping to Proposed Event Schema

| Proposed Field | LangSmith Equivalent | Notes |
|---|---|---|
| `event_id` | `id` | Direct 1:1 UUID mapping |
| `event_type` | `run_type` | LangSmith uses flat enum; proposed uses dot-namespaced strings -- richer |
| `occurred_at` | `start_time` | Direct mapping |
| `ended_at` | `end_time` | Direct mapping |
| `session_id` | `session_name` / `session_id` | LangSmith uses project-level sessions, not agent session |
| `agent_id` | (none) | **Gap** -- LangSmith does not have a first-class agent identity field |
| `trace_id` | `trace_id` | Direct mapping |
| `parent_event_id` | `parent_run_id` | Direct mapping |
| `tool_name` | `name` (when `run_type=tool`) | Derived, not a dedicated field |
| `payload_ref` | `inputs` / `outputs` (inline) | LangSmith inlines payloads; proposed uses references |
| `status` | Derived from `error` | LangSmith has no explicit status enum |
| `schema_version` | (none) | **Gap** -- no schema versioning |
| `global_position` | `dotted_order` | Different ordering approach |

### Integration Friction: **Low-Medium**

LangSmith exposes a REST API for posting runs, and the callback system can be extended with custom handlers. An adapter could intercept `LangChainTracer` callbacks and transform runs into the proposed event schema. The main friction is:
- Mapping flat `run_type` enum to dot-namespaced `event_type`
- Extracting `agent_id` from context (not first-class in LangSmith)
- Converting inline payloads to `payload_ref` references

### Gaps This Project Fills

- **No agent identity**: LangSmith traces runs, not agents. No way to ask "what did agent X do across sessions?"
- **No immutable ledger**: LangSmith runs can be deleted/modified; no append-only guarantee
- **No cross-framework traces**: LangSmith only traces LangChain-native operations
- **No graph projection**: No lineage queries like "what influenced this output?"

---

## 2. CrewAI

### How It Works

CrewAI provides built-in tracing covering agent decisions, task execution timelines, tool usage, and LLM calls. The tracing system is implemented as a thread-safe singleton (`Telemetry` class) that manages OpenTelemetry span collection.

CrewAI organizes work as:
- **Crew**: Top-level orchestration unit
- **Agent**: Role-playing autonomous unit with backstory, goal, tools
- **Task**: Work unit assigned to an agent with context and expected output

### Telemetry Data Emitted

- Task interpretation and delegation events
- Tool call invocations and results
- Agent decision-making steps
- Validation and output events
- LLM call details (when opted in via `share_crew=True`)

By default, CrewAI collects *anonymous* telemetry only. Detailed execution data (prompts, outputs, backstories) requires explicit opt-in.

### OpenTelemetry Integration

- Native `opentelemetry-instrumentation-crewai` package logs prompts, completions, and embeddings to span attributes
- Compatible with Langfuse, SigNoz, AgentOps, and other OTel backends
- Telemetry can be disabled via `OTEL_SDK_DISABLED=true`

### Mapping to Proposed Event Schema

| Proposed Field | CrewAI Equivalent | Notes |
|---|---|---|
| `event_id` | OTel span ID | Generated by OTel instrumentation |
| `event_type` | Span name / event category | Not dot-namespaced; would need mapping |
| `occurred_at` | Span start time | Standard OTel timestamp |
| `session_id` | Crew execution ID | One crew run = one session |
| `agent_id` | Agent role/name | CrewAI has strong agent identity (role, backstory) |
| `trace_id` | OTel trace ID | Standard OTel propagation |
| `tool_name` | Tool invocation span | Available in tool call spans |
| `parent_event_id` | OTel parent span ID | Standard nesting |
| `payload_ref` | Span attributes (inline) | Detailed payloads only with `share_crew=True` |
| `status` | Span status code | OK / ERROR via OTel |
| `schema_version` | (none) | **Gap** |

### Integration Friction: **Medium**

- CrewAI's detailed telemetry requires `share_crew=True` opt-in -- without it, payloads are unavailable
- OTel span attributes need transformation to the proposed event schema
- Agent identity is strong (role-based) but not UUID-based
- No public REST API for trace data; must intercept OTel spans

### Gaps This Project Fills

- **No persistent lineage**: CrewAI traces are ephemeral OTel spans, not stored in an immutable ledger
- **No causal graph**: Cannot query "which tool output influenced which agent decision"
- **Limited provenance**: Traces show what happened but not why (no causal links between events)
- **No cross-crew tracing**: Cannot trace data flow across separate crew executions

---

## 3. AutoGen / AG2

### How It Works

AutoGen 0.4 (released January 2025) introduced a re-architected system with event-driven communication. Messages are routed through a centralized component rather than directly between agents, making observation easier.

The AG2 fork continues the v0.2 API with improved trace logs and token spend monitoring.

**Key events captured:**
- `ToolCallRequestEvent` -- function invocations
- `ToolCallExecutionEvent` -- function results
- `ToolCallSummaryMessage` -- formatted outputs
- `TextMessage` exchanges between agents
- Team operations (group chat coordination, selector decisions)

### OpenTelemetry Integration

AutoGen 0.4 follows OpenTelemetry Semantic Conventions for agents and tools. Setup:
1. Configure `TracerProvider` with `Resource` metadata
2. Attach `BatchSpanProcessor` with OTLP exporter
3. Set tracer provider globally

The AgentChat runtime automatically logs message metadata without explicit instrumentation.

### Mapping to Proposed Event Schema

| Proposed Field | AutoGen Equivalent | Notes |
|---|---|---|
| `event_id` | OTel span ID | Auto-generated |
| `event_type` | Event class name (`ToolCallRequestEvent`, etc.) | Structured but not dot-namespaced |
| `occurred_at` | Span timestamp | Standard OTel |
| `session_id` | Runtime/conversation context | Implicit in runtime, not a first-class field |
| `agent_id` | Agent name/role in span attributes | Available but not UUID-standardized |
| `trace_id` | OTel trace ID | Standard |
| `tool_name` | Function name in `ToolCallRequestEvent` | Available |
| `parent_event_id` | OTel parent span ID | Standard nesting |
| `payload_ref` | Span attributes (arguments, results) | Inline in span data |
| `status` | Span status | OK / ERROR |
| `schema_version` | (none) | **Gap** |

### Integration Friction: **Medium**

- AutoGen's event-driven architecture is well-suited for event capture, but events are OTel spans, not persisted events
- The centralized message routing is a natural interception point for an adapter
- AG2 fork has a different API surface, requiring a separate adapter
- Microsoft Agent Framework (unifying SK + AutoGen) is the future direction -- integration target is shifting

### Gaps This Project Fills

- **No immutable event store**: Traces are ephemeral; no replay capability
- **No graph projection**: Cannot query multi-agent interaction patterns as a graph
- **No cross-framework tracing**: AutoGen traces don't connect to LangChain or CrewAI traces
- **Fragmented ecosystem**: AutoGen vs AG2 vs Microsoft Agent Framework creates adapter confusion

---

## 4. OpenAI Agents SDK (Successor to Assistants API)

### How It Works

The Assistants API is **deprecated** (removal August 2026). The replacement is the **Responses API + Agents SDK** (released March 2025), which shifts from stateful management to request/response with developer-managed conversation history.

The Agents SDK standardizes interactions into a loop: **prompt -> tool call -> reasoning -> action**.

### Tracing Data Model

**Traces:**
- `workflow_name`: Logical workflow identifier
- `trace_id`: Format `trace_<32_alphanumeric>`
- `group_id`: Optional, links traces in the same conversation
- `metadata`: Supplementary information

**Spans (operation-specific):**
| Span Type | Description |
|---|---|
| `agent_span()` | Individual agent execution |
| `generation_span()` | LLM API calls |
| `function_span()` | Tool function invocations |
| `guardrail_span()` | Guardrail evaluations |
| `handoff_span()` | Agent-to-agent handoffs |
| `transcription_span()` | Speech-to-text |
| `speech_span()` | Text-to-speech |
| `speech_group_span()` | Container for audio spans |
| `custom_span()` | User-defined tracking |

Each span has: `trace_id`, `span_id`, `parent_id`, `span_data`, `started_at`, `ended_at`.

### Mapping to Proposed Event Schema

| Proposed Field | OpenAI SDK Equivalent | Notes |
|---|---|---|
| `event_id` | `span_id` | Unique per span |
| `event_type` | Span type (e.g., `function_span`) | Flat naming; would need dot-namespace mapping |
| `occurred_at` | `started_at` | Direct |
| `ended_at` | `ended_at` | Direct |
| `session_id` | `group_id` | Maps well conceptually |
| `agent_id` | Agent name in `agent_span` data | Not a dedicated ID field |
| `trace_id` | `trace_id` | Direct but custom format (`trace_<32>`) |
| `tool_name` | Function name in `function_span` | Available |
| `parent_event_id` | `parent_id` | Direct |
| `payload_ref` | Span data (inline) | Subject to `trace_include_sensitive_data` |
| `status` | (derived from span completion) | No explicit status field |
| `schema_version` | (none) | **Gap** |

### Integration Friction: **Low**

- The Agents SDK has a clean, well-documented tracing API
- Custom `TracingProcessor` interface allows intercepting all traces and spans
- Span types map cleanly to event types
- `group_id` aligns with `session_id` concept
- Main friction: custom `trace_id` format requires normalization

### Gaps This Project Fills

- **OpenAI-only scope**: Traces only OpenAI SDK operations; no visibility into non-OpenAI tools
- **No persistent store**: Traces are sent to OpenAI's dashboard or custom processors; no immutable ledger
- **No graph query**: Cannot traverse "what influenced this output" across multiple traces
- **Sensitive data controls**: Default exclusion of payloads limits provenance depth

---

## 5. Semantic Kernel / Microsoft Agent Framework

### How It Works

Semantic Kernel implements the three pillars of observability (logging, metrics, tracing) compliant with OpenTelemetry standards, using the `Microsoft.SemanticKernel` activity source.

As of October 2025, Semantic Kernel and AutoGen have entered maintenance mode, with development centering on the unified **Microsoft Agent Framework**.

### Telemetry Emitted

**Metrics:**
- `semantic_kernel.function.invocation.duration` (Histogram)
- `semantic_kernel.function.streaming.duration` (Histogram)
- `semantic_kernel.function.invocation.token_usage.prompt` (Histogram)
- `semantic_kernel.function.invocation.token_usage.completion` (Histogram)

**Tracing:**
- Each kernel function execution and AI model call is recorded as a span
- Follows OpenTelemetry Semantic Conventions for Generative AI (experimental)
- Python: auto function invocation loop, kernel function execution, AI model calls
- C#: kernel function execution and AI model calls

**Logging:**
- Kernel events, plugin/function events, AI connector events
- Sensitive data at Trace/Debug level only

### Mapping to Proposed Event Schema

| Proposed Field | Semantic Kernel Equivalent | Notes |
|---|---|---|
| `event_id` | OTel span/activity ID | Auto-generated |
| `event_type` | Function name / operation | Would need dot-namespace mapping |
| `occurred_at` | Span start time | Standard OTel |
| `session_id` | (none -- app-level concern) | **Gap** -- no session concept |
| `agent_id` | (none) | **Gap** -- SK is function-centric, not agent-centric |
| `trace_id` | OTel trace ID | Standard |
| `tool_name` | Plugin function name | Well-structured (plugin.function) |
| `parent_event_id` | OTel parent span ID | Standard |
| `payload_ref` | Log entries / span attributes | Sensitive data gated |
| `status` | Span status | Standard OTel |
| `schema_version` | (none) | **Gap** |

### Integration Friction: **Low-Medium**

- Strong OTel compliance means standard exporters can intercept spans
- Well-structured plugin.function naming maps naturally to dot-namespaced event types
- No agent identity concept; SK is kernel/function-oriented
- Microsoft Agent Framework is the new target, but still early

### Gaps This Project Fills

- **No agent identity**: SK is function-centric; no "agent X did Y" queries
- **No session concept**: No conversation/session-level grouping
- **No causal lineage**: Function traces show call hierarchy but not data provenance
- **No immutable ledger**: Spans are ephemeral OTel data

---

## 6. Emerging Standards

### Agent2Agent Protocol (A2A)

Introduced by Google (April 2025), now stewarded by the Linux Foundation.

**Core Data Model:**
- **AgentCard**: JSON capability manifest describing an agent
- **Task**: Interaction unit with `id`, `status`, `sessionId`, `history`, `artifacts`, `metadata`
- **Artifact**: Output generated by an agent, composed of Parts
- **Part**: Atomic content unit (TextPart, UriPart, DataPart, JsonPart, etc.)
- **contextId**: Groups multiple Tasks for continuity

**Tracing:** Each request carries trace IDs and OTLP metrics. Structured logs in OpenTelemetry Protocol format.

**Relevance:** A2A defines inter-agent communication but not internal agent tracing. The context graph could serve as the provenance layer that A2A lacks.

### Open Agent Specification (Agent Spec)

Oracle-led framework-agnostic declarative language for describing agents.

**Key feature:** Agent Spec Tracing lets standardized events flow to frontends and downstream observability/evaluation tools via pluggable hooks.

**Relevance:** Agent Spec provides the "what an agent is" description; the context graph provides the "what an agent did" record.

### OpenTelemetry Semantic Conventions for GenAI Agents

**Status:** Development (experimental)

**Key attributes defined:**
- `gen_ai.agent.id` -- unique agent identifier
- `gen_ai.agent.name` -- human-readable name
- `gen_ai.agent.description` -- free-form description
- `gen_ai.conversation.id` -- session/thread identifier
- `gen_ai.operation.name` -- `create_agent`, `invoke_agent`
- `gen_ai.provider.name` -- provider discriminator

**Span types:** `create_agent`, `invoke_agent` with defined required/optional attributes.

**Relevance:** These conventions are the closest to a universal schema for agent tracing. The proposed event schema should align with these attribute names where possible to ease OTel-based ingestion.

### Agentic AI Foundation (AAIF)

Launched December 2025 by Anthropic, OpenAI, and Block under the Linux Foundation. Coordinates open, interoperable infrastructure for agentic AI systems.

### AGNTCY

Launched July 2025 under the Linux Foundation (Cisco-led, with Google, Dell, Red Hat). Provides infrastructure for multi-agent collaboration including discovery, identity, secure messaging, and observability.

---

## Comparison Matrix

| Dimension | LangSmith | CrewAI | AutoGen 0.4 | OpenAI Agents SDK | Semantic Kernel | OTel GenAI |
|---|---|---|---|---|---|---|
| **Trace hierarchy** | Run tree (trace > runs) | Crew > Agent > Task spans | Event-driven message spans | Trace > Spans (typed) | Function invocation spans | Agent > invoke spans |
| **Agent identity** | None (run-centric) | Role-based (strong) | Name-based | Name in span data | None (function-centric) | `gen_ai.agent.id` defined |
| **Session concept** | Project-level | Crew execution | Runtime context | `group_id` | None | `gen_ai.conversation.id` |
| **Tool call tracking** | `run_type=tool` | OTel span | `ToolCallRequestEvent` | `function_span()` | Plugin function span | Standard span |
| **Immutable ledger** | No (mutable) | No (ephemeral) | No (ephemeral) | No (ephemeral) | No (ephemeral) | N/A (convention only) |
| **Causal lineage** | Parent-child only | Parent-child only | Parent-child only | Parent-child only | Parent-child only | Parent-child only |
| **Cross-framework** | LangChain only | CrewAI only | AutoGen only | OpenAI only | SK only | Framework-agnostic |
| **Graph queries** | No | No | No | No | No | No |
| **Payload handling** | Inline (full) | Opt-in (`share_crew`) | Inline (span attrs) | Gated (sensitive) | Gated (log level) | Events (opt-in) |
| **Schema versioning** | No | No | No | No | No | No |
| **OTel compliance** | Via Langfuse/export | Native | Native | Custom (+ OTLP) | Native | Is the standard |
| **Deterministic replay** | No | No | No | No | No | No |
| **Provenance annotations** | No | No | No | No | No | No |

---

## Integration Recommendations

### Priority 1: OpenTelemetry Collector Adapter (All Frameworks)

**Recommendation:** Build an OTel Collector receiver/exporter that transforms OTel spans following GenAI semantic conventions into the proposed event schema.

**Why:** AutoGen, CrewAI, Semantic Kernel, and (via third-party integrations) LangChain all emit OTel spans. A single OTel-based adapter covers the widest surface area with the least integration code.

**Mapping strategy:**
- `gen_ai.agent.id` / agent span name -> `agent_id`
- `gen_ai.conversation.id` / group_id -> `session_id`
- OTel trace ID -> `trace_id`
- OTel span ID -> `event_id`
- OTel parent span ID -> `parent_event_id`
- Span name / `gen_ai.operation.name` -> `event_type` (with dot-namespace normalization)
- Span start/end -> `occurred_at` / `ended_at`
- Span status -> `status`
- Span attributes -> `payload_ref` (externalized to blob store)

### Priority 2: LangSmith Webhook / Callback Adapter

**Recommendation:** Build a LangChain callback handler that transforms runs directly into events, bypassing LangSmith.

**Why:** LangChain has the largest market share. Direct callback integration avoids requiring LangSmith as an intermediary and provides the richest data (inline payloads).

**Implementation:** Custom `BaseCallbackHandler` subclass that posts events to the context graph API on `on_llm_start`, `on_tool_start`, `on_chain_start`, etc.

### Priority 3: OpenAI Agents SDK TracingProcessor

**Recommendation:** Implement a custom `TracingProcessor` for the OpenAI Agents SDK that sends traces/spans to the context graph.

**Why:** Clean API, low friction, and growing adoption. The typed span model (agent, generation, function, guardrail, handoff) maps well to dot-namespaced event types.

**Implementation:** Implement `TracingProcessor.on_trace_start`, `on_span_start`, `on_span_end`, `on_trace_end` to transform and ingest events.

### Priority 4: A2A Protocol Task Listener

**Recommendation:** Build an A2A-aware listener that captures Task lifecycle events (submitted -> working -> completed) and Artifact creation as events in the context graph.

**Why:** A2A is becoming the inter-agent communication standard. Capturing A2A task flows provides cross-agent lineage that no individual framework offers.

---

## Key Findings for ADR-0001

### 1. The proposed context graph fills a real gap

No existing framework provides:
- **Immutable event storage** with append-only guarantees
- **Cross-framework tracing** spanning multiple agent frameworks
- **Graph-based lineage queries** beyond parent-child span relationships
- **Provenance-annotated context retrieval** for agents
- **Deterministic replay** from an event ledger
- **Schema versioning** for event evolution

### 2. Schema alignment recommendations

The proposed event schema should adopt OTel GenAI semantic convention attribute names where possible:
- Use `gen_ai.agent.id` as the canonical agent identifier attribute name in OTel adapters
- Use `gen_ai.conversation.id` as the canonical session identifier
- Support `gen_ai.operation.name` values as a mapping source for `event_type`

### 3. The `event_type` dot-namespace is a differentiator

All frameworks use flat or class-based event naming. The proposed dot-namespaced `event_type` (e.g., `agent.tool.invoke`, `agent.llm.generate`) provides richer taxonomy than any existing approach. Define a canonical namespace registry early.

### 4. `payload_ref` is architecturally correct

All frameworks inline payloads in spans/runs, which limits scalability and creates data sensitivity issues. The proposed `payload_ref` (reference to externalized payload) is the right design for an immutable ledger serving multiple frameworks.

### 5. `global_position` enables capabilities no framework offers

The `BIGSERIAL global_position` field enables deterministic replay and ordered projection -- capabilities that none of the surveyed frameworks provide. This is the strongest differentiator for the traceability-first approach.

---

## Sources

- [LangSmith Trace Documentation](https://docs.langchain.com/langsmith/trace-with-api)
- [LangSmith Run Schema](https://docs.smith.langchain.com/reference/python/schemas/langsmith.schemas.Run)
- [LangSmith Deep Dive](https://medium.com/@aviadr1/langsmith-tracing-deep-dive-beyond-the-docs-75016c91f747)
- [CrewAI Tracing](https://docs.crewai.com/en/observability/tracing)
- [CrewAI OTel Instrumentation](https://pypi.org/project/opentelemetry-instrumentation-crewai/)
- [CrewAI Observability with Langfuse](https://langfuse.com/integrations/frameworks/crewai)
- [AutoGen Tracing and Observability](https://microsoft.github.io/autogen/stable//user-guide/agentchat-user-guide/tracing.html)
- [AutoGen 0.4 Launch](https://devblogs.microsoft.com/autogen/autogen-reimagined-launching-autogen-0-4/)
- [Microsoft Agent Framework](https://visualstudiomagazine.com/articles/2025/10/01/semantic-kernel-autogen--open-source-microsoft-agent-framework.aspx)
- [OpenAI Agents SDK Tracing](https://openai.github.io/openai-agents-python/tracing/)
- [OpenAI Agents SDK Span Types](https://openai.github.io/openai-agents-python/ref/tracing/spans/)
- [Semantic Kernel Observability](https://learn.microsoft.com/en-us/semantic-kernel/concepts/enterprise-readiness/observability/)
- [Semantic Kernel Telemetry](https://github.com/microsoft/semantic-kernel/blob/main/dotnet/docs/TELEMETRY.md)
- [OTel GenAI Agent Spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/)
- [OTel GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- [OTel GenAI Agentic Systems Proposal](https://github.com/open-telemetry/semantic-conventions/issues/2664)
- [Agent2Agent Protocol Specification](https://a2a-protocol.org/latest/specification/)
- [A2A Protocol Explained](https://www.altexsoft.com/blog/a2a-protocol-explained/)
- [Open Agent Specification](https://blogs.oracle.com/ai-and-datascience/introducing-open-agent-specification)
- [Agentic AI Foundation](https://openai.com/index/agentic-ai-foundation/)
- [AI Agent Observability - OpenTelemetry Blog](https://opentelemetry.io/blog/2025/ai-agent-observability/)
