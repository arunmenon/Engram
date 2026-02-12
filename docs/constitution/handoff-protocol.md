# Engram Context Graph -- Handoff Protocol

> Canonical reference for phase completion handoffs. Every phase produces a handoff
> document that records what was built, what is frozen, what passed, and what the
> next phase should know. This protocol ensures continuity across development phases
> and prevents regressions on completed contracts.

---

## 1. Handoff Document Format

Every phase completion MUST produce a document at:

```
docs/handoffs/phase-N-complete.md
```

Where `N` is the phase number (0, 1, 2, 3, 4, ...).

Sub-phase documents (e.g., `phase-0-redis.md`, `phase-0-neo4j.md`) are allowed when a phase
has distinct infrastructure components that are validated independently.

### Required Sections

Every handoff document MUST contain the following sections in this order:

#### 1.1 Summary

One-paragraph description of what this phase accomplished and its relationship to the
overall architecture.

```markdown
## Summary

Phase 1 implemented the domain models, port interfaces, and application settings.
These form the shared contract layer that all subsequent phases build upon.
The domain package has zero framework dependencies and defines the Event schema,
graph node types, edge types, Atlas response pattern, and query models.
```

#### 1.2 Files Created/Modified

A complete list of every file created or modified during the phase, organized by package.

```markdown
## Files Created/Modified

### Created
- `src/context_graph/domain/models.py` -- Event schema, graph models, Atlas response
- `src/context_graph/domain/validation.py` -- Event envelope validation rules
- `src/context_graph/ports/event_store.py` -- EventStore protocol interface
- `src/context_graph/ports/graph_store.py` -- GraphStore protocol interface
- `src/context_graph/ports/embedding.py` -- EmbeddingService protocol interface
- `src/context_graph/ports/extraction.py` -- ExtractionService protocol interface
- `src/context_graph/settings.py` -- Pydantic BaseSettings configuration

### Modified
- `pyproject.toml` -- Added domain dependencies
```

#### 1.3 Frozen Contracts

The list of files and interfaces that are now FROZEN (see Section 3 for rules).

```markdown
## Frozen Contracts

The following files are FROZEN as of this phase. Subsequent phases MUST NOT modify
existing method signatures, model fields, or class hierarchies in these files.

| File | Frozen Scope |
|------|-------------|
| `src/context_graph/domain/models.py` | All model classes, enums, field definitions |
| `src/context_graph/ports/event_store.py` | EventStore protocol methods |
| `src/context_graph/ports/graph_store.py` | GraphStore protocol methods |
| `src/context_graph/settings.py` | All settings classes and field names |
```

#### 1.4 Quality Gate Results

Actual output of the quality gate checks. Not "it passes" -- the actual command output or a summary of results.

```markdown
## Quality Gate Results

### `make lint`
```
ruff check src/ tests/ -- OK (0 errors)
ruff format --check src/ tests/ -- OK (0 reformats needed)
mypy src/context_graph/ -- Success: no issues found in 12 source files
```

### `make test`
```
tests/unit/domain/test_models.py .......... PASSED (10 tests)
tests/unit/domain/test_validation.py ....... PASSED (7 tests)
17 passed in 0.43s
```

### `docker compose ps`
```
NAME         SERVICE    STATUS
redis        redis      Up 2 minutes (healthy)
neo4j        neo4j      Up 2 minutes (healthy)
```
```

#### 1.5 Known Issues and Limitations

Every handoff MUST explicitly list known issues. If there are none, state "None" -- do not omit this section.

```markdown
## Known Issues and Limitations

1. **NOT NULL constraints unavailable**: Neo4j Community Edition does not support
   property existence constraints. Mitigation: application-layer validation in
   the projection worker (Phase 2).

2. **RediSearch tag escaping**: Hyphens and dots in tag field values must be escaped
   in query strings. The adapter query layer must handle this (Phase 2).

3. **No GDS library**: Centrality computed via plain Cypher, not GDS procedures.
   Acceptable for MVP.
```

