"""Async circuit breaker for protecting external service calls.

Implements the standard closed -> open -> half-open -> closed/open
state machine.  When a downstream service (Neo4j, LLM) accumulates
failures beyond the threshold, the circuit opens and rejects calls
immediately until the recovery timeout elapses.

Usage:
    cb = CircuitBreaker("neo4j_write", failure_threshold=5, recovery_timeout=30.0)
    result = await cb.call(some_async_func, arg1, kwarg=val)
"""

from __future__ import annotations

import asyncio
import time
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when a call is rejected because the circuit is open."""


class CircuitBreaker:
    """Async circuit breaker with configurable thresholds.

    State transitions:
      - CLOSED: normal operation; failures increment counter
      - OPEN: all calls rejected with CircuitOpenError
      - HALF_OPEN: one probe call allowed; success closes, failure re-opens
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max: int = 1,
    ) -> None:
        self.name = name
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_max = half_open_max
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._half_open_calls = 0
        self._state = CircuitState.CLOSED
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Return the effective circuit state.

        If the circuit is OPEN and the recovery timeout has elapsed,
        the effective state is HALF_OPEN (without mutating internal state
        until a call actually goes through).
        """
        if (
            self._state == CircuitState.OPEN
            and time.monotonic() - self._last_failure_time >= self._recovery_timeout
        ):
            return CircuitState.HALF_OPEN
        return self._state

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute *func* through the circuit breaker.

        Raises CircuitOpenError if the circuit is open.
        """
        current = self.state

        if current == CircuitState.OPEN:
            raise CircuitOpenError(f"Circuit '{self.name}' is open")

        if current == CircuitState.HALF_OPEN:
            async with self._lock:
                if self._half_open_calls >= self._half_open_max:
                    raise CircuitOpenError(f"Circuit '{self.name}' half-open limit reached")
                self._half_open_calls += 1

        try:
            result = await func(*args, **kwargs)
            async with self._lock:
                self._failure_count = 0
                self._half_open_calls = 0
                self._state = CircuitState.CLOSED
            return result
        except Exception:
            async with self._lock:
                self._failure_count += 1
                self._last_failure_time = time.monotonic()
                if (
                    current == CircuitState.HALF_OPEN
                    or self._failure_count >= self._failure_threshold
                ):
                    self._state = CircuitState.OPEN
                    self._half_open_calls = 0
            raise
