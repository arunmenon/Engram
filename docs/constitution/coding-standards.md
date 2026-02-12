# Engram Context Graph -- Coding Standards

> Canonical reference for all contributors. This document is the authoritative source
> for import rules, async patterns, naming conventions, error handling, and data store
> write patterns. When in doubt, follow what is written here.

---

## 1. Import Rules

The dependency graph flows strictly inward: **outer layers depend on inner layers, never the reverse.**

```
api/  worker/  -->  adapters/  -->  ports/  -->  domain/
```

### `domain/` -- Zero Framework Imports

The domain package is pure Python plus Pydantic v2. It MUST NOT import:

- FastAPI, Starlette, or any ASGI framework
- `redis`, `neo4j`, or any data store client
- `structlog` (logging is a side effect; domain functions return results)
- Any adapter or API module

Allowed imports:

- Python standard library (`uuid`, `datetime`, `re`, `enum`, `typing`, etc.)
- `pydantic` and `pydantic.Field` for model definitions
- Other `domain/` submodules

```python
# CORRECT -- domain/models.py
from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

# WRONG -- domain/models.py
from fastapi import HTTPException    # Framework import in domain
from redis import Redis              # Adapter import in domain
import structlog                     # Side-effect import in domain
```

### `ports/` -- Only `typing.Protocol`

Port interfaces define structural contracts via `typing.Protocol`. They MUST NOT import:

- FastAPI, Redis, Neo4j, or any concrete framework
- Adapter implementations

Allowed imports:

- `typing.Protocol`, `typing.Any`, other typing constructs
- `domain/` models and types (the contracts reference domain objects)

```python
# CORRECT -- ports/event_store.py
from typing import Protocol
from context_graph.domain.models import Event, EventQuery

class EventStore(Protocol):
    async def append(self, event: Event) -> str: ...

# WRONG -- ports/event_store.py
from redis.asyncio import Redis      # Concrete implementation in port
```

### `adapters/` -- Framework + Domain + Ports

Each adapter imports exactly:

- Its specific framework (`redis.asyncio`, `neo4j.AsyncGraphDatabase`)
- `domain/` models and types
- `ports/` protocol interfaces (to satisfy structural subtyping)

Adapters MUST NOT import from `api/` or `worker/`.

```python
# CORRECT -- adapters/redis/store.py
from redis.asyncio import Redis
from context_graph.domain.models import Event
from context_graph.ports.event_store import EventStore
```

### `api/` -- FastAPI + Domain + Ports

The API layer imports:

- FastAPI, Pydantic request/response models
- `domain/` models
- `ports/` interfaces (injected via FastAPI dependency injection)

The API layer MUST NOT import adapter implementations directly. Adapters are wired at application startup in `api/app.py` and injected through FastAPI's `Depends()`.

```python
# CORRECT -- api/routes/events.py
from fastapi import APIRouter, Depends
from context_graph.domain.models import Event
from context_graph.ports.event_store import EventStore

# WRONG -- api/routes/events.py
from context_graph.adapters.redis.store import RedisEventStore  # Direct adapter import
```

### `worker/` -- Domain + Ports + Adapters

The worker process wires adapters to ports at startup. It may import:

- `domain/` models, validation, projection logic
- `ports/` interfaces
- `adapters/` concrete implementations (for wiring only)

---

## 2. Async Patterns

### All I/O is Async

Every function that performs I/O (network, disk, database) MUST be declared `async def`. This includes:

- All port interface methods
- All adapter implementations
- All API route handlers
- All worker processing functions

```python
# CORRECT
async def append(self, event: Event) -> str:
    await self._redis.execute_command(...)

# WRONG -- blocking I/O in async context
def append(self, event: Event) -> str:
    self._redis.execute_command(...)  # Blocks the event loop
```

### Never Block the Event Loop

Do not call blocking I/O functions inside async code. Specifically:

- Never use synchronous `redis` client methods; always use `redis.asyncio`
- Never use synchronous `neo4j` driver methods; always use `AsyncGraphDatabase`
- Never call `time.sleep()`; use `asyncio.sleep()`
- Never use `requests`; use `httpx.AsyncClient`

