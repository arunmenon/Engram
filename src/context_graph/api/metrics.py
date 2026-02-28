"""Prometheus metrics definitions for the Context Graph API.

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

CONSUMER_LAG = Gauge(
    "engram_consumer_lag_messages",
    "Consumer group lag",
    ["group"],
)

# ---------------------------------------------------------------------------
# Graph queries
# ---------------------------------------------------------------------------

GRAPH_QUERY_DURATION = Histogram(
    "engram_graph_query_duration_seconds",
    "Neo4j query duration",
    ["query_type"],
)
