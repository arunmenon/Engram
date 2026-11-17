"""Factory boundaries only; these do not prove production tenant isolation."""

from __future__ import annotations

from contextlib import AsyncExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from context_graph.api.app import create_app, lifespan
from context_graph.api.middleware import RateLimitMiddleware
from context_graph.settings import Settings


def configuration(key, database):
    settings = Settings()
    for port in ("event_log", "subscription", "graph", "keyword_index", "vector_index"):
        setattr(settings.storage, port, "memory")
    settings.archive.enabled = False
    settings.intent.use_llm = False
    settings.auth.api_key = key
    settings.auth.admin_key = key + "-admin"
    settings.spanner.database = database
    settings.ontology.packs = []
    settings.ontology.builtin_packs = []
    return settings


@pytest.mark.asyncio
async def test_two_explicit_apps_keep_settings_auth_and_stores_separate(monkeypatch):
    import context_graph.adapters.llm.client as llm

    monkeypatch.setattr(llm, "LLMExtractionClient", lambda **kwargs: object())
    first = configuration("key-a", "database-a")
    second = configuration("key-b", "database-b")
    apps = [create_app(first), create_app(second)]
    first.auth.api_key = "caller-mutated-key"
    second.spanner.database = "caller-mutated-db"
    monkeypatch.setenv("CG_STORAGE_GRAPH", "invalid-ambient-backend")
    monkeypatch.setenv("CG_SPANNER_DATABASE", "ambient-database")
    monkeypatch.setenv("CG_AUTH_API_KEY", "ambient-key")
    event_id = str(uuid4())
    async with AsyncExitStack() as stack:
        for index, app in enumerate(apps):
            await stack.enter_async_context(lifespan(app))
            client = await stack.enter_async_context(
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url="http://test",
                )
            )
            key = ("key-a", "key-b")[index]
            other = ("key-b", "key-a")[index]
            body = {
                "event_id": event_id,
                "event_type": "observation.input",
                "occurred_at": "2026-10-07T00:00:00Z",
                "session_id": "same-session",
                "agent_id": "same-agent",
                "trace_id": "same-trace",
                "payload_ref": "fixture:shared-id",
                "payload": {"content": key},
            }
            refused = await client.post(
                "/v1/events", json=body, headers={"Authorization": "Bearer " + other}
            )
            assert refused.status_code == 401
            assert await app.state.stores.event_log.get_documents([event_id]) == [None]
            accepted = await client.post(
                "/v1/events", json=body, headers={"Authorization": "Bearer " + key}
            )
            assert accepted.status_code == 201, accepted.text
            middleware = next(
                item for item in app.user_middleware if item.cls is RateLimitMiddleware
            )
            assert middleware.kwargs["settings"] is app.state.settings
            assert app.state.settings.spanner.database == ("database-a", "database-b")[index]
            assert {name for name, _version in app.state.bundle.pack_identities} == {"core"}
        for index, app in enumerate(apps):
            document = (await app.state.stores.event_log.get_documents([event_id]))[0]
            assert document["payload"] == {"content": ("key-a", "key-b")[index]}
        assert apps[0].state.stores is not apps[1].state.stores
        assert apps[0].state.retrieval is not apps[1].state.retrieval


@pytest.mark.asyncio
async def test_worker_explicit_snapshot_reaches_constructor_and_closes(monkeypatch):
    import asyncio

    import context_graph.worker.__main__ as entry

    settings = configuration("key-a", "database-a")
    captured = []
    consumer = SimpleNamespace(run=AsyncMock(), stop=lambda: None)
    stores = SimpleNamespace(close=AsyncMock())

    async def build(kind, selected):
        captured.append((kind, selected))
        settings.spanner.database = "caller-mutated-db"
        return consumer, stores

    monkeypatch.setattr(entry, "_build_consumer", build)
    monkeypatch.setattr(asyncio.get_running_loop(), "add_signal_handler", lambda *args: None)
    monkeypatch.setenv("CG_SPANNER_DATABASE", "ambient-database")
    await entry.run_worker("projection", settings=settings)
    assert captured[0][0] == "projection"
    assert captured[0][1] is not settings
    assert captured[0][1].spanner.database == "database-a"
    consumer.run.assert_awaited_once()
    stores.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_pinned_bundle_survives_manifest_removal_in_api_and_worker(tmp_path, monkeypatch):
    import context_graph.adapters.llm.client as llm
    import context_graph.worker.__main__ as entry
    from context_graph.domain.pack_bundle import resolve_bundle
    from context_graph.ontology.loader import load_registry

    monkeypatch.setattr(llm, "LLMExtractionClient", lambda **kwargs: object())
    path = tmp_path / "lab.pack.yaml"
    path.write_text("pack:\n  name: lab\n  version: 1.0.0\n  description: pinned\n")
    settings = configuration("key-a", "database-a")
    settings.ontology.packs = ["lab"]
    settings.ontology.pack_dirs = [str(tmp_path)]
    bundle = resolve_bundle(load_registry(["lab"], [tmp_path], builtin_packs=[]))
    app = create_app(settings, bundle=bundle)
    path.unlink()
    async with lifespan(app):
        assert app.state.bundle is bundle
        assert app.state.ontology.pack("lab").pack.description == "pinned"
        assert app.state.stores.pack_reads is not None
        assert app.state.retrieval._bundle is bundle
    for kind in entry.VALID_CONSUMERS:
        consumer, stores = await entry._build_consumer(kind, settings, bundle=bundle)
        try:
            if kind == "projection":
                assert consumer._pack_projector.registry.pack("lab").pack.description == "pinned"
            if kind == "extraction":
                assert consumer._user_store is None
        finally:
            await stores.close()


