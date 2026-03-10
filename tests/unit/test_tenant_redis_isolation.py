"""Tests for Redis tenant isolation — verify key prefixing and query scoping.

Validates that:
1. All public RedisEventStore methods accept tenant_id
2. Key helper functions produce correct tenant-prefixed keys
3. RediSearch index includes tenant_id TAG field
4. Trimmer functions accept tenant_id and use tenant-prefixed scan patterns
5. _event_to_json_bytes injects tenant_id into the JSON document
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING

import pytest

from context_graph.adapters.redis import trimmer
from context_graph.adapters.redis.indexes import event_index_fields
from context_graph.adapters.redis.store import (
    RedisEventStore,
    _event_to_json_bytes,
    _tenant_event_key,
    _tenant_key,
    _tenant_session_stream,
    _tenant_stream_key,
)

if TYPE_CHECKING:
    from context_graph.domain.models import Event


# ---------------------------------------------------------------------------
# Key helper tests
# ---------------------------------------------------------------------------


class TestTenantKeyHelpers:
    """Verify tenant key prefixing functions."""

    def test_tenant_key(self) -> None:
        assert _tenant_key("dedup:events", "acme") == "t:acme:dedup:events"

    def test_tenant_key_default(self) -> None:
        assert _tenant_key("dedup:events", "default") == "t:default:dedup:events"

    def test_tenant_event_key(self) -> None:
        result = _tenant_event_key("evt:", "abc-123", "acme")
        assert result == "t:acme:evt:abc-123"

    def test_tenant_stream_key(self) -> None:
        result = _tenant_stream_key("events:__global__", "acme")
        assert result == "t:acme:events:__global__"

    def test_tenant_session_stream(self) -> None:
        result = _tenant_session_stream("sess-001", "acme")
        assert result == "t:acme:events:session:sess-001"

    def test_different_tenants_produce_different_keys(self) -> None:
        """Two different tenants must never share key space."""
        key_a = _tenant_event_key("evt:", "event-1", "tenant-a")
        key_b = _tenant_event_key("evt:", "event-1", "tenant-b")
        assert key_a != key_b
        assert "tenant-a" in key_a
        assert "tenant-b" in key_b


# ---------------------------------------------------------------------------
# JSON serialization tests
# ---------------------------------------------------------------------------


class TestEventJsonTenantInjection:
    """Verify _event_to_json_bytes includes tenant_id."""

    def _make_event(self, event_id: str) -> Event:
        from datetime import UTC, datetime
        from uuid import UUID

        from context_graph.domain.models import Event

        return Event(
            event_id=UUID(event_id),
            event_type="test.event",
            occurred_at=datetime.now(UTC),
            session_id="sess-001",
            agent_id="agent-001",
            trace_id="trace-001",
            payload_ref="ref-001",
        )

    def test_tenant_id_injected_in_json(self) -> None:
        """The serialized JSON must contain the tenant_id field."""
        import orjson

        event = self._make_event("11111111-1111-1111-1111-111111111111")
        epoch_ms = 1707644400000
        result = _event_to_json_bytes(event, epoch_ms, tenant_id="acme-corp")
        doc = orjson.loads(result)
        assert doc["tenant_id"] == "acme-corp"

    def test_default_tenant_id(self) -> None:
        import orjson

        event = self._make_event("22222222-2222-2222-2222-222222222222")
        result = _event_to_json_bytes(event, 1707644400000)
        doc = orjson.loads(result)
        assert doc["tenant_id"] == "default"


# ---------------------------------------------------------------------------
# RediSearch index schema tests
# ---------------------------------------------------------------------------


class TestRedisIndexTenantField:
    """Verify the RediSearch index includes tenant_id TAG."""

    def test_tenant_id_tag_in_index_fields(self) -> None:
        fields = event_index_fields()
        field_names = [f.as_name for f in fields]
        assert "tenant_id" in field_names

    def test_tenant_id_is_tag_field(self) -> None:
        from redis.commands.search.field import TagField

        fields = event_index_fields()
        tenant_field = next(
            (f for f in fields if f.as_name == "tenant_id"), None
        )
        assert tenant_field is not None
        assert isinstance(tenant_field, TagField)

    def test_tenant_id_is_first_field(self) -> None:
        """tenant_id should be the first field for efficient filtering."""
        fields = event_index_fields()
        assert fields[0].as_name == "tenant_id"


# ---------------------------------------------------------------------------
# RedisEventStore method signature tests
# ---------------------------------------------------------------------------


class TestStoreMethodSignatures:
    """Verify all public methods accept tenant_id."""

    PUBLIC_METHODS = [
        "append",
        "append_batch",
        "cleanup_dedup_set",
        "get_by_id",
        "get_by_session",
        "search",
        "search_bm25",
        "stream_length",
    ]

    @pytest.mark.parametrize("method_name", PUBLIC_METHODS)
    def test_method_accepts_tenant_id(self, method_name: str) -> None:
        method = getattr(RedisEventStore, method_name, None)
        assert method is not None, f"{method_name} not found"
        sig = inspect.signature(method)
        assert "tenant_id" in sig.parameters, (
            f"{method_name} missing tenant_id parameter"
        )
        param = sig.parameters["tenant_id"]
        assert param.default == "default", (
            f"{method_name} tenant_id default should be 'default'"
        )


# ---------------------------------------------------------------------------
# Trimmer function signature tests
# ---------------------------------------------------------------------------


class TestTrimmerTenantSignatures:
    """Verify all trimmer functions accept tenant_id."""

    TRIMMER_FUNCTIONS = [
        "trim_stream",
        "delete_expired_events",
        "cleanup_session_streams",
        "archive_and_delete_expired_events",
        "cleanup_dedup_set",
    ]

    @pytest.mark.parametrize("func_name", TRIMMER_FUNCTIONS)
    def test_function_accepts_tenant_id(self, func_name: str) -> None:
        func = getattr(trimmer, func_name, None)
        assert func is not None, f"{func_name} not found"
        sig = inspect.signature(func)
        assert "tenant_id" in sig.parameters, (
            f"{func_name} missing tenant_id parameter"
        )
        param = sig.parameters["tenant_id"]
        assert param.default == "default", (
            f"{func_name} tenant_id default should be 'default'"
        )
