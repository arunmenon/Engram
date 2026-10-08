"""Pinned store construction refuses owner/schema/config mismatches."""

import asyncio
import threading
from unittest.mock import patch

import pytest

from context_graph.adapters.registry import open_stores
from context_graph.adapters.spanner.tenant_control import TenantFence, TenantFenceError
from context_graph.tenancy import TenantConfigurationError
from tests.unit.test_tenant_catalog import bind, configuration


class Snapshot:
    def __init__(self, database):
        self.database = database

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute_sql(self, sql):
        if "INFORMATION_SCHEMA.COLUMNS" in sql:
            return self.database.columns
        if "INFORMATION_SCHEMA.INDEX_COLUMNS" in sql:
            return self.database.key
        raise AssertionError("Unexpected application read during construction")

    def read(self, table, columns, keys):
        assert table == "TenantControl"
        return [self.database.row]


class Database:
    def __init__(self, binding):
        self.name = binding.database_resource
        self.row = [
            binding.tenant_id,
            binding.database_resource,
            binding.binding_id,
            binding.epoch,
            binding.bundle_digest,
            "active",
        ]
        self.columns = [
            ("control_id", "STRING(16)", "NO"),
            ("tenant_id", "STRING(128)", "NO"),
            ("database_resource", "STRING(MAX)", "NO"),
            ("binding_id", "STRING(128)", "NO"),
            ("epoch", "INT64", "NO"),
            ("bundle_digest", "STRING(80)", "NO"),
            ("serving_state", "STRING(16)", "NO"),
        ]
        self.key = [("control_id", "ASC")]

    def snapshot(self, **kwargs):
        return Snapshot(self)

    def run_in_transaction(self, callback):
        return callback(Snapshot(self))


@pytest.mark.asyncio
async def test_caller_mutation_during_opener_cannot_switch_bound_stores():
    binding = bind()
    settings = binding.settings()
    database = Database(binding)
    opening = threading.Event()
    release = threading.Event()

    def opener(private_settings):
        opening.set()
        assert release.wait(timeout=2)
        assert private_settings.database == binding.settings().spanner.database
        return database

    with (
        patch("context_graph.adapters.spanner.schema.open_database", side_effect=opener),
        patch("context_graph.adapters.spanner.lifecycle.close_database"),
    ):
        task = asyncio.create_task(open_stores(settings, tenant_binding=binding))
        try:
            assert await asyncio.to_thread(opening.wait, 1)
            for port in ("event_log", "subscription", "graph", "keyword_index", "vector_index"):
                setattr(settings.storage, port, "memory")
            settings.spanner.database = "caller-mutated"
        finally:
            release.set()
        stores = await task
        try:
            assert all(
                value == "spanner" for name, value in stores.backends.items() if name != "archive"
            )
            assert stores.event_log._database is database
            assert stores.graph._database is database
            assert stores.subscription("group", "worker")._database is database
        finally:
            await stores.close()


@pytest.mark.asyncio
async def test_all_store_mutations_share_exact_verified_fence():
    binding = bind()
    database = Database(binding)
    with (
        patch("context_graph.adapters.spanner.schema.open_database", return_value=database),
        patch("context_graph.adapters.spanner.lifecycle.close_database") as close,
    ):
        stores = await open_stores(binding.settings(), tenant_binding=binding)
        try:
            ledger = stores.event_log
            graph = stores.graph
            subscription = stores.subscription("group", "worker")
            assert ledger._tenant_fence is graph._tenant_fence is subscription._tenant_fence
            assert ledger._tenant_fence == TenantFence.from_binding(binding)
            database.row[3] += 1
            with pytest.raises(TenantFenceError):
                await subscription.ensure_group()
        finally:
            await stores.close()
        close.assert_called_once_with(database)


@pytest.mark.asyncio
@pytest.mark.parametrize("mismatch", ["database", "policy", "bundle"])
async def test_configuration_mismatch_opens_zero_databases(mismatch):
    binding = bind()
    settings = binding.settings()
    kwargs = {}
    if mismatch == "database":
        settings.spanner.database = "other"
    elif mismatch == "policy":
        settings.query.default_neighbor_limit += 1
    else:
        kwargs["bundle"] = bind(settings=configuration("other")).bundle
    with patch("context_graph.adapters.spanner.schema.open_database") as opener:
        with pytest.raises(TenantConfigurationError):
            await open_stores(settings, tenant_binding=binding, **kwargs)
        opener.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mismatch",
    [
        "owner",
        "epoch",
        "digest",
        "frozen",
        "wrong_handle",
        "missing_schema",
        "nullable",
        "wrong_type",
        "wrong_key",
        "extra_column",
    ],
)
async def test_failed_handshake_closes_database_without_constructing_stores(mismatch):
    binding = bind()
    database = Database(binding)
    if mismatch == "owner":
        database.row[0] = "other"
    elif mismatch == "epoch":
        database.row[3] += 1
    elif mismatch == "digest":
        database.row[4] = "sha256:" + "b" * 64
    elif mismatch == "frozen":
        database.row[5] = "frozen"
    elif mismatch == "wrong_handle":
        database.name += "-other"
    elif mismatch == "missing_schema":
        database.columns = []
    elif mismatch == "nullable":
        database.columns[4] = ("epoch", "INT64", "YES")
    elif mismatch == "wrong_type":
        database.columns[4] = ("epoch", "STRING(MAX)", "NO")
    elif mismatch == "wrong_key":
        database.key = [("tenant_id", "ASC")]
    else:
        database.columns.append(("unexpected", "BOOL", "NO"))
    with (
        patch("context_graph.adapters.spanner.schema.open_database", return_value=database),
        patch("context_graph.adapters.spanner.lifecycle.close_database") as close,
        patch("context_graph.adapters.spanner.log.SpannerEventLog") as ledger,
    ):
        with pytest.raises(TenantFenceError):
            await open_stores(binding.settings(), tenant_binding=binding)
        ledger.assert_not_called()
        close.assert_called_once_with(database)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["read", "processing"])
async def test_worker_can_reopen_during_drain_but_external_api_cannot(mode):
    binding = bind()
    database = Database(binding)
    database.row[-1] = "draining"
    with (
        patch("context_graph.adapters.spanner.schema.open_database", return_value=database),
        patch("context_graph.adapters.spanner.lifecycle.close_database"),
    ):
        if mode == "read":
            with pytest.raises(TenantFenceError):
                await open_stores(
                    binding.settings(), tenant_binding=binding, tenant_read_operation=mode
                )
        else:
            stores = await open_stores(
                binding.settings(), tenant_binding=binding, tenant_read_operation=mode
            )
            try:
                assert stores.graph._tenant_read_operation == "processing"
                assert stores.event_log._tenant_read_operation == "processing"
                assert stores.subscription("group", "worker")._tenant_read_operation == "processing"
            finally:
                await stores.close()


@pytest.mark.asyncio
async def test_response_check_is_fresh_active_even_for_draining_worker_store():
    binding = bind()
    database = Database(binding)
    with (
        patch("context_graph.adapters.spanner.schema.open_database", return_value=database),
        patch("context_graph.adapters.spanner.lifecycle.close_database"),
    ):
        stores = await open_stores(
            binding.settings(), tenant_binding=binding, tenant_read_operation="processing"
        )
        try:
            await stores.tenant_read_check()
            database.row[-1] = "draining"
            with pytest.raises(TenantFenceError):
                await stores.tenant_read_check()
            database.row[-1] = "active"
            database.row[3] += 1
            with pytest.raises(TenantFenceError):
                await stores.tenant_read_check()
        finally:
            await stores.close()
