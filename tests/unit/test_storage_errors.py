"""Tests for the neutral storage error set and adapter translation (ADR-0019)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from neo4j import exceptions as neo4j_errors
from redis import exceptions as redis_errors

from context_graph.adapters.errors import translate_errors
from context_graph.adapters.neo4j.errors import translate_neo4j_error
from context_graph.adapters.redis.errors import translate_redis_error
from context_graph.adapters.redis.store import RedisEventStore
from context_graph.ports.errors import (
    ConflictError,
    InvalidRequestError,
    StorageError,
    StorageTimeoutError,
    UnavailableError,
)


class TestRedisTranslation:
    @pytest.mark.parametrize(
        ("driver_error", "neutral"),
        [
            (redis_errors.TimeoutError("t"), StorageTimeoutError),
            (redis_errors.ConnectionError("c"), UnavailableError),
            (redis_errors.BusyLoadingError("b"), UnavailableError),
            (redis_errors.ResponseError("r"), InvalidRequestError),
            (redis_errors.DataError("d"), StorageError),
        ],
    )
    def test_maps_driver_errors(self, driver_error, neutral) -> None:
        assert type(translate_redis_error(driver_error)) is neutral

    def test_ignores_other_errors(self) -> None:
        assert translate_redis_error(ValueError("v")) is None


class TestNeo4jTranslation:
    @pytest.mark.parametrize(
        ("driver_error", "neutral"),
        [
            (neo4j_errors.ServiceUnavailable("s"), UnavailableError),
            (neo4j_errors.SessionExpired("s"), UnavailableError),
            (neo4j_errors.ConnectionAcquisitionTimeoutError("t"), StorageTimeoutError),
            (neo4j_errors.TransientError(), UnavailableError),
            (neo4j_errors.ConstraintError(), ConflictError),
            (neo4j_errors.CypherSyntaxError(), InvalidRequestError),
            (neo4j_errors.DatabaseError(), StorageError),
        ],
    )
    def test_maps_driver_errors(self, driver_error, neutral) -> None:
        assert type(translate_neo4j_error(driver_error)) is neutral

    def test_ignores_other_errors(self) -> None:
        assert translate_neo4j_error(KeyError("k")) is None


class TestTimeoutIsBuiltinTimeout:
    def test_existing_timeout_handlers_still_catch(self) -> None:
        assert issubclass(StorageTimeoutError, TimeoutError)
        assert issubclass(StorageError, Exception)


class TestDecorator:
    @pytest.mark.asyncio()
    async def test_public_methods_translate_and_chain(self) -> None:
        redis = AsyncMock()
        redis.execute_command.side_effect = redis_errors.ConnectionError("down")
        store = RedisEventStore(client=redis, settings=MagicMock(event_key_prefix="evt:"))
        with pytest.raises(UnavailableError) as info:
            await store.get_by_id("e1")
        assert isinstance(info.value.__cause__, redis_errors.ConnectionError)

    @pytest.mark.asyncio()
    async def test_non_driver_errors_pass_through(self) -> None:
        @translate_errors(translate_redis_error)
        class Adapter:
            async def run(self) -> None:
                raise ValueError("bad input")

            async def _private(self) -> None:
                raise redis_errors.ConnectionError("down")

        with pytest.raises(ValueError):
            await Adapter().run()
        with pytest.raises(redis_errors.ConnectionError):
            await Adapter()._private()
