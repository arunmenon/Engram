"""Private tenant-bound factory startup proof; no requests or worker loops."""

from __future__ import annotations

from engram_experiment_support import runtime_settings as runtime_settings

import asyncio
from unittest.mock import patch

from engram_spanner_process_bootstrap import ScriptedProvider
from engram_spanner_tenant_control_cases import read_owner
from google.cloud import spanner
from google.oauth2.credentials import Credentials

from context_graph.adapters.spanner.graph import SpannerGraphStore
from context_graph.adapters.spanner.tenant_control import TenantFence
from context_graph.api.tenants import _create_bound_child
from context_graph.settings import Settings
from context_graph.tenancy import TenantBinding
from context_graph.worker.__main__ import _build_consumer


async def verify_runtime(database, values, run_id, evidence, checks, fingerprint, persist):
    settings = runtime_settings(values)
    owner = await asyncio.to_thread(read_owner, database)
    assert len(owner) == 1 and owner[0][-1] == "active"
    binding = TenantBinding.from_settings(
        "compat-control",
        "compat-control-binding",
        owner[0][3],
        settings,
        engine_revision="tenant-control-conformance-v1",
    )
    fence = TenantFence.from_binding(binding)
    assert owner[0][4] == fence.bundle_digest
    key = ("OntologyState", "OntologyState:active")
    graph = SpannerGraphStore(database, tenant_fence=fence)
    assert not await graph._get_nodes([key]), "Metadata already exists; refuse claiming ownership"
    evidence["runtime_intent"] = {
        "owner": owner,
        "metadata_key": list(key),
        "cleanup_only_new_metadata": True,
        "public_activation": False,
        "providers": "Scripted LLM; embedding constructor disabled; startup only",
        "worker_loops": False,
        "requests": False,
    }
    persist(evidence)
    original_client = spanner.Client
    credentials = Credentials(token=values["GOOGLE_OAUTH_ACCESS_TOKEN"])

    def authenticated_client(*args, **kwargs):
        kwargs["credentials"] = credentials
        return original_client(*args, **kwargs)

    def record(name):
        checks.append({"name": name, "passed": True, "scenarios": []})
        evidence["runtime_checks"] = [c["name"] for c in checks]
        persist(evidence)

    def check_stores(stores):
        assert stores.graph._tenant_fence == fence
        assert stores.event_log._tenant_fence == fence
        assert stores.subscription("runtime-conformance", "startup-only")._tenant_fence == fence
        assert stores.graph._database.name == binding.database_resource

    try:
        with (
            patch.object(spanner, "Client", authenticated_client),
            patch("context_graph.adapters.llm.client.LLMExtractionClient", ScriptedProvider),
            patch(
                "context_graph.adapters.embedding.service.SentenceTransformerEmbedder",
                lambda **kwargs: None,
            ),
        ):
            app = _create_bound_child(binding)
            async with app.router.lifespan_context(app):
                check_stores(app.state.stores)
                assert app.state.bundle is binding.bundle
                record("private_api_lifespan_exact_database_bundle_and_fence")
            record("private_api_lifespan_closed")
            for kind in (
                "projection",
                "extraction",
                "enrichment",
                "consolidation",
                "pack_extraction",
            ):
                consumer, stores = await _build_consumer(
                    kind, binding.settings(), tenant_binding=binding
                )
                try:
                    check_stores(stores)
                    record(kind + "_factory_exact_database_bundle_and_fence")
                    if kind == "projection":
                        metadata = (await graph._get_nodes([key]))[key]
                        assert metadata["version"] == binding.bundle.registry.version
                        assert metadata["packs"] == [
                            f"{p.name}@{p.version}" for p in binding.bundle.registry.packs
                        ]
                        assert metadata["applied"] == "initial"
                        evidence["projection_metadata"] = metadata
                        record("projection_metadata_exact_pinned_pack_version")
                finally:
                    await stores.close()
                record(kind + "_stores_closed")
    finally:
        assert await asyncio.to_thread(read_owner, database) == owner, (
            "Owner changed; refuse cleanup"
        )
        evidence["runtime_cleanup_intent"] = list(key)
        persist(evidence)
        await graph._delete_nodes([key])
        assert not await graph._get_nodes([key])
        evidence["runtime_cleanup_complete"] = True
        persist(evidence)


