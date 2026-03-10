# Benchmark Suite

Performance benchmarks for the context-graph (Engram) service. Measures
Redis ingestion throughput, Neo4j read/write performance, consumer
projection rates, graph compaction, end-to-end latency, and scaled
degradation curves.

## Prerequisites

1. **Docker services** -- Redis Stack and Neo4j must be running:

   ```bash
   docker compose -f docker/docker-compose.yml up -d
   ```

2. **Benchmark dependencies** -- install the benchmark extras:

   ```bash
   uv sync --extra benchmark
   ```

## Running Benchmarks

### All benchmarks (excluding slow/scaled)

```bash
uv run pytest tests/benchmark/ -m "not slow and not scaled" --benchmark-json=.benchmarks/results.json -v
```

### Fast benchmarks only

```bash
uv run pytest tests/benchmark/ -m "not slow" --benchmark-json=.benchmarks/fast.json -v
```

### Scaled load profiles (L/XL tiers)

```bash
uv run pytest tests/benchmark/ -m scaled --benchmark-json=.benchmarks/scaled.json -v
```

### Neo4j benchmarks only

```bash
uv run pytest tests/benchmark/test_neo4j_writes.py tests/benchmark/test_neo4j_reads.py -v
```

### Redis benchmarks only

```bash
uv run pytest tests/benchmark/test_redis_ingestion.py -v
```

### Dry run (collect without executing)

```bash
uv run pytest tests/benchmark/ --collect-only
```

### Disable benchmarks (validate syntax only)

```bash
uv run pytest tests/benchmark/ --benchmark-disable -v
```

## Comparing Baselines

### Save a baseline

```bash
cp .benchmarks/results.json .benchmarks/baseline.json
```

### Compare against baseline

```bash
uv run pytest tests/benchmark/ --benchmark-compare=.benchmarks/baseline.json -v
```

### Generate comparison table

```bash
uv run pytest tests/benchmark/ \
  --benchmark-compare=.benchmarks/baseline.json \
  --benchmark-columns=min,max,mean,stddev,rounds \
  -v
```

## Test Organization

| File                            | What it measures                                                                                 |
| ------------------------------- | ------------------------------------------------------------------------------------------------ |
| `test_redis_ingestion.py`       | Single append, batch pipeline, batch concurrent, BM25 search, stream read, memory growth         |
| `test_neo4j_writes.py`          | Single MERGE, batch MERGE (events + entities), edge creation (single + batch)                    |
| `test_neo4j_reads.py`           | Session events, lineage traversal (depth 1/3/5), neighbor expansion, seed selection, graph stats |
| `test_projection_throughput.py` | Full projection pipeline (Redis->domain->Neo4j) + pure domain throughput                         |
| `test_compaction.py`            | Graph compaction throughput, node budget query latency                                           |
| `test_e2e_latency.py`           | Ingest-to-queryable round-trip with phase breakdown (p50/p95)                                    |
| `test_scaled_reads.py`          | Degradation curves at S/M/L/XL graph sizes (10K-5M nodes)                                        |

## Expected Baselines

These are approximate baselines measured on a MacBook Pro (M-series) with
local Docker containers. Your results will vary with hardware and Docker
resource limits.

### Redis Operations

| Benchmark              | Metric      | Expected Range  |
| ---------------------- | ----------- | --------------- |
| Single append          | events/sec  | 2,000 - 5,000   |
| Batch pipeline (100)   | events/sec  | 3,000 - 8,000   |
| Batch concurrent (100) | events/sec  | 5,000 - 15,000  |
| BM25 search            | p50 latency | 1 - 10 ms       |
| Stream XRANGE (100)    | entries/sec | 10,000 - 50,000 |
| Memory per event       | bytes       | 1,000 - 3,000   |

### Neo4j Write Operations

| Benchmark                 | Metric    | Expected Range |
| ------------------------- | --------- | -------------- |
| Single MERGE (event)      | nodes/sec | 500 - 2,000    |
| Batch MERGE events (100)  | nodes/sec | 2,000 - 10,000 |
| Batch MERGE entities (50) | nodes/sec | 1,500 - 8,000  |
| Single edge creation      | edges/sec | 300 - 1,500    |
| Batch edge creation (100) | edges/sec | 1,000 - 5,000  |

### Neo4j Read Operations

| Benchmark               | Metric      | Expected Range |
| ----------------------- | ----------- | -------------- |
| Session events lookup   | p50 latency | 1 - 5 ms       |
| Lineage depth 1         | p50 latency | 1 - 5 ms       |
| Lineage depth 3         | p50 latency | 2 - 15 ms      |
| Lineage depth 5         | p50 latency | 5 - 50 ms      |
| Neighbor expansion      | p50 latency | 1 - 10 ms      |
| Seed selection (causal) | p50 latency | 2 - 20 ms      |
| Seed selection (entity) | p50 latency | 2 - 20 ms      |
| Graph stats             | p50 latency | 5 - 50 ms      |

### Pipeline Operations

| Benchmark              | Metric      | Expected Range   |
| ---------------------- | ----------- | ---------------- |
| Projection throughput  | events/sec  | 50 - 500         |
| Domain-only projection | events/sec  | 50,000 - 200,000 |
| Compaction             | events/sec  | 10 - 50          |
| Node budget query      | p50 latency | 5 - 30 ms        |
| E2E latency            | p50         | 50 - 200 ms      |

