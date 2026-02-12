# Phase 0 Neo4j Signoff

## Neo4j Version
- Image: `neo4j:5-community`
- Neo4j version: **5.26.21**
- Edition: **Community**
- Bolt protocol: 5.8

## Capability Validation

| # | Capability | ADR Source | Status | Notes |
|---|-----------|-----------|--------|-------|
| 1 | MERGE with properties (idempotent) | ADR-0009 | **PASS** | MERGE twice produces single node; ON CREATE/ON MATCH work correctly |
| 2a | CREATE CONSTRAINT (uniqueness) | ADR-0011 | **PASS** | 3 uniqueness constraints created: event_pk, entity_pk, summary_pk |
| 2b | Uniqueness constraint enforcement | ADR-0011 | **PASS** | Duplicate CREATE raises ConstraintError as expected |
| 2c | NOT NULL constraint (limitation) | ADR-0011 | **PASS** | Confirmed NOT available in Community Edition (see Important Finding) |
| 3 | Typed relationships (5 edge types) | ADR-0009 | **PASS** | FOLLOWS, CAUSED_BY, SIMILAR_TO, REFERENCES, SUMMARIZES all created and queried |
| 4 | Variable-length path traversal | ADR-0009 | **PASS** | `[:CAUSED_BY*1..5]` traverses causal chain A->B->C->D->E with depth bounds |
| 5 | UNWIND + MERGE batch pattern | ADR-0005 | **PASS** | 20-event batch UNWIND+MERGE; idempotent on re-run |
| 6 | Node property lists | ADR-0009 | **PASS** | LIST<STRING> (keywords) and LIST<FLOAT> (embedding) stored and retrieved correctly |
| 7 | Async driver (Python) | ADR-0002 | **PASS** | `AsyncGraphDatabase.driver()` connects and executes queries |
| 8 | Degree centrality via Cypher | ADR-0008 | **PASS** | In-degree computed via plain Cypher; results: A=3, B=1, C=1, D=0, E=0 |
| 9 | Transaction functions | — | **PASS** | `execute_write()` and `execute_read()` both work in async mode |
| 10 | Performance: 1000-node MERGE batch | — | **PASS** | Completed in **0.124 seconds** (well under 5s threshold) |

**Result: 12/12 PASS**

## Important Finding: NOT NULL Constraints Require Enterprise Edition

**Property existence (IS NOT NULL) constraints are NOT available in Neo4j Community Edition.**

This means the 7 NOT NULL constraints from ADR-0011 Section 7 (`event_type_not_null`, `event_occurred_not_null`, `event_session_not_null`, `event_gp_not_null`, `entity_name_not_null`, `entity_type_not_null`, `summary_scope_not_null`) **cannot** be created.

**Mitigation** (already planned in ADR-0011 layered enforcement strategy):
- **API layer**: Pydantic v2 strict mode validates all required fields at ingestion time
- **Projection worker**: Application code validates required properties before MERGE
- **constraints.cypher**: Updated to include only the 3 supported UNIQUENESS constraints

This is acceptable for MVP — ADR-0011's enforcement table already designates property existence as "Projection worker validation" for Community Edition.

## GDS Availability

- GDS (Graph Data Science) library is **NOT available** in Neo4j Community Edition
- Centrality must be computed via plain Cypher (in-degree counting via `MATCH (n)<-[r]-() RETURN count(r)`)
- This is a known and acceptable limitation — ADR-0008's centrality requirement uses Cypher, not GDS procedures

## Constraints Validated

| Constraint Name | Type | Label | Property | Status |
|----------------|------|-------|----------|--------|
| event_pk | UNIQUENESS | Event | event_id | Created and enforced |
| entity_pk | UNIQUENESS | Entity | entity_id | Created and enforced |
| summary_pk | UNIQUENESS | Summary | summary_id | Created and enforced |

## Performance Baseline
- 1000-node MERGE batch: **0.124 seconds** (124ms)
- Well within the 5-second threshold
- Indicates batch projection from Redis to Neo4j will be performant

## How to Run

```bash
docker compose -f docker/docker-compose.yml up -d neo4j
source .venv/bin/activate
pytest tests/infra/test_neo4j.py -v -s
```

## Recommendations

1. **Application-layer NOT NULL enforcement is mandatory**: Since Community Edition cannot enforce property existence, every MERGE in the projection worker must validate required fields before writing.
2. **Enterprise Edition evaluation**: If the project scales beyond MVP, evaluate Neo4j Enterprise for NOT NULL constraints, GDS library (PageRank, community detection), and production features (clustering, backup).
3. **Constraint creation on startup**: The `docker/neo4j/init.sh` script applies constraints via `cypher-shell` on first boot. For existing databases, run constraints manually or via the application startup lifecycle.
4. **Batch size for projection**: At 124ms for 1000 MERGEs, batch sizes of 100-500 are recommended for the projection worker to balance throughput and latency.

## Frozen Artifacts
- `docker/docker-compose.yml` (Neo4j service section)
- `docker/neo4j/constraints.cypher`
- `docker/neo4j/init.sh`
- `tests/infra/test_neo4j.py`
