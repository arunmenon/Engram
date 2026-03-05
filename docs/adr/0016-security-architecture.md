# ADR-0016: Security Architecture

Status: **Accepted**
Date: 2026-03-03

## Context

The Engram context graph service exposes a REST API that stores and queries sensitive agent execution traces. As the service moves toward multi-tenant deployment, authentication, authorization, rate limiting, and input validation must be formally documented.

## Decision

### Authentication

Two-tier bearer token authentication using HMAC-safe constant-time comparison:

| Guard | Settings Key | Protects |
|-------|-------------|----------|
| `require_api_key` | `CG_AUTH_API_KEY` | All `/v1/` endpoints |
| `require_admin_key` | `CG_AUTH_ADMIN_KEY` | `/v1/admin/*`, GDPR endpoints |

When the corresponding key is not set (None), the guard is disabled, allowing unauthenticated access in development mode. Token extraction uses the `Authorization: Bearer <token>` header pattern.

Implementation: `api/dependencies.py` — `require_api_key()`, `require_admin_key()`.

### Rate Limiting

Token bucket algorithm with two tiers:

| Tier | Requests | Window | Burst |
|------|----------|--------|-------|
| default | 120 | 30s | 120 |
| admin | 30 | 30s | 30 |

Rate limit state is stored in-memory per process. The `X-RateLimit-Remaining` and `X-RateLimit-Reset` headers are returned on every response. Exempt endpoints: `/health`, `/metrics`, `/docs`, `/openapi.json`.

Implementation: `api/rate_limit.py` — `RateLimiterStore`, `resolve_tier()`.
Metric: `engram_rate_limit_exceeded_total` counter with `tier` label.

### CORS Policy

Configured via `CORSMiddleware` in `api/middleware.py`:
- Origins: configurable via `CG_CORS_ORIGINS` (default: `["*"]` for development)
- Methods: `GET`, `POST`, `DELETE`, `OPTIONS`
- Credentials: disabled by default

### Input Validation

- All event payloads validated through Pydantic v2 strict mode at the API boundary
- Event types must be dot-namespaced strings (validated in `domain/validation.py`)
- UUIDs validated as proper UUID format
- Query parameters enforce bounds: `max_nodes` capped at 500, `max_depth` at 10

### Secrets Management

All secrets use Pydantic `SecretStr` fields and are never logged or serialized:
- `CG_AUTH_API_KEY` — API key for standard access
- `CG_AUTH_ADMIN_KEY` — Admin key for privileged operations
- `CG_REDIS_PASSWORD` — Redis connection password
- `CG_NEO4J_PASSWORD` — Neo4j connection password

## Consequences

- Development mode works without any auth configuration (all guards disabled when keys are None)
- Production deployments must set `CG_AUTH_API_KEY` and `CG_AUTH_ADMIN_KEY`
- Rate limiting is per-process; horizontal scaling requires external rate limiting (e.g., API gateway)
- CORS must be tightened for production deployments
