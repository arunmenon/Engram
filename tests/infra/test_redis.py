"""
Phase 0 Infrastructure Validation: Redis Stack Capabilities

Validates every Redis Stack capability assumed by ADR-0010, ADR-0005, and ADR-0013.
Run with: source .venv/bin/activate && pytest tests/infra/test_redis.py -v

Requires:
  - redis/redis-stack:latest running on localhost:6379
  - Python redis>=5.0 with hiredis
"""

import asyncio
import json
import re
import time
import uuid

import pytest
import redis.asyncio as aioredis

# ---------------------------------------------------------------------------
# Marker: all tests in this file are infrastructure validation tests
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.infra

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

REDIS_URL = "redis://localhost:6379/0"
STREAM_ID_PATTERN = re.compile(r"^\d+-\d+$")


@pytest.fixture
async def redis_client():
    """Create and yield an async Redis client; print server info on setup."""
    client = aioredis.from_url(REDIS_URL, decode_responses=True)
    try:
        info = await client.info("server")
        print(f"\n  Redis version : {info.get('redis_version', 'unknown')}")
        print(f"  Redis mode    : {info.get('redis_mode', 'unknown')}")

        # Print loaded modules
        modules = await client.module_list()
        for module in modules:
            module_name = module.get("name", "unknown")
            module_ver = module.get("ver", "unknown")
            print(f"  Module        : {module_name} v{module_ver}")

        yield client
    finally:
        await client.aclose()


def _unique_prefix(test_number: int) -> str:
    """Generate a unique key prefix for a test to avoid collisions."""
    tag = uuid.uuid4().hex[:8]
    return f"test:redis:{test_number}:{tag}"


# ---------------------------------------------------------------------------
# Helper: build an event-shaped JSON document
# ---------------------------------------------------------------------------

def _make_event(
    event_id: str = "evt-test-001",
    event_type: str = "tool.execute",
    occurred_at: str = "2026-02-12T10:30:00Z",
    occurred_at_epoch_ms: int = 1770808200000,
    session_id: str = "sess-test-001",
    agent_id: str = "agent-test-001",
    trace_id: str = "trace-test-001",
    tool_name: str = "web_search",
    payload_ref: str = "payload:evt-test-001",
    status: str = "completed",
) -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "occurred_at_epoch_ms": occurred_at_epoch_ms,
        "session_id": session_id,
        "agent_id": agent_id,
        "trace_id": trace_id,
        "tool_name": tool_name,
        "payload_ref": payload_ref,
        "status": status,
    }


# ---------------------------------------------------------------------------
# Test 1 — Streams: XADD + auto-generated IDs
# ---------------------------------------------------------------------------

async def test_01_stream_xadd_auto_id(redis_client: aioredis.Redis):
    """XADD to a stream with auto-generated ID; confirm {ms}-{seq} format."""
    prefix = _unique_prefix(1)
    stream_key = f"{prefix}:stream"

    try:
        entry_id = await redis_client.xadd(
            stream_key,
            {"event_id": "evt-001", "event_type": "tool.execute"},
        )
        assert entry_id is not None, "XADD returned None"
        assert STREAM_ID_PATTERN.match(entry_id), (
            f"Stream entry ID '{entry_id}' does not match {{ms}}-{{seq}} format"
        )

        # Verify the entry can be read back
        entries = await redis_client.xrange(stream_key, "-", "+")
        assert len(entries) == 1
        read_id, fields = entries[0]
        assert read_id == entry_id
        assert fields["event_id"] == "evt-001"
        assert fields["event_type"] == "tool.execute"

        # Add a second entry and verify ordering
        entry_id_2 = await redis_client.xadd(
            stream_key,
            {"event_id": "evt-002", "event_type": "tool.result"},
        )
        assert STREAM_ID_PATTERN.match(entry_id_2)

        # Second entry should have an equal or greater ID
        ms1, seq1 = entry_id.split("-")
        ms2, seq2 = entry_id_2.split("-")
        assert (int(ms2), int(seq2)) >= (int(ms1), int(seq1)), (
            "Second stream entry ID is not >= first"
        )

        print(f"  Stream entry IDs: {entry_id}, {entry_id_2}")
    finally:
        await redis_client.delete(stream_key)