## Scaled Read Degradation Curves

The `test_scaled_reads.py` module profiles query performance at four graph sizes:

| Tier | Nodes | Edges | Sessions | Entities | Marks         | Heap Requirement |
| ---- | ----- | ----- | -------- | -------- | ------------- | ---------------- |
| S    | 10K   | ~30K  | 100      | 500      | (none)        | 1-2 GB           |
| M    | 100K  | ~300K | 1K       | 5K       | (none)        | 2-4 GB           |
| L    | 1M    | ~3M   | 10K      | 50K      | @slow @scaled | 4-8 GB           |
| XL   | 5M    | ~15M  | 50K      | 250K     | @slow @scaled | 16-32 GB         |

### Queries Profiled per Tier

- `session_events` -- Lookup all events in a single session
- `lineage_depth3` -- CAUSED_BY traversal at depth 3
- `lineage_depth5` -- CAUSED_BY traversal at depth 5
- `neighbor_batch` -- Batch neighbor expansion for 10 events
- `seed_causal` -- Causal root seed selection
- `seed_entity_hubs` -- Entity hub seed selection
- `graph_stats` -- Full cardinality count by label/type
- `node_budget` -- Tenant node budget utilization query

### Interpreting Degradation Curves

Plot S/M/L/XL latency per query type to identify:

1. **Linear scaling** -- latency grows proportionally with graph size (acceptable)
2. **Super-linear** -- latency grows faster than graph size (add indexes)
3. **Inflection point** -- sudden jump at a specific tier (memory pressure, cache eviction)

A healthy graph should show near-constant latency for indexed session/event
lookups and sub-linear growth for traversal queries up to the M tier.

### Neo4j Memory Sizing Recommendations

| Graph Size | Nodes  | Recommended Heap | Page Cache | Total RAM |
| ---------- | ------ | ---------------- | ---------- | --------- |
| Small      | < 50K  | 1 GB             | 512 MB     | 4 GB      |
| Medium     | < 500K | 2-4 GB           | 1-2 GB     | 8 GB      |
| Large      | < 5M   | 4-8 GB           | 2-4 GB     | 16 GB     |
| X-Large    | < 50M  | 16-32 GB         | 8-16 GB    | 64 GB     |

Configure via Docker Compose environment:

```yaml
NEO4J_server_memory_heap_initial__size: "2g"
NEO4J_server_memory_heap_max__size: "4g"
NEO4J_server_memory_pagecache_size: "1g"
```

## CI Integration

### GitHub Actions -- fast benchmarks on PR

```yaml
- name: Run fast benchmarks
  run: |
    uv run pytest tests/benchmark/ \
      -m "not slow and not scaled" \
      --benchmark-json=.benchmarks/pr-${{ github.sha }}.json \
      --benchmark-min-rounds=3 \
      -v
```

### Nightly -- full scaled profile

```yaml
- name: Run scaled benchmarks
  run: |
    uv run pytest tests/benchmark/ \
      --benchmark-json=.benchmarks/nightly-$(date +%Y%m%d).json \
      --benchmark-min-rounds=5 \
      -v
```

### Regression Detection

Compare PR results against the saved baseline:

```yaml
- name: Compare benchmarks
  run: |
    uv run pytest tests/benchmark/ \
      -m "not slow" \
      --benchmark-compare=.benchmarks/baseline.json \
      --benchmark-compare-fail=mean:10% \
      -v
```

The `--benchmark-compare-fail=mean:10%` flag fails the build if any benchmark
regresses more than 10% from the baseline.

## Interpreting Results

- **min/max/mean**: Use `min` for best-case throughput, `mean` for average.
- **stddev**: High variance indicates inconsistent performance (often GC or
  Docker resource contention).
- **rounds**: More rounds = more statistically significant results.
- **Memory growth**: The `test_memory_growth_per_10k_events` test outputs a
  JSON report with `bytes_per_event`. Values above 3KB warrant investigation.
- **Degradation curves**: Scaled read tests produce latency measurements at
  different graph sizes. Plot these to identify the inflection point where
  performance degrades beyond acceptable thresholds.
- **Phase breakdown**: The E2E phase breakdown test reports p50/p95 for
  ingest, project, and query phases separately, helping identify bottlenecks.

## Benchmark Isolation

- All benchmarks use `tenant_id="bench-tenant"` for key isolation.
- The `cleanup_bench_keys` fixture (autouse) deletes all `t:bench-tenant:*`
  Redis keys after each test.
- The `cleanup_bench_neo4j` fixture (autouse) deletes all Neo4j nodes with
  `tenant_id="bench-tenant"` after each test.
- Benchmark tests are in `tests/benchmark/` and are NOT collected by
  `pytest tests/unit/` or `pytest tests/integration/`.

## Graceful Degradation

All benchmark tests gracefully skip (not fail) when infrastructure is
unavailable:

- **No Redis**: Tests marked `skip_no_redis` are skipped
- **No Neo4j**: Tests marked `skip_no_neo4j` are skipped
- **No pytest-benchmark**: Tests marked `skip_no_benchmark` are skipped
- **Both required**: Tests like projection and E2E need both Redis and Neo4j
