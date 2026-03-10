# ADR-0018: Billion-Scale Graph Architecture

Status: **Proposed**
Date: 2026-03-10
Extends: ADR-0003 (dual store), ADR-0007 (memory tiers), ADR-0014 (archival lifecycle)

## Context

The Engram context graph currently runs on a single Neo4j Community instance and a single Redis Stack instance. This architecture supports early-stage deployments but has well-defined scaling ceilings that will be reached as agent adoption grows. This ADR establishes a phased scaling roadmap with quantitative migration triggers so the team can plan infrastructure evolution proactively rather than reactively.

### Per-Session Growth Model

Each agent session contributes a predictable volume of nodes and edges to the graph. Based on observed session structure and the graph schema defined in ADR-0009 and ADR-0012:

| Component                | Nodes per Session | Edges per Session | Notes                               |
| ------------------------ | ----------------: | ----------------: | ----------------------------------- |
| Event nodes              |             15-50 |                -- | One per agent/tool action           |
| FOLLOWS edges            |                -- |             14-49 | Sequential event chain              |
| CAUSED_BY edges          |                -- |              3-10 | Causal links between events         |
| Entity nodes (extracted) |               3-8 |                -- | Named entities from session content |
| REFERENCES edges         |                -- |              5-15 | Event-to-Entity links               |
| SIMILAR_TO edges         |                -- |               2-8 | Semantic similarity (enrichment)    |
| Summary nodes            |               1-2 |                -- | Created during consolidation        |
| SUMMARIZES edges         |                -- |              5-15 | Summary-to-Event links              |
| User profile nodes       |               0-1 |                -- | Created once per user, reused       |
| Preference/Skill/Pattern |               0-3 |                -- | Extracted from session content      |
| User relationship edges  |                -- |               0-6 | HAS_PREFERENCE, HAS_SKILL, etc.     |
| **Totals**               |        **~20-65** |       **~30-105** | Median: ~40 nodes, ~65 edges        |

Using the median estimates (40 nodes, 65 edges per session, ~1.5 KB per Redis event):

### Growth Projection Table

| Deployment Tier             | Sessions/Day | Nodes/Month |  Nodes/Year | Redis Events/Year | Redis Memory/Year |
| --------------------------- | -----------: | ----------: | ----------: | ----------------: | ----------------: |
| **Solo dev**                |           10 |      12,000 |     146,000 |           109,500 |           ~160 MB |
| **Small team** (5 devs)     |           50 |      60,000 |     730,000 |           547,500 |           ~800 MB |
| **Mid-stage** (50 devs)     |          500 |     600,000 |   7,300,000 |         5,475,000 |             ~8 GB |
| **Growth** (200 devs)       |        2,000 |   2,400,000 |  29,200,000 |        21,900,000 |            ~32 GB |
| **Enterprise** (1000+ devs) |        5,000 |   6,000,000 |  73,000,000 |        54,750,000 |            ~80 GB |
| **Platform** (multi-tenant) |       50,000 |  60,000,000 | 730,000,000 |       547,500,000 |           ~800 GB |

_Redis memory estimates use ~1.5 KB per event (JSON document + stream entry + index overhead) before stream trimming. After the 7-day hot window trim (ADR-0014), stream entry memory is reclaimed, reducing per-event cost to ~0.8 KB for cold events._

### Current Architecture Ceilings

**Neo4j Community (single instance):**

- Practical ceiling: 500M-1B nodes depending on query complexity and available RAM
- No native clustering or sharding (Enterprise-only features)
- No Graph Data Science (GDS) library at scale (Community has basic algorithms only)
- Performance degrades non-linearly beyond ~50M nodes without careful index coverage
- Heap pressure becomes critical above ~100M nodes on 32 GB RAM (recommended page cache: 2x data size)
- The current default pool size (`max_connection_pool_size=50`) is adequate for single-instance but cannot distribute load

**Redis Stack (single instance):**

