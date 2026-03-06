# ADR-0017: Observability Architecture

Status: **Accepted**
Date: 2026-03-03

## Context

The Engram context graph service requires comprehensive observability for production operations: monitoring service health, diagnosing latency, tracking consumer progress, and correlating requests across the event pipeline.

## Decision

### Metrics (Prometheus)

Ten application-level metrics defined in `metrics.py`:

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `engram_http_requests_total` | Counter | method, endpoint, status | Total HTTP requests |
| `engram_http_request_duration_seconds` | Histogram | method, endpoint | HTTP request latency |
| `engram_rate_limit_exceeded_total` | Counter | tier | Rate-limited requests |
| `engram_events_ingested_total` | Counter | — | Total events ingested |
| `engram_events_batch_size` | Histogram | — | Batch ingestion sizes |
| `engram_consumer_messages_processed_total` | Counter | consumer | Messages processed per consumer |
| `engram_consumer_message_errors_total` | Counter | consumer | Consumer processing errors |
| `engram_consumer_messages_dead_lettered_total` | Counter | consumer | Messages sent to DLQ |
| `engram_consumer_lag_messages` | Gauge | group | Consumer group lag (defined, not yet populated) |
| `engram_graph_query_duration_seconds` | Histogram | query_type | Neo4j query latency |

Metrics endpoint: `GET /metrics` (Prometheus scrape target, exempt from auth and rate limiting).

### Structured Logging (structlog)

All logging uses `structlog` with bound context variables:
- Logger instances created via `structlog.get_logger(__name__)`
- Key-value structured output for machine parsing
- Log level configurable via `CG_LOG_LEVEL` environment variable (default: `INFO`)
- Filter bound logger configured in worker entry points

### Request Tracing

Request correlation via `X-Request-ID` header:
- Generated as UUID4 if not provided by the client
- Propagated through structlog context variables
- Returned in the response via `X-Request-ID` header
- `X-Request-Time-Ms` header added to every response with processing duration

Implementation: `api/middleware.py` — `RequestTimingMiddleware`.

### Health Checks

| Endpoint | Purpose | Auth Required |
|----------|---------|---------------|
| `GET /health` | Basic liveness check | No |
| `GET /v1/admin/health/detailed` | Redis + Neo4j connectivity, graph stats, stream length | Admin key |

### Consumer Observability

Each consumer worker logs structured events for:
- Message processing success/failure
- Dead-letter queue moves (after max retries)
- Consumer group lag (via `XINFO GROUPS`)
- Consolidation cycle start/complete/failure
- Timer loop intervals

## Consequences

- All metrics are collected in-process via `prometheus_client`; no external agent required
- structlog output is JSON-compatible for log aggregation (ELK, Datadog, etc.)
- Request IDs enable end-to-end tracing from API call through consumer processing
- Consumer lag gauge is defined but requires periodic population (future enhancement)
- Health checks provide both simple liveness and detailed dependency checks
