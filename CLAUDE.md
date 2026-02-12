# Context Graph — Project Guide

## Overview

A traceability-first context graph service for AI agents. Captures immutable event records of agent/tool actions, projects them into a graph for lineage queries, and returns provenance-annotated context to agents.

## Architecture (from ADRs)

- **Stack**: Python 3.12+ / FastAPI / Pydantic v2
- **Dual Store**: Redis Stack (source of truth, immutable event ledger) + Neo4j Community (query-optimized graph projection)
- **Projection**: 4 async consumer groups read from Redis Streams → project into Neo4j
- **API**: REST endpoints at `/v1/` for event ingest, session context retrieval, subgraph query, and node lineage

### Dual Store Roles (ADR-0003, ADR-0010)

| Store | Role | Data |
|-------|------|------|
| Redis Stack (Streams + JSON + Search) | Event ledger, source of truth | Immutable events, hot/cold tiers |
| Neo4j Community | Derived graph projection | 8 node types, 16 edge types, intent-weighted traversal |

### Consumer Groups (ADR-0013)

| Consumer | Stream Group | Trigger | LLM Required |
|----------|-------------|---------|-------------|
| Consumer 1: Graph Projection | `graph-projection` | Per-event | No |
| Consumer 2: Session Extraction | `session-extraction` | Session end | Yes |
| Consumer 3: Enrichment | `enrichment` | Per-event-batch | No (embedding model) |
| Consumer 4: Consolidation | `consolidation` | Scheduled (6h) | Yes |

## Key Design Principles

1. **Traceability over memory** — every piece of context must have provenance back to source events
2. **Immutable events** — never mutate the event ledger; append-only with idempotent ingestion via Lua dedup script
3. **Derived projection** — Neo4j is disposable and rebuildable from Redis events
4. **Framework-agnostic domain** — `domain/` package must have zero imports from FastAPI or any web framework
5. **Bounded queries** — all graph queries enforce depth, node count, and timeout limits
6. **System-owned retrieval** — the context graph infers intent, selects seeds, and surfaces proactive context

## Project Structure

```
src/context_graph/
    settings.py               # Pydantic BaseSettings (CG_ env prefix)
    domain/                   # Pure Python — NO framework imports
        models.py             # Event, Node, Edge, Query, Atlas models (FROZEN Phase 1)
        validation.py         # Event envelope rules
        projection.py         # Event → graph transform logic
        scoring.py            # 4-factor Ebbinghaus decay scoring
        intent.py             # Rule-based intent classification
        lineage.py            # Bounded traversal algorithms
        consolidation.py      # Re-consolidation logic
        forgetting.py         # Retention tier enforcement
        extraction.py         # Extraction target models
        entity_resolution.py  # Three-tier entity resolution
    ports/                    # typing.Protocol interfaces (FROZEN Phase 1)
        event_store.py        # EventStore protocol
        graph_store.py        # GraphStore protocol
        embedding.py          # EmbeddingService protocol
        extraction.py         # ExtractionService protocol
    adapters/
        redis/                # Redis Stack EventStore implementation
            store.py          # XADD, JSON.SET, FT.SEARCH
            lua/              # Lua scripts (ingest.lua, dedup)
            indexes.py        # RediSearch index definitions
        neo4j/                # Neo4j GraphStore implementation
            store.py          # MERGE-based Cypher
            queries.py        # Intent-weighted traversals
            maintenance.py    # Batch pruning, centrality
            user_queries.py   # User subgraph queries
        llm/                  # LLM client adapter
            client.py         # Instructor/litellm
    api/                      # FastAPI layer
        app.py                # Factory: create_app()
        routes/               # events, context, query, lineage, health, entities, admin, users
        middleware.py         # Error handling, metrics
        dependencies.py       # Dependency injection
    worker/                   # Consumer workers (separate processes)
        consumer.py           # Base consumer class (XREADGROUP lifecycle)
        projection.py         # Consumer 1: structural graph projection
        extraction.py         # Consumer 2: LLM session extraction
        enrichment.py         # Consumer 3: embeddings, SIMILAR_TO, REFERENCES
        consolidation.py      # Consumer 4: summaries, forgetting, patterns
```

## Graph Schema (ADR-0009, ADR-0011, ADR-0012)

### 8 Node Types