# ---------------------------------------------------------------------------
# Test 2 — Consumer groups: XREADGROUP + XACK + PEL tracking
# ---------------------------------------------------------------------------

async def test_02_consumer_group_readgroup_ack(redis_client: aioredis.Redis):
    """Create group, read with BLOCK, ACK, verify PEL tracking."""
    prefix = _unique_prefix(2)
    stream_key = f"{prefix}:stream"
    group_name = f"{prefix}:group"
    consumer_name = "worker-1"

    try:
        # Seed the stream with entries before creating the group
        ids = []
        for i in range(3):
            entry_id = await redis_client.xadd(
                stream_key,
                {"event_id": f"evt-{i:03d}", "seq": str(i)},
            )
            ids.append(entry_id)

        # Create consumer group starting from the beginning
        await redis_client.xgroup_create(stream_key, group_name, id="0")

        # Read entries via XREADGROUP (non-blocking since data already exists)
        result = await redis_client.xreadgroup(
            group_name,
            consumer_name,
            streams={stream_key: ">"},
            count=10,
            block=100,
        )
        assert result is not None and len(result) > 0, "XREADGROUP returned no data"

        stream_name, messages = result[0]
        assert len(messages) == 3, f"Expected 3 messages, got {len(messages)}"

        # Check PEL — all 3 entries should be pending (unacknowledged)
        pending_info = await redis_client.xpending(stream_key, group_name)
        assert pending_info["pending"] == 3, (
            f"Expected 3 pending entries, got {pending_info['pending']}"
        )

        # ACK two of three entries
        acked = await redis_client.xack(stream_key, group_name, ids[0], ids[1])
        assert acked == 2, f"Expected 2 acks, got {acked}"

        # Check PEL again — only 1 should remain
        pending_info = await redis_client.xpending(stream_key, group_name)
        assert pending_info["pending"] == 1, (
            f"Expected 1 pending entry after ACK, got {pending_info['pending']}"
        )

        # ACK the last one
        acked = await redis_client.xack(stream_key, group_name, ids[2])
        assert acked == 1

        pending_info = await redis_client.xpending(stream_key, group_name)
        assert pending_info["pending"] == 0, "PEL should be empty after all ACKs"

        print("  Consumer group PEL tracking verified: 3 -> 1 -> 0 pending")
    finally:
        try:
            await redis_client.xgroup_destroy(stream_key, group_name)
        except Exception:
            pass
        await redis_client.delete(stream_key)


# ---------------------------------------------------------------------------
# Test 3 — Multiple consumer groups on one stream (ADR-0013: 4 consumers)
# ---------------------------------------------------------------------------

async def test_03_multiple_consumer_groups(redis_client: aioredis.Redis):
    """Create 4 groups on the same stream; each gets all messages independently."""
    prefix = _unique_prefix(3)
    stream_key = f"{prefix}:stream"
    group_names = [
        f"{prefix}:graph-projection",
        f"{prefix}:session-extraction",
        f"{prefix}:enrichment",
        f"{prefix}:consolidation",
    ]

    try:
        # Add 5 events to the stream
        for i in range(5):
            await redis_client.xadd(
                stream_key,
                {"event_id": f"evt-{i:03d}", "event_type": "tool.execute"},
            )

        # Create 4 consumer groups, all starting from the beginning
        for group_name in group_names:
            await redis_client.xgroup_create(stream_key, group_name, id="0")

        # Each group reads independently and should see all 5 messages
        for group_name in group_names:
            result = await redis_client.xreadgroup(
                group_name,
                "worker-1",
                streams={stream_key: ">"},
                count=10,
                block=100,
            )
            assert result is not None and len(result) > 0
            _, messages = result[0]
            assert len(messages) == 5, (
                f"Group {group_name} expected 5 messages, got {len(messages)}"
            )

        # Verify each group has 5 pending entries independently
        for group_name in group_names:
            pending_info = await redis_client.xpending(stream_key, group_name)
            assert pending_info["pending"] == 5, (
                f"Group {group_name}: expected 5 pending, got {pending_info['pending']}"
            )

        # ACK all for group 1 only; others should remain pending
        result_g1 = await redis_client.xreadgroup(
            group_names[0],
            "worker-1",
            streams={stream_key: "0"},  # re-read claimed
            count=10,
        )
        if result_g1:
            _, messages = result_g1[0]
            for msg_id, _ in messages:
                await redis_client.xack(stream_key, group_names[0], msg_id)

        pending_g1 = await redis_client.xpending(stream_key, group_names[0])
        assert pending_g1["pending"] == 0, "Group 1 should have 0 pending after ACK-all"

        for group_name in group_names[1:]:
            pending = await redis_client.xpending(stream_key, group_name)
            assert pending["pending"] == 5, (
                f"Group {group_name} should still have 5 pending"
            )

        print("  4 consumer groups verified: independent delivery and PEL tracking")
    finally:
        for group_name in group_names:
            try:
                await redis_client.xgroup_destroy(stream_key, group_name)
            except Exception:
                pass
        await redis_client.delete(stream_key)


