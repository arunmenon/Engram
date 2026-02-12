# Engram Context Graph -- Testing Strategy

> Canonical reference for test organization, infrastructure, naming conventions,
> coverage targets, and test data factories. All contributors must follow these
> standards when writing or modifying tests.

---

## 1. Test Pyramid

The project follows a strict test pyramid with clear boundaries between layers:

```
        /----------\
       /   10% e2e  \          Full API flows through FastAPI TestClient
      /   (API flows) \        Requires all services running
     /------------------\
    /   30% integration   \    Redis adapter, Neo4j adapter, projection pipeline
   /   (adapter + pipeline) \  Requires Docker services (Redis Stack + Neo4j)
  /--------------------------\
 /      60% unit tests        \  Domain logic, validation, scoring, models
/  (domain, validation, pure)  \  Zero external dependencies
\------------------------------/
```

### Unit Tests (60%)

- **Scope**: Domain models, validation rules, scoring algorithms, projection logic, query parsing
- **Dependencies**: None. Zero network calls, zero Docker, zero file I/O
- **Speed**: Entire unit suite must complete in under 10 seconds
- **Location**: `tests/unit/`

### Integration Tests (30%)

- **Scope**: Redis adapter (event store), Neo4j adapter (graph store), projection worker pipeline, end-to-end event ingestion through projection
- **Dependencies**: Docker services (Redis Stack + Neo4j), started via `docker compose`
- **Speed**: Entire integration suite should complete in under 60 seconds
- **Location**: `tests/integration/`

### End-to-End Tests (10%)

- **Scope**: Full API request/response flows through FastAPI's `TestClient`, including serialization, middleware, error handling, and the Atlas response format
- **Dependencies**: Docker services + running application (or TestClient with wired adapters)
- **Speed**: Entire e2e suite should complete in under 30 seconds
- **Location**: `tests/e2e/`

---

## 2. Test Infrastructure

### Framework and Plugins

| Tool | Version | Purpose |
|------|---------|---------|
| `pytest` | >= 8.0 | Test runner |
| `pytest-asyncio` | >= 0.24 | Async test support |
| `pytest-cov` | >= 6.0 | Coverage reporting |
| `httpx` | >= 0.28 | Async HTTP client for API tests |
| `ruff` | >= 0.8 | Linting of test files |
| `mypy` | >= 1.13 | Type checking of test files |

### Async Mode

All async tests use `asyncio_mode = "auto"` (configured in `pyproject.toml`). This means:

- Test functions declared as `async def` are automatically treated as async tests
- No need for `@pytest.mark.asyncio` decorator on individual tests
- All tests share the same event loop policy

```python
# CORRECT -- auto mode handles this
async def test_event_append_returns_stream_id(redis_store):
    event = make_event()
    position = await redis_store.append(event)
    assert position is not None

# UNNECESSARY -- auto mode makes this redundant
@pytest.mark.asyncio
async def test_event_append_returns_stream_id(redis_store):
    ...
```

### Docker Services for Integration Tests

Integration and e2e tests require:

| Service | Image | Ports |
|---------|-------|-------|
| Redis Stack | `redis/redis-stack:latest` | 6379, 8001 (RedisInsight) |
| Neo4j | `neo4j:5-community` | 7474 (HTTP), 7687 (Bolt) |

Start services before running integration tests:

```bash
make docker-up            # Starts all services
make integration          # Runs integration tests
make docker-down          # Stops services
```

Or manually:

```bash
docker compose -f docker/docker-compose.yml up -d
pytest tests/integration -v --tb=short -m integration
```

### Shared Fixtures in `tests/conftest.py`

All reusable fixtures live in `tests/conftest.py`. Layer-specific conftest files are allowed:

```
tests/
    conftest.py                 # Shared fixtures (event factories, settings)
    unit/
        conftest.py             # Unit-specific fixtures (if needed)
    integration/
        conftest.py             # Redis/Neo4j connection fixtures
    e2e/
        conftest.py             # FastAPI TestClient fixture
```