#### 1.6 Recommendations for Next Phase

Concrete, actionable guidance for the team working on the next phase.

```markdown
## Recommendations for Next Phase

1. **Pin Docker image versions** before starting adapter implementation to prevent
   unexpected breaking changes from upstream.

2. **Implement Lua dedup script** as a production artifact in
   `src/context_graph/adapters/redis/lua/ingest.lua`.

3. **Batch size for projection**: Use 100-500 events per UNWIND batch based on
   Phase 0 performance baseline (124ms for 1000 MERGEs).

4. **Application-layer NOT NULL enforcement**: Every MERGE in the projection worker
   must validate required fields before writing to Neo4j.
```

---

## 2. Handoff Document Template

Copy this template when starting a new handoff document:

```markdown
# Phase N Complete -- [Brief Title]

## Summary

[One paragraph describing what was accomplished and why it matters.]

## Files Created/Modified

### Created
- `path/to/file.py` -- [Brief description]

### Modified
- `path/to/existing.py` -- [What changed and why]

## Frozen Contracts

The following files are FROZEN as of this phase. Subsequent phases MUST NOT modify
existing method signatures, model fields, or class hierarchies in these files.

| File | Frozen Scope |
|------|-------------|
| `path/to/file.py` | [What exactly is frozen] |

## Quality Gate Results

### `make lint`
```
[Actual output]
```

### `make test`
```
[Actual output]
```

### `docker compose ps`
```
[Actual output]
```

## Capability Validation

| # | Capability | Status | Notes |
|---|-----------|--------|-------|
| 1 | [Capability name] | **PASS** / **FAIL** | [Details] |

## Known Issues and Limitations

1. **[Issue title]**: [Description and mitigation plan.]

## Recommendations for Next Phase

1. **[Recommendation]**: [Specific, actionable guidance.]
```

---

## 3. Frozen Contract Rules

### Freeze Schedule

Each phase freezes specific outputs for all subsequent phases:

| Phase | Outputs Frozen | Frozen For |
|-------|---------------|------------|
| **Phase 0** | `docker/docker-compose.yml`, `docker/redis/redis.conf`, `docker/neo4j/constraints.cypher`, `docker/neo4j/init.sh`, `tests/infra/*` | Phase 1+ |
| **Phase 1** | `src/context_graph/domain/models.py`, `src/context_graph/ports/*`, `src/context_graph/settings.py` | Phase 2+ |
| **Phase 2** | `src/context_graph/adapters/redis/store.py`, `src/context_graph/adapters/neo4j/store.py` | Phase 3+ |
| **Phase 3** | `src/context_graph/domain/scoring.py`, `src/context_graph/api/routes/query.py` | Phase 4+ |

### What "Frozen" Means

"Frozen" means: **DO NOT modify existing method signatures or model fields.**

Specifically, you MUST NOT:

- Remove or rename an existing field on a Pydantic model
- Change the type annotation of an existing field
- Remove or rename an existing method on a Protocol interface
- Change the parameter types or return type of an existing method
- Remove or rename an existing enum member
- Change the value of an existing enum member
- Change the default value of an existing field in a way that breaks existing callers

### What You MAY Do to Frozen Files

You MAY:

- **Add new methods** to Protocol interfaces (existing implementations are not required to implement them immediately if they are optional)
- **Add new fields** to Pydantic models, provided they have default values (so existing callers are not broken)
- **Add new enum members** (existing `match` statements should have a default case)
- **Add new files** to a frozen package (e.g., add `domain/scoring.py` alongside frozen `domain/models.py`)
- **Add docstrings** or comments
- **Fix bugs** in frozen implementations, provided the fix does not change the method signature or model field types

### Enforcement

Before starting a new phase:

1. Read the handoff document(s) for all prior phases
2. Identify all frozen contracts
3. Verify you understand the frozen interfaces
4. If you need to change a frozen interface, raise it in the handoff discussion BEFORE making changes