# ---------------------------------------------------------------------------
# Test 4 — RedisJSON: JSON.SET + JSON.GET (event-shaped documents)
# ---------------------------------------------------------------------------

async def test_04_redisjson_set_get(redis_client: aioredis.Redis):
    """Store event-shaped JSON documents and retrieve nested fields."""
    prefix = _unique_prefix(4)
    doc_key = f"{prefix}:evt:evt-test-001"

    event = _make_event()

    try:
        # JSON.SET the full document
        await redis_client.json().set(doc_key, "$", event)

        # JSON.GET the full document
        full_doc = await redis_client.json().get(doc_key, "$")
        assert full_doc is not None
        assert full_doc[0]["event_id"] == "evt-test-001"
        assert full_doc[0]["event_type"] == "tool.execute"
        assert full_doc[0]["occurred_at_epoch_ms"] == 1770808200000
        assert full_doc[0]["session_id"] == "sess-test-001"

        # JSON.GET specific nested fields
        session_id = await redis_client.json().get(doc_key, "$.session_id")
        assert session_id == ["sess-test-001"]

        agent_id = await redis_client.json().get(doc_key, "$.agent_id")
        assert agent_id == ["agent-test-001"]

        tool_name = await redis_client.json().get(doc_key, "$.tool_name")
        assert tool_name == ["web_search"]

        # Verify numeric field retrieval
        epoch_ms = await redis_client.json().get(doc_key, "$.occurred_at_epoch_ms")
        assert epoch_ms == [1770808200000]

        # Store a document with nested payload
        nested_key = f"{prefix}:evt:evt-test-002"
        nested_event = _make_event(
            event_id="evt-test-002",
            event_type="tool.result",
        )
        nested_event["payload"] = {
            "result": {"search_results": [{"title": "Test", "url": "https://example.com"}]},
            "metadata": {"latency_ms": 250},
        }
        await redis_client.json().set(nested_key, "$", nested_event)

        # Retrieve deeply nested field
        latency = await redis_client.json().get(nested_key, "$.payload.metadata.latency_ms")
        assert latency == [250]

        print("  RedisJSON: event doc stored and retrieved with nested field access")
    finally:
        await redis_client.delete(doc_key)
        await redis_client.delete(f"{prefix}:evt:evt-test-002")


# ---------------------------------------------------------------------------
# Test 5 — RediSearch: FT.CREATE + FT.SEARCH on JSON documents
# ---------------------------------------------------------------------------