If you must call a blocking library, offload it:

```python
import asyncio

result = await asyncio.to_thread(blocking_function, arg1, arg2)
```

### Use `asyncio.TaskGroup` for Concurrency

When executing multiple independent async operations, use `asyncio.TaskGroup` (Python 3.11+):

```python
async def enrich_events(events: list[Event]) -> list[EnrichedEvent]:
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(enrich_single(e)) for e in events]
    return [t.result() for t in tasks]
```

### Async Context Managers for Resources

All resources with connection lifecycles (Redis pool, Neo4j driver) MUST implement `__aenter__` / `__aexit__` or provide an explicit `close()` method that is called during shutdown.

---

## 3. Naming Conventions

### Event Types

Dot-namespaced, all lowercase. Format: `<category>.<action>[.<sub_action>]`

```
agent.invoke
tool.execute
llm.chat
llm.completion
observation.input
system.session_start
user.preference.stated
user.skill.declared
```

Pattern: `^[a-z][a-z0-9]*(\.[a-z][a-z0-9_]*)+$`

Known prefixes: `agent`, `tool`, `llm`, `observation`, `system`, `user`

### Edge Types

UPPER_SNAKE_CASE. These are Neo4j relationship types.

```
CAUSED_BY
FOLLOWS
SIMILAR_TO
REFERENCES
SUMMARIZES
SAME_AS
RELATED_TO
HAS_PROFILE
HAS_PREFERENCE
HAS_SKILL
DERIVED_FROM
EXHIBITS_PATTERN
INTERESTED_IN
ABOUT
ABSTRACTED_FROM
PARENT_SKILL
```

### Redis Keys

Colon-namespaced. The colon acts as a logical separator for key hierarchies.

```
evt:{event_id}           -- Single event JSON document
events:__global__        -- Global event stream
dedup:events             -- Dedup sorted set
idx:events               -- RediSearch index name
session:{session_id}     -- Session metadata
```

### Neo4j Node Labels

PascalCase. These are Neo4j node labels.

```
Event
Entity
Summary
UserProfile
Preference
Skill
Workflow
BehavioralPattern
```

### Python Modules

snake_case for all module and package names.

```
domain/models.py
domain/validation.py
domain/projection.py
adapters/redis/store.py
adapters/neo4j/store.py
api/routes/events.py
worker/projector.py
```

### Pydantic Models

PascalCase for all model class names.

```python
class Event(BaseModel): ...
class AtlasResponse(BaseModel): ...
class SubgraphQuery(BaseModel): ...
class EventNode(BaseModel): ...
class PreferenceNode(BaseModel): ...
```

### Python Variables and Functions

snake_case for all variables, functions, and methods.

```python
event_store = RedisEventStore(...)
async def get_by_session(self, session_id: str) -> list[Event]: ...
validation_result = validate_event(event)
```

### Constants

UPPER_SNAKE_CASE for module-level constants.

```python
MAX_PAYLOAD_REF_LENGTH = 2048
MAX_FUTURE_DRIFT_SECONDS = 300
KNOWN_PREFIXES = frozenset({"agent", "tool", "llm", "observation", "system", "user"})
```

---

## 4. Error Handling

### Domain Exceptions

All domain-specific exceptions are defined in `domain/exceptions.py`. They carry structured context, not HTTP status codes.

```python
# domain/exceptions.py
class ContextGraphError(Exception):
    """Base exception for all domain errors."""

class ValidationError(Exception):
    """Raised when event validation fails."""
    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message

class EventNotFoundError(ContextGraphError):
    """Raised when a referenced event does not exist."""

class SessionNotFoundError(ContextGraphError):
    """Raised when a session has no events."""

class QueryBoundsExceededError(ContextGraphError):
    """Raised when a query exceeds depth/node/timeout limits."""
```

### Caught at the API Boundary

