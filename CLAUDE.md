# Context Graph — Project Guide

## Overview

A traceability-first context graph service for AI agents. Captures immutable event records of agent/tool actions, projects them into a graph for lineage queries, and returns provenance-annotated context to agents.

## Architecture (from ADRs)

- **Stack**: Python 3.12+ / FastAPI / Pydantic v2
- **Dual Store**: Postgres (source of truth, immutable event ledger) + Neo4j (query-optimized graph projection)
- **Projection**: Async worker polls Postgres events → UNWIND+MERGE into Neo4j
- **API**: REST endpoints at `/v1/` for event ingest, session context retrieval, subgraph query, and node lineage

## Key Design Principles

1. **Traceability over memory** — every piece of context must have provenance back to source events
2. **Immutable events** — never mutate the event ledger; append-only with idempotent ingestion (`ON CONFLICT DO NOTHING`)
3. **Derived projection** — Neo4j is disposable and rebuildable from Postgres events
4. **Framework-agnostic domain** — `domain/` package must have zero imports from FastAPI or any web framework
5. **Bounded queries** — all graph queries enforce depth, node count, and timeout limits

## Project Structure

```
src/context_graph/
    settings.py           # Pydantic BaseSettings
    domain/               # Pure Python — NO framework imports
        models.py         # Event, Node, Edge, Session models
        validation.py     # Event envelope rules
        projection.py     # Event → graph transform logic
        lineage.py        # Traversal algorithms
    ports/                # typing.Protocol interfaces
        event_store.py
        graph_store.py
    adapters/
        postgres/         # asyncpg EventStore implementation
        neo4j/            # Neo4j async GraphStore implementation
    api/                  # FastAPI layer
        app.py            # Factory: create_app()
        routes/           # events, context, query, lineage, health
    worker/               # Projection worker (separate process)
        projector.py
        cursor.py
```

## Event Schema

Events must include: `event_id` (UUID PK), `event_type` (dot-namespaced), `occurred_at`, `session_id`, `agent_id`, `trace_id`, `payload_ref`, optional `tool_name`, `parent_event_id`, `ended_at`, `status`, `schema_version`, `global_position` (BIGSERIAL).

## Coding Conventions

- Use descriptive variable names
- Never implement mock data — real functionality or TODO comments
- Don't use adjectives in file names (e.g., `web_search.py` not `real_web_search.py`)
- Use `asyncpg` for Postgres (raw, not SQLAlchemy ORM)
- Use `neo4j` async driver with MERGE-based Cypher for idempotent writes
- Use `orjson` via `ORJSONResponse` for JSON serialization
- Use `typing.Protocol` for port interfaces (not ABCs)
- Pydantic v2 with strict mode for event validation
- Use `structlog` for structured logging

## API Response Pattern

All graph query responses use the Atlas pattern:
```json
{
  "nodes": { "node-id": { "type": "...", "attributes": {...}, "provenance": {...} } },
  "edges": [{ "source": "...", "target": "...", "type": "..." }],
  "pagination": { "cursor": "...", "has_more": false },
  "meta": { "query_ms": 120, "nodes_returned": 12, "truncated": false }
}
```

## Dependencies

```
fastapi>=0.115, pydantic>=2.9, asyncpg>=0.29, neo4j>=5.25,
orjson>=3.10, structlog>=24.4, prometheus-client>=0.21,
pydantic-settings>=2.5, alembic>=1.13
```

## Agent Team Configuration

When working as an agent team on this project, use these roles:

### Team Roles

1. **Domain Architect** — owns `domain/`, `ports/`, event schema, validation rules, and projection logic. Ensures framework-agnostic design.
2. **API Engineer** — owns `api/` routes, request/response models, middleware, error handling. Builds the FastAPI layer.
3. **Data Engineer** — owns `adapters/` (Postgres + Neo4j), migrations, Docker Compose, and the projection worker.
4. **Test Engineer** — owns `tests/`, fixtures, integration test infrastructure (testcontainers), and CI validation.

### File Ownership (avoid conflicts)

- Domain Architect: `src/context_graph/domain/**`, `src/context_graph/ports/**`
- API Engineer: `src/context_graph/api/**`, `src/context_graph/settings.py`
- Data Engineer: `src/context_graph/adapters/**`, `src/context_graph/worker/**`, `docker/`, `alembic.ini`, migrations
- Test Engineer: `tests/**`, `conftest.py`, `pyproject.toml` (test deps only)

### Coordination Rules

- Domain Architect must complete port interfaces before API Engineer and Data Engineer start adapter work
- Data Engineer must have Docker Compose + migrations ready before Test Engineer writes integration tests
- All teammates must use the shared event schema defined in `domain/models.py`
- Never edit files outside your ownership zone without coordinating via messages