async def test_05_redisearch_create_search(redis_client: aioredis.Redis):
    """Create index on JSON docs; search by session_id, agent_id, time range, composite."""
    prefix = _unique_prefix(5)
    index_name = f"{prefix}:idx:events"

    events = [
        _make_event(
            event_id="evt-s5-001",
            event_type="tool.execute",
            session_id="sess-alpha",
            agent_id="agent-A",
            occurred_at_epoch_ms=1770808200000,
            tool_name="web_search",
        ),
        _make_event(
            event_id="evt-s5-002",
            event_type="tool.result",
            session_id="sess-alpha",
            agent_id="agent-A",
            occurred_at_epoch_ms=1770808201000,
            tool_name="web_search",
        ),
        _make_event(
            event_id="evt-s5-003",
            event_type="tool.execute",
            session_id="sess-beta",
            agent_id="agent-B",
            occurred_at_epoch_ms=1770808202000,
            tool_name="code_exec",
        ),
        _make_event(
            event_id="evt-s5-004",
            event_type="session.start",
            session_id="sess-gamma",
            agent_id="agent-A",
            occurred_at_epoch_ms=1770808203000,
            tool_name="",
        ),
    ]

    doc_keys = []
    try:
        # Store JSON documents with the required prefix
        for event in events:
            doc_key = f"{prefix}:evt:{event['event_id']}"
            doc_keys.append(doc_key)
            await redis_client.json().set(doc_key, "$", event)

        # Create a RediSearch index on JSON documents
        from redis.commands.search.field import NumericField, TagField
        from redis.commands.search.index_definition import IndexDefinition, IndexType

        index_def = IndexDefinition(
            prefix=[f"{prefix}:evt:"],
            index_type=IndexType.JSON,
        )

        await redis_client.ft(index_name).create_index(
            [
                TagField("$.session_id", as_name="session_id"),
                TagField("$.agent_id", as_name="agent_id"),
                TagField("$.event_type", as_name="event_type"),
                TagField("$.tool_name", as_name="tool_name"),
                NumericField("$.occurred_at_epoch_ms", as_name="occurred_at_epoch_ms"),
            ],
            definition=index_def,
        )

        # Wait briefly for indexing to complete
        await asyncio.sleep(0.5)

        from redis.commands.search.query import Query

        # Search by session_id
        query = Query("@session_id:{sess\\-alpha}").no_content()
        result = await redis_client.ft(index_name).search(query)
        assert result.total == 2, (
            f"Expected 2 results for sess-alpha, got {result.total}"
        )

        # Search by agent_id
        query = Query("@agent_id:{agent\\-A}").no_content()
        result = await redis_client.ft(index_name).search(query)
        assert result.total == 3, (
            f"Expected 3 results for agent-A, got {result.total}"
        )

        # Search by time range
        query = Query(
            "@occurred_at_epoch_ms:[1770808200000 1770808201000]"
        ).no_content()
        result = await redis_client.ft(index_name).search(query)
        assert result.total == 2, (
            f"Expected 2 results in time range, got {result.total}"
        )

        # Composite search: session_id + event_type
        query = Query(
            "@session_id:{sess\\-alpha} @event_type:{tool\\.execute}"
        ).no_content()
        result = await redis_client.ft(index_name).search(query)
        assert result.total == 1, (
            f"Expected 1 result for composite query, got {result.total}"
        )

        # Search by tool_name
        query = Query("@tool_name:{web_search}").no_content()
        result = await redis_client.ft(index_name).search(query)
        assert result.total == 2, (
            f"Expected 2 results for web_search tool, got {result.total}"
        )

        print("  RediSearch: index created, queried by session, agent, time, composite")
    finally:
        try:
            await redis_client.ft(index_name).dropindex(delete_documents=False)
        except Exception:
            pass
        for key in doc_keys:
            await redis_client.delete(key)


# ---------------------------------------------------------------------------
# Test 6 — RediSearch: SORTBY on numeric field (replay ordering)
# ---------------------------------------------------------------------------

