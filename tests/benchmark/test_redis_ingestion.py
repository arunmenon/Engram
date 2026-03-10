"""Redis ingestion benchmarks.

Measures throughput for single event append, batch pipeline, batch concurrent
ingestion, BM25 search latency, stream read throughput, and memory growth.

Prerequisites:
- Redis Stack running at localhost:6379
- pytest-benchmark installed (``uv run --extra benchmark``)

Run: ``uv run pytest tests/benchmark/test_redis_ingestion.py -v``
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

import pytest

from tests.benchmark.conftest import (
    BENCHMARK_TENANT,
    make_bench_events,
    skip_no_benchmark,
    skip_no_redis,
)

if TYPE_CHECKING:
    from context_graph.adapters.redis.store import RedisEventStore

pytestmark = [
    pytest.mark.benchmark,
    skip_no_redis,
    skip_no_benchmark,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_async(coro):
    """Run an async coroutine synchronously for pytest-benchmark compatibility.

    pytest-benchmark's ``benchmark`` fixture calls the target function
    synchronously, so we need a bridge to run async store methods.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# 1. Single append throughput
# ---------------------------------------------------------------------------


class TestSingleAppendThroughput:
    """Benchmark single event append via Lua ingestion script.

    Measures: events/sec for individual ``store.append()`` calls.
    Expected baseline: ~2-5K events/sec on local Redis.
    """

    def test_single_append_throughput(self, benchmark, redis_store: RedisEventStore) -> None:
        """Benchmark a single ``store.append()`` call."""
        events = make_bench_events(200)
        idx = {"i": 0}

        def append_one():
            event = events[idx["i"] % len(events)]
            # Generate a fresh event_id each iteration to avoid dedup
            from uuid import uuid4

            from context_graph.domain.models import Event

            fresh_event = Event(
                event_id=uuid4(),
                event_type=event.event_type,
                occurred_at=event.occurred_at,
                session_id=event.session_id,
                agent_id=event.agent_id,
                trace_id=event.trace_id,
                payload_ref=event.payload_ref,
                tool_name=event.tool_name,
                importance_hint=event.importance_hint,
            )
            idx["i"] += 1
            return _run_async(redis_store.append(fresh_event, tenant_id=BENCHMARK_TENANT))

        result = benchmark(append_one)
        assert result is not None  # Stream entry ID returned


# ---------------------------------------------------------------------------
# 2. Batch pipeline throughput
# ---------------------------------------------------------------------------


class TestBatchPipelineThroughput:
    """Benchmark batch ingestion using Redis pipeline.

    The pipeline strategy sends all Lua EVALSHA calls in a single
    round-trip. ``append_batch`` uses pipeline for batches <= 10.
    """

    @pytest.mark.parametrize("batch_size", [10, 50, 100])
    def test_batch_pipeline_throughput(
        self,
        benchmark,
        redis_store: RedisEventStore,
        batch_size: int,
    ) -> None:
        """Benchmark ``store.append_batch()`` with pipeline strategy.

        For batch_size > 10, append_batch delegates to concurrent mode.
        To isolate the pipeline path, we use the pipeline code directly
        for all sizes by calling the internal pipeline logic.
        """

        def ingest_batch():
            events = make_bench_events(batch_size)
            return _run_async(_pipeline_ingest(redis_store, events, BENCHMARK_TENANT))

        benchmark.extra_info["batch_size"] = batch_size
        result = benchmark(ingest_batch)
        assert result is not None
        assert len(result) == batch_size