- Practical ceiling: ~100M events in-memory on commodity hardware (150 GB RAM)
- At ~1.5 KB per event (hot) / ~0.8 KB (cold after stream trim), 100M events requires ~80-150 GB
- RediSearch index memory grows linearly with document count (~200-400 bytes per indexed document)
- `maxmemory-policy noeviction` (ADR-0010) means Redis will reject writes when memory is exhausted
- The 90-day retention ceiling (ADR-0014) bounds growth for community deployments but limits historical access

**Timeline to ceiling (without compaction or archival):**

| Deployment Tier | Neo4j 50M Node Ceiling | Neo4j 500M Node Ceiling | Redis 100M Event Ceiling |
| --------------- | ---------------------: | ----------------------: | -----------------------: |
| Solo dev        |                  Never |                   Never |                    Never |
| Small team      |               ~7 years |                   Never |                    Never |
| Mid-stage       |              ~7 months |                ~6 years |                ~18 years |
| Growth          |             ~21 months |               ~17 years |               ~4.5 years |
| Enterprise      |              ~8 months |                ~7 years |               ~22 months |
| Platform        |               ~25 days |               ~8 months |                ~2 months |

_Note: Graph compaction (summary node replacement) and the 90-day retention ceiling extend these timelines by 3-10x for Neo4j and indefinitely for Redis respectively. The table shows raw growth without mitigation to illustrate where each phase becomes relevant._

### Why Act Now

Mid-stage and enterprise deployments will approach the Neo4j 50M-node performance threshold within 1-2 years. Platform (multi-tenant) deployments hit it within weeks. While compaction and archival (ADR-0008, ADR-0014) extend these timelines significantly, they do not eliminate the fundamental single-instance ceiling. A documented scaling strategy ensures the team can evolve infrastructure incrementally rather than facing an emergency migration under production pressure.

## Decision

The scaling strategy is organized into four phases, each independently deployable. Phases are triggered by quantitative thresholds, not calendar dates. The existing `GraphStore` protocol (FROZEN, Phase 1) is preserved across all phases -- scaling is achieved through adapter composition, not protocol changes.

### Phase A: Tenant-Sharded Neo4j

**Scope**: 10M-500M total nodes across all tenants.

**Architecture**: A `ShardRouter` adapter sits in front of N Neo4j instances, each holding a subset of tenants. The router implements the existing `GraphStore` protocol so all upstream code (workers, API routes) is unaware of sharding.

```
                     ┌─────────────┐
   GraphStore ──────>│ ShardRouter │
   protocol          └──────┬──────┘
                            │
              ┌─────────────┼─────────────┐
              v             v             v
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ Neo4j #1 │  │ Neo4j #2 │  │ Neo4j #3 │
        │ tenant-a │  │ tenant-c │  │ tenant-e │
        │ tenant-b │  │ tenant-d │  │ tenant-f │
        └──────────┘  └──────────┘  └──────────┘
```

**Shard assignment**: Consistent hashing on `tenant_id` maps each tenant to exactly one shard. The hash ring uses virtual nodes (default: 150 per physical shard) to ensure even distribution. The mapping is stored in Redis as a hash (`shard:assignments`) for fast lookup and atomicity during rebalancing.

**Migration triggers** (any one is sufficient):

- Any single Neo4j instance exceeds 10M nodes
- Total node count across all tenants exceeds 10M
- Query p95 latency exceeds 200ms at current load on a single instance
- Neo4j heap utilization exceeds 80% sustained over 1 hour

**Cross-shard queries**: Not supported in Phase A. All data for a given tenant resides on a single shard. Queries that span tenants (e.g., platform-wide analytics) must be executed as fan-out queries aggregated at the application layer. This is acceptable because the current API is tenant-scoped -- no existing endpoint queries across tenants.

**Rebalancing**: Moving a tenant from shard A to shard B is accomplished by replaying that tenant's events from Redis into a fresh projection on shard B. The replay uses the same projection worker logic (ADR-0005), filtered by `tenant_id`. During replay, the tenant's data is read-only on shard A. After replay completes and catches up to the current stream position, the shard assignment is atomically updated in Redis, and the tenant's data on shard A is deleted.

**Configuration**:

```
CG_NEO4J_SHARDS=bolt://neo4j-1:7687,bolt://neo4j-2:7687,bolt://neo4j-3:7687
CG_NEO4J_SHARD_VIRTUAL_NODES=150
```

