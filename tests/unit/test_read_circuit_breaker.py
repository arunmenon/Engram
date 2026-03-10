"""Tests for the Neo4j read circuit breaker.

Validates:
- Read CB settings exist in CircuitBreakerSettings
- Read CB opens after neo4j_read_failure_threshold consecutive failures
- Read CB rejects calls when open
- Read CB transitions to half-open after recovery timeout
- Read CB closes on successful probe call
- Read CB has a separate instance from write CB in Neo4jGraphStore
"""

from __future__ import annotations

import time

import pytest

from context_graph.adapters.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
)
from context_graph.settings import CircuitBreakerSettings

# ---------------------------------------------------------------------------
# Settings tests
# ---------------------------------------------------------------------------


class TestReadCBSettings:
    """Verify read circuit breaker settings exist and have sensible defaults."""

    def test_read_failure_threshold_exists(self) -> None:
        settings = CircuitBreakerSettings()
        assert hasattr(settings, "neo4j_read_failure_threshold")
        assert settings.neo4j_read_failure_threshold == 8

    def test_read_recovery_timeout_exists(self) -> None:
        settings = CircuitBreakerSettings()
        assert hasattr(settings, "neo4j_read_recovery_timeout")
        assert settings.neo4j_read_recovery_timeout == 30.0

    def test_read_threshold_higher_than_write(self) -> None:
        """Read CB should be more tolerant than write CB (higher threshold)."""
        settings = CircuitBreakerSettings()
        assert settings.neo4j_read_failure_threshold >= settings.neo4j_failure_threshold


# ---------------------------------------------------------------------------
# Behavior tests using CircuitBreaker directly
# ---------------------------------------------------------------------------


async def _success() -> str:
    return "ok"


async def _failure() -> str:
    raise RuntimeError("read failed")


@pytest.mark.asyncio
async def test_read_cb_starts_closed() -> None:
    """A new read circuit breaker starts in CLOSED state."""
    cb = CircuitBreaker("neo4j_read", failure_threshold=8, recovery_timeout=30.0)
    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_read_cb_opens_after_n_failures() -> None:
    """After 8 consecutive failures, the read CB opens."""
    cb = CircuitBreaker("neo4j_read", failure_threshold=8, recovery_timeout=60.0)

    for _ in range(8):
        with pytest.raises(RuntimeError):
            await cb.call(_failure)

    assert cb.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_read_cb_does_not_open_below_threshold() -> None:
    """Below failure_threshold, the read CB stays closed."""
    cb = CircuitBreaker("neo4j_read", failure_threshold=8, recovery_timeout=60.0)

    for _ in range(7):
        with pytest.raises(RuntimeError):
            await cb.call(_failure)

    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_read_cb_rejects_when_open() -> None:
    """An open read CB raises CircuitOpenError immediately."""
    cb = CircuitBreaker("neo4j_read", failure_threshold=8, recovery_timeout=60.0)

    # Trip the breaker
    for _ in range(8):
        with pytest.raises(RuntimeError):
            await cb.call(_failure)

    assert cb.state == CircuitState.OPEN

    with pytest.raises(CircuitOpenError, match="is open"):
        await cb.call(_success)


@pytest.mark.asyncio
async def test_read_cb_transitions_to_half_open() -> None:
    """After recovery timeout, state transitions to HALF_OPEN."""
    cb = CircuitBreaker("neo4j_read", failure_threshold=8, recovery_timeout=1.0)

    for _ in range(8):
        with pytest.raises(RuntimeError):
            await cb.call(_failure)

    assert cb.state == CircuitState.OPEN

    # Simulate time passing beyond recovery timeout
    cb._last_failure_time = time.monotonic() - 2.0
    assert cb.state == CircuitState.HALF_OPEN


@pytest.mark.asyncio
async def test_read_cb_closes_on_successful_probe() -> None:
    """A successful call in HALF_OPEN closes the circuit."""
    cb = CircuitBreaker("neo4j_read", failure_threshold=8, recovery_timeout=1.0)

    for _ in range(8):
        with pytest.raises(RuntimeError):
            await cb.call(_failure)

    # Simulate recovery period elapsed
    cb._last_failure_time = time.monotonic() - 2.0
    assert cb.state == CircuitState.HALF_OPEN

    result = await cb.call(_success)
    assert result == "ok"
    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_read_cb_reopens_on_half_open_failure() -> None:
    """A failed probe in HALF_OPEN re-opens the circuit."""
    cb = CircuitBreaker("neo4j_read", failure_threshold=8, recovery_timeout=1.0)

    for _ in range(8):
        with pytest.raises(RuntimeError):
            await cb.call(_failure)

    cb._last_failure_time = time.monotonic() - 2.0
    assert cb.state == CircuitState.HALF_OPEN

    with pytest.raises(RuntimeError):
        await cb.call(_failure)

    assert cb.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_read_cb_success_resets_failure_count() -> None:
    """A successful call resets the failure counter before threshold."""
    cb = CircuitBreaker("neo4j_read", failure_threshold=8, recovery_timeout=60.0)

    # 7 failures (below threshold)
    for _ in range(7):
        with pytest.raises(RuntimeError):
            await cb.call(_failure)

    assert cb.state == CircuitState.CLOSED

    # Success resets counter
    await cb.call(_success)
    assert cb._failure_count == 0

    # 7 more failures still below threshold
    for _ in range(7):
        with pytest.raises(RuntimeError):
            await cb.call(_failure)

    assert cb.state == CircuitState.CLOSED


# ---------------------------------------------------------------------------
# Neo4jGraphStore integration (read CB is a separate instance from write CB)
# ---------------------------------------------------------------------------


class TestReadCBInStore:
    """Verify that Neo4jGraphStore wires up a separate read circuit breaker."""

    def test_store_has_read_cb_attribute(self) -> None:
        """Neo4jGraphStore.__init__ should create self._read_cb."""
        # Check the class has _read_cb initialization in __init__
        # by inspecting the source code (avoid connecting to Neo4j)
        import inspect

        from context_graph.adapters.neo4j.store import Neo4jGraphStore

        source = inspect.getsource(Neo4jGraphStore.__init__)
        assert "_read_cb" in source
        assert "neo4j_read" in source

    def test_read_cb_settings_wired(self) -> None:
        """CircuitBreakerSettings has neo4j_read_failure_threshold and recovery_timeout."""
        settings = CircuitBreakerSettings()
        assert isinstance(settings.neo4j_read_failure_threshold, int)
        assert isinstance(settings.neo4j_read_recovery_timeout, float)
        assert settings.neo4j_read_failure_threshold > 0
        assert settings.neo4j_read_recovery_timeout > 0