### Key Fixtures

```python
# tests/conftest.py

@pytest.fixture
def settings() -> Settings:
    """Application settings with test overrides."""
    return Settings(
        debug=True,
        log_level="DEBUG",
    )

# tests/integration/conftest.py

@pytest.fixture
async def redis_client():
    """Connected Redis client. Flushes DB before each test."""
    client = Redis(host="localhost", port=6379, db=0)
    await client.flushdb()
    yield client
    await client.aclose()

@pytest.fixture
async def redis_store(redis_client) -> RedisEventStore:
    """Wired Redis event store adapter."""
    store = RedisEventStore(redis_client)
    await store.initialize()
    yield store
    await store.close()

@pytest.fixture
async def neo4j_driver():
    """Connected Neo4j async driver. Clears database before each test."""
    driver = AsyncGraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "engram-dev-password"))
    async with driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")
    yield driver
    await driver.close()

@pytest.fixture
async def graph_store(neo4j_driver) -> Neo4jGraphStore:
    """Wired Neo4j graph store adapter."""
    store = Neo4jGraphStore(neo4j_driver)
    yield store
    await store.close()
```

---

## 3. Event Factories

All test data is built using factory functions in `tests/fixtures/events.py`. Tests MUST NOT construct `Event` objects with inline field values. Use the factories to ensure consistency and reduce boilerplate.

### `make_event()` -- Single Event with Sensible Defaults

```python
from tests.fixtures.events import make_event

def test_validation_accepts_valid_event():
    event = make_event()
    result = validate_event(event)
    assert result.is_valid

def test_validation_rejects_bad_event_type():
    event = make_event(event_type="INVALID")
    result = validate_event(event)
    assert not result.is_valid
```

Factory signature:

```python
def make_event(
    *,
    event_id: UUID | None = None,
    event_type: str = "agent.invoke",
    occurred_at: datetime | None = None,
    session_id: str = "test-session-001",
    agent_id: str = "test-agent-001",
    trace_id: str = "test-trace-001",
    payload_ref: str = "s3://test-bucket/payload.json",
    tool_name: str | None = None,
    parent_event_id: UUID | None = None,
    ended_at: datetime | None = None,
    status: EventStatus | None = None,
    schema_version: int = 1,
    importance_hint: int | None = None,
    global_position: str | None = None,
) -> Event:
    """Build a single Event with sensible defaults. Override any field by name."""
    ...
```

### `make_session_events(n)` -- Sequence of Events in a Session

Produces `n` events sharing the same `session_id` and `trace_id`, with monotonically increasing `occurred_at` timestamps and linked `parent_event_id` chains.

```python
def test_session_retrieval_returns_all_events(redis_store):
    events = make_session_events(5, session_id="sess-abc")
    for e in events:
        await redis_store.append(e)
    result = await redis_store.get_by_session("sess-abc")
    assert len(result) == 5
```

Factory signature:

```python
def make_session_events(
    n: int,
    *,
    session_id: str = "test-session-001",
    agent_id: str = "test-agent-001",
    trace_id: str = "test-trace-001",
    start_time: datetime | None = None,
    interval_seconds: int = 1,
) -> list[Event]:
    """Build a sequence of n events in a single session with causal chain."""
    ...
```

### `make_tool_event()` -- Tool Execution Event

Convenience factory for `tool.execute` events with `tool_name` pre-filled.

```python
def make_tool_event(
    *,
    tool_name: str = "web_search",
    parent_event_id: UUID | None = None,
    **kwargs,
) -> Event:
    """Build a tool.execute event with tool_name set."""
    return make_event(
        event_type="tool.execute",
        tool_name=tool_name,
        parent_event_id=parent_event_id,
        **kwargs,
    )
```

### Additional Factories

As the project grows, add factories for:

