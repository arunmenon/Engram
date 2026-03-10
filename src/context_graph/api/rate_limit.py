"""Token bucket rate limiter with LRU client tracking.

Pure-Python implementation with no external dependencies.
Uses time.monotonic() for accurate, monotonic timing.

Three tiers: exempt (no limit), standard (configurable RPM),
admin (configurable RPM).
"""

from __future__ import annotations

import time
from collections import OrderedDict


class TokenBucket:
    """Token bucket rate limiter for a single client.

    Refills tokens at a constant rate up to capacity.
    Each consume() call removes one token; returns False when empty.
    """

    __slots__ = ("capacity", "tokens", "refill_rate", "last_refill")

    def __init__(self, capacity: float, refill_rate: float) -> None:
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.last_refill = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def consume(self) -> bool:
        """Try to consume one token. Returns True if successful."""
        self._refill()
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    def time_until_available(self) -> float:
        """Seconds until at least one token is available."""
        self._refill()
        if self.tokens >= 1.0:
            return 0.0
        return (1.0 - self.tokens) / self.refill_rate


class RateLimiterStore:
    """LRU-bounded store of per-client token buckets.

    Evicts the least-recently-used client when the store exceeds
    max_clients entries.
    """

    def __init__(self, max_clients: int = 10000) -> None:
        self._buckets: OrderedDict[str, TokenBucket] = OrderedDict()
        self._max_clients = max_clients

    def get_or_create(self, client_id: str, capacity: float, refill_rate: float) -> TokenBucket:
        """Return existing bucket or create a new one for client_id."""
        if client_id in self._buckets:
            self._buckets.move_to_end(client_id)
            return self._buckets[client_id]
        bucket = TokenBucket(capacity, refill_rate)
        self._buckets[client_id] = bucket
        while len(self._buckets) > self._max_clients:
            self._buckets.popitem(last=False)
        return bucket


# ---------------------------------------------------------------------------
# Tier resolution
# ---------------------------------------------------------------------------

_EXEMPT_PATHS = frozenset(
    {
        "/v1/health",
        "/v1/health/live",
        "/v1/health/ready",
        "/health",
        "/health/live",
        "/health/ready",
        "/metrics",
    }
)
_ADMIN_PREFIXES = ("/v1/admin/",)


def resolve_tier(path: str, method: str = "GET") -> str:
    """Classify a request path into a rate-limit tier.

    Returns one of: "exempt", "admin", "standard".
    """
    if path in _EXEMPT_PATHS:
        return "exempt"
    if any(path.startswith(p) for p in _ADMIN_PREFIXES):
        return "admin"
    if path.endswith("/data-export"):
        return "admin"
    if method == "DELETE" and "/users/" in path:
        return "admin"
    return "standard"