When `CG_NEO4J_SHARDS` is unset or contains a single URI, the system operates in single-instance mode (current behavior). The `ShardRouter` adapter is a no-op wrapper in this case.

**Implementation notes**:

- `ShardRouter` is a new adapter in `adapters/neo4j/shard_router.py` implementing `GraphStore`
- Each shard gets its own `Neo4jGraphStore` instance with independent connection pool
- The projection worker reads `tenant_id` from each event and routes to the correct shard
- Health checks must verify all shards; the `/health/ready` endpoint reports per-shard status

### Phase B: Time-Partitioned Graph

**Scope**: 500M-5B total nodes across all shards.

**Architecture**: Within each shard, the graph is split into a hot partition and a cold partition. The hot partition handles all writes and real-time queries. The cold partition is read-only and contains archived graph data beyond the hot window.

```
        ┌──────────────────────────────────────┐
        │           FederatedGraphStore        │
        │     (implements GraphStore protocol) │
        └───────────────┬──────────────────────┘
                        │
              ┌─────────┴─────────┐
              v                   v
     ┌────────────────┐  ┌────────────────┐
     │  Hot Partition  │  │  Cold Partition │
     │   (Neo4j)       │  │  (PostgreSQL    │
     │   Last 30 days  │  │   + AGE, or     │
     │   All writes    │  │   read-only     │
     │   Real-time     │  │   Neo4j)        │
     │   queries       │  │                 │
     └────────────────┘  └────────────────┘
```

**Hot partition (Neo4j)**:

- Receives all writes from the projection worker
- Contains the last 30 days of graph data (configurable via `CG_GRAPH_HOT_WINDOW_DAYS`)
- Compaction (summary node replacement) is aggressively applied
- Handles all low-latency queries (context retrieval, subgraph, real-time lineage)

**Cold partition (PostgreSQL with Apache AGE extension, or read-only Neo4j)**:

- Read-only. Contains graph data older than the hot window
- Rebuilt periodically (daily or weekly) from the archive store (ADR-0014)
- Contains summary nodes, entity nodes, and their relationships -- not raw event nodes
- Serves historical lineage queries and cross-session entity lookup
- PostgreSQL + AGE is preferred for cost (disk-based, ~10x cheaper than Neo4j RAM) and operational simplicity (single binary, standard Postgres tooling). A read-only Neo4j instance is an alternative if Cypher compatibility is prioritized over cost.

**Query federation**: A `FederatedGraphStore` adapter implements the `GraphStore` protocol. Query routing:

1. All write operations go to the hot partition only
2. Read queries check the hot partition first
3. If the query requests data older than the hot window, or if hot results are incomplete (e.g., lineage chain crosses the time boundary), the cold partition is queried
4. Results from both partitions are merged, deduplicated by node ID, and returned as a single Atlas response
5. The `meta.capacity` field in the response indicates which partition(s) were consulted

**Migration triggers** (any one is sufficient):

- Hot partition exceeds 100M nodes despite compaction
- Query p95 latency exceeds 500ms at current load
- Neo4j heap utilization on any shard exceeds 85% sustained
- Compaction cannot keep pace with ingestion (compaction backlog > 24 hours)

**Configuration**:

```
CG_GRAPH_HOT_WINDOW_DAYS=30
CG_GRAPH_COLD_BACKEND=postgres-age    # or "neo4j-readonly"
CG_GRAPH_COLD_URI=postgresql://...    # or bolt://neo4j-cold:7687
CG_GRAPH_COLD_REBUILD_SCHEDULE=0 3 * * *  # cron: daily at 3 AM
```

### Phase C: Event Store Migration

**Scope**: 5B+ total events in the ledger.

**Architecture**: Redis Streams is replaced as the durable event log by Apache Kafka (or Redpanda). Redis remains as a hot cache for the most recent events (last 7 days), preserving the existing consumer group interface for workers. The change is transparent to consumers via an adapter layer.

