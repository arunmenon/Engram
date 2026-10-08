"""Tenant bindings reach every composition root; reference ports, no cloud."""

import asyncio
import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from context_graph.adapters.registry import open_stores as reference_open
from context_graph.api.tenants import (
    TenantServiceNotReadyError,
    _create_bound_child,
    create_tenant_app,
)
from context_graph.ports.errors import RuntimeFencedError
from context_graph.settings import Settings
from context_graph.tenancy import TenantConfigurationError
from tests.unit.test_tenant_catalog import bind


def memory_settings():
    settings = Settings()
    for port in ("event_log", "subscription", "graph", "keyword_index", "vector_index"):
        setattr(settings.storage, port, "memory")
    settings.archive.enabled = False
    settings.ontology.packs = []
    settings.ontology.builtin_packs = []
    return settings


def providers(monkeypatch):
    import context_graph.adapters.llm.client as llm

    monkeypatch.setattr(llm, "LLMExtractionClient", MagicMock())
    import context_graph.adapters.embedding.service as embedding

    monkeypatch.setattr(embedding, "SentenceTransformerEmbedder", lambda **kwargs: None)


@pytest.mark.asyncio
async def test_private_bound_api_child_passes_exact_binding_to_stores(monkeypatch):
    module = importlib.import_module("context_graph.api.app")
    providers(monkeypatch)
    binding = bind()
    captured = []

    async def recording_open(settings, **kwargs):
        captured.append((settings, kwargs))
        return await reference_open(memory_settings(), bundle=kwargs["bundle"])

    monkeypatch.setattr(module, "open_stores", recording_open)
    child = _create_bound_child(binding)
    monkeypatch.setenv("CG_STORAGE_GRAPH", "invalid-ambient")
    async with module.lifespan(child):
        assert child.state.bundle is binding.bundle
        assert child.state.tenant_binding is binding
        assert child.state.settings.model_dump() == binding.settings().model_dump()
    assert captured[0][1]["tenant_binding"] is binding
    assert captured[0][1]["bundle"] is binding.bundle
    assert captured[0][1]["prepare_ingest"] is True
    assert captured[0][1].get("tenant_read_operation", "read") == "read"
    with pytest.raises(TenantServiceNotReadyError):
        create_tenant_app(None)  # Public production path remains unavailable.


@pytest.mark.asyncio
async def test_bound_api_rejects_mutated_configuration_before_open_or_provider(monkeypatch):
    module = importlib.import_module("context_graph.api.app")
    child = _create_bound_child(bind())
    child.state.configured_settings.spanner.database = "other"
    opener = AsyncMock()
    monkeypatch.setattr(module, "open_stores", opener)
    with pytest.raises(TenantConfigurationError):
        async with module.lifespan(child):
            pytest.fail("Mismatched child served")
    opener.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kind", ["projection", "extraction", "enrichment", "consolidation", "pack_extraction"]
)
async def test_every_worker_forwards_same_pinned_binding(kind, monkeypatch):
    entry = importlib.import_module("context_graph.worker.__main__")
    providers(monkeypatch)
    monkeypatch.setattr(entry, "_open_embedding_service", lambda *args: None)
    binding = bind()
    captured = []

    async def recording_open(settings, **kwargs):
        captured.append((settings, kwargs))
        stores = await reference_open(memory_settings(), bundle=kwargs["bundle"])
        # Factory forwarding probe only: no fabricated accepted records may be read.
        stores.event_log.get_accepted_records = AsyncMock(
            side_effect=AssertionError("factory probe only")
        )
        return stores

    monkeypatch.setattr(entry, "open_stores", recording_open)
    monkeypatch.setenv("CG_SPANNER_DATABASE", "ambient-database")
    consumer, stores = await entry._build_consumer(kind, binding.settings(), tenant_binding=binding)
    try:
        assert captured[0][1]["tenant_binding"] is binding
        assert captured[0][1]["bundle"] is binding.bundle
        assert captured[0][0].model_dump() == binding.settings().model_dump()
        assert captured[0][1]["tenant_read_operation"] == "processing"
        assert consumer._group_name == getattr(binding.settings().consumer, "group_" + kind)
        if kind in ("extraction", "consolidation"):
            assert consumer._settings.spanner.database == binding.settings().spanner.database
    finally:
        await stores.close()


@pytest.mark.asyncio
async def test_bound_worker_runner_uses_no_ambient_settings_and_closes_on_fence(monkeypatch):
    entry = importlib.import_module("context_graph.worker.__main__")
    binding = bind()
    consumer = SimpleNamespace(
        run=AsyncMock(side_effect=RuntimeFencedError("changed")), stop=lambda: None
    )
    stores = SimpleNamespace(close=AsyncMock())
    captured = []

    async def build(kind, settings, **kwargs):
        captured.append((settings, kwargs))
        return consumer, stores

    monkeypatch.setattr(entry, "_build_consumer", build)
    monkeypatch.setattr(
        entry, "Settings", MagicMock(side_effect=AssertionError("Ambient settings"))
    )
    monkeypatch.setattr(asyncio.get_running_loop(), "add_signal_handler", lambda *args: None)
    with pytest.raises(RuntimeFencedError):
        await entry.run_worker("projection", tenant_binding=binding)
    assert captured[0][1]["tenant_binding"] is binding
    assert captured[0][1]["bundle"] is binding.bundle
    stores.close.assert_awaited_once()
