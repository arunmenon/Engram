# Phase 0 Redis Signoff

## Redis Version
- Image: `redis/redis-stack:latest`
- Redis version: **7.4.7**
- Modules:
  - search v21020 (RediSearch)
  - ReJSON v20809
  - RedisCompat v1
  - redisgears_2 v20020
  - timeseries v11206
  - bf v20816 (Bloom Filter)

## Capability Validation

| # | Capability | ADR Source | Status | Notes |
|---|-----------|-----------|--------|-------|
| 1 | Streams: XADD + auto-generated IDs | ADR-0010 | **PASS** | Entry ID format `{ms}-{seq}` confirmed, monotonically increasing |
| 2 | Consumer groups: XREADGROUP + XACK | ADR-0005, ADR-0013 | **PASS** | PEL tracking verified: 3 -> 1 -> 0 pending after selective ACK |
| 3 | Multiple consumer groups on one stream | ADR-0013 | **PASS** | 4 groups (graph-projection, session-extraction, enrichment, consolidation) each get all messages independently |
| 4 | RedisJSON: JSON.SET + JSON.GET | ADR-0010 | **PASS** | Event-shaped JSON docs stored and retrieved; nested field access via JSONPath works |
| 5 | RediSearch: FT.CREATE + FT.SEARCH | ADR-0010 | **PASS** | Index on JSON docs; queries by session_id, agent_id, time range, composite, tool_name all work |
| 6 | RediSearch: SORTBY on numeric field | ADR-0010 | **PASS** | FT.SEARCH with SORTBY occurred_at_epoch_ms ASC returns correctly ordered results |
| 7 | Lua scripting: EVALSHA | ADR-0010 | **PASS** | SCRIPT LOAD + EVALSHA for atomic Stream + JSON write works |
| 8 | Lua: dedup pattern | ADR-0010 | **PASS** | Sorted-set dedup: first write returns NEW, duplicate returns DUPLICATE with original stream ID |
| 9 | XTRIM with MINID | ADR-0010 | **PASS** | Trim old entries with `approximate=False`; exact trimming verified |
| 10 | Stream + JSON independence | ADR-0010 | **PASS** | After XTRIM, all JSON docs remain and are searchable/sortable via RediSearch |
| 11 | MODULE LIST | — | **PASS** | ReJSON and search modules confirmed loaded |

**Result: 11/11 PASS**

## Configuration
- `appendonly`: yes
- `appendfsync`: everysec
- `maxmemory-policy`: noeviction

Source: `docker/redis/redis.conf`

## How to Run

```bash
docker compose -f docker/docker-compose.yml up -d redis
source .venv/bin/activate
pytest tests/infra/test_redis.py -v -s
```

## Recommendations

1. **Pin image version**: Before Phase 1, pin to `redis/redis-stack:7.4.7-v0` (or the exact tag) to prevent unexpected module version changes.
2. **RediSearch Tag escaping**: Tag fields require escaping of hyphens and dots in query strings (e.g., `sess\\-alpha`, `tool\\.execute`). The application query layer must handle this consistently.
3. **SORTBY requires sortable flag**: The `sortable=True` parameter must be set on NumericField at index creation time; omitting it causes sort to fail silently.
4. **XTRIM approximate vs exact**: Default `approximate=True` may leave extra entries. Use `approximate=False` for precise retention enforcement.
5. **Lua dedup script**: The dedup pattern (test 8) should be promoted to a production artifact in `src/context_graph/adapters/redis/lua/` during Phase 2.
6. **Consumer group naming**: Use convention from ADR-0013: `graph-projection`, `session-extraction`, `enrichment`, `consolidation`.
7. **Memory monitoring**: Use RedisInsight (port 8001) to monitor `redis_memory_used_bytes` during development.

## Frozen Artifacts
- `docker/docker-compose.yml` (Redis service section)
- `docker/redis/redis.conf`
- `tests/infra/test_redis.py`