- `make_event_node()` -- EventNode for graph store tests
- `make_entity_node()` -- EntityNode for graph store tests
- `make_preference_node()` -- PreferenceNode for user personalization tests
- `make_atlas_response()` -- AtlasResponse for API response tests

All factories follow the same pattern: keyword-only arguments, sensible defaults, override any field.

---

## 4. Coverage Targets

| Package | Target | Rationale |
|---------|--------|-----------|
| `domain/` | 90% | Core business logic. Must be exhaustively tested. |
| `adapters/` | 80% | I/O-heavy code. Integration tests cover most paths. |
| `api/` | 85% | Route handlers, middleware, error mapping. |
| `worker/` | 75% | Projection loop, cursor management. Some paths are hard to trigger in tests. |
| **Overall** | **80%** | Enforced by `fail_under = 70` in pyproject.toml (will be raised as coverage improves). |

### Measuring Coverage

```bash
# Run with coverage
pytest tests/ --cov=src/context_graph --cov-report=html --cov-report=term-missing

# View HTML report
open htmlcov/index.html
```

### What Counts Toward Coverage

- Unit tests, integration tests, and e2e tests all contribute to the same coverage report
- Infrastructure validation tests (`tests/infra/`) do NOT count toward coverage (they test Docker services, not application code)

### Excluded from Coverage

The following are excluded via `[tool.coverage.run] omit`:

- `*/tests/*` -- Test code itself
- Third-party packages

---

## 5. Naming Conventions

### Test Files

Mirror the source module path with a `test_` prefix:

```
src/context_graph/domain/models.py       -->  tests/unit/domain/test_models.py
src/context_graph/domain/validation.py   -->  tests/unit/domain/test_validation.py
src/context_graph/adapters/redis/store.py --> tests/integration/adapters/test_redis_store.py
src/context_graph/adapters/neo4j/store.py --> tests/integration/adapters/test_neo4j_store.py
src/context_graph/api/routes/events.py   -->  tests/e2e/test_events_api.py
src/context_graph/worker/projector.py    -->  tests/integration/worker/test_projector.py
```

### Test Functions

Use the pattern: `test_{behavior}_when_{condition}`

```python
# Describes WHAT the code does WHEN a specific condition holds
def test_validation_succeeds_when_event_is_well_formed():
    ...

def test_validation_fails_when_event_type_missing_dot():
    ...

def test_append_returns_stream_id_when_event_is_new():
    ...

def test_append_returns_existing_id_when_event_is_duplicate():
    ...

def test_subgraph_query_returns_atlas_response_when_session_has_events():
    ...

def test_subgraph_query_raises_when_max_depth_exceeded():
    ...
```

### Test Classes

Group related tests into classes. Class names use `Test` prefix + the concept being tested:

```python
class TestEventValidation:
    """Tests for domain/validation.py validate_event()."""

    def test_accepts_valid_event(self):
        ...

    def test_rejects_self_referential_parent(self):
        ...

    def test_rejects_future_timestamp(self):
        ...


class TestRedisEventStoreAppend:
    """Tests for RedisEventStore.append() method."""

    async def test_returns_stream_id(self, redis_store):
        ...

    async def test_is_idempotent(self, redis_store):
        ...
```

### Pytest Markers

```python
@pytest.mark.unit          # No external dependencies
@pytest.mark.integration   # Requires Docker services
@pytest.mark.infra         # Infrastructure validation (Phase 0)
```

Run by marker:

```bash
pytest -m unit                # Unit tests only
pytest -m integration         # Integration tests only
pytest -m "not infra"         # Everything except infra validation
```

---

## 6. Test Organization

### Directory Structure

