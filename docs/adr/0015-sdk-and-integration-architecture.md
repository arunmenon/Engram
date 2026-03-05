# ADR-0015: SDK and Integration Architecture

Status: **Proposed**
Date: 2026-02-28
Extends: ADR-0006 (API design), ADR-0009 (graph schema), ADR-0012 (user personalization)

## Context

Engram exposes a REST API at `/v1/` for event ingestion, context retrieval, subgraph queries, and lineage traversal. Today, every agent framework must handcraft HTTP calls, manage authentication headers, serialize events into the correct schema, and parse the Atlas response format. This creates a **5-8x cognitive load gap** compared to competing agentic memory systems.

### Competitive Landscape (February 2026)

| System | Lines to first value | Key DX pattern |
|--------|---------------------|----------------|
| Mem0 | 3 lines | `add(message, user_id=)` — LLM auto-extracts facts |
| Zep | 4 lines | Declarative context templates (`%{edges limit=4}`) |
| Cognee | 5 lines | Three-verb pipeline: `add`, `cognify`, `search` |
| **Engram (current)** | **~25 lines** | Manual Event dict, raw HTTP, Atlas response parsing |

### Engram's Unique Strengths (to preserve, not hide)

1. **Full provenance** — every context node traces back to source events
2. **16 typed edge relationships** — CAUSED_BY, FOLLOWS, SIMILAR_TO, etc.
3. **8 intent types** — intent-weighted traversal (why, when, what, related, etc.)
4. **Causal lineage** — `trace()` returns the full causal chain
5. **Proactive context** — system surfaces relevant context the agent didn't ask for
6. **Decay scoring** — Ebbinghaus-based relevance that accounts for recency, importance, access frequency

These capabilities are invisible if the only interface is raw HTTP.

### Problem Statement

No SDK, no MCP server, and no framework adapters exist. Developers building with LangChain, CrewAI, OpenAI Agents SDK, or any other framework must:

1. Construct `Event` dicts with 10+ required/optional fields
2. Generate UUIDs for `event_id`, `trace_id`
3. Manage `session_id` lifecycle manually
4. POST to the correct endpoint with auth headers
5. Parse nested Atlas responses (nodes → provenance → scores)
6. Handle cursor pagination manually
7. Implement retry/backoff for 429/503 responses

This is unacceptable for an agent memory system that should be as easy to use as `memory.add()`.

## Decision

### Three-Layer Integration Architecture

```
Layer 3: Framework Adapters (per-framework packages)
         LangChain, CrewAI, OpenAI Agents, LlamaIndex

Layer 2: Protocol Servers (MCP, auto-generated OpenAPI SDK)
         engram-mcp (7 tools)

Layer 1: Core SDK (engram package)
         Simple API + Full API + Context Templates
         + Auto-Instrumentation + Transport
```

Each layer builds on the one below. Framework adapters depend on the core SDK. The MCP server depends on the core SDK. All external integration flows through Layer 1.

### Layer 1: Core SDK (`engram` package)

#### 1.1 Simple API — Progressive Entry Point

Three module-level functions provide the minimum-viable interface:

```python
import engram

# Record an event (auto-generates IDs, manages session)
await engram.record(
    "User asked about payment processing",
    agent_id="my-agent",
)

# Recall context (routes to best endpoint automatically)
context = await engram.recall(query="payment issues")

# Trace provenance (Engram's differentiator)
lineage = await engram.trace("evt-abc-123")
```

**Auto-generation rules:**
- `event_id`: UUID4, always auto-generated
- `trace_id`: UUID4, auto-generated per session (reused within session)
- `session_id`: UUID4, auto-generated on first `record()`, reused until explicit end or timeout
- `occurred_at`: `datetime.utcnow()`, always auto-set
- `event_type`: Inferred from content if not provided (e.g., "tool" mention → `tool.execute`)
- `payload_ref`: Content string wrapped and stored

**Configuration:** Via environment variables (`ENGRAM_BASE_URL`, `ENGRAM_API_KEY`) or explicit `engram.configure(base_url=..., api_key=...)` call. Zero-config if env vars are set.

