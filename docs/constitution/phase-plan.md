# Engram Implementation Plan: Constitution, Phases, Teams, Handoffs

## Context

Engram is a traceability-first context graph for AI agents (13 ADRs designed, zero source code). The goal is a phased implementation that runs on **autopilot** with minimal human intervention. This requires:

1. An **infrastructure validation** gate — verify Redis Stack + Neo4j actually support our ADR requirements before writing any code
2. A **constitution** (best practices KB) that every agent reads before coding
3. **6 sequential phases** with quality gates between them
4. **Clear team composition** per phase with no file conflicts
5. **Structured handoffs** via frozen contracts, test suites, and handoff documents

---

## Phase Overview

| Phase | Name | Teams/Agents | ADRs | Gate |
|-------|------|:---:|------|------|
| **0** | Infrastructure Validation | 1 team, 2 agents | 0010, 0003 | Redis modules confirmed + Neo4j capabilities confirmed + docker-compose validated |
| **1** | Constitution + Scaffolding | 1 team, 3 agents | 0001, 0002, 0004, 0010, 0011 | `make lint` + `make test` + `docker compose up` |
| **2** | Core Event Store + Projection | 1 team, 3 agents | 0003, 0004, 0005, 0010 | Events ingest -> Redis -> Neo4j with FOLLOWS/CAUSED_BY |
| **3** | Graph Schema + API + Decay | 1 team, 3 agents | 0006, 0008, 0009 | Full Atlas API, intent-weighted traversal, decay scoring |
| **4** | Memory Intelligence | 1 team, 2 agents | 0008 (Stages 2-3) | Enrichment, consolidation, forgetting, summary nodes |
| **5** | Personalization + Extraction | 1 team, 3 agents | 0012, 0013 | LLM extraction, user nodes, DERIVED_FROM provenance |

**Human intervention points**: After Phase 0 (review infra signoff), After Phase 1 (review contracts), After Phase 3 (review API surface), After Phase 5 (review extraction quality).

---

## Phase 0: Infrastructure Validation

### Purpose
Before writing a single line of application code, verify that Redis Stack and Neo4j actually support every capability our ADRs assume. Catch infra surprises now, not in Phase 2.

### Team: `engram-infra-validation` (2 agents)

| Agent | Role | Files Owned |
|-------|------|-------------|
| **redis-validator** | Redis Stack validation | `docker/docker-compose.yml`, `docker/redis/redis.conf`, `tests/infra/test_redis.py`, `docs/handoffs/phase-0-redis.md` |
| **neo4j-validator** | Neo4j validation | `docker/neo4j/constraints.cypher`, `docker/neo4j/neo4j.conf`, `tests/infra/test_neo4j.py`, `docs/handoffs/phase-0-neo4j.md` |

### Quality Gate
- Docker services start healthy
- All capability tests pass (23/23)
- Signoff documents contain no FAIL entries

**Status: COMPLETE** (see `docs/handoffs/phase-0-redis.md` and `docs/handoffs/phase-0-neo4j.md`)

---

## Phase 1: Constitution + Scaffolding

### Purpose
Create the foundation that enables all subsequent phases to run autonomously.

### Team: `engram-constitution` (3 agents)