| Node Type | Label | Source |
|-----------|-------|--------|
| Event | `:Event` | ADR-0009 — projected from Redis events |
| Entity | `:Entity` | ADR-0009 — derived during enrichment |
| Summary | `:Summary` | ADR-0009 — created during re-consolidation |
| UserProfile | `:UserProfile` | ADR-0012 — persistent cross-session user profile |
| Preference | `:Preference` | ADR-0012 — user preference as first-class node |
| Skill | `:Skill` | ADR-0012 — user skill/competency |
| Workflow | `:Workflow` | ADR-0012 — detected workflow pattern |
| BehavioralPattern | `:BehavioralPattern` | ADR-0012 — cross-session behavioral pattern |

### 16 Edge Types

| Edge Type | From → To | View | Source |
|-----------|-----------|------|--------|
| FOLLOWS | Event → Event | Temporal | ADR-0009 |
| CAUSED_BY | Event → Event | Causal | ADR-0009 |
| SIMILAR_TO | Event → Event | Semantic | ADR-0009 |
| REFERENCES | Event → Entity | Entity | ADR-0009 |
| SUMMARIZES | Summary → Event/Summary | Hierarchical | ADR-0009 |
| SAME_AS | Entity → Entity | Entity Resolution | ADR-0011 |
| RELATED_TO | Entity → Entity | Entity Resolution | ADR-0011 |
| HAS_PROFILE | Entity → UserProfile | User | ADR-0012 |
| HAS_PREFERENCE | Entity → Preference | User | ADR-0012 |
| HAS_SKILL | Entity → Skill | User | ADR-0012 |
| DERIVED_FROM | Pref/Pattern/Skill/Workflow → Event | Provenance | ADR-0012 |
| EXHIBITS_PATTERN | Entity → BehavioralPattern | Behavioral | ADR-0012 |
| INTERESTED_IN | Entity → Entity | User | ADR-0012 |
| ABOUT | Preference → Entity | User | ADR-0012 |
| ABSTRACTED_FROM | Workflow → Workflow | Behavioral | ADR-0012 |
| PARENT_SKILL | Skill → Skill | User | ADR-0012 |

### 8 Intent Types

`why`, `when`, `what`, `related`, `general`, `who_is`, `how_does`, `personalize`

## Event Schema (ADR-0004 + ADR-0010)

Required: `event_id` (UUID), `event_type` (dot-namespaced), `occurred_at`, `session_id`, `agent_id`, `trace_id`, `payload_ref`, `global_position` (Redis Stream entry ID, auto-assigned).

Optional: `tool_name`, `parent_event_id` (UUID), `ended_at`, `status`, `schema_version` (int), `importance_hint` (1-10).

## ADR-to-Module Mapping

| ADR | Primary Module(s) |
|-----|-------------------|
| ADR-0001 | Core principles — enforced throughout |
| ADR-0002 | `pyproject.toml`, stack choices |
| ADR-0003 | `adapters/redis/`, `adapters/neo4j/` |
| ADR-0004 | `domain/models.py` (Event), `domain/validation.py` |
| ADR-0005 | `worker/consumer.py`, `worker/projection.py` |
| ADR-0006 | `api/routes/*`, `domain/models.py` (Atlas pattern) |
| ADR-0007 | `settings.py` (tier config) |
| ADR-0008 | `domain/scoring.py`, `domain/forgetting.py`, `worker/consolidation.py` |
| ADR-0009 | `domain/models.py` (edges/nodes/intents), `domain/intent.py` |
| ADR-0010 | `adapters/redis/store.py`, `adapters/redis/lua/` |
| ADR-0011 | `domain/models.py` (enums/taxonomy), `domain/entity_resolution.py` |
| ADR-0012 | `domain/models.py` (user types), `adapters/neo4j/user_queries.py` |
| ADR-0013 | `worker/extraction.py`, `adapters/llm/client.py` |

## Coding Conventions

- Use descriptive variable names
- Never implement mock data — real functionality or TODO comments
- Don't use adjectives in file names
- Use `redis` async client (redis-py with hiredis)
- Use `neo4j` async driver with MERGE-based Cypher for idempotent writes
- Use `orjson` via `ORJSONResponse` for JSON serialization
- Use `typing.Protocol` for port interfaces (not ABCs)
- Pydantic v2 with strict mode for event validation
- Use `structlog` for structured logging
- All configuration in `settings.py` — no hardcoded magic numbers
- Event types: dot-namespaced (`agent.invoke`, `tool.execute`)
- Edge types: UPPER_SNAKE_CASE (`CAUSED_BY`, `SIMILAR_TO`)
- Redis keys: colon-namespaced (`evt:{event_id}`, `events:{session_id}`)