Domain functions return results or raise domain exceptions. They NEVER raise `HTTPException` or produce HTTP status codes. The API layer catches domain exceptions in middleware and maps them to HTTP responses.

```python
# CORRECT -- domain function returns a result
def validate_event(event: Event) -> ValidationResult:
    result = ValidationResult()
    if not EVENT_TYPE_PATTERN.match(event.event_type):
        result.add_error("event_type", "Must be dot-namespaced")
    return result

# CORRECT -- API route catches and maps
@router.post("/events")
async def ingest_event(event: Event, store: EventStore = Depends(get_store)):
    result = validate_event(event)
    if not result.is_valid:
        raise HTTPException(status_code=422, detail=[...])
    position = await store.append(event)
    return {"global_position": position}

# WRONG -- domain function raises HTTP exception
def validate_event(event: Event) -> None:
    if not EVENT_TYPE_PATTERN.match(event.event_type):
        raise HTTPException(status_code=422)  # Framework coupling in domain
```

### Structured Logging with structlog

Use `structlog` for all logging outside the domain layer. Log entries include structured context, not string interpolation.

```python
import structlog

logger = structlog.get_logger()

# CORRECT
logger.info("event_ingested", event_id=str(event.event_id), session_id=event.session_id)

# WRONG
logger.info(f"Event {event.event_id} ingested for session {event.session_id}")
```

### Never Swallow Exceptions Silently

Always log exceptions before re-raising or handling them. Use `logger.exception()` for unexpected errors.

```python
try:
    await store.append(event)
except Exception:
    logger.exception("event_append_failed", event_id=str(event.event_id))
    raise
```

---

## 5. Neo4j Write Patterns

### MERGE, Never CREATE (for Existing Types)

All node and relationship writes MUST use `MERGE` to maintain idempotency. The projection worker may re-process events (after restart, replay, etc.), and `CREATE` would produce duplicates.

```cypher
-- CORRECT
MERGE (e:Event {event_id: $event_id})
ON CREATE SET e.event_type = $event_type, e.occurred_at = $occurred_at, ...
ON MATCH SET e.last_accessed_at = $now

-- WRONG
CREATE (e:Event {event_id: $event_id, ...})
```

### UNWIND + MERGE for Batch Operations

When projecting multiple events, always use the UNWIND batch pattern for performance. Never loop individual MERGE statements from Python.

```cypher
UNWIND $events AS evt
MERGE (e:Event {event_id: evt.event_id})
ON CREATE SET
    e.event_type = evt.event_type,
    e.occurred_at = evt.occurred_at,
    e.session_id = evt.session_id,
    e.agent_id = evt.agent_id,
    e.trace_id = evt.trace_id,
    e.global_position = evt.global_position
```

Recommended batch size: 100-500 events (validated at 124ms for 1000 MERGEs in Phase 0).

### Writes Go Through the Projection Worker Only

The API layer MUST NOT write directly to Neo4j. The data flow is:

```
API  -->  Redis (event store)  -->  Projection Worker  -->  Neo4j (graph)
```

This ensures:

1. Redis remains the source of truth
2. Neo4j is fully rebuildable from Redis events
3. Write contention on Neo4j is bounded to the worker process

### Transaction Functions

Always use Neo4j transaction functions (`execute_write`, `execute_read`) rather than raw sessions. The driver handles retries for transient errors.

```python
# CORRECT
async with driver.session() as session:
    result = await session.execute_write(merge_events_tx, events=batch)

# WRONG
async with driver.session() as session:
    tx = await session.begin_transaction()
    await tx.run("MERGE ...")
    await tx.commit()
```

---

## 6. Redis Patterns

### Atomic Operations via Lua Scripts

Multi-step Redis operations that must be atomic (dedup check + stream write + JSON store) MUST use Lua scripts executed via `EVALSHA`. Never rely on Python-side transaction pipelines for atomicity.

```python
# Lua script for idempotent event ingestion:
# 1. Check dedup sorted set
# 2. If new: XADD to stream + JSON.SET for document + ZADD to dedup set
# 3. If duplicate: return existing stream ID
```