Violations of frozen contracts are treated as blocking issues that must be resolved before the phase can proceed.

---

## 4. Quality Gate Checklist

Every handoff document MUST confirm each item below. Include the actual check results, not just checkmarks.

```markdown
### Quality Gate Checklist

- [ ] `make lint` passes (ruff check + ruff format --check + mypy clean)
- [ ] `make test` passes (all unit tests green)
- [ ] `docker compose ps` shows all services healthy (for phases with infra changes)
- [ ] No FAIL entries in capability validation table
- [ ] All new files have module-level docstrings
- [ ] All new public functions/methods have docstrings
- [ ] No hardcoded magic numbers (all tunables in settings.py)
- [ ] All new Pydantic models use strict mode where appropriate
- [ ] All new port methods are async
- [ ] All new adapter writes use MERGE (never CREATE) for Neo4j
- [ ] All new Redis operations use Lua scripts where atomicity is required
- [ ] Frozen contracts from prior phases are not violated
```

### Handling Failures

If any quality gate check fails:

1. Document the failure in the **Known Issues** section with full details
2. Classify it as **BLOCKING** or **NON-BLOCKING**
3. **BLOCKING**: Must be fixed before the handoff is accepted
4. **NON-BLOCKING**: Document the mitigation plan and which phase will address it

A handoff with BLOCKING failures MUST NOT be accepted. The phase continues until all BLOCKING issues are resolved.

---

## 5. Phase Dependency Chain

```
Phase 0: Infrastructure Validation
    |-- Docker Compose (Redis Stack + Neo4j)
    |-- Capability smoke tests
    |-- Configuration files (redis.conf, constraints.cypher)
    v
Phase 1: Domain Layer + Contracts
    |-- domain/models.py (Event schema, graph models, Atlas response)
    |-- domain/validation.py (event envelope rules)
    |-- ports/* (EventStore, GraphStore, EmbeddingService, ExtractionService)
    |-- settings.py (all configuration)
    v
Phase 2: Adapter Implementations
    |-- adapters/redis/store.py (EventStore implementation)
    |-- adapters/redis/lua/* (Lua scripts for atomic operations)
    |-- adapters/neo4j/store.py (GraphStore implementation)
    |-- worker/projector.py (Redis -> Neo4j projection)
    |-- worker/cursor.py (consumer group cursor management)
    v
Phase 3: Query Engine + Scoring
    |-- domain/scoring.py (decay scoring, relevance ranking)
    |-- domain/projection.py (event -> graph transform logic)
    |-- domain/lineage.py (traversal algorithms)
    |-- api/routes/* (events, context, query, lineage, health)
    |-- api/app.py (FastAPI application factory)
    v
Phase 4: Enrichment + Extraction Pipeline
    |-- Knowledge extraction (LLM-based entity/preference extraction)
    |-- Embedding generation (sentence-transformers)
    |-- Summary consolidation
    |-- User personalization graph construction
```

### Cross-Phase Dependencies

- Phase 2 depends on Phase 0 (Docker services) and Phase 1 (domain contracts)
- Phase 3 depends on Phase 2 (working adapters for testing query logic)
- Phase 4 depends on Phase 3 (working API and scoring for end-to-end pipeline)

No phase may skip its predecessors. If a prior phase handoff has unresolved BLOCKING issues, the subsequent phase must wait.

---

## 6. Handoff Acceptance Criteria

A handoff is accepted when:

1. The handoff document follows the format in Section 1
2. All files listed in "Created/Modified" exist and are syntactically valid
3. All quality gate checks pass (no BLOCKING failures)
4. Frozen contracts are correctly declared
5. Known issues are documented with mitigation plans
6. Recommendations are concrete and actionable
7. The handoff document is committed to `docs/handoffs/`

### Acceptance Sign-off

The handoff document should end with:

```markdown
---

**Phase N Status: COMPLETE**
**Date: YYYY-MM-DD**
**Quality Gate: PASS (X/Y checks)**
```
