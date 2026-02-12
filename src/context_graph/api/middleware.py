"""API middleware: error handling and request timing.

Registers exception handlers and a request timing middleware
on the FastAPI app.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import structlog
from fastapi.responses import ORJSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from context_graph.domain.validation import ValidationError

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
            "type": type(exc).__name__,
        },
    )


# ---------------------------------------------------------------------------
# Request timing middleware
# ---------------------------------------------------------------------------


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Adds an X-Request-Time-Ms header to every response."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        start_time = time.monotonic()
        response: Response = await call_next(request)
        elapsed_ms = (time.monotonic() - start_time) * 1000
        response.headers["X-Request-Time-Ms"] = f"{elapsed_ms:.1f}"
        return response


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_middleware(app: FastAPI) -> None:
    """Attach all middleware and exception handlers to the app."""
    app.add_exception_handler(ValidationError, _validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _generic_error_handler)
    app.add_middleware(RequestTimingMiddleware)