#### 1.2 Full API — Typed Client

```python
from engram import EngramClient

client = EngramClient(
    base_url="http://localhost:8000",
    api_key="...",
    timeout=30.0,
    max_retries=3,
    rate_limit_aware=True,
)
```

The `EngramClient` exposes all REST endpoints as typed async methods:

| Method | Maps to | Returns |
|--------|---------|---------|
| `client.ingest(event)` | `POST /v1/events` | `IngestResult` |
| `client.ingest_batch(events)` | `POST /v1/events/batch` | `BatchResult` |
| `client.get_context(session_id, **kwargs)` | `GET /v1/context/{id}` | `AtlasResponse` |
| `client.query_subgraph(query)` | `POST /v1/query/subgraph` | `AtlasResponse` |
| `client.get_lineage(node_id, **kwargs)` | `GET /v1/nodes/{id}/lineage` | `AtlasResponse` |
| `client.get_entity(entity_id)` | `GET /v1/entities/{id}` | `EntityResponse` |
| `client.get_user_profile(user_id)` | `GET /v1/users/{id}/profile` | `UserProfile` |
| `client.health()` | `GET /v1/health` | `HealthStatus` |

All response types are Pydantic models mirroring the server-side models.

#### 1.3 Session Manager

```python
async with client.session(agent_id="my-agent") as session:
    await session.record(event_type="tool.execute", payload={...})
    context = await session.context(query="...")
    # Session auto-ends on exit → triggers extraction consumer
```

The `SessionManager`:
- Generates and tracks `session_id` and `trace_id`
- Links events via `parent_event_id` (auto-chains FOLLOWS)
- Sends `system.session_end` event on `__aexit__`
- Exposes `session.id`, `session.trace_id`, `session.event_count`

#### 1.4 Context Templates

Inspired by Zep's declarative templates, extended with Engram-specific directives:

```
%{events limit=N intent=INTENT_TYPE}     — recent events by intent
%{lineage node=NODE_ID depth=N}          — causal chain
%{entities limit=N types=[TYPE,...]}      — related entities
%{user_profile}                          — full user profile
%{user_preferences limit=N}              — user preferences
%{user_skills limit=N}                   — user skills
%{proactive limit=N}                     — system-selected context
%{summary session=SESSION_ID}            — session summary
```

Templates are:
- Defined as strings with `%{directive}` placeholders
- Registered server-side via `POST /v1/templates` (new endpoint)
- Referenced by ID in `recall()` or `session.context()`
- Rendered into both structured text (for LLM system prompts) and typed Atlas response (for programmatic use)

**Engram-unique directives** not possible in competing systems:
- `%{lineage}` — causal provenance chain
- `%{proactive}` — system-inferred relevant context
- `%{events intent=why}` — intent-filtered retrieval

#### 1.5 Auto-Instrumentation

Optional monkey-patching for zero-code event capture:

```python
from engram.instrument import patch

# Patches OpenAI, Anthropic, LangChain, or any registered provider
patch(client, providers=["openai", "anthropic"])
```

**What gets captured:**

| Provider | Event type | Captured fields |
|----------|-----------|-----------------|
| OpenAI | `llm.completion` | model, tokens, finish_reason, prompt_hash |
| Anthropic | `llm.completion` | model, tokens, stop_reason |
| LangChain | `agent.step`, `tool.execute` | chain name, tool name, inputs/outputs |
| Generic | `tool.execute` | function name, args, duration_ms |

**Implementation approach:** Callback-based where possible (LangChain callbacks, OpenAI response hooks). Monkey-patching only as fallback. The `instrument` module is optional — not imported unless explicitly used.

#### 1.6 Transport Layer

The HTTP transport wraps `httpx.AsyncClient` with:

- **Connection pooling**: Persistent connections with keep-alive
- **Retry with backoff**: Exponential backoff on 429, 503, connection errors (configurable max_retries)
- **Rate limit awareness**: Reads `Retry-After` and `X-RateLimit-*` headers, backs off automatically
- **Cursor pagination**: `async for page in client.paginate(...)` iterator
- **Request ID propagation**: Forwards `X-Request-ID` for distributed tracing
- **Timeout configuration**: Per-request and client-level timeouts

