"""Tests for ADR-0019 step 1: storage settings, registry and worker wiring."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from context_graph.adapters.redis.subscription import RedisStreamSubscription
from context_graph.adapters.registry import UnknownBackendError, open_stores
from context_graph.settings import Settings


class TestConsumerSettingAliases:
    """Consumer settings fall back to their old CG_REDIS_* names."""

    def test_defaults_match_redis_settings(self) -> None:
        settings = Settings()
        assert settings.consumer.source == settings.redis.global_stream
        assert settings.consumer.group_projection == "graph-projection"
        assert settings.consumer.group_extraction == "session-extraction"
        assert settings.consumer.group_enrichment == "enrichment"
        assert settings.consumer.group_consolidation == "consolidation"
        assert settings.consumer.block_timeout_ms == settings.redis.block_timeout_ms

    def test_old_redis_names_still_honoured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CG_REDIS_GLOBAL_STREAM", "events:legacy")
        monkeypatch.setenv("CG_REDIS_GROUP_PROJECTION", "legacy-projection")
        monkeypatch.setenv("CG_REDIS_BLOCK_TIMEOUT_MS", "250")
        settings = Settings()
        assert settings.consumer.source == "events:legacy"
        assert settings.consumer.group_projection == "legacy-projection"
        assert settings.consumer.block_timeout_ms == 250

    def test_new_names_take_precedence(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CG_REDIS_GROUP_ENRICHMENT", "old")
        monkeypatch.setenv("CG_CONSUMER_GROUP_ENRICHMENT", "new")
        assert Settings().consumer.group_enrichment == "new"


class TestRetentionSettingAliases:
    def test_defaults_match_redis_settings(self) -> None:
        settings = Settings()
        assert settings.retention.log_hot_window_days == settings.redis.hot_window_days
        assert (
            settings.retention.log_retention_ceiling_days == settings.redis.retention_ceiling_days
        )
        assert (
            settings.retention.log_session_index_max_age_hours
            == settings.redis.session_stream_retention_hours
        )

    def test_old_and_new_names(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CG_REDIS_HOT_WINDOW_DAYS", "3")
        monkeypatch.setenv("CG_REDIS_RETENTION_CEILING_DAYS", "30")
        monkeypatch.setenv("CG_RETENTION_LOG_RETENTION_CEILING_DAYS", "45")
        retention = Settings().retention
        assert retention.log_hot_window_days == 3
        assert retention.log_retention_ceiling_days == 45


class TestStorageSettings:
    def test_defaults_are_todays_backends(self) -> None:
        storage = Settings().storage
        assert storage.event_log == "redis"
        assert storage.subscription == "redis"
        assert storage.graph == "neo4j"
        assert storage.keyword_index == "redis"
        assert storage.vector_index == "neo4j"

    def test_archive_falls_back_to_archive_backend(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CG_ARCHIVE_BACKEND", "gcs")
        assert Settings().storage.archive == "gcs"

    def test_storage_archive_overrides(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CG_ARCHIVE_BACKEND", "gcs")
        monkeypatch.setenv("CG_STORAGE_ARCHIVE", "fs")
        assert Settings().storage.archive == "fs"


class TestOpenStores:
    @pytest.mark.asyncio()
    async def test_unknown_backend_rejected_before_connecting(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CG_STORAGE_GRAPH", "spanner")
        with (
            patch("redis.asyncio.Redis") as redis_cls,
            pytest.raises(UnknownBackendError, match="CG_STORAGE_GRAPH"),
        ):
            await open_stores(Settings())
        redis_cls.assert_not_called()

    @pytest.mark.asyncio()
    async def test_subscription_must_match_event_log(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "context_graph.adapters.registry.SUBSCRIPTION_BACKENDS", ("redis", "other")
        )
        monkeypatch.setenv("CG_STORAGE_SUBSCRIPTION", "other")
        with pytest.raises(UnknownBackendError, match="cannot read"):
            await open_stores(Settings())

    @pytest.mark.asyncio()
    async def test_worker_stores_share_one_redis_client(self) -> None:
        redis_client = AsyncMock()
        graph = AsyncMock()
        with (
            patch("redis.asyncio.Redis", return_value=redis_client),
            patch("context_graph.adapters.neo4j.store.Neo4jGraphStore", return_value=graph),
        ):
            settings = Settings()
            stores = await open_stores(settings)

        graph.ensure_constraints.assert_awaited_once()
        assert stores.archive is None
        assert stores.backends["event_log"] == "redis"
        assert stores.event_log.client is redis_client

        subscription = stores.subscription("graph-projection", "projection-1")
        assert isinstance(subscription, RedisStreamSubscription)
        assert subscription.source_name == settings.consumer.source
        assert subscription.dlq_stream_key == f"{settings.consumer.source}:dlq"

        await stores.close()
        redis_client.aclose.assert_awaited_once()
        graph.close.assert_awaited_once()

    @pytest.mark.asyncio()
    async def test_graph_takes_only_its_own_settings(self) -> None:
        with (
            patch("redis.asyncio.Redis", return_value=AsyncMock()),
            patch(
                "context_graph.adapters.neo4j.store.Neo4jGraphStore", return_value=AsyncMock()
            ) as graph_cls,
        ):
            settings = Settings()
            stores = await open_stores(settings)

        assert graph_cls.call_args.args == (settings.neo4j,)
        assert graph_cls.call_args.kwargs == {"query_settings": settings.query}
        assert stores.graph_reads is graph_cls.return_value.reads
        assert stores.backends["keyword_index"] == "redis"
        assert stores.backends["vector_index"] == "neo4j"

    @pytest.mark.asyncio()
    async def test_archive_opened_on_request(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        monkeypatch.setenv("CG_ARCHIVE_FS_BASE_PATH", str(tmp_path))
        with (
            patch("redis.asyncio.Redis", return_value=AsyncMock()),
            patch("context_graph.adapters.neo4j.store.Neo4jGraphStore", return_value=AsyncMock()),
        ):
            stores = await open_stores(Settings(), with_archive=True)

        from context_graph.adapters.fs.archive import FilesystemArchiveStore

        assert isinstance(stores.archive, FilesystemArchiveStore)


class TestWorkerSubscriptions:
    def test_groups_and_consumer_names_unchanged(self) -> None:
        from context_graph.worker.__main__ import CONSUMER_SUBSCRIPTIONS, VALID_CONSUMERS

        settings = Settings()
        resolved = {
            consumer_type: (getattr(settings.consumer, group_field), consumer_name)
            for consumer_type, (group_field, consumer_name) in CONSUMER_SUBSCRIPTIONS.items()
        }
        assert set(resolved) == set(VALID_CONSUMERS)
        assert resolved == {
            "projection": ("graph-projection", "projection-1"),
            "enrichment": ("enrichment", "enrichment-1"),
            "extraction": ("session-extraction", "extraction-1"),
            "consolidation": ("consolidation", "consolidation-1"),
        }

    @pytest.mark.asyncio()
    async def test_unknown_consumer_rejected(self) -> None:
        from context_graph.worker.__main__ import _build_consumer

        with pytest.raises(ValueError, match="Unknown consumer type"):
            await _build_consumer("nope", MagicMock())