```
     ┌──────┐       ┌───────────────┐       ┌──────────────┐
     │ API  │──────>│    Kafka      │──────>│ Redis (cache) │
     │      │ write │ (durable log) │ mirror│ (hot 7 days)  │
     └──────┘       └───────┬───────┘       └──────┬────────┘
                            │                      │
                    ┌───────┴──────┐        ┌──────┴──────┐
                    │ Kafka        │        │ Redis       │
                    │ consumers    │        │ consumer    │
                    │ (replay,     │        │ groups      │
                    │  cold reads) │        │ (real-time) │
                    └──────────────┘        └─────────────┘
```

**Why**: At 5B events, Redis in-memory storage requires ~4-7.5 TB of RAM (at 0.8-1.5 KB per event). Even with the 90-day retention ceiling (ADR-0014), high-throughput deployments accumulate events faster than the ceiling can trim them. Kafka stores events on disk at 10-100x lower cost per GB than Redis RAM, and Kafka's log compaction provides the same append-only, replay-from-offset semantics.

**Event flow**:

1. API writes events to Kafka topic (`engram.events`) with `event_id` as the message key (ensuring per-key ordering)
2. A mirror process reads from Kafka and populates Redis (Streams + JSON + Search) for the hot window
3. Real-time consumer groups (projection, extraction, enrichment, consolidation) continue reading from Redis -- no changes to worker code
4. Historical replay and cold reads go directly to Kafka using offset-based consumption

**Consumer compatibility**: A `KafkaEventStore` adapter implements the same `EventStore` protocol. The API layer is configured to write to Kafka instead of Redis. Workers continue reading from Redis consumer groups for real-time processing. A `KafkaReplayConsumer` provides replay capability for cold data beyond the Redis window.

**Migration triggers** (any one is sufficient):

- Redis memory cost exceeds the deployment's infrastructure budget threshold (e.g., >$2,000/month for mid-stage)
- Event backlog size approaches `maxmemory` despite the retention ceiling
- The 90-day retention ceiling is insufficient for compliance requirements (audit trails require >1 year)
- Event ingestion rate exceeds 10,000 events/sec sustained (Redis single-writer Lua serialization bottleneck)

**Configuration**:

```
CG_EVENT_STORE_BACKEND=kafka          # "redis" (default) or "kafka"
CG_KAFKA_BROKERS=kafka-1:9092,kafka-2:9092,kafka-3:9092
CG_KAFKA_TOPIC=engram.events
CG_KAFKA_REPLICATION_FACTOR=3
CG_REDIS_CACHE_WINDOW_DAYS=7          # Redis serves as hot cache only
```

**Migration procedure**: The migration from Redis-primary to Kafka-primary is performed as a dual-write cutover:

1. Enable dual-write mode: API writes to both Kafka and Redis simultaneously
2. Verify Kafka consumer catches up and data is consistent
3. Switch `CG_EVENT_STORE_BACKEND` to `kafka`
4. Disable Redis writes; Redis is now populated only by the Kafka mirror process
5. Existing Redis data remains accessible until it ages out of the retention ceiling

### Phase D: Distributed Graph (Optional)

**Scope**: 10B+ total nodes. This phase is optional and depends on whether tenant-sharded Neo4j (Phase A) combined with time-partitioning (Phase B) and compaction can sustain the largest deployments.

**When to evaluate**: Phase D becomes relevant only if a single tenant's graph exceeds 1B nodes after compaction, making it impossible to fit on a single Neo4j shard. For most deployments, Phases A-C provide sufficient runway.

**Candidate systems**:

| System             | Query Language                | Sharding              | Operational Model    | Cypher Compatible           | Estimated Cost |
| ------------------ | ----------------------------- | --------------------- | -------------------- | --------------------------- | -------------- |
| **NebulaGraph**    | nGQL (Cypher-like)            | Native hash/range     | Self-hosted          | Partial (nGQL ~80% overlap) | Low (OSS)      |
| **JanusGraph**     | Gremlin                       | Via Cassandra/HBase   | Self-hosted          | No (Gremlin only)           | Low (OSS)      |
| **Amazon Neptune** | Gremlin / SPARQL / openCypher | Managed auto-sharding | Managed              | Yes (openCypher)            | Medium-High    |
| **TigerGraph**     | GSQL                          | Native distributed    | Self-hosted or cloud | No                          | High           |