async def _pipeline_ingest(
    store: RedisEventStore,
    events: list,
    tenant_id: str,
) -> list[str]:
    """Force pipeline-based batch ingestion regardless of batch size.

    Replicates the pipeline path from ``store.append_batch()`` to
    isolate pipeline performance from the concurrent strategy.
    """
    from context_graph.adapters.redis.store import (
        _event_to_epoch_ms,
        _event_to_json_bytes,
        _tenant_event_key,
        _tenant_key,
        _tenant_session_stream,
        _tenant_stream_key,
    )

    if store._script_sha is None:
        await store._register_script()

    global_stream = _tenant_stream_key(store._settings.global_stream, tenant_id)
    dedup_set = _tenant_key(store._settings.dedup_set, tenant_id)

    pipe = store._client.pipeline(transaction=False)
    for event in events:
        event_id_str = str(event.event_id)
        json_key = _tenant_event_key(store._settings.event_key_prefix, event_id_str, tenant_id)
        occurred_at_epoch_ms = _event_to_epoch_ms(event)
        event_json = _event_to_json_bytes(event, occurred_at_epoch_ms, tenant_id=tenant_id)
        session_stream_key = _tenant_session_stream(str(event.session_id), tenant_id)

        pipe.evalsha(
            store._script_sha,
            4,
            global_stream,
            json_key,
            dedup_set,
            session_stream_key,
            event_id_str,
            event_json,
            str(occurred_at_epoch_ms),
            str(store._settings.global_stream_maxlen),
        )

    results = await pipe.execute()
    return [r.decode() if isinstance(r, bytes) else str(r) for r in results]


# ---------------------------------------------------------------------------
# 3. Batch concurrent throughput
# ---------------------------------------------------------------------------


class TestBatchConcurrentThroughput:
    """Benchmark concurrent batch ingestion using semaphore-bounded gather.

    Uses ``asyncio.Semaphore`` to parallelize Lua EVALSHA calls across
    multiple Redis pool connections. Expected: 2-3x improvement over
    pipeline for large batches.
    """

    @pytest.mark.parametrize("batch_size", [10, 50, 100])
    def test_batch_concurrent_throughput(
        self,
        benchmark,
        redis_store: RedisEventStore,
        batch_size: int,
    ) -> None:
        """Benchmark ``store.append_batch_concurrent()``."""

        def ingest_batch():
            events = make_bench_events(batch_size)
            return _run_async(
                redis_store.append_batch_concurrent(events, tenant_id=BENCHMARK_TENANT)
            )

        benchmark.extra_info["batch_size"] = batch_size
        result = benchmark(ingest_batch)
        assert result is not None
        assert len(result) == batch_size


# ---------------------------------------------------------------------------
# 4. BM25 search latency
# ---------------------------------------------------------------------------


class TestSearchBM25Latency:
    """Benchmark RediSearch BM25 full-text search.

    Pre-ingests 500 events with keyword-rich payloads, then measures
    search latency across varied query terms.
    """

    @pytest.fixture(autouse=True)
    def _seed_search_data(self, redis_store: RedisEventStore) -> None:
        """Pre-ingest events with varied payloads for BM25 search."""
        keywords = [
            "authentication",
            "database",
            "migration",
            "deployment",
            "caching",
            "performance",
            "security",
            "monitoring",
            "refactoring",
            "testing",
            "integration",
            "optimization",
        ]
        events = make_bench_events(500, session_id="bench-search-session")
        payloads = []
        for i, _event in enumerate(events):
            keyword_set = [keywords[i % len(keywords)], keywords[(i + 3) % len(keywords)]]
            payloads.append(
                {
                    "summary": f"Event about {' and '.join(keyword_set)} in production",
                    "keywords": keyword_set,
                }
            )
        _run_async(redis_store.append_batch(events, payloads=payloads, tenant_id=BENCHMARK_TENANT))

    @pytest.mark.parametrize(
        "query_term",
        ["authentication", "database migration", "performance optimization"],
    )
    def test_search_bm25_latency(
        self,
        benchmark,
        redis_store: RedisEventStore,
        query_term: str,
    ) -> None:
        """Benchmark BM25 search for a given query term."""

        def search():
            return _run_async(
                redis_store.search_bm25(
                    query_term,
                    limit=50,
                    tenant_id=BENCHMARK_TENANT,
                )
            )

        benchmark.extra_info["query_term"] = query_term
        result = benchmark(search)
        # BM25 search may return 0 results if the index schema does not
        # include summary/keywords as TEXT fields -- that is expected in
        # some configurations. The benchmark measures latency regardless.
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# 5. Stream read throughput
# ---------------------------------------------------------------------------