A synchronous wrapper (`EngramSyncClient`) is provided for non-async contexts, using `asyncio.run()` internally.

### Layer 2: MCP Server (`engram-mcp` package)

A standalone MCP server exposing Engram as tools for any MCP-compatible client (Claude Desktop, Cursor, custom agents).

**7 tools:**

| Tool name | Description | Parameters |
|-----------|-------------|------------|
| `engram_record` | Record an observation or event | `content`, `event_type?`, `importance?`, `metadata?` |
| `engram_recall` | Retrieve context for current session | `query?`, `session_id?`, `template?`, `max_nodes?` |
| `engram_search` | Search across all sessions/entities | `query`, `max_nodes?`, `intents?` |
| `engram_trace` | Get provenance/lineage for a node | `node_id`, `max_depth?`, `intent?` |
| `engram_profile` | View user profile and preferences | `user_id` |
| `engram_entities` | List known entities with relationships | `limit?`, `entity_type?` |
| `engram_forget` | Request GDPR data deletion | `user_id` |

**Deployment:** `uvx engram-mcp` or Docker. Configurable via `ENGRAM_BASE_URL` and `ENGRAM_API_KEY` env vars.

**Session management:** The MCP server maintains a session per MCP connection. All `engram_record` calls within a connection share the same `session_id`. The session ends when the MCP connection closes.

### Layer 3: Framework Adapters

Each adapter is a thin wrapper that maps framework-specific interfaces to the core SDK.

#### LangChain / LangGraph (`engram[langchain]`)

```python
from engram.integrations.langchain import EngramMemory, EngramRetriever

# As conversation memory (auto-records human/AI turns)
memory = EngramMemory(client=engram_client, agent_id="my-agent")
chain = ConversationChain(llm=llm, memory=memory)

# As retriever (for RAG chains)
retriever = EngramRetriever(
    client=engram_client,
    session_id="s-123",
    include_lineage=True,
)

# As LangGraph tools (agent-controlled recording/recall)
from engram.integrations.langgraph import engram_tools
tools = engram_tools(client=engram_client)
agent = create_react_agent("openai:gpt-4o", tools=tools)
```

#### CrewAI (`engram[crewai]`)

```python
from engram.integrations.crewai import EngramCrewMemory

crew = Crew(
    agents=[researcher, coder, reviewer],
    memory=EngramCrewMemory(
        client=engram_client,
        shared_session=True,  # all agents share context
    ),
)
```

#### OpenAI Agents SDK (`engram[openai]`)

```python
from engram.integrations.openai_agents import EngramTools

tools = EngramTools(client=engram_client)
agent = Agent(
    name="coding-assistant",
    tools=[tools.record, tools.recall, tools.trace],
)
```

#### LlamaIndex (`engram[llamaindex]`)

```python
from engram.integrations.llamaindex import EngramRetriever

retriever = EngramRetriever(client=engram_client, session_id="s-123")
query_engine = RetrieverQueryEngine(retriever=retriever)
```

### Package Distribution

| Package | PyPI name | Dependencies | Contents |
|---------|-----------|-------------|----------|
| Core SDK | `engram` | `httpx`, `pydantic` | Simple API, Full API, Templates, Transport |
| MCP Server | `engram-mcp` | `engram`, `mcp` | MCP server + 7 tools |
| LangChain | `engram[langchain]` | `engram`, `langchain-core` | Memory, Retriever, Tools |
| CrewAI | `engram[crewai]` | `engram`, `crewai` | CrewMemory |
| OpenAI | `engram[openai]` | `engram`, `openai-agents` | Agent Tools |
| LlamaIndex | `engram[llamaindex]` | `engram`, `llama-index-core` | Retriever |
| Instrumentation | `engram[instrument]` | `engram` | Auto-patchers |

Extras are declared in `pyproject.toml` so `pip install engram[langchain]` pulls the right deps.

### New Server-Side Endpoints Required