```
tests/
    __init__.py
    conftest.py                      # Shared fixtures, factories import
    fixtures/
        __init__.py
        events.py                    # Event factory functions
        nodes.py                     # Node factory functions (Phase 2+)
        responses.py                 # Atlas response factory (Phase 3+)
    unit/
        __init__.py
        conftest.py
        domain/
            __init__.py
            test_models.py           # Pydantic model validation
            test_validation.py       # Event envelope validation
            test_projection.py       # Event -> graph transform logic
            test_lineage.py          # Traversal algorithms
            test_scoring.py          # Decay + relevance scoring (Phase 3)
    integration/
        __init__.py
        conftest.py                  # Redis/Neo4j connection fixtures
        adapters/
            __init__.py
            test_redis_store.py      # Redis EventStore adapter
            test_neo4j_store.py      # Neo4j GraphStore adapter
        worker/
            __init__.py
            test_projector.py        # Projection pipeline end-to-end
    e2e/
        __init__.py
        conftest.py                  # FastAPI TestClient fixture
        test_events_api.py           # Event ingestion endpoints
        test_context_api.py          # Context retrieval endpoints
        test_query_api.py            # Subgraph query endpoints
        test_lineage_api.py          # Lineage traversal endpoints
        test_health_api.py           # Health check endpoint
    infra/
        __init__.py
        test_redis.py               # Redis capability validation (FROZEN)
        test_neo4j.py               # Neo4j capability validation (FROZEN)
```

---

## 7. Integration Test Patterns

### Database Isolation

Every integration test starts with a clean database state:

- **Redis**: `FLUSHDB` before each test via fixture
- **Neo4j**: `MATCH (n) DETACH DELETE n` before each test via fixture

This ensures test independence. Tests must never depend on state from a prior test.

### Async Fixture Lifecycle

```python
@pytest.fixture
async def redis_store():
    # Setup: create and initialize
    store = await create_redis_store()
    await store.initialize()

    yield store

    # Teardown: clean up
    await store.close()
```

### Testing Idempotency

All adapter write tests MUST include an idempotency check:

```python
async def test_append_is_idempotent(redis_store):
    event = make_event()
    pos1 = await redis_store.append(event)
    pos2 = await redis_store.append(event)  # Same event again
    assert pos1 == pos2  # Returns same position, does not duplicate
```

### Testing the Projection Pipeline

End-to-end projection tests verify the full data flow:

```python
async def test_projection_pipeline(redis_store, graph_store, projector):
    # 1. Ingest events into Redis
    events = make_session_events(5)
    for e in events:
        await redis_store.append(e)

    # 2. Run projection worker
    processed = await projector.process_batch(batch_size=10)
    assert processed == 5

    # 3. Verify events appear in Neo4j
    response = await graph_store.get_context(session_id="test-session-001")
    assert response.meta.nodes_returned == 5
```

---

## 8. Test Quality Rules

### No Mocks for Domain Logic

Domain functions are pure. Test them directly with real inputs and assert real outputs. Do not mock domain internals.

### Mocks Allowed for External Services

When testing adapters in isolation (without Docker), use `unittest.mock.AsyncMock` to simulate the external client. However, prefer real integration tests when Docker is available.

### No Sleep in Tests

Never use `asyncio.sleep()` or `time.sleep()` in tests. If you need to wait for an async operation, use proper await or polling with a timeout.

### Assertions Must Be Specific

```python
# CORRECT -- specific assertions
assert result.is_valid is True
assert len(result.errors) == 0
assert response.meta.nodes_returned == 5
assert response.nodes["evt-001"].node_type == "Event"

# WRONG -- vague assertions
assert result  # Truthy check tells you nothing on failure
assert response.nodes  # What are you checking?
```

### One Concept Per Test

Each test function verifies a single behavior or edge case. Do not test multiple unrelated behaviors in one function.

```python
# CORRECT -- focused tests
def test_validation_rejects_self_referential_parent():
    ...

def test_validation_rejects_future_timestamp():
    ...

# WRONG -- combined test
def test_validation_rejects_bad_events():
    # Tests 5 different things in one function
    ...
```