@pytest.mark.asyncio
async def test_api_closes_acquired_stores_when_initialization_fails(monkeypatch):
    import context_graph.adapters.llm.client as llm
    import context_graph.api.app as module

    monkeypatch.setattr(llm, "LLMExtractionClient", lambda **kwargs: object())
    real_open = module.open_stores
    captured = []

    async def fail_schema(settings, **kwargs):
        stores = await real_open(settings, **kwargs)
        stores.close = AsyncMock(wraps=stores.close)
        monkeypatch.setattr(
            stores.graph,
            "ensure_pack_schema",
            AsyncMock(side_effect=RuntimeError("controlled schema failure")),
        )
        captured.append(stores)
        return stores

    monkeypatch.setattr(module, "open_stores", fail_schema)
    app = create_app(configuration("key-a", "database-a"))
    with pytest.raises(RuntimeError, match="controlled schema failure"):
        async with lifespan(app):
            pytest.fail("invalid initialization served")
    captured[0].close.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kind,module_name,class_name",
    [
        ("projection", "projection", "ProjectionConsumer"),
        ("enrichment", "enrichment", "EnrichmentConsumer"),
        ("extraction", "extraction", "ExtractionConsumer"),
        ("consolidation", "consolidation", "ConsolidationConsumer"),
        ("pack_extraction", "pack_extraction", "PackExtractionConsumer"),
    ],
)
async def test_worker_closes_stores_after_constructor_failure(
    monkeypatch, kind, module_name, class_name
):
    import importlib

    import context_graph.adapters.llm.client as llm
    import context_graph.worker.__main__ as entry

    monkeypatch.setattr(llm, "LLMExtractionClient", lambda **kwargs: object())
    captured = []
    real_open = entry.open_stores

    async def recording_open(settings, **kwargs):
        stores = await real_open(settings, **kwargs)
        stores.close = AsyncMock(wraps=stores.close)
        captured.append(stores)
        return stores

    def fail_constructor(*args, **kwargs):
        raise RuntimeError("controlled consumer constructor failure")

    monkeypatch.setattr(entry, "open_stores", recording_open)
    monkeypatch.setattr(
        importlib.import_module("context_graph.worker." + module_name), class_name, fail_constructor
    )
    with pytest.raises(RuntimeError, match="controlled consumer constructor failure"):
        await entry._build_consumer(kind, configuration("key-a", "database-a"))
    assert len(captured) == 1
    captured[0].close.assert_awaited_once()


@pytest.mark.asyncio
async def test_extraction_model_and_write_gate_use_same_pinned_user_capability(
    tmp_path, monkeypatch
):
    import context_graph.adapters.llm.client as llm
    import context_graph.worker.__main__ as entry
    from context_graph.domain.pack_bundle import resolve_bundle
    from context_graph.ontology.loader import load_registry

    model_settings = []

    def model(**kwargs):
        model_settings.append(kwargs)
        return object()

    monkeypatch.setattr(llm, "LLMExtractionClient", model)
    path = tmp_path / "lab.pack.yaml"
    path.write_text("pack:\n  name: lab\n  version: 1.0.0\n")
    settings = configuration("key-a", "database-a")
    settings.ontology.packs = ["lab"]
    settings.ontology.builtin_packs = ["user"]
    settings.ontology.pack_dirs = [str(tmp_path)]
    bundle = resolve_bundle(load_registry(["lab"], [tmp_path], builtin_packs=["user"]))
    path.unlink()
    consumer, stores = await entry._build_consumer("extraction", settings, bundle=bundle)
    try:
        assert model_settings[0]["include_user"] is True
        assert consumer._user_store is stores.graph
    finally:
        await stores.close()
