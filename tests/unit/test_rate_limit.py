"""Unit tests for api/rate_limit.py — Token bucket and tier resolution."""

from __future__ import annotations

from context_graph.api.rate_limit import (
    RateLimiterStore,
    TokenBucket,
    resolve_tier,
)

# ---------------------------------------------------------------------------
# TokenBucket
# ---------------------------------------------------------------------------


class TestTokenBucket:
    def test_allows_within_capacity(self):
        bucket = TokenBucket(capacity=5.0, refill_rate=1.0)
        for _ in range(5):
            assert bucket.consume() is True

    def test_rejects_when_empty(self):
        bucket = TokenBucket(capacity=2.0, refill_rate=1.0)
        assert bucket.consume() is True
        assert bucket.consume() is True
        assert bucket.consume() is False

    def test_refills_after_time(self):
        bucket = TokenBucket(capacity=1.0, refill_rate=10.0)  # 10 tokens/sec
        assert bucket.consume() is True
        assert bucket.consume() is False

        # Simulate 0.2s passing (should refill ~2 tokens)
        bucket.last_refill -= 0.2
        assert bucket.consume() is True

    def test_does_not_exceed_capacity(self):
        bucket = TokenBucket(capacity=3.0, refill_rate=100.0)
        # Drain all tokens
        for _ in range(3):
            bucket.consume()
        # Simulate a very long wait
        bucket.last_refill -= 1000.0
        bucket._refill()
        assert bucket.tokens == 3.0

    def test_time_until_available_zero_when_tokens_exist(self):
        bucket = TokenBucket(capacity=5.0, refill_rate=1.0)
        assert bucket.time_until_available() == 0.0

    def test_time_until_available_positive_when_empty(self):
        bucket = TokenBucket(capacity=1.0, refill_rate=2.0)
        bucket.consume()  # drain
        wait = bucket.time_until_available()
        assert wait > 0.0
        assert wait <= 1.0  # At most 1/refill_rate = 0.5s


# ---------------------------------------------------------------------------
# RateLimiterStore
# ---------------------------------------------------------------------------


class TestRateLimiterStore:
    def test_creates_new_bucket(self):
        store = RateLimiterStore(max_clients=10)
        bucket = store.get_or_create("client-1", capacity=10.0, refill_rate=1.0)
        assert isinstance(bucket, TokenBucket)
        assert bucket.capacity == 10.0

    def test_returns_existing_bucket(self):
        store = RateLimiterStore(max_clients=10)
        bucket1 = store.get_or_create("client-1", capacity=10.0, refill_rate=1.0)
        bucket1.consume()
        bucket2 = store.get_or_create("client-1", capacity=10.0, refill_rate=1.0)
        assert bucket1 is bucket2
        assert bucket2.tokens < 10.0  # Same object, tokens were consumed

    def test_evicts_oldest_when_over_capacity(self):
        store = RateLimiterStore(max_clients=2)
        store.get_or_create("a", 10.0, 1.0)
        store.get_or_create("b", 10.0, 1.0)
        store.get_or_create("c", 10.0, 1.0)

        # "a" should have been evicted
        assert "a" not in store._buckets
        assert "b" in store._buckets
        assert "c" in store._buckets

    def test_move_to_end_on_access(self):
        store = RateLimiterStore(max_clients=2)
        store.get_or_create("a", 10.0, 1.0)
        store.get_or_create("b", 10.0, 1.0)
        # Access "a" again to move it to end
        store.get_or_create("a", 10.0, 1.0)
        # Now "b" is the oldest; adding "c" should evict "b"
        store.get_or_create("c", 10.0, 1.0)
        assert "a" in store._buckets
        assert "b" not in store._buckets
        assert "c" in store._buckets


# ---------------------------------------------------------------------------
# resolve_tier
# ---------------------------------------------------------------------------


class TestResolveTier:
    def test_health_exempt(self):
        assert resolve_tier("/v1/health") == "exempt"

    def test_metrics_exempt(self):
        assert resolve_tier("/metrics") == "exempt"

    def test_events_standard(self):
        assert resolve_tier("/v1/events") == "standard"

    def test_context_standard(self):
        assert resolve_tier("/v1/context/session-1") == "standard"

    def test_admin_stats(self):
        assert resolve_tier("/v1/admin/stats") == "admin"

    def test_admin_consolidation(self):
        assert resolve_tier("/v1/admin/consolidation") == "admin"

    def test_data_export_admin(self):
        assert resolve_tier("/v1/users/user-1/data-export") == "admin"

    def test_user_delete_admin(self):
        assert resolve_tier("/v1/users/user-1", method="DELETE") == "admin"

    def test_user_get_standard(self):
        assert resolve_tier("/v1/users/user-1", method="GET") == "standard"