async def test_06_redisearch_sortby_numeric(redis_client: aioredis.Redis):
    """FT.SEARCH with SORTBY occurred_at_epoch_ms ASC; verify ordering."""
    prefix = _unique_prefix(6)
    index_name = f"{prefix}:idx:events"

    # Create events with known timestamps in non-sorted order
    timestamps = [
        1770808205000,  # 5th
        1770808201000,  # 1st
        1770808203000,  # 3rd
        1770808202000,  # 2nd
        1770808204000,  # 4th
    ]
    events = []
    for i, ts in enumerate(timestamps):
        events.append(
            _make_event(
                event_id=f"evt-s6-{i:03d}",
                event_type="tool.execute",
                session_id="sess-sort-test",
                occurred_at_epoch_ms=ts,
            )
        )

    doc_keys = []
    try:
        for event in events:
            doc_key = f"{prefix}:evt:{event['event_id']}"
            doc_keys.append(doc_key)
            await redis_client.json().set(doc_key, "$", event)

        from redis.commands.search.field import NumericField, TagField
        from redis.commands.search.index_definition import IndexDefinition, IndexType

        index_def = IndexDefinition(
            prefix=[f"{prefix}:evt:"],
            index_type=IndexType.JSON,
        )

        await redis_client.ft(index_name).create_index(
            [
                TagField("$.session_id", as_name="session_id"),
                NumericField(
                    "$.occurred_at_epoch_ms",
                    as_name="occurred_at_epoch_ms",
                    sortable=True,
                ),
            ],
            definition=index_def,
        )

        await asyncio.sleep(0.5)

        from redis.commands.search.query import Query

        # Search all events for this session, sorted by occurred_at_epoch_ms ASC
        query = (
            Query("@session_id:{sess\\-sort\\-test}")
            .sort_by("occurred_at_epoch_ms", asc=True)
            .return_field("$.occurred_at_epoch_ms", as_field="occurred_at_epoch_ms")
        )
        result = await redis_client.ft(index_name).search(query)
        assert result.total == 5, f"Expected 5 results, got {result.total}"

        # Extract the epoch_ms values in the order returned
        returned_timestamps = []
        for doc in result.docs:
            ts_val = getattr(doc, "occurred_at_epoch_ms", None)
            if ts_val is not None:
                returned_timestamps.append(int(ts_val))

        expected_sorted = sorted(timestamps)
        assert returned_timestamps == expected_sorted, (
            f"Timestamps not in ASC order.\n"
            f"  Expected: {expected_sorted}\n"
            f"  Got:      {returned_timestamps}"
        )

        print(f"  RediSearch SORTBY ASC verified: {returned_timestamps}")
    finally:
        try:
            await redis_client.ft(index_name).dropindex(delete_documents=False)
        except Exception:
            pass
        for key in doc_keys:
            await redis_client.delete(key)


# ---------------------------------------------------------------------------
# Test 7 — Lua scripting: EVALSHA (atomic Stream + JSON write)
# ---------------------------------------------------------------------------

async def test_07_lua_atomic_stream_json(redis_client: aioredis.Redis):
    """Load and execute a Lua script that writes to Stream + JSON atomically."""
    prefix = _unique_prefix(7)
    stream_key = f"{prefix}:stream"
    doc_key = f"{prefix}:evt:evt-lua-001"

    lua_script = """
    local stream_key = KEYS[1]
    local doc_key = KEYS[2]
    local event_json = ARGV[1]
    local event_id = ARGV[2]

    -- Atomically write to stream and JSON document
    local stream_id = redis.call('XADD', stream_key, '*', 'event_id', event_id)
    redis.call('JSON.SET', doc_key, '$', event_json)

    return stream_id
    """

    try:
        # Load the script and get the SHA
        sha = await redis_client.script_load(lua_script)
        assert sha is not None and len(sha) > 0, "Script load returned empty SHA"

        event = _make_event(event_id="evt-lua-001")
        event_json = json.dumps(event)

        # Execute via EVALSHA
        stream_id = await redis_client.evalsha(
            sha,
            2,  # number of KEYS
            stream_key,
            doc_key,
            event_json,
            "evt-lua-001",
        )

        # Verify stream entry
        assert STREAM_ID_PATTERN.match(stream_id), (
            f"Lua returned stream ID '{stream_id}' does not match format"
        )
        entries = await redis_client.xrange(stream_key, "-", "+")
        assert len(entries) == 1
        assert entries[0][1]["event_id"] == "evt-lua-001"

        # Verify JSON document
        doc = await redis_client.json().get(doc_key, "$")
        assert doc is not None
        assert doc[0]["event_id"] == "evt-lua-001"
        assert doc[0]["session_id"] == "sess-test-001"

        print(f"  Lua atomic write: stream_id={stream_id}, JSON doc verified")
    finally:
        await redis_client.delete(stream_key)
        await redis_client.delete(doc_key)