| Endpoint | Purpose | ADR Impact |
|----------|---------|------------|
| `POST /v1/templates` | Create context template | Extends ADR-0006 |
| `GET /v1/templates/{id}` | Get template by ID | Extends ADR-0006 |
| `POST /v1/templates/{id}/render` | Render template for a session | Extends ADR-0006 |
| `POST /v1/sessions/{id}/end` | Explicitly end a session | Extends ADR-0013 |

The template storage can use Redis JSON (lightweight, no schema migration needed). Template rendering happens server-side to keep the SDK thin.

## Consequences

### Positive

- **5x reduction in integration code** — from ~25 lines to ~5 lines for basic usage
- **Competitive DX parity** — matches Mem0/Zep/Cognee on ease-of-use while exceeding them on graph depth
- **Framework reach** — adapters for 4+ major frameworks + MCP opens Engram to every MCP-compatible agent
- **Progressive disclosure** — Simple API doesn't sacrifice power; Full API is always available
- **Provenance as differentiator** — `trace()` and `%{lineage}` templates surface Engram's unique value through the SDK, not despite it
- **Auto-instrumentation** — zero-code adoption path for existing agent codebases

### Negative

- **Maintenance surface** — 6+ packages to maintain, test, and version
- **Server-side changes** — Context templates require new endpoints and storage
- **Version coupling** — SDK must stay compatible with server API; breaking server changes require SDK updates
- **Instrumentation fragility** — monkey-patching breaks on upstream library changes
- **Template complexity** — Template DSL is a new language to learn; may not be necessary for simple use cases

### Risks

| Risk | Mitigation |
|------|-----------|
| SDK version drift from server | Semantic versioning; SDK declares compatible server version range |
| Framework adapters lag upstream changes | Pin adapter deps to specific framework version ranges; CI matrix tests |
| MCP spec evolution | MCP is stabilizing; pin to specific MCP protocol version |
| Template DSL complexity | Templates are optional; Simple API works without them |
| Auto-instrumentation breaks on library updates | Instrumentation is opt-in; version-pin supported provider ranges |

## Alternatives Considered

### 1. Auto-generated SDK only (OpenAPI codegen)
Rejected. OpenAPI generators produce low-level typed HTTP clients but cannot provide session management, auto-instrumentation, context templates, or the `record`/`recall`/`trace` Simple API. An auto-generated client could serve as the transport layer underneath the handcrafted SDK.

### 2. Server-side "simple ingest" endpoint instead of SDK
Considered. A `POST /v1/simple/record` endpoint that auto-generates IDs server-side would reduce some SDK complexity. However, this doesn't solve context templates, auto-instrumentation, session management, or framework adapters. The SDK is still needed; a simple endpoint merely moves some auto-generation server-side.

### 3. Expose only MCP, no SDK
Rejected. MCP is powerful but limited to MCP-compatible clients. Python developers need a native SDK. Framework adapters need a Python client. MCP complements the SDK; it doesn't replace it.

### 4. Monorepo single package
Considered. Shipping all adapters in a single `engram` package with optional dependencies. Rejected because framework dependencies (langchain-core, crewai, etc.) are heavy and shouldn't be required for basic SDK usage. Extras (`engram[langchain]`) achieves the same UX with better dependency isolation.

## Implementation Phases

### Phase 1: Core SDK (2 weeks)
- `engram` package: Simple API, Full API, Transport, Pydantic models
- `EngramClient` + `EngramSyncClient`
- `SessionManager` with auto-ID generation
- Cursor pagination iterator
- Tests: unit + integration against running server
- PyPI publish

### Phase 2: MCP Server (1 week)
- `engram-mcp` package: 7 tools
- Session-per-connection management
- Tests: MCP protocol compliance
- PyPI publish

### Phase 3: Context Templates (1-2 weeks)
- Server-side: `/v1/templates` endpoints + Redis storage
- SDK-side: `ContextTemplate` class + template rendering
- Engram-specific directives (`%{lineage}`, `%{proactive}`)
- Tests: template parsing, rendering, round-trip

### Phase 4: Framework Adapters (2 weeks, parallelizable)
- LangChain/LangGraph adapter
- CrewAI adapter
- OpenAI Agents SDK adapter
- LlamaIndex adapter
- Tests: per-framework integration tests