**Decision criteria** (weighted):

1. **Cypher/openCypher compatibility** (weight: 0.35) -- minimizes query rewrite effort
2. **Operational complexity** (weight: 0.25) -- managed > self-hosted for small teams
3. **Cost at 10B nodes** (weight: 0.20) -- total infrastructure cost including storage, compute, network
4. **Query latency at scale** (weight: 0.15) -- p95 for 3-hop traversal at 10B nodes
5. **Community/ecosystem maturity** (weight: 0.05) -- driver support, documentation, release cadence

**Migration path**: Same as Phase A shard rebalancing -- replay events from the durable log (Kafka, by Phase D) through a new `GraphStore` adapter for the target system. The `GraphStore` protocol (FROZEN) ensures the adapter boundary is clean. Tenants can be migrated individually, enabling a gradual rollout.

**Current recommendation**: Do not select a Phase D system until at least one tenant approaches the 1B-node threshold on a single shard. The distributed graph landscape is evolving rapidly (NebulaGraph 4.x, Neptune openCypher support, SurrealDB graph mode), and a premature commitment locks in operational complexity. Instead, maintain Cypher-centric query patterns and the `GraphStore` protocol boundary so that any Cypher-compatible backend can be adopted with adapter-only changes.

## Consequences

### Positive

- **Clear scaling runway**: The four-phase roadmap provides a documented path from 10M to 10B+ nodes, eliminating uncertainty about when and how to scale
- **Incremental deployment**: Each phase is independently deployable. A solo-dev deployment may never need Phase A. A mid-stage deployment may stop at Phase A. Only platform-scale deployments need Phases B-D
- **Protocol preservation**: The `GraphStore` protocol (FROZEN) is unchanged across all phases. Scaling is achieved through adapter composition (`ShardRouter`, `FederatedGraphStore`, `KafkaEventStore`), not API changes
- **Event replay as migration mechanism**: The append-only event ledger (ADR-0010) enables safe migration between any two graph backends by replaying events through a new adapter. No data transformation or ETL pipeline is required
- **Cost optimization**: Each phase introduces a lower-cost storage tier (Phase B: disk-based cold partition; Phase C: Kafka disk log; Phase D: distributed storage), reducing the per-node and per-event infrastructure cost
- **Quantitative triggers**: Migration decisions are driven by measurable thresholds (node count, p95 latency, memory utilization), not subjective assessments. This enables automated monitoring and alerting

### Negative

- **Phase A latency overhead**: The `ShardRouter` adds ~1-2ms per query for shard lookup and connection routing. For latency-sensitive deployments, this overhead may require co-locating the router with Neo4j instances
- **No cross-shard queries until Phase B**: Phase A restricts all queries to a single tenant's shard. Platform-wide analytics or cross-tenant entity resolution require fan-out queries or Phase B federation
- **Phase B operational complexity**: Running both a hot Neo4j partition and a cold PostgreSQL+AGE (or read-only Neo4j) partition doubles the graph infrastructure. The cold partition rebuild schedule adds a batch processing dependency
- **Phase C is a major infrastructure change**: Introducing Kafka adds a significant new component with its own operational requirements (brokers, ZooKeeper/KRaft, topic management, consumer lag monitoring). This is the highest-effort phase
- **Phase D vendor lock-in risk**: Selecting a distributed graph backend creates a dependency on that system's query language, operational model, and release cadence. The `GraphStore` protocol boundary mitigates but does not eliminate this risk
- **Compaction dependency**: Phases A and B assume that graph compaction (summary node replacement) is effective at reducing node counts by 3-10x. If compaction ratios are lower than expected, ceilings are reached sooner

### Risks to Monitor