# ---------------------------------------------------------------------------
# Test 8 — Lua: dedup pattern (ADR-0010 idempotent ingestion)
# ---------------------------------------------------------------------------

async def test_08_lua_dedup_pattern(redis_client: aioredis.Redis):
    """Lua dedup: check sorted set, write if absent, return existing if present."""
    prefix = _unique_prefix(8)
    stream_key = f"{prefix}:stream"
    dedup_key = f"{prefix}:dedup:events"

    lua_dedup_script = """
    local stream_key = KEYS[1]
    local dedup_key = KEYS[2]
    local doc_key = KEYS[3]
    local event_id = ARGV[1]
    local event_json = ARGV[2]
    local now_ms = ARGV[3]

    -- Check if event_id already exists in the dedup sorted set
    local existing_score = redis.call('ZSCORE', dedup_key, event_id)
    if existing_score then
        -- Already ingested: return the existing stream ID stored as the score context
        -- We store the stream ID in a hash for lookup
        local existing_stream_id = redis.call('HGET', dedup_key .. ':ids', event_id)
        return 'DUPLICATE:' .. (existing_stream_id or 'unknown')
    end

    -- Not a duplicate: write atomically to stream, JSON doc, and dedup set
    local stream_id = redis.call('XADD', stream_key, '*', 'event_id', event_id)
    redis.call('JSON.SET', doc_key, '$', event_json)
    redis.call('ZADD', dedup_key, now_ms, event_id)
    redis.call('HSET', dedup_key .. ':ids', event_id, stream_id)

    return 'NEW:' .. stream_id
    """

    doc_key_1 = f"{prefix}:evt:evt-dedup-001"
    doc_key_2 = f"{prefix}:evt:evt-dedup-002"

    try:
        sha = await redis_client.script_load(lua_dedup_script)

        event_1 = _make_event(event_id="evt-dedup-001")
        event_1_json = json.dumps(event_1)
        now_ms = str(int(time.time() * 1000))

        # First ingestion: should succeed
        result_1 = await redis_client.evalsha(
            sha, 3,
            stream_key, dedup_key, doc_key_1,
            "evt-dedup-001", event_1_json, now_ms,
        )
        assert result_1.startswith("NEW:"), f"Expected NEW, got: {result_1}"
        stream_id_1 = result_1.split(":", 1)[1]
        assert STREAM_ID_PATTERN.match(stream_id_1)

        # Second ingestion of the same event: should be rejected as duplicate
        result_2 = await redis_client.evalsha(
            sha, 3,
            stream_key, dedup_key, doc_key_1,
            "evt-dedup-001", event_1_json, now_ms,
        )
        assert result_2.startswith("DUPLICATE:"), f"Expected DUPLICATE, got: {result_2}"
        returned_stream_id = result_2.split(":", 1)[1]
        assert returned_stream_id == stream_id_1, (
            "Duplicate should return the original stream ID"
        )

        # Verify only 1 entry in stream (dedup worked)
        entries = await redis_client.xrange(stream_key, "-", "+")
        assert len(entries) == 1, f"Expected 1 stream entry, got {len(entries)}"

        # Third call with a different event_id: should succeed
        event_2 = _make_event(event_id="evt-dedup-002", event_type="tool.result")
        event_2_json = json.dumps(event_2)
        result_3 = await redis_client.evalsha(
            sha, 3,
            stream_key, dedup_key, doc_key_2,
            "evt-dedup-002", event_2_json, now_ms,
        )
        assert result_3.startswith("NEW:"), f"Expected NEW for evt-002, got: {result_3}"

        # Verify 2 entries in stream now
        entries = await redis_client.xrange(stream_key, "-", "+")
        assert len(entries) == 2, f"Expected 2 stream entries, got {len(entries)}"

        # Verify dedup set has 2 members
        dedup_count = await redis_client.zcard(dedup_key)
        assert dedup_count == 2, f"Expected 2 members in dedup set, got {dedup_count}"

        print("  Lua dedup: NEW accepted, DUPLICATE rejected, idempotent ingestion verified")
    finally:
        await redis_client.delete(stream_key)
        await redis_client.delete(dedup_key)
        await redis_client.delete(f"{dedup_key}:ids")
        await redis_client.delete(doc_key_1)
        await redis_client.delete(doc_key_2)


