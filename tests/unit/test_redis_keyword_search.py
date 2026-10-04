"""Redis side of the keyword channel (domain/keyword_search.py).

The conformance suite checks behaviour on Redis Stack when it is
available; these pin the commands: payload text stored at ingest, an
any-term FT.SEARCH query, and the index upgrade for existing indexes.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import orjson
import pytest

from context_graph.adapters.redis.indexes import ensure_event_index
from context_graph.adapters.redis.store import RedisEventStore, _event_to_json_bytes
from tests.fixtures.events import make_event


def _store(redis: AsyncMock) -> RedisEventStore:
    settings = MagicMock()
    settings.event_index = "idx:events"
    return RedisEventStore(client=redis, settings=settings)


class TestSearchText:
    def test_document_carries_payload_text(self) -> None:
        event = make_event(tool_name="web_search")
        document = orjson.loads(
            _event_to_json_bytes(
                event, 1, payload={"output": "Enterprise edition"}, search_text_max_chars=100
            )
        )
        assert document["search_text"] == "web_search Enterprise edition"

    def test_no_text_no_field(self) -> None:
        document = orjson.loads(_event_to_json_bytes(make_event(), 1, search_text_max_chars=100))
        assert "search_text" not in document


class TestSearchBm25:
    @pytest.mark.asyncio()
    async def test_any_term_query_with_session_filter(self) -> None:
        redis = AsyncMock()
        redis.execute_command.return_value = [0]

        await _store(redis).search_bm25(
            "Why was the payment for card 4242 declined?", session_id="s-1", limit=7
        )

        redis.execute_command.assert_awaited_once_with(
            "FT.SEARCH",
            "idx:events",
            "(payment|card|4242|declined) @session_id:{s\\-1}",
            "LIMIT",
            "0",
            "7",
        )

    @pytest.mark.asyncio()
    async def test_stopwords_only_skips_search(self) -> None:
        redis = AsyncMock()
        assert await _store(redis).search_bm25("why did it?") == []
        redis.execute_command.assert_not_awaited()


def _info(*names: str) -> dict[str, list[list[bytes]]]:
    return {
        "attributes": [
            [b"identifier", f"$.{name}".encode(), b"attribute", name.encode(), b"type", b"TEXT"]
            for name in names
        ]
    }


def _client(info: object) -> tuple[MagicMock, MagicMock]:
    client = MagicMock()
    client.execute_command = AsyncMock()
    index = MagicMock()
    if isinstance(info, Exception):
        index.info = AsyncMock(side_effect=info)
    else:
        index.info = AsyncMock(return_value=info)
    index.create_index = AsyncMock()
    client.ft.return_value = index
    return client, index


class TestIndexUpgrade:
    @pytest.mark.asyncio()
    async def test_adds_search_text_to_an_existing_index(self) -> None:
        client, index = _client(_info("summary", "keywords"))
        await ensure_event_index(client, "idx:events")
        client.execute_command.assert_awaited_once_with(
            "FT.ALTER",
            "idx:events",
            "SCHEMA",
            "ADD",
            "$.search_text",
            "AS",
            "search_text",
            "TEXT",
            "WEIGHT",
            1.0,
        )
        index.create_index.assert_not_awaited()

    @pytest.mark.asyncio()
    async def test_current_index_is_left_alone(self) -> None:
        client, _index = _client(_info("summary", "keywords", "search_text"))
        await ensure_event_index(client, "idx:events")
        client.execute_command.assert_not_awaited()

    @pytest.mark.asyncio()
    async def test_unrecognised_info_is_not_altered(self) -> None:
        client, _index = _client({"attributes": []})
        await ensure_event_index(client, "idx:events")
        client.execute_command.assert_not_awaited()

    @pytest.mark.asyncio()
    async def test_missing_index_is_created_with_search_text(self) -> None:
        client, index = _client(RuntimeError("Unknown index name"))
        await ensure_event_index(client, "idx:events")
        fields = index.create_index.await_args.kwargs["fields"]
        assert "search_text" in {field.as_name for field in fields}
        client.execute_command.assert_not_awaited()
