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

    def consume(self, amount: float = 1.0) -> bool:
        """Try to consume ``amount`` tokens. Returns True if successful."""
        self._refill()
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False

    def time_until_available(self, amount: float = 1.0) -> float:
        """Seconds until at least ``amount`` tokens are available."""
        self._refill()
        if self.tokens >= amount:
            return 0.0
        return (amount - self.tokens) / self.refill_rate


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


class EventQuota:
    """Events per minute per client, charged by the number of events ingested.

    The request rate limit counts a 1,000-event batch as one request; this
    counts it as 1,000 events. In-process, like the request limiter: each
    API replica keeps its own buckets.
    """

    def __init__(self, events_per_minute: int, max_clients: int = 10000) -> None:
        self._capacity = float(events_per_minute)
        self._refill_rate = events_per_minute / 60.0
        self._store = RateLimiterStore(max_clients=max_clients)

    def charge(self, client_id: str, count: int) -> float | None:
        """Take ``count`` events from the client's quota; None, or seconds to wait.

        A request larger than a whole minute's quota waits for a full bucket
        and then goes through, so oversized batches are slowed, never refused
        forever.
        """
        bucket = self._store.get_or_create(client_id, self._capacity, self._refill_rate)
        amount = min(float(count), self._capacity)
        if bucket.consume(amount):
            return None
        return bucket.time_until_available(amount)


# ---------------------------------------------------------------------------
# Tier resolution
# ---------------------------------------------------------------------------

_EXEMPT_PATHS = frozenset({"/v1/health", "/metrics"})
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