| Risk                                         | Trigger                                             | Mitigation                                                                      |
| -------------------------------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------- |
| Shard hotspot (Phase A)                      | One shard has 3x more nodes than others             | Rebalance: replay hot tenant's events to a new shard; adjust virtual node count |
| Cold partition query latency (Phase B)       | Cross-partition lineage queries exceed 2s p95       | Pre-materialize common cross-boundary paths; increase cold partition resources  |
| Kafka mirror lag (Phase C)                   | Redis hot cache falls >5 minutes behind Kafka       | Scale mirror consumers; increase Redis pipeline batch size                      |
| Compaction ratio degrades                    | Compaction achieves <2x reduction (expected: 3-10x) | Tune compaction thresholds; increase summary granularity; shorten hot window    |
| Event replay duration during migration       | Replaying 1B events takes >48 hours                 | Parallelize replay by session; use snapshot + incremental replay                |
| Distributed graph query regression (Phase D) | 3-hop traversal p95 exceeds 1s at 10B nodes         | Evaluate alternative backends; consider query-specific materialized views       |

## Alternatives Considered

### 1. Neo4j Enterprise Clustering

Neo4j Enterprise Edition provides Causal Clustering with automatic leader election, read replicas, and data partitioning. This would solve the single-instance ceiling without custom sharding.

**Rejected** because:

- Enterprise licensing cost is significant ($$$) and scales with instance count
- Enterprise clustering distributes replicas, not partitions -- a single database still has a node count ceiling
- The `GraphStore` protocol already abstracts the backend, making custom sharding straightforward
- Community Edition is sufficient for the vast majority of deployments

### 2. Single Neo4j with Aggressive Compaction Only

Rely solely on graph compaction to keep node counts below the single-instance ceiling. No sharding, no partitioning.

**Rejected** because:

- Compaction ratios are bounded (typically 3-10x). A platform deployment generating 730M nodes/year cannot be compacted below the 500M-1B ceiling indefinitely
- Compaction is lossy: replacing event nodes with summary nodes sacrifices granularity. Over-aggressive compaction degrades lineage query precision
- This approach delays the problem without solving it. When the ceiling is finally reached, there is no incremental migration path -- only an emergency re-architecture

### 3. Replace Neo4j with PostgreSQL Recursive CTEs

Replace Neo4j entirely with PostgreSQL, using recursive CTEs (`WITH RECURSIVE`) for graph traversal and the `ltree` extension for lineage paths.

**Rejected** because:

- Recursive CTEs have O(n) performance characteristics for deep traversals. Neo4j's native graph storage provides O(1) relationship traversal via index-free adjacency
- The 8 intent types and 20 edge types produce traversal queries that are significantly more readable and maintainable in Cypher than in recursive SQL
- PostgreSQL does not support native graph algorithms (centrality, community detection) without extensions
- The migration effort would require rewriting all Cypher queries, the projection worker, and the query layer -- a multi-month project with high regression risk

### 4. Pre-Computed Materialized Views

Pre-compute common query patterns (session context, entity neighborhoods, lineage chains) as materialized views in Redis or PostgreSQL, serving reads from the views instead of real-time graph traversal.

**Rejected as a standalone strategy** because:

- Materialized views help read throughput but do not address write throughput or storage volume, which are the primary scaling bottlenecks
- The 8 intent types with variable weight matrices produce a combinatorial explosion of possible query shapes that cannot be pre-materialized efficiently
- View staleness introduces a consistency gap between the live graph and the materialized data
- However, materialized views are a useful supplementary optimization within any phase and are not precluded by this ADR

## Cross-References

- **ADR-0003** (Dual Store): The dual-store architecture (Redis + Neo4j) is preserved across all phases. Phase A extends it with sharding; Phase B adds a cold graph tier; Phase C replaces the event store backend while maintaining the dual-store pattern
- **ADR-0007** (Memory Tiers): Phase B introduces a new cold graph tier that extends the existing four-tier cognitive memory model. The cold partition serves as a long-term semantic memory archive, complementing the hot Neo4j partition (active semantic memory) and Redis (episodic memory)
- **ADR-0010** (Redis Event Store): Phase C replaces Redis as the primary event store with Kafka while preserving Redis as a hot cache. The `EventStore` protocol boundary ensures this transition is transparent to consumers
- **ADR-0014** (Archival Lifecycle): Phase B's cold partition consumes data from the archive store (GCS/filesystem). The archive-before-delete lifecycle (ADR-0014) feeds the cold partition rebuild process. Phase C's Kafka log replaces the need for aggressive Redis archival since Kafka provides durable long-term event retention on disk