class TestStreamReadThroughput:
    """Benchmark Redis Stream XRANGE read throughput.

    Pre-populates a stream with 1000 events, then measures read
    throughput for varying batch sizes.
    """

    @pytest.fixture(autouse=True)
    def _seed_stream_data(self, redis_store: RedisEventStore) -> None:
        """Pre-ingest 1000 events into the global stream."""
        events = make_bench_events(1000, session_id="bench-stream-session")
        _run_async(redis_store.append_batch(events, tenant_id=BENCHMARK_TENANT))

    @pytest.mark.parametrize("count", [10, 50, 100])
    def test_stream_read_throughput(
        self,
        benchmark,
        redis_store: RedisEventStore,
        count: int,
    ) -> None:
        """Benchmark XRANGE reads from the global event stream."""
        from context_graph.adapters.redis.store import _tenant_stream_key

        stream_key = _tenant_stream_key(redis_store._settings.global_stream, BENCHMARK_TENANT)

        def read_stream():
            return _run_async(redis_store._client.xrange(stream_key, count=count))

        benchmark.extra_info["count"] = count
        result = benchmark(read_stream)
        assert isinstance(result, list)
        assert len(result) <= count


# ---------------------------------------------------------------------------
# 6. Memory growth measurement (NOT a pytest-benchmark test)
# ---------------------------------------------------------------------------


class TestMemoryGrowth:
    """Measure Redis memory growth per event.

    This is NOT a pytest-benchmark test -- it ingests 10K events and
    records memory before/after to compute bytes-per-event. The result
    is printed to stdout and can be captured via ``-s`` or ``--capture=no``.
    """

    @pytest.mark.slow
    def test_memory_growth_per_10k_events(
        self,
        redis_store: RedisEventStore,
    ) -> None:
        """Ingest 10K events and measure memory growth."""

        async def _measure():
            # Record baseline memory
            mem_before = await redis_store.get_memory_info()
            before_bytes = mem_before["used_memory_bytes"]

            # Ingest 10K events in batches of 500
            total_events = 10_000
            batch_size = 500
            for batch_start in range(0, total_events, batch_size):
                events = make_bench_events(
                    batch_size,
                    session_id=f"bench-memory-{batch_start}",
                )
                await redis_store.append_batch(events, tenant_id=BENCHMARK_TENANT)

            # Record post-ingestion memory
            mem_after = await redis_store.get_memory_info()
            after_bytes = mem_after["used_memory_bytes"]

            growth = after_bytes - before_bytes
            bytes_per_event = growth / total_events if total_events > 0 else 0

            return {
                "events": total_events,
                "memory_before_bytes": before_bytes,
                "memory_after_bytes": after_bytes,
                "memory_growth_bytes": growth,
                "bytes_per_event": round(bytes_per_event, 2),
            }

        result = _run_async(_measure())

        # Output result as JSON for capture
        print("\n--- Memory Growth Report ---")  # noqa: T201
        print(json.dumps(result, indent=2))  # noqa: T201
        print("--- End Report ---\n")  # noqa: T201

        # Sanity check: bytes per event should be under 5000
        # Typical Redis JSON + Stream overhead is 1-2KB per event
        assert result["bytes_per_event"] < 5000, (
            f"Memory growth per event ({result['bytes_per_event']} bytes) "
            f"exceeds sanity threshold of 5000 bytes"
        )

        # Write result to stdout for CI capture
        print(  # noqa: T201
            f"BENCHMARK_MEMORY: {json.dumps(result)}"
        )