### Phase 5: Auto-Instrumentation (1 week)
- OpenAI patcher
- Anthropic patcher
- LangChain callback handler
- Tests: verify event capture without explicit recording

---

## Amendment: Security Hardening (Post-Phase 2)

Date: 2026-02-28

### Context

After Phase 1 (Core SDK) and Phase 2 (MCP Server) were implemented with 91 SDK tests and 16 MCP tests, an adversarial red-teaming exercise identified **40+ vulnerabilities** across four attack surfaces. All tests at that point covered only happy paths. A 4-squad red team was deployed to write adversarial tests proving the vulnerabilities and then fix the source code.

### Attack Surface Analysis

| Category | Critical Findings |
|----------|------------------|
| **Injection** | Unvalidated path params (`session_id`, `entity_id`, `user_id`, `node_id`) interpolated directly into URLs. `entity_type` in MCP `engram_entities` tool interpolated into query string without sanitization. No input length limits. |
| **Resilience** | Infinite pagination loop (server sends `has_more: true` forever). `Retry-After` header accepted without cap (server forces 24-hour sleep). Malformed JSON responses surfaced raw `JSONDecodeError`. Sync client `future.result()` blocked forever on stuck coroutines. |
| **Security** | API key visible in `repr(EngramConfig)` — leaked via any logging or debugging. Empty string `""` accepted as valid API key. Environment variable parsing raised raw `ValueError` instead of `ConfigurationError`. Error messages forwarded server-side stack traces, file paths, and connection strings to callers. |
| **Concurrency** | Thread-unsafe global config singleton. Race condition in `SessionManager.record()` corrupting event chains under concurrent access. Duplicate `httpx.AsyncClient` creation under concurrent lazy initialization. MCP server `start()` callable twice, registering tools twice. |

### Decisions

#### D1: Input validation at SDK boundary