# ---------------------------------------------------------------------------
# Test 9 — XTRIM with MINID (stream trimming for cold tier)
# ---------------------------------------------------------------------------

async def test_09_xtrim_minid(redis_client: aioredis.Redis):
    """Trim stream entries older than a given ID; verify remaining entries."""
    prefix = _unique_prefix(9)
    stream_key = f"{prefix}:stream"

    try:
        # Add entries with explicit IDs to control timestamps
        # Using explicit IDs: {timestamp_ms}-{seq}
        base_ts = 1770808200000
        entry_ids = []
        for i in range(5):
            entry_id = await redis_client.xadd(
                stream_key,
                {"event_id": f"evt-trim-{i:03d}", "seq": str(i)},
                id=f"{base_ts + i * 1000}-0",
            )
            entry_ids.append(entry_id)

        # Verify 5 entries exist
        length_before = await redis_client.xlen(stream_key)
        assert length_before == 5, f"Expected 5 entries, got {length_before}"

        # Trim entries with IDs less than the 3rd entry (keep entries 2, 3, 4)
        # MINID means: keep entries with ID >= minid
        trim_minid = entry_ids[2]  # Keep from entry index 2 onward
        trimmed = await redis_client.xtrim(stream_key, minid=trim_minid, approximate=False)

        # Verify remaining entries
        length_after = await redis_client.xlen(stream_key)
        assert length_after == 3, (
            f"Expected 3 entries after XTRIM MINID, got {length_after}"
        )

        remaining = await redis_client.xrange(stream_key, "-", "+")
        remaining_ids = [entry[0] for entry in remaining]

        # The remaining entries should be entries 2, 3, 4
        assert remaining_ids == entry_ids[2:], (
            f"Remaining IDs mismatch.\n"
            f"  Expected: {entry_ids[2:]}\n"
            f"  Got:      {remaining_ids}"
        )

        print(
            f"  XTRIM MINID: trimmed {trimmed} entries, "
            f"{length_after} remain (from ID {trim_minid})"
        )
    finally:
        await redis_client.delete(stream_key)


# ---------------------------------------------------------------------------
# Test 10 — Stream + JSON independence (cold tier: trim stream, JSON persists)
# ---------------------------------------------------------------------------