| Agent | Role | Files Owned |
|-------|------|-------------|
| **infra-agent** | Project infrastructure | `pyproject.toml`, `Makefile`, `docker/`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml` |
| **domain-agent** | Domain models + ports | `src/context_graph/domain/models.py`, `src/context_graph/domain/validation.py`, `src/context_graph/ports/*`, `src/context_graph/settings.py`, all `__init__.py` files |
| **standards-agent** | Constitution docs + test scaffold | `CLAUDE.md` (rewrite), `docs/constitution/*`, `tests/conftest.py`, `tests/fixtures/*`, `tests/unit/test_models.py` |

### Quality Gate
- `ruff check src/ tests/unit/` clean
- `ruff format --check src/ tests/unit/` clean
- `mypy src/context_graph/` clean
- `pytest tests/unit` all pass (87 tests)

**Status: COMPLETE** (see `docs/handoffs/phase-1-complete.md`)

---

## Phase 2: Core Event Store + Projection

### Purpose
Implement the event ingestion pipeline: events flow from API -> Redis -> Neo4j with FOLLOWS and CAUSED_BY edges.

### Team: `engram-core` (3 agents)

| Agent | Role | Files Owned |
|-------|------|-------------|
| **data-engineer** | Redis + Neo4j adapters | `adapters/redis/*`, `adapters/neo4j/store.py`, `adapters/neo4j/queries.py` |
| **domain-architect** | Projection logic + worker | `domain/projection.py`, `worker/consumer.py`, `worker/projection.py` |
| **api-engineer** | Event ingest endpoints | `api/app.py`, `api/routes/events.py`, `api/routes/health.py`, `api/middleware.py`, `api/dependencies.py` |

### Key Deliverables
- `adapters/redis/store.py` — EventStore implementation (XADD, JSON.SET, FT.SEARCH)
- `adapters/redis/lua/ingest.lua` — Atomic idempotent ingestion (dedup check + dual-write)
- `adapters/redis/indexes.py` — RediSearch index definitions
- `adapters/neo4j/store.py` — GraphStore implementation (MERGE-based Cypher)
- `domain/projection.py` — Event -> FOLLOWS/CAUSED_BY edge transform logic
- `worker/consumer.py` — Base consumer class (XREADGROUP lifecycle, graceful shutdown)
- `worker/projection.py` — Consumer 1: structural graph projection
- `api/app.py` — FastAPI factory with lifespan (Redis + Neo4j connection management)
- `api/routes/events.py` — POST /v1/events, POST /v1/events/batch
- `api/routes/health.py` — GET /v1/health

### ADR Compliance Checklist
- [ ] Lua script performs dedup + dual-write atomically (ADR-0010)
- [ ] global_position is Redis Stream entry ID string (ADR-0010)
- [ ] MERGE-based Neo4j writes, never CREATE for existing nodes (ADR-0009)
- [ ] Consumer uses XREADGROUP with XACK after success (ADR-0005)
- [ ] FOLLOWS edges have session_id + delta_ms properties (ADR-0009)
- [ ] CAUSED_BY edges have mechanism property (direct/inferred) (ADR-0009)
- [ ] Idempotent — re-ingesting same event_id is a no-op (ADR-0004)

### Quality Gate
```bash
make lint && make test
curl -X POST localhost:8000/v1/events     # event stored in Redis
# Check Redis: XLEN events:__global__ > 0
# Check Neo4j: MATCH (e:Event) RETURN count(e) > 0
# Check projection: MATCH ()-[:FOLLOWS]->() RETURN count(*) > 0
```

---

## Phase 3: Graph Schema + API + Decay Scoring

### Purpose
Implement the full query API with intent-aware traversal and decay scoring. After this phase, the system is a usable MVP.

### Team: `engram-api` (3 agents)

| Agent | Role | Files Owned |
|-------|------|-------------|
| **domain-architect** | Scoring + intent + lineage | `domain/scoring.py`, `domain/lineage.py`, `domain/intent.py` |
| **data-engineer** | Neo4j query extensions + Consumer 3 | `adapters/neo4j/queries.py` (extend), `worker/enrichment.py` |
| **api-engineer** | Query endpoints | `api/routes/context.py`, `api/routes/query.py`, `api/routes/lineage.py`, `api/routes/entities.py` |

### Key Deliverables
- `domain/scoring.py` — 4-factor Ebbinghaus decay
- `domain/intent.py` — Rule-based intent classification
- `domain/lineage.py` — Bounded traversal algorithms
- `worker/enrichment.py` — Consumer 3: embeddings, keywords, SIMILAR_TO/REFERENCES
- Query endpoints: context, subgraph, lineage, entities

### Quality Gate
```bash
make lint && make test
POST /v1/events (batch of 10 session events)
GET /v1/context/{session_id}
POST /v1/query/subgraph {query: "why did X happen?"}
GET /v1/nodes/{node_id}/lineage
```

**HUMAN REVIEW POINT**: Review API surface and Atlas response format.

---

## Phase 4: Memory Intelligence

### Purpose
Implement consolidation (Stage 3), active forgetting, summary node generation, and reflection triggers.

### Team: `engram-memory` (2 agents)

| Agent | Role | Files Owned |
|-------|------|-------------|
| **memory-architect** | Domain logic + worker + Neo4j maintenance | `domain/consolidation.py`, `domain/forgetting.py`, `worker/consolidation.py`, `adapters/neo4j/maintenance.py`, `adapters/redis/trimmer.py` |
| **test-api-engineer** | Admin API + tests | `api/routes/admin.py`, tests |

### Quality Gate
```bash
make lint && make test
POST /v1/admin/reconsolidate
# Verify Summary nodes created, warm-tier pruning works
```

---

## Phase 5: Personalization + Extraction Pipeline

### Purpose
Implement LLM-based knowledge extraction from sessions, user personalization nodes/edges, and GDPR compliance.

### Team: `engram-extraction` (3 agents)

| Agent | Role | Files Owned |
|-------|------|-------------|
| **domain-architect** | Extraction models + entity resolution | `domain/extraction.py`, `domain/entity_resolution.py`, `domain/models.py` (extend) |
| **data-engineer** | Consumer 2 + LLM client + user queries | `worker/extraction.py`, `adapters/llm/client.py`, `adapters/neo4j/user_queries.py` |
| **api-engineer** | User endpoints + GDPR | `api/routes/users.py`, extend `api/routes/query.py` |

### Quality Gate
```bash
make lint && make test
# Verify extraction produces Preference/Skill nodes with DERIVED_FROM provenance
```

**HUMAN REVIEW POINT**: Review extraction quality and LLM prompt tuning.

---

## Contract Freeze Chain

```
Phase 0 freezes -> docker-compose.yml, redis.conf, neo4j constraints, tests/infra/*
Phase 1 freezes -> domain/models.py, ports/*, settings.py
Phase 2 freezes -> adapters/redis/store.py, adapters/neo4j/store.py, worker/consumer.py
Phase 3 freezes -> domain/scoring.py, domain/intent.py, api/routes/query.py
Phase 4 freezes -> domain/forgetting.py, worker/consolidation.py
```

Each phase MAY add new methods/fields to frozen files (with defaults). Each phase MUST NOT modify existing signatures in frozen files.

---

## Total Teams and Agents

| Phase | Team Name | Agents | Purpose |
|:-----:|-----------|:------:|---------|
| 0 | engram-infra-validation | 2 | Validate Redis Stack + Neo4j capabilities |
| 1 | engram-constitution | 3 | Models, ports, settings, constitution docs |
| 2 | engram-core | 3 | Redis adapter, Neo4j adapter, Consumer 1, event ingest API |
| 3 | engram-api | 3 | Query endpoints, intent traversal, decay scoring, Consumer 3 |
| 4 | engram-memory | 2 | Consumer 4, forgetting, summaries, Redis trimmer |
| 5 | engram-extraction | 3 | Consumer 2, LLM extraction, user nodes, GDPR |
| **Total** | **6 teams** | **16 agent slots** | |