All path parameters are validated before URL interpolation via `_validate_path_param()` in `client.py`:
- Rejects empty/whitespace-only values
- Rejects path traversal characters (`..`, `/`, `\`)
- Rejects null bytes, CRLF, invisible unicode (RTL overrides, zero-width joiners)
- Rejects URL-encoded sequences (`%2e%2e`)
- Enforces maximum length (512 characters)

Numeric parameters validated via `_validate_numeric_param()`:
- `max_nodes`: 1–10,000
- `max_depth`: 1–100
- Payload size: max 10MB

MCP tools validated via `_validate_entity_type()` allowlist and `_safe_int()` bounds clamping:
- `entity_type` restricted to: `agent`, `user`, `service`, `tool`, `resource`, `concept`
- Content capped at 1MB, metadata at 100KB

**Rationale:** The SDK is the trust boundary. Input must be validated here, not deferred to the server, because (a) it prevents malformed requests from consuming network resources and (b) server-side validation may not catch URL path traversal.

#### D2: Resource exhaustion caps

Pagination hardened in `pagination.py`:
- `max_pages` parameter (default: 100) — stops iteration after N pages
- Cursor cycle detection — tracks seen cursors, stops on repeat
- Cursor size cap (4KB) — prevents memory abuse via oversized cursors

Transport hardened in `transport.py`:
- `Retry-After` capped at 60 seconds max
- NaN, infinity, negative values → safe defaults
- Sync client `future.result()` has timeout (`config.timeout + 5`)

**Rationale:** The SDK must be resilient to adversarial or misbehaving servers. A malicious server should not be able to cause the client to hang, loop, or sleep indefinitely.

#### D3: Credential protection in all representations

Config hardened in `config.py`:
- `EngramConfig.__repr__()` and `__str__()` redact `api_key` and `admin_key` as `"***"`
- Empty/whitespace API keys normalized to `None`
- Newlines in API keys rejected (`ConfigurationError`)
- `Bearer ` prefix auto-stripped to prevent double-prefix in auth headers
- Environment variable coercion wrapped: `ENGRAM_TIMEOUT="abc"` → `ConfigurationError` (not `ValueError`)
- Negative timeout/retries rejected at config time
- HTTP base URLs in non-localhost contexts emit a `UserWarning`

Error messages scrubbed in `transport.py`:
- `_scrub_credentials()` strips API keys, admin keys, passwords, tokens, and connection strings from all error messages and response bodies before surfacing to the caller

MCP error output scrubbed in `tools.py`:
- `_sanitize_error()` strips file paths, stack traces, connection strings, and credential patterns from all exception messages shown to LLM users

**Rationale:** SDK error messages are frequently logged, displayed in UIs, or forwarded to LLMs. Credentials and internal paths must never appear in any string representation.

#### D4: Concurrency safety via locking

Thread safety for global config in `config.py`:
- `threading.Lock` guards all access to `_global_config` (`get_config`, `configure`, `reset_config`)

Async safety for shared state:
- `sessions.py`: `asyncio.Lock` on `SessionManager.record()` and `end()`, with internal `_record_unlocked()` to avoid deadlock
- `simple.py`: `asyncio.Lock` on `_get_session()` lazy initialization
- `transport.py`: `asyncio.Lock` on `_ensure_client()` to prevent duplicate `httpx.AsyncClient` creation
- `server.py` (MCP): `_started` guard on `start()` to prevent double initialization; `asyncio.Lock` on event state

**Rationale:** The SDK is used from multi-threaded applications (sync client), concurrent async tasks (async client), and long-running MCP server connections. All shared mutable state must be protected.

### Files Modified

| File | Changes |
|------|---------|
| `sdk/engram/src/engram/client.py` | `_validate_path_param()`, `_validate_numeric_param()`, payload size check |
| `sdk/engram/src/engram/config.py` | `__repr__` redaction, key normalization, env coercion, `threading.Lock`, HTTP warning |
| `sdk/engram/src/engram/transport.py` | `Retry-After` cap, `_scrub_credentials()`, `asyncio.Lock` on `_ensure_client` |
| `sdk/engram/src/engram/pagination.py` | `max_pages`, cursor cycle detection, cursor size cap |
| `sdk/engram/src/engram/sync_client.py` | Timeout on `future.result()` |
| `sdk/engram/src/engram/sessions.py` | `asyncio.Lock`, `_record_unlocked()` |
| `sdk/engram/src/engram/simple.py` | `asyncio.Lock` on `_get_session()` |
| `sdk/engram-mcp/src/engram_mcp/server.py` | `_started` guard, `asyncio.Lock` |
| `sdk/engram-mcp/src/engram_mcp/tools.py` | `_validate_entity_type()`, `_safe_int()`, `_sanitize_error()`, size limits |

### Test Coverage

| Test File | Tests | Category |
|-----------|-------|----------|
| `sdk/engram/tests/test_injection.py` | 35 | Path traversal, Cypher injection, XSS, unicode, boundary values |
| `sdk/engram/tests/test_resilience.py` | 35 | Malformed responses, pagination DoS, retry manipulation, timeouts |
| `sdk/engram/tests/test_security.py` | 25 | Credential leakage, key validation, HTTPS enforcement, env coercion |
| `sdk/engram/tests/test_concurrency.py` | 44 | Config races, session races, transport races, sync client threads |
| `sdk/engram-mcp/tests/test_injection.py` | 31 | Record/recall/entity/forget injection |
| `sdk/engram-mcp/tests/test_resilience.py` | 10 | Error resilience, missing args, partial failures |
| `sdk/engram-mcp/tests/test_security.py` | 15 | Session hijacking, admin key enforcement, error disclosure |
| `sdk/engram-mcp/tests/test_concurrency.py` | 10 | Event chain concurrency, cancellation, server lifecycle |

**Total: 205 adversarial tests added. Combined with 91 existing SDK + 16 existing MCP = 312 total tests. Zero regressions.**

### Consequences

**Positive:**
- SDK is now defensively hardened against the OWASP API Security Top 10 categories relevant to client libraries
- Credential leakage risk eliminated from logging, error handling, and string representations
- Client cannot be weaponized against itself by a malicious server (DoS via pagination/retry)
- Concurrent usage is safe across threads (sync client) and async tasks (async client)

**Negative:**
- Input validation adds ~1-2ms overhead per client call (negligible vs network latency)
- `max_pages=100` default may need tuning for bulk export use cases (configurable)
- Locking in `SessionManager` serializes concurrent records within a single session (by design — event chain ordering requires it)

### Amendment: Typed Returns, Simple API, and Framework Adapter Packages (2026-03-04)

**Full Typed Client Methods (16/16):**
All `EngramClient` methods now return typed Pydantic v2 models instead of raw dicts. Complete method table:

| Method | Return Type |
|--------|------------|
| `record()` | `IngestResult` |
| `record_batch()` | `IngestResult` |
| `get_session_context()` | `AtlasResponse` |
| `query_subgraph()` | `AtlasResponse` |
| `get_entity()` | `AtlasResponse` |
| `get_lineage()` | `AtlasResponse` |
| `get_user_preferences()` | `list[PreferenceNode]` |
| `get_user_skills()` | `list[SkillNode]` |
| `get_user_patterns()` | `list[BehavioralPatternNode]` |
| `get_user_interests()` | `list[InterestNode]` |
| `export_user_data()` | `GDPRExportResponse` |
| `delete_user()` | `GDPRDeleteResponse` |
| `stats()` | `StatsResponse` |
| `reconsolidate()` | `ReconsolidateResponse` |
| `prune()` | `PruneResponse` |
| `health_detailed()` | `DetailedHealthResponse` |

All response models use `model_config = {"extra": "allow"}` for forward compatibility with future server-side field additions.

**AtlasResponse Convenience Methods:**
- `.node_ids -> list[str]` — extracts all node IDs from the response
- `.texts() -> list[str]` — extracts primary text from each node using a priority key list: `content`, `payload_ref`, `summary`, `text`, `belief_text`, `description`, `name`
- `.as_context_string(separator="\n---\n") -> str` — formats nodes as an LLM-injectable context block: `[NodeType] text (score: X.XX)`

**Simple API — add() and search():**
Two ultra-simple methods for the "3 lines to first value" experience:
- `add(text, user_id=None, agent_id="default", importance=None) -> IngestResult` — wraps `record()` with `event_type="observation.output"`
- `search(query, user_id=None, top_k=10) -> list[Memory]` — wraps `query_subgraph()`, extracts text from nodes, returns flat list sorted by score

The `Memory` model: `text: str`, `confidence: float`, `source_session: str | None`, `created_at: str | None`, `memory_id: str`, `node_type: str`, `score: float`

**Session Lifecycle Management:**
- `aclose()` — gracefully ends the active session and closes the HTTP client. Safe to call multiple times (idempotent).
- `configure()` now emits `ResourceWarning` if called while a session is already active, alerting developers to potential session leaks.

**LangChain Adapter — Separate Package:**
The LangChain integration is a separate package (`sdk/engram-langchain/`, PyPI: `engram-langchain`) rather than an optional extra. Three adapter classes:

| Class | Base Class | Purpose |
|-------|-----------|---------|
| `EngramCallbackHandler` | `BaseCallbackHandler` | Auto-records chain/tool/LLM actions as Engram events |
| `EngramRetriever` | `BaseRetriever` | Queries Engram subgraph, returns LangChain `Document` objects |
| `EngramChatMessageHistory` | `BaseChatMessageHistory` | Persists conversation history through Engram events |

Note: The originally-specified `EngramMemory` class has been replaced by `EngramChatMessageHistory`, which implements LangChain's standard `BaseChatMessageHistory` interface.

**CrewAI Adapter — Separate Package:**
The CrewAI integration is a separate package (`sdk/engram-crewai/`, PyPI: `engram-crewai`) rather than an optional extra. One adapter class:

| Class | Purpose |
|-------|---------|
| `EngramStorageBackend` | Custom memory storage for CrewAI with sync and async dual-mode support |

Maps CrewAI scopes to Engram session IDs. Implements `save()`, `search()`, `delete()`, `list_scopes()`.

Note: The originally-specified `EngramCrewMemory` class has been replaced by `EngramStorageBackend`.