async def verify_responses(database, values, run_id, evidence, checks, fingerprint, persist):
    """Actual bound child + real control reads; test-only monotonic freeze/recovery."""
    import httpx
    from engram_spanner_tenant_control_cases import operator_transition

    from context_graph.tenancy import Principal

    settings = runtime_settings(values)
    owner = (await asyncio.to_thread(read_owner, database))[0]
    assert owner[-1] == "active"
    binding = TenantBinding.from_settings(
        "compat-control",
        "compat-control-binding",
        owner[3],
        settings,
        engine_revision="tenant-control-conformance-v1",
    )
    assert binding.bundle_digest == owner[4]
    original_owner = list(owner)
    evidence["response_intent"] = {
        "owner": owner,
        "public_activation": False,
        "requests": "Private authenticated-scope fixture routes; core-only; real control snapshots",
        "providers": "ScriptedLLM, disabled embedding constructor; no model inference",
        "control_changes": "test-only freeze then monotonic epoch recovery; no application writes",
    }
    persist(evidence)

    def record(name):
        checks.append({"name": name, "passed": True, "scenarios": []})
        evidence["response_checks"] = [c["name"] for c in checks]
        persist(evidence)

    async def transition(expected, state, advance=False):
        evidence["response_transition_intent"] = {
            "expected": expected,
            "state": state,
            "advance": advance,
        }
        persist(evidence)
        row = await asyncio.to_thread(
            operator_transition, database, expected, state=state, advance=advance
        )
        evidence["response_control_current"] = row
        persist(evidence)
        return row

    original_client = spanner.Client
    credentials = Credentials(token=values["GOOGLE_OAUTH_ACCESS_TOKEN"])

    def authenticated_client(*args, **kwargs):
        kwargs["credentials"] = credentials
        return original_client(*args, **kwargs)

    private_value = "private-response-" + run_id
    calls = []
    observations = []

    def child_for(selected):
        child = _create_bound_child(selected)

        @child.get("/v1/compat-response-probe")
        async def probe(mode: str = "cached"):
            calls.append(mode)
            if mode == "freeze":
                current = (await asyncio.to_thread(read_owner, database))[0]
                await transition(current, "frozen")
            return {} if mode == "empty" else {"private": private_value}

        async def authenticated(scope, receive, send):
            scope = dict(scope)
            scope["engram.principal"] = Principal(
                "compat-response", selected.tenant_id, frozenset({"api", "admin"})
            )
            current = []

            async def capture(message):
                current.append(
                    {
                        "type": message["type"],
                        "status": message.get("status"),
                        "contains_fixture": private_value.encode() in message.get("body", b""),
                    }
                )
                await send(message)

            try:
                await child(scope, receive, capture)
            finally:
                observations.append(current)

        return child, authenticated

    with (
        patch.object(spanner, "Client", authenticated_client),
        patch("context_graph.adapters.llm.client.LLMExtractionClient", ScriptedProvider),
        patch(
            "context_graph.adapters.embedding.service.SentenceTransformerEmbedder",
            lambda **kwargs: None,
        ),
    ):
        try:
            child, app = child_for(binding)
            async with child.router.lifespan_context(child), httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://compat"
            ) as client:
                response = await client.get("/v1/compat-response-probe")
                assert response.status_code == 200 and response.json() == {
                    "private": private_value
                }
                record("actual_bound_api_cached_response_authorized")
                response = await client.get("/v1/compat-response-probe?mode=empty")
                assert response.status_code == 200 and response.json() == {}
                record("actual_bound_api_empty_response_authorized")
                before = len(calls)
                response = await client.get("/v1/compat-response-probe?cursor=foreign")
                assert response.status_code == 400 and len(calls) == before
                response = await client.post("/v1/events/import", content=b"invalid fixture")
                assert response.status_code == 503 and len(calls) == before
                record("unfinished_cursor_and_import_paths_refused_before_effects")
                response = await client.get("/v1/compat-response-probe?mode=freeze")
                assert response.status_code == 503 and private_value not in response.text
                assert [
                    m["status"] for m in observations[-1] if m["type"] == "http.response.start"
                ] == [503]
                assert not any(m["contains_fixture"] for m in observations[-1])
                record("freeze_after_handler_discards_entire_response_before_success_start")
                before = len(calls)
                response = await client.get("/v1/compat-response-probe")
                assert response.status_code == 503 and len(calls) == before
                record("frozen_runtime_refused_before_handler")
        finally:
            current = (await asyncio.to_thread(read_owner, database))[0]
            assert current[:3] == original_owner[:3] and current[4] == original_owner[4]
            assert current[3] in (original_owner[3], original_owner[3] + 1)
            if current[-1] != "active":
                current = await transition(current, "active", advance=True)
            evidence["response_recovered_owner"] = current
            persist(evidence)
        renewed = TenantBinding.from_settings(
            "compat-control",
            "compat-control-binding",
            current[3],
            settings,
            engine_revision="tenant-control-conformance-v1",
        )
        child, app = child_for(renewed)
        async with child.router.lifespan_context(child), httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://compat"
        ) as client:
            response = await client.get("/v1/compat-response-probe")
            assert response.status_code == 200 and response.json() == {"private": private_value}
            record("renewed_epoch_bound_api_recovers_after_freeze")
        evidence["response_observations"] = observations
        evidence["response_handler_calls"] = calls
        persist(evidence)
        record("all_owned_child_lifespans_closed")