Lua scripts are stored in `src/context_graph/adapters/redis/lua/` and loaded at adapter startup via `SCRIPT LOAD`.

### Idempotent Ingestion

All event writes go through the idempotent ingestion Lua script. The dedup mechanism uses a Redis sorted set (`dedup:events`) keyed by `event_id`. Duplicate submissions return the original stream entry ID without writing.

### Consumer Groups for All Stream Reads

Stream consumers MUST use `XREADGROUP`, never raw `XREAD`. This ensures:

- At-least-once delivery semantics
- Message acknowledgment tracking via PEL (Pending Entries List)
- Multiple independent consumer groups on the same stream

Consumer group names follow ADR-0013:

```
graph-projection      -- Projection worker (Redis -> Neo4j)
session-extraction    -- Knowledge extraction pipeline
enrichment            -- Embedding + importance scoring
consolidation         -- Summary + decay processing
```

### RediSearch for Secondary Queries

All event queries beyond direct key lookup (`evt:{event_id}`) MUST use RediSearch (`FT.SEARCH`). This includes:

- Query by `session_id`
- Query by `agent_id`
- Query by `event_type`
- Time range queries on `occurred_at`
- Combined filter queries

RediSearch index: `idx:events`

Important: Tag fields require escaping of hyphens and dots in query strings (e.g., `sess\\-alpha`, `tool\\.execute`).

### Key Expiration and Retention

- Stream entries: trimmed via `XTRIM MINID` after the hot window (default: 7 days)
- JSON documents: retained for the full retention ceiling (default: 90 days)
- Stream trimming does NOT affect JSON documents -- they are independent

---

## 7. Pydantic Conventions

### Strict Mode for Events

The `Event` model uses `model_config = {"strict": True}` to prevent type coercion. A string passed where a UUID is expected will raise a validation error, not silently coerce.

### Field Constraints via `Field()`

Use `Field()` for all numeric bounds, string constraints, and documentation:

```python
max_nodes: int = Field(default=100, ge=1, le=500)
session_id: str = Field(..., min_length=1)
importance_hint: int | None = Field(default=None, ge=1, le=10)
```

### Union Types Use `X | None`

Use PEP 604 union syntax, not `Optional[X]`:

```python
# CORRECT
tool_name: str | None = None

# WRONG
tool_name: Optional[str] = None
```

---

## 8. Configuration

### All Settings in `settings.py`

No hardcoded magic numbers anywhere in the codebase. Every tunable value lives in `settings.py` as a Pydantic `BaseSettings` field with a sensible default and an environment variable override.

Environment variable prefix: `CG_` (nested: `CG_REDIS_`, `CG_NEO4J_`, `CG_DECAY_`, etc.)

```python
# CORRECT
from context_graph.settings import Settings
settings = Settings()
max_depth = settings.query.default_max_depth

# WRONG
max_depth = 3  # Magic number
```

---

## 9. API Response Pattern

All graph query endpoints return the Atlas response pattern:

```json
{
  "nodes": { "<node-id>": { "node_type": "...", "attributes": {}, "provenance": {}, "scores": {} } },
  "edges": [{ "source": "...", "target": "...", "edge_type": "..." }],
  "pagination": { "cursor": null, "has_more": false },
  "meta": { "query_ms": 120, "nodes_returned": 12, "truncated": false }
}
```

Use `ORJSONResponse` for JSON serialization in all API responses.

---

## 10. Type Annotations

### Full Type Annotations Everywhere

Every function signature, variable assignment, and return type MUST have explicit type annotations. `mypy --strict` is enforced in CI.

```python
# CORRECT
async def get_by_session(
    self,
    session_id: str,
    limit: int = 100,
    after: str | None = None,
) -> list[Event]:
    ...

# WRONG -- missing return type
async def get_by_session(self, session_id, limit=100, after=None):
    ...
```

### Use `from __future__ import annotations`

Every module MUST include this import for deferred annotation evaluation (PEP 563). This enables forward references and consistent behavior with stringified annotations.