## API Response Pattern

All graph query responses use the Atlas pattern:
```json
{
  "nodes": {
    "node-id": {
      "node_type": "Event",
      "attributes": {...},
      "provenance": {
        "event_id": "...", "global_position": "1707644400000-0",
        "source": "redis", "occurred_at": "...", "session_id": "...",
        "agent_id": "...", "trace_id": "..."
      },
      "scores": {"decay_score": 0.87, "relevance_score": 0.92, "importance_score": 7},
      "retrieval_reason": "direct"
    }
  },
  "edges": [{"source": "...", "target": "...", "edge_type": "FOLLOWS", "properties": {"delta_ms": 1200}}],
  "pagination": {"cursor": "...", "has_more": false},
  "meta": {
    "query_ms": 145, "nodes_returned": 18, "truncated": false,
    "inferred_intents": {"why": 0.7, "when": 0.4},
    "seed_nodes": ["entity:card_declined"],
    "proactive_nodes_count": 3,
    "scoring_weights": {"recency": 1.0, "importance": 1.0, "relevance": 1.0},
    "capacity": {"max_nodes": 100, "used_nodes": 18, "max_depth": 3}
  }
}
```

## Dependencies

```
fastapi>=0.115, uvicorn[standard]>=0.32, pydantic>=2.9, pydantic-settings>=2.5,
redis>=5.0, neo4j>=5.25, orjson>=3.10, structlog>=24.4, prometheus-client>=0.21
```

Dev: `pytest>=8.0, pytest-asyncio>=0.24, pytest-cov>=6.0, ruff>=0.8, mypy>=1.13, pre-commit>=4.0, httpx>=0.28`

Future (Phase 3+): `sentence-transformers, instructor, litellm`

## Contract Freeze Rules (Implementation Phases)

- Phase 0 outputs are FROZEN for Phase 1+: `docker-compose.yml`, `redis.conf`, `constraints.cypher`, `tests/infra/*`
- Phase 1 outputs are FROZEN for Phase 2+: `domain/models.py`, `ports/*`, `settings.py`
- Phase 2 outputs are FROZEN for Phase 3+: `adapters/redis/store.py`, `adapters/neo4j/store.py`
- Phase 3 outputs are FROZEN for Phase 4+: `domain/scoring.py`, `api/routes/query.py`
- "Frozen" means: DO NOT modify existing method signatures or model fields. You MAY add new methods, new fields (with defaults), new files.

## File Ownership Zones (Per Phase)

### Phase 2: Core Event Store + Projection
| Agent | Files |
|-------|-------|
| data-engineer | `adapters/redis/*`, `adapters/neo4j/store.py`, `adapters/neo4j/queries.py` |
| domain-architect | `domain/projection.py`, `worker/consumer.py`, `worker/projection.py` |
| api-engineer | `api/app.py`, `api/routes/events.py`, `api/routes/health.py`, `api/middleware.py`, `api/dependencies.py` |

### Phase 3: Graph Schema + API + Decay
| Agent | Files |
|-------|-------|
| domain-architect | `domain/scoring.py`, `domain/lineage.py`, `domain/intent.py` |
| data-engineer | `adapters/neo4j/queries.py` (extend), `worker/enrichment.py` |
| api-engineer | `api/routes/context.py`, `api/routes/query.py`, `api/routes/lineage.py`, `api/routes/entities.py` |

### Phase 4: Memory Intelligence
| Agent | Files |
|-------|-------|
| memory-architect | `domain/consolidation.py`, `domain/forgetting.py`, `worker/consolidation.py`, `adapters/neo4j/maintenance.py`, `adapters/redis/trimmer.py` |
| test-api-engineer | `api/routes/admin.py`, tests |

### Phase 5: Personalization + Extraction
| Agent | Files |
|-------|-------|
| domain-architect | `domain/extraction.py`, `domain/entity_resolution.py`, `domain/models.py` (extend) |
| data-engineer | `worker/extraction.py`, `adapters/llm/client.py`, `adapters/neo4j/user_queries.py` |
| api-engineer | `api/routes/users.py`, extend `api/routes/query.py` |