async def test_10_stream_json_independence(redis_client: aioredis.Redis):
    """XTRIM stream, verify JSON docs still exist and are searchable."""
    prefix = _unique_prefix(10)
    stream_key = f"{prefix}:stream"
    index_name = f"{prefix}:idx:events"

    base_ts = 1770808200000
    events = []
    doc_keys = []
    stream_ids = []

    try:
        # Create 5 events as both stream entries and JSON documents
        for i in range(5):
            event = _make_event(
                event_id=f"evt-indep-{i:03d}",
                event_type="tool.execute",
                session_id="sess-independence",
                occurred_at_epoch_ms=base_ts + i * 1000,
            )
            events.append(event)
            doc_key = f"{prefix}:evt:{event['event_id']}"
            doc_keys.append(doc_key)

            # Write to both stream and JSON
            stream_id = await redis_client.xadd(
                stream_key,
                {"event_id": event["event_id"]},
                id=f"{base_ts + i * 1000}-0",
            )
            stream_ids.append(stream_id)
            await redis_client.json().set(doc_key, "$", event)

        # Create a RediSearch index
        from redis.commands.search.field import NumericField, TagField
        from redis.commands.search.index_definition import IndexDefinition, IndexType

        index_def = IndexDefinition(
            prefix=[f"{prefix}:evt:"],
            index_type=IndexType.JSON,
        )
        await redis_client.ft(index_name).create_index(
            [
                TagField("$.session_id", as_name="session_id"),
                NumericField(
                    "$.occurred_at_epoch_ms",
                    as_name="occurred_at_epoch_ms",
                    sortable=True,
                ),
            ],
            definition=index_def,
        )
        await asyncio.sleep(0.5)

        # Verify all 5 events are searchable before trimming
        from redis.commands.search.query import Query

        query = Query("@session_id:{sess\\-independence}").no_content()
        result_before = await redis_client.ft(index_name).search(query)
        assert result_before.total == 5, (
            f"Expected 5 searchable docs before trim, got {result_before.total}"
        )

        # Trim the stream aggressively: keep only the last 2 entries
        trim_minid = stream_ids[3]  # Keep entries 3 and 4 only
        await redis_client.xtrim(stream_key, minid=trim_minid, approximate=False)
        stream_length = await redis_client.xlen(stream_key)
        assert stream_length == 2, (
            f"Expected 2 stream entries after trim, got {stream_length}"
        )

        # Verify all 5 JSON documents still exist
        for doc_key in doc_keys:
            doc = await redis_client.json().get(doc_key, "$")
            assert doc is not None, f"JSON doc {doc_key} should still exist after XTRIM"

        # Verify all 5 events are still searchable via RediSearch
        result_after = await redis_client.ft(index_name).search(query)
        assert result_after.total == 5, (
            f"Expected 5 searchable docs after trim, got {result_after.total}"
        )

        # Verify sorted search still works on cold data
        sorted_query = (
            Query("@session_id:{sess\\-independence}")
            .sort_by("occurred_at_epoch_ms", asc=True)
            .return_field("$.occurred_at_epoch_ms", as_field="occurred_at_epoch_ms")
        )
        sorted_result = await redis_client.ft(index_name).search(sorted_query)
        assert sorted_result.total == 5

        returned_timestamps = []
        for doc in sorted_result.docs:
            ts_val = getattr(doc, "occurred_at_epoch_ms", None)
            if ts_val is not None:
                returned_timestamps.append(int(ts_val))

        expected = [base_ts + i * 1000 for i in range(5)]
        assert returned_timestamps == expected, (
            f"Sorted cold query returned wrong order: {returned_timestamps}"
        )

        print(
            f"  Stream/JSON independence verified: "
            f"stream trimmed to {stream_length} entries, "
            f"all 5 JSON docs still searchable and sorted"
        )
    finally:
        try:
            await redis_client.ft(index_name).dropindex(delete_documents=False)
        except Exception:
            pass
        await redis_client.delete(stream_key)
        for key in doc_keys:
            await redis_client.delete(key)


# ---------------------------------------------------------------------------
# Test 11 — MODULE LIST: confirm ReJSON and Search modules are loaded
# ---------------------------------------------------------------------------

async def test_11_module_list(redis_client: aioredis.Redis):
    """Confirm that ReJSON and search modules are loaded in Redis Stack."""
    modules = await redis_client.module_list()
    module_names = {m["name"].lower() for m in modules}

    # Redis Stack module names can vary by version:
    # ReJSON might be listed as "ReJSON" or "rejson"
    # Search might be listed as "search" or "ft"
    has_json = any(
        name in module_names
        for name in ("rejson", "redisjson", "json")
    )
    has_search = any(
        name in module_names
        for name in ("search", "ft", "redisearch")
    )

    assert has_json, (
        f"ReJSON module not found. Loaded modules: {module_names}"
    )
    assert has_search, (
        f"Search module not found. Loaded modules: {module_names}"
    )

    # Print module details
    for module in modules:
        module_name = module.get("name", "unknown")
        module_ver = module.get("ver", "unknown")
        print(f"  Module: {module_name} (version {module_ver})")

    print("  All required modules (ReJSON, Search) confirmed loaded")
