# Phase 1 Handoff: Constitution + Scaffolding

**Status**: COMPLETE
**Date**: 2026-02-12
**Team**: engram-constitution (3 agents: infra-agent, domain-agent, standards-agent)

---

## Quality Gate Results

| Check | Result |
|-------|--------|
| `ruff check src/context_graph/ tests/unit/` | PASS |
| `ruff format --check src/context_graph/ tests/unit/` | PASS (19 files formatted) |
| `mypy src/context_graph/` | PASS (16 source files, strict mode) |
| `pytest tests/unit -v` | PASS (87/87 tests) |
| Docker services healthy | PASS (from Phase 0) |

---

## Deliverables

### Domain Models (`src/context_graph/domain/models.py`) — FROZEN

The single shared contract for all phases:

- **Event** model: 8 required + 6 optional fields (ADR-0004 + ADR-0010)
- **16 enums**: EventType (16 values), EntityType (6), EdgeType (16), IntentType (8), NodeType (8), EventStatus (5), RetentionTier (4), ReferenceRole (5), PreferencePolarity (3), PreferenceSource (4), PreferenceCategory (6), PreferenceScope (3), WorkflowAbstractionLevel (3), BehavioralPatternType (6), DerivationMethod (8), CausalMechanism (2)
- **8 node models**: EventNode, EntityNode, SummaryNode, UserProfileNode, PreferenceNode, SkillNode, WorkflowNode, BehavioralPatternNode
- **Atlas response models**: AtlasResponse, AtlasNode, AtlasEdge, Provenance, NodeScores, QueryMeta, QueryCapacity, Pagination
- **Query models**: EventQuery, SubgraphQuery, LineageQuery

### Validation (`src/context_graph/domain/validation.py`)

- Event envelope rules beyond Pydantic field validators
- Dot-namespace pattern enforcement
- Future drift check (5 min max)
- Self-referential parent check
- ended_at >= occurred_at check
- payload_ref length limit

### Port Interfaces (`src/context_graph/ports/`) — FROZEN

| Port | Protocol Methods |
|------|-----------------|
| `event_store.py` | append, append_batch, get_by_id, get_by_session, search, get_stream_length, get_last_position |
| `graph_store.py` | merge_event_node, create_edge, get_subgraph, get_lineage, get_context, delete_node, get_node_count |
| `embedding.py` | embed_text, embed_batch |
| `extraction.py` | extract_from_session |

### Settings (`src/context_graph/settings.py`) — FROZEN

All configuration via Pydantic BaseSettings with `CG_` env prefix:
- Redis/Neo4j connection params
- Consumer group names and block timeouts
- Decay scoring defaults (S_base=168, S_boost=24)
- Query limits (max_depth, max_nodes, timeout_ms)
- Retention tier boundaries
- Intent weight matrix defaults
- Similarity/reflection thresholds

### Project Infrastructure

| File | Purpose |
|------|---------|
| `pyproject.toml` | Package metadata, all deps, ruff/mypy/pytest config |
| `Makefile` | dev, test, lint, format, docker-up/down targets |
| `.pre-commit-config.yaml` | ruff + mypy hooks |
| `.github/workflows/ci.yml` | lint + unit + integration CI jobs |
| `CLAUDE.md` | Full project guide (Redis-based, 4 consumers, 16 edges, 8 nodes) |

### Constitution Documents (`docs/constitution/`)

| Document | Purpose |
|----------|---------|
| `coding-standards.md` | Import rules, async patterns, naming conventions |
| `testing-strategy.md` | Test pyramid, coverage targets, fixture strategy |
| `handoff-protocol.md` | Handoff format template, freeze rules |
| `phase-plan.md` | Full 6-phase plan persisted in repo |

### Test Scaffold

| File | Tests |
|------|-------|
| `tests/conftest.py` | Shared fixtures, event factories |
| `tests/fixtures/events.py` | Reusable test data builders |
| `tests/unit/test_models.py` | 67 tests — Event creation, field constraints, enum completeness, query models, Atlas response |
| `tests/unit/test_validation.py` | 20 tests — valid events, self-referential parent, ended_at, future drift, type prefix |

### Package Structure

All `__init__.py` files created for:
- `src/context_graph/`
- `src/context_graph/domain/`
- `src/context_graph/ports/`
- `src/context_graph/adapters/`
- `src/context_graph/adapters/redis/`
- `src/context_graph/adapters/neo4j/`
- `src/context_graph/adapters/llm/`
- `src/context_graph/api/`
- `src/context_graph/api/routes/`
- `src/context_graph/worker/`

---

## Frozen Contracts (Phase 2+ MUST NOT modify existing signatures)

- `src/context_graph/domain/models.py` — all model fields and enum values
- `src/context_graph/ports/event_store.py` — EventStore protocol methods
- `src/context_graph/ports/graph_store.py` — GraphStore protocol methods
- `src/context_graph/ports/embedding.py` — EmbeddingService protocol methods
- `src/context_graph/ports/extraction.py` — ExtractionService protocol methods
- `src/context_graph/settings.py` — all settings fields

Phase 2 MAY:
- Add new methods to port protocols
- Add new fields (with defaults) to models
- Add new enum values
- Create new files

Phase 2 MUST NOT:
- Change existing method signatures
- Remove or rename existing model fields
- Change existing enum values

---

## Known Issues / Notes

1. **Ruff TC003 per-file ignore**: `models.py` has `TCH003` ignored because Pydantic requires `datetime` and `UUID` at runtime, not just in TYPE_CHECKING blocks. This is documented in `pyproject.toml`.

2. **Phase 0 frozen test files**: `tests/infra/test_redis.py` and `tests/infra/test_neo4j.py` have 7 ruff lint warnings (SIM105, B905, E501). These are Phase 0 frozen files and should not be modified.

3. **Python 3.14 compatibility**: Tests run on Python 3.14.2 with no issues. Project targets Python 3.12+.

---

## Next Phase: Phase 2 — Core Event Store + Projection

### Team Composition
| Agent | Files |
|-------|-------|
| data-engineer | `adapters/redis/*`, `adapters/neo4j/store.py`, `adapters/neo4j/queries.py` |
| domain-architect | `domain/projection.py`, `worker/consumer.py`, `worker/projection.py` |
| api-engineer | `api/app.py`, `api/routes/events.py`, `api/routes/health.py`, `api/middleware.py`, `api/dependencies.py` |

### Prerequisites
- Docker services running (`docker compose up -d`)
- All Phase 1 contracts frozen — import from `context_graph.domain.models` and `context_graph.ports.*`
- Settings loaded from `context_graph.settings.Settings`
