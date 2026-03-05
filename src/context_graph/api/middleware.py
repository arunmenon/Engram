"""API middleware: error handling, request timing, and observability.

Registers exception handlers, request ID propagation, and a request
timing middleware with Prometheus instrumentation on the FastAPI app.
"""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Any

import structlog
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from context_graph.api.rate_limit import RateLimiterStore, resolve_tier
from context_graph.domain.validation import ValidationError
from context_graph.metrics import (
    HTTP_REQUEST_DURATION,
    HTTP_REQUESTS_TOTAL,
    RATE_LIMIT_EXCEEDED,
)
from context_graph.settings import Settings

if TYPE_CHECKING:
    from fastapi import FastAPI, Request, Response

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


async def _validation_error_handler(
    _request: Request,
    exc: ValidationError,
) -> ORJSONResponse:
    """Convert domain ValidationError to a 422 response."""
    return ORJSONResponse(
        status_code=422,
        content={
            "detail": [
                {
                    "field": exc.field,
                    "message": exc.message,
                }
            ]
        },
    )


async def _generic_error_handler(
    _request: Request,
    exc: Exception,
) -> ORJSONResponse:
    """Convert unhandled exceptions to a structured 500 response."""
    logger.error("unhandled_exception", exc_info=exc)
    return ORJSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
        },
    )


# ---------------------------------------------------------------------------
# Request ID middleware
# ---------------------------------------------------------------------------


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Propagate or generate an X-Request-ID header for every request.

    If the incoming request carries an ``X-Request-ID`` header, it is
    reused; otherwise a new UUID4 is generated. The ID is bound to the
    structlog context and returned in the response header.
    """

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        structlog.contextvars.unbind_contextvars("request_id")
        return response


# ---------------------------------------------------------------------------
# Request timing middleware
# ---------------------------------------------------------------------------


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Adds an X-Request-Time-Ms header and records Prometheus metrics."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        start_time = time.monotonic()
        response: Response = await call_next(request)
        elapsed_seconds = time.monotonic() - start_time
        elapsed_ms = elapsed_seconds * 1000
        response.headers["X-Request-Time-Ms"] = f"{elapsed_ms:.1f}"

        # Record Prometheus metrics — use route template to avoid high-cardinality
        method = request.method
        route = request.scope.get("route")
        path = route.path if route else request.url.path
        status = str(response.status_code)
        HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=path, status=status).inc()
        HTTP_REQUEST_DURATION.labels(method=method, endpoint=path).observe(elapsed_seconds)

        return response


# ---------------------------------------------------------------------------
# Rate limit middleware
# ---------------------------------------------------------------------------


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-client token bucket rate limiting.

    Three tiers: exempt (health/metrics), standard, admin.
    Returns 429 with Retry-After header when the bucket is empty.
    """

    def __init__(self, app: Any, settings: Settings) -> None:
        super().__init__(app)
        self._settings = settings.rate_limit
        self._store = RateLimiterStore(max_clients=self._settings.max_clients)

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        if not self._settings.enabled:
            resp: Response = await call_next(request)
            return resp

        tier = resolve_tier(request.url.path, request.method)
        if tier == "exempt":
            resp_exempt: Response = await call_next(request)
            return resp_exempt

        rpm = self._settings.admin_rpm if tier == "admin" else self._settings.standard_rpm

        capacity = float(rpm)
        refill_rate = rpm / 60.0  # per second

        client_id = request.client.host if request.client else "unknown"
        bucket = self._store.get_or_create(f"{tier}:{client_id}", capacity, refill_rate)

        if not bucket.consume():
            retry_after = bucket.time_until_available()
            RATE_LIMIT_EXCEEDED.labels(tier=tier).inc()
            return ORJSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded", "retry_after": round(retry_after, 1)},
                headers={
                    "Retry-After": str(int(retry_after) + 1),
                    "X-RateLimit-Limit": str(rpm),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(rpm)
        response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
        return response


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_middleware(app: FastAPI, settings: Settings | None = None) -> None:
    """Attach all middleware and exception handlers to the app."""
    if settings is None:
        settings = Settings()
    app.add_exception_handler(ValidationError, _validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _generic_error_handler)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RequestTimingMiddleware)
    app.add_middleware(RateLimitMiddleware, settings=settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )
