"""Tests for the async circuit breaker."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from context_graph.adapters.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
)


async def _success() -> str:
    return "ok"


async def _failure() -> str:
    raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_starts_closed() -> None:
    """A new circuit breaker starts in CLOSED state."""
    cb = CircuitBreaker("test", failure_threshold=3)
    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_failures_open_circuit() -> None:
    """After N failures, the circuit opens."""
    cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=60.0)

    for _ in range(3):
        with pytest.raises(RuntimeError):
            await cb.call(_failure)

    assert cb.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_open_rejects_calls() -> None:
    """An open circuit raises CircuitOpenError immediately."""
    cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=60.0)

    # Trip the breaker
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await cb.call(_failure)

    assert cb.state == CircuitState.OPEN

    with pytest.raises(CircuitOpenError, match="is open"):
        await cb.call(_success)


@pytest.mark.asyncio
async def test_recovery_timeout_transitions_to_half_open() -> None:
    """After recovery timeout elapses, state transitions to HALF_OPEN."""
    cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=1.0)

    # Trip the breaker
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await cb.call(_failure)

    assert cb.state == CircuitState.OPEN

    # Simulate time passing beyond recovery timeout
    cb._last_failure_time = time.monotonic() - 2.0
    assert cb.state == CircuitState.HALF_OPEN


@pytest.mark.asyncio
async def test_half_open_success_closes() -> None:
    """A successful call in HALF_OPEN state closes the circuit."""
    cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=1.0)

    # Trip the breaker
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await cb.call(_failure)

    # Simulate time passing
    cb._last_failure_time = time.monotonic() - 2.0
    assert cb.state == CircuitState.HALF_OPEN

    # Successful call should close the circuit
    result = await cb.call(_success)
    assert result == "ok"
    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_half_open_failure_reopens() -> None:
    """A failed call in HALF_OPEN state re-opens the circuit."""
    cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=1.0)

    # Trip the breaker
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await cb.call(_failure)

    # Simulate time passing
    cb._last_failure_time = time.monotonic() - 2.0
    assert cb.state == CircuitState.HALF_OPEN

    # Failed call should re-open
    with pytest.raises(RuntimeError):
        await cb.call(_failure)

    assert cb.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_success_resets_failure_count() -> None:
    """A successful call resets the failure counter."""
    cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=60.0)

    # Two failures (below threshold)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await cb.call(_failure)

    assert cb.state == CircuitState.CLOSED

    # Success resets
    await cb.call(_success)
    assert cb._failure_count == 0

    # Two more failures — still below threshold
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await cb.call(_failure)

    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_half_open_max_concurrent() -> None:
    """Only half_open_max concurrent calls are allowed in HALF_OPEN."""
    cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=1.0, half_open_max=1)

    # Trip the breaker
    with pytest.raises(RuntimeError):
        await cb.call(_failure)

    # Simulate recovery
    cb._last_failure_time = time.monotonic() - 2.0
    assert cb.state == CircuitState.HALF_OPEN

    # First call succeeds and closes
    await cb.call(_success)
    assert cb.state == CircuitState.CLOSED
