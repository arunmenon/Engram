"""Prometheus metrics definitions for the Context Graph service.

Defines all application-level metrics collected by the service:
HTTP layer, event ingestion, consumer workers, and graph queries.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------

HTTP_REQUESTS_TOTAL = Counter(
    "engram_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "engram_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
)

RATE_LIMIT_EXCEEDED = Counter(
    "engram_rate_limit_exceeded_total",
    "Rate limited requests",
    ["tier"],
)

# ---------------------------------------------------------------------------
# Event ingestion
# ---------------------------------------------------------------------------

EVENTS_INGESTED_TOTAL = Counter(
    "engram_events_ingested_total",
    "Total events ingested",
)

EVENTS_BATCH_SIZE = Histogram(
    "engram_events_batch_size",
    "Batch ingestion size",
)

# ---------------------------------------------------------------------------
# Consumer workers
# ---------------------------------------------------------------------------

CONSUMER_MESSAGES_PROCESSED = Counter(
    "engram_consumer_messages_processed_total",
    "Messages processed by consumers",
    ["consumer"],
)

CONSUMER_MESSAGE_ERRORS = Counter(
    "engram_consumer_message_errors_total",
    "Consumer processing errors",
    ["consumer"],
)

CONSUMER_MESSAGES_DEAD_LETTERED = Counter(
    "engram_consumer_messages_dead_lettered_total",
    "Messages moved to dead-letter queue after max retries",
    ["consumer"],
)

CONSUMER_LAG = Gauge(
    "engram_consumer_lag_messages",
    "Consumer group lag",
    ["group"],
)

CONSUMER_THROUGHPUT = Gauge(
    "engram_consumer_events_per_second",
    "Consumer processing rate",
    ["consumer"],
)

CONSUMER_BATCH_ACTUAL_SIZE = Histogram(
    "engram_consumer_batch_actual_size",
    "Actual batch size used by consumer after adaptive sizing",
    ["consumer"],
)

# ---------------------------------------------------------------------------
# Graph queries
# ---------------------------------------------------------------------------

GRAPH_QUERY_DURATION = Histogram(
    "engram_graph_query_duration_seconds",
    "Neo4j query duration",
    ["query_type"],
)

# ---------------------------------------------------------------------------
# Per-operation latency
# ---------------------------------------------------------------------------

REDIS_OP_DURATION = Histogram(
    "engram_redis_op_duration_seconds",
    "Redis operation duration",
    ["operation"],
)

NEO4J_OP_DURATION = Histogram(
    "engram_neo4j_op_duration_seconds",
    "Neo4j operation duration",
    ["operation"],
)

LLM_CALL_DURATION = Histogram(
    "engram_llm_call_duration_seconds",
    "LLM call duration",
    ["model"],
)

# ---------------------------------------------------------------------------
# Redis pool and memory
# ---------------------------------------------------------------------------

REDIS_POOL_SIZE = Gauge(
    "engram_redis_pool_size",
    "Redis connection pool size",
)

REDIS_POOL_IN_USE = Gauge(
    "engram_redis_pool_in_use",
    "Redis connections currently in use",
)

REDIS_MEMORY_USED = Gauge(
    "engram_redis_memory_used_bytes",
    "Redis used memory in bytes",
)

REDIS_MEMORY_PEAK = Gauge(
    "engram_redis_memory_peak_bytes",
    "Redis peak memory in bytes",
)

REDIS_MEMORY_FRAGMENTATION = Gauge(
    "engram_redis_memory_fragmentation_ratio",
    "Redis memory fragmentation ratio",
)

# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------

CIRCUIT_BREAKER_STATE = Gauge(
    "engram_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half-open)",
    ["name"],
)
