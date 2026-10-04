# Neo4j to Spanner Graph: gap analysis (spike, no code)

**Date:** 2026-10-04
**Status:** analysis only. No migration work is proposed for now.
**Read with:** [PDLC ontology and ontology packs](pdlc-ontology-and-ontology-packs.md), whose generic GraphStore port is the main lever on the cost below.

## 0. Verdict

- **The rewrite is real but contained.** It sits almost entirely in `src/context_graph/adapters/neo4j/` (5 files, about 3,850 lines, 68 query constants) plus the Neo4j-specific infrastructure (`docker/neo4j/constraints.cypher`, compose service, infra tests). The domain layer, the ledger, the workers' logic and the API do not change, because the code already talks to the graph through `typing.Protocol` ports (`ports/graph_store.py`, `user_store.py`, `maintenance.py`, `retention.py`).
- **Nothing we use is missing on Spanner.** We use no APOC and no GDS. Personalized PageRank is approximated in Python (`retrieval._apply_ppr`). Vector search, full-text search, variable-length paths and optional matches all have Spanner equivalents. The hard parts are the write model (no `MERGE`), async client maturity and semantic differences in pattern matching.
- **Do the ontology packs first.** Ported as-is, Spanner means re-writing 68 hand-tuned queries with hardcoded labels. After the pack work, the adapter implements about ten generic operations plus a few named plugins. Rough effort: 4–6 engineer-weeks now, 2–3 after packs (estimates, not measured).
- **Pick the schemaless Spanner layout.** One `Nodes` table and one `Edges` table with a label column and JSON properties (Spanner's `DYNAMIC LABEL` / `DYNAMIC PROPERTIES`). A new ontology pack then needs no DDL, and Google states schemaless performs better for quantified paths that span several node or edge types, which is what our multi-view traversal does.
- **Licensing gate:** Spanner Graph requires the **Enterprise** edition or higher. Standard edition does not include it.

## 1. How the two models differ

| Topic | Neo4j (today) | Spanner Graph | Consequence |
|---|---|---|---|
| Schema | schema-optional; labels appear when written | graph declared with `CREATE PROPERTY GRAPH` over tables; labels static unless dynamic-label mode is used | schematized layout needs DDL per new type; schemaless layout does not |
| Query language | Cypher | GQL (ISO/IEC 39075) inside GoogleSQL; an openCypher compatibility guide exists | rewrite queries; patterns are close, clauses differ |
| Writes | `MERGE`, `CREATE`, `SET`, `DELETE` in Cypher | SQL DML (`INSERT`, `INSERT OR UPDATE`, `INSERT OR IGNORE`, `UPDATE`, `DELETE`) or the mutations API on the underlying tables; GQL is read-only | every MERGE becomes a table upsert; batching via mutations is a natural fit for `UNWIND` batches |
| Multiple graphs | one default graph per database | many graphs per database; queries start with `GRAPH <name>` | blue/green projections per ontology version can be separate graphs over the same tables, or separate tables |
| Edge identity | any number of relationships between two nodes | an edge is identified by source and destination keys by default; add edge type (or another column) to the element key to allow several edges between the same pair | `Edges` primary key must include `edge_type` |
| Match semantics | relationship uniqueness within one MATCH | repeated edges returned by default; `TRAIL` mode gives uniqueness | silent result differences; port tests must compare outputs |
| Constraints | Community edition: uniqueness only | primary keys, unique indexes, `NOT NULL`, foreign keys, check constraints | an improvement: ADR-0011 rules Neo4j Community cannot enforce become enforceable |
| Vector search | `db.index.vector.queryNodes` on `Entity.embedding` | KNN with `COSINE_DISTANCE`; ANN with vector indexes and `APPROX_COSINE_DISTANCE` | rewrite the vector seed query; index DDL differs |
| Full-text | not used in Neo4j (BM25 runs on Redis) | `SEARCH()` with full-text indexes | no change needed; optional consolidation later |
| Graph algorithms | none used server-side | PageRank, community detection and weakly connected components are offered, with schema requirements (edge table interleaved in source node table, FK to destination) | not needed today; if wanted later, design the tables to meet the requirements from day one |
| Transactions | async driver, explicit sessions | strongly consistent read-write transactions, stale reads, partitioned DML; client sessions and retries | the retry and abort model differs; idempotent writes (already a design rule) make retries safe |
| Local development | `neo4j:5-community` container | Spanner emulator (graph support must be confirmed for our pinned version) | compose, infra tests and CI change |
| Operations | self-managed Community | managed; billed by compute (processing units) and storage; Enterprise edition needed | cost and procurement question, see §5 |

## 2. Feature-by-feature mapping of what Engram uses

Counts are from `adapters/neo4j/*.py` on this branch.

| Engram usage | Count | Spanner equivalent | Effort |
|---|---|---|---|
| `MERGE … ON CREATE SET …` idempotent upserts (events, entities, edges, user nodes) | most writes; 6 `ON CREATE SET` | `INSERT OR UPDATE` / `INSERT OR IGNORE` DML or `insert_or_update` mutations; "set only on create" needs `INSERT OR IGNORE` then `UPDATE`, or a read-then-write in one transaction | medium |
| `UNWIND $rows` batch writes and reads | 14 | mutation batches for writes; `UNNEST(@rows)` for reads | low to medium |
| Variable-length paths `[:SAME_AS*0..3]`, lineage depth | 2 literal, plus lineage traversal | quantified path patterns `-[e:SAME_AS]-{0,3}` | low |
| `OPTIONAL MATCH` | 12 | `OPTIONAL MATCH` in GQL | low; verify null semantics in tests |
| `labels(n)`, `type(r)`, `properties(r)` in neighbour expansion | several | label column / `LABELS(n)` and the JSON properties column in schemaless mode | low in schemaless mode |
| Vector seed query on `Entity.embedding` | 1 | vector index + `APPROX_COSINE_DISTANCE` (or exact `COSINE_DISTANCE` at small scale) | medium |
| `DETACH DELETE` in retention and forgetting | 9 | delete node rows; edges removed by interleaving with `ON DELETE CASCADE` or explicit deletes in the same transaction | medium |
| Subqueries `CALL { … }` | 2 | GQL subqueries / SQL joins over the tables | low to medium |
| Per-label uniqueness constraints (11) and session index | 12 | primary keys and secondary indexes in table DDL | low |
| Access-count bumps on read (`_bump_access_counts`) | 1 | DML update; consider a separate counters table to avoid write contention on hot node rows | medium |
| Async Neo4j driver everywhere | whole adapter | `google-cloud-spanner` 3.71 ships an `spanner_v1/_async` package; the leading underscore suggests it is not yet a stable public API, so confirm status or run the sync client in a thread pool | medium to high |

## 3. Recommended Spanner layout (schemaless, ontology-pack friendly)

```sql
CREATE TABLE Nodes (
  node_id      STRING(MAX) NOT NULL,      -- "<type>:<key>", from the ontology pack
  node_type    STRING(MAX) NOT NULL,      -- dynamic label
  props        JSON,                      -- dynamic properties
  occurred_at  TIMESTAMP,                 -- hot columns promoted out of JSON for indexing
  session_id   STRING(MAX),
  status       STRING(MAX),
  embedding    ARRAY<FLOAT32>(vector_length=>384),
  ontology_version STRING(64) NOT NULL,
) PRIMARY KEY (node_id);

CREATE TABLE Edges (
  node_id      STRING(MAX) NOT NULL,      -- source; interleaving keeps out-edges with the source row
  edge_type    STRING(MAX) NOT NULL,      -- in the key so several edge types can join the same pair
  dest_id      STRING(MAX) NOT NULL,
  props        JSON,
  confidence   FLOAT64,
  method       STRING(MAX),
  CONSTRAINT fk_dest FOREIGN KEY (dest_id) REFERENCES Nodes (node_id),
) PRIMARY KEY (node_id, edge_type, dest_id),
  INTERLEAVE IN PARENT Nodes ON DELETE CASCADE;

CREATE PROPERTY GRAPH Engram
  NODE TABLES (Nodes KEY (node_id) DYNAMIC LABEL (node_type) DYNAMIC PROPERTIES (props))
  EDGE TABLES (Edges KEY (node_id, edge_type, dest_id)
    SOURCE KEY (node_id) REFERENCES Nodes (node_id)
    DESTINATION KEY (dest_id) REFERENCES Nodes (node_id)
    DYNAMIC LABEL (edge_type) DYNAMIC PROPERTIES (props));
```

This is a sketch to confirm against current documentation before use. Points to verify: exact `DYNAMIC LABEL` syntax, whether a dynamic label holds one label or several per row, vector column and index syntax, and whether the interleaving above meets the graph-algorithm schema requirements.

Why this layout:
- A new ontology pack adds rows, not tables. The registry, not the database, holds the type system, which is the ADR-0018 design.
- The interleaved edge table puts a node's out-edges next to it, which is the access pattern of `neighbors(seed_ids)`.
- Hot fields (`occurred_at`, `session_id`, `status`, `embedding`) are real columns so they can be indexed; everything else stays in JSON.
- In-edges (needed for `impact` traversals and inbound PDLC queries) need a secondary index on `Edges(dest_id, edge_type)`.

## 4. What changes in the codebase

| Area | Change |
|---|---|
| `adapters/spanner/` (new) | implementations of the existing ports, ideally only the generic operations from ADR-0018 plus plugins |
| `adapters/neo4j/` | unchanged; stays as the reference backend during migration |
| `settings.py` | new `SpannerSettings` (project, instance, database, graph name); additive, so the freeze holds |
| `api/dependencies.py` | backend selection by setting |
| `docker/` | Spanner emulator service; new infra tests beside the frozen Neo4j ones |
| schema | DDL generated from the ontology registry instead of a hand-written constraints file |
| tests | a backend conformance suite: same events in, same Atlas responses out, run against both adapters. This is the safety net for the match-semantics differences in §1 |
| migration of data | none needed: build the Spanner projection by replaying the Redis ledger, compare, switch |

## 5. Questions to settle before any build

1. **Is Spanner available to us, and in which edition?** Needs a person with GCP console access. Checklist:
   - In each candidate project, *APIs & Services → Enabled APIs*: is **Cloud Spanner API** enabled?
   - *Spanner → Instances*: do any instances exist? For each, note the **edition** (Standard, Enterprise, Enterprise Plus; Spanner Graph needs Enterprise or higher), the **instance configuration** (regional or multi-region, which region), and **compute capacity** (processing units or nodes).
   - Is there an org policy restricting Spanner, or a procurement path for Enterprise edition?
   - Can a non-production instance be created (the smallest is 100 processing units), or is the emulator the only option for now?
   - Which service account would the Engram workers use, and what IAM role can it get (`roles/spanner.databaseUser` is the usual minimum)?
2. Is the async client usable in production, or do we wrap the sync client?
3. Does the emulator in our version support `CREATE PROPERTY GRAPH`, dynamic labels and vector functions?
4. Cost at our expected scale (events per day, retained graph size, query rate). Not estimated here.
5. Is there appetite to also move the ledger (Redis Streams) onto Spanner change streams later? Out of scope; noted because it would revisit ADR-0003 and ADR-0010.

## 6. Confidence and sources

Google's documentation domain was blocked for direct fetch from this session, so the Spanner facts above come from search-result extracts of the official pages, not full reads. Items marked "verify" must be checked against the docs before design sign-off. The Python client facts come from inspecting the `google-cloud-spanner` 3.71.0 wheel. Engram facts come from this branch's code.

Sources: [Spanner editions overview](https://docs.cloud.google.com/spanner/docs/editions-overview), [Announcing Spanner editions](https://cloud.google.com/blog/products/databases/announcing-spanner-editions), [openCypher vs Spanner Graph](https://docs.cloud.google.com/spanner/docs/graph/opencypher-reference), [Manage schemaless data](https://docs.cloud.google.com/spanner/docs/graph/manage-schemaless-data), [Best practices for designing a Spanner Graph schema](https://docs.cloud.google.com/spanner/docs/graph/best-practices-designing-schema), [Insert, update and delete graph data](https://docs.cloud.google.com/spanner/docs/graph/insert-update-delete-data), [Vector search with Spanner Graph](https://docs.cloud.google.com/spanner/docs/graph/perform-vector-similarity-search), [Queries overview](https://docs.cloud.google.com/spanner/docs/graph/queries-overview), [Graph algorithms](https://docs.cloud.google.com/spanner/docs/graph/algorithms), [Algorithm schema requirements](https://docs.cloud.google.com/spanner/docs/graph/algorithm-schema-requirements-and-feature-compatibility).
