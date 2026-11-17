"""Run lifetime tests with controlled SDK boundaries; no live Spanner claims."""

import asyncio
import json
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from context_graph.adapters.spanner.tenant_control import TenantFence
from context_graph.settings import Settings
from context_graph.workbench.engine import composed
from context_graph.workbench.execution import (
    RunEnvironment,
    SandboxCleanupError,
    SpannerExecution,
    sandbox_source_id,
)
from context_graph.workbench.models import Content
from context_graph.workbench.spanner_pool import Lease, SandboxPool


class Slot:
    resource = "projects/test-project/instances/test-instance/databases/dedicated-sandbox"
    pool_id = "test-pool"

    def __init__(self):
        self.claimed = threading.Event()
        self.allow_claim = threading.Event()
        self.allow_claim.set()
        self.cleaned = False
        self.cleanup_failed = False

    def claim(self, *, run_id, bundle_digest, lease_seconds):
        self.claimed.set()
        assert self.allow_claim.wait(3), "test did not release claim"
        return Lease(
            self.pool_id, TenantFence("wb-" + self.pool_id, self.resource, run_id, 2, bundle_digest)
        )

    def cleanup(self, lease):
        if self.cleanup_failed:
            raise RuntimeError("injected cleanup failure")
        self.cleaned = True


@pytest.fixture
def bundle():
    fixture = json.loads(
        (Path(__file__).parents[1] / "fixtures/workbench/incident.json").read_text()
    )
    with composed(Content.model_validate(fixture["content"]), fixture["proposal"]["pack"]) as (
        _,
        bundle,
        _,
    ):
        yield bundle


def runner(slot):
    return SpannerExecution(SandboxPool((slot,)), Settings())


@pytest.mark.asyncio
async def test_bound_startup_and_cleanup_survive_lost_progress_observer(bundle, monkeypatch):
    slot = Slot()
    closed = []

    async def close():
        closed.append(True)

    async def open_stores(settings, *, prepare_ingest, bundle, tenant_binding):
        assert prepare_ingest and settings.spanner.database == "dedicated-sandbox"
        assert tenant_binding.epoch == 2
        assert tenant_binding.settings().ontology.trusted_source_ids == [
            sandbox_source_id("pagerduty")
        ]
        assert settings.storage.graph == settings.storage.event_log == "spanner"
        assert not settings.spanner.create_if_missing and not settings.archive.enabled
        return SimpleNamespace(close=close)

    monkeypatch.setattr("context_graph.workbench.execution.open_stores", open_stores)

    def broken_observer(_):
        raise RuntimeError("observer disconnected")

    async with runner(slot).open(bundle, ["pagerduty"], broken_observer) as runtime:
        assert runtime.backend == runtime.provenance_source == "spanner"
        assert not slot.cleaned
    assert closed and slot.cleaned
    assert runtime.evidence["cleanup"] == "verified"
    assert runtime.evidence["progress_reporting"] == "unavailable"


def test_legacy_sample_aliases_use_distinct_bound_sources_without_rewriting_events(
    bundle, monkeypatch
):
    from context_graph.domain.models import Event

    aliases = ["webhook:github", "webhook:jira"]
    slot = Slot()
    _, _, binding = runner(slot)._claim(bundle, aliases, "sample-run")
    trusted = binding.settings().ontology.trusted_source_ids
    assert len(trusted) == 2 and all(":" not in source for source in trusted)
    contexts = []

    class Ledger:
        def admission_writer(self, context):
            contexts.append(context)
            return self

    monkeypatch.setattr("context_graph.adapters.spanner.log.SpannerEventLog", Ledger)
    ledger = Ledger()
    runtime = RunEnvironment(binding.settings(), SimpleNamespace(event_log=ledger), binding)
    # A caller spelling the encoded trusted ID must not inherit its trust.
    for alias in [*aliases, trusted[0], "untrusted"]:
        event = Event.model_validate(
            {
                "event_id": "00000000-0000-4000-8000-000000000001",
                "occurred_at": "2026-11-03T00:00:00Z",
                "payload_ref": "synthetic",
                "event_type": "agent.observation",
                "agent_id": alias,
                "session_id": "synthetic",
                "trace_id": "synthetic",
                "payload": {},
            },
            strict=False,
        )
        before = event.model_dump()
        runtime.writer(event)
        assert event.model_dump() == before
    sources = [context.source_id for context in contexts]
    assert set(sources[:2]) == set(trusted)
    assert not set(sources[2:]) & set(trusted)
    assert len(set(sources)) == 4


@pytest.mark.asyncio
async def test_cancel_during_claim_waits_for_committed_claim_then_cleans(bundle):
    slot = Slot()
    slot.allow_claim.clear()

    async def run():
        async with runner(slot).open(bundle, []) as _runtime:
            pytest.fail("cancelled run must not execute")

    task = asyncio.create_task(run())
    assert await asyncio.to_thread(slot.claimed.wait, 2)
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()
    slot.allow_claim.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert slot.cleaned


@pytest.mark.asyncio
async def test_failed_open_still_cleans_claim_and_failed_cleanup_cannot_pass(bundle, monkeypatch):
    slot = Slot()

    async def refuse(*args, **kwargs):
        raise RuntimeError("open refused")

    monkeypatch.setattr("context_graph.workbench.execution.open_stores", refuse)
    with pytest.raises(RuntimeError, match="open refused"):
        async with runner(slot).open(bundle, []):
            pytest.fail("must not execute")
    assert slot.cleaned
    slot.cleaned = False
    slot.cleanup_failed = True
    phases = []
    with pytest.raises(SandboxCleanupError, match="could not be verified"):
        async with runner(slot).open(bundle, [], lambda event: phases.append(event["phase"])):
            pytest.fail("must not execute")
    assert not slot.cleaned and phases[-1] == "cleanup_failed"


@pytest.mark.asyncio
async def test_recovery_cleans_only_expired_claims_and_continues_after_unavailable_slot():
    cleaned = []

    class RecoverSlot:
        pool_id = "pool"

        def __init__(self, resource, result):
            self.resource = resource
            self.result = result

        def recover_expired(self):
            if isinstance(self.result, Exception):
                raise self.result
            return self.result

        def cleanup(self, lease):
            cleaned.append((self.resource, lease))

    pool = SandboxPool(
        tuple(
            RecoverSlot(resource, result)
            for resource, result in (
                ("unreachable", RuntimeError("offline")),
                ("still-running", None),
                ("expired", "expired-lease"),
            )
        )
    )
    await SpannerExecution(pool, Settings()).recover()
    assert cleaned == [("expired", "expired-lease")]


@pytest.mark.asyncio
async def test_sandbox_reports_worker_exit_without_waiting_for_overall_timeout(monkeypatch):
    from context_graph.workbench.sandbox import run_sandbox

    async def exit_worker(_self):
        return

    monkeypatch.setattr("context_graph.workbench.sandbox.ProjectionConsumer.run", exit_worker)
    fixture = json.loads(
        (Path(__file__).parents[1] / "fixtures/workbench/incident.json").read_text()
    )
    async with asyncio.timeout(2):
        with pytest.raises(RuntimeError, match="worker stopped"):
            await run_sandbox(
                Content.model_validate(fixture["content"]), fixture["proposal"]["pack"]
            )


@pytest.mark.asyncio
async def test_cancel_during_open_waits_for_handle_then_closes_and_cleans(bundle, monkeypatch):
    slot = Slot()
    opening, release = asyncio.Event(), asyncio.Event()
    closed = []

    async def close():
        closed.append(True)

    async def open_stores(*args, **kwargs):
        opening.set()
        await release.wait()
        return SimpleNamespace(close=close)

    monkeypatch.setattr("context_graph.workbench.execution.open_stores", open_stores)

    async def run():
        async with runner(slot).open(bundle, []):
            pytest.fail("cancelled opening must not execute the scenario")

    task = asyncio.create_task(run())
    await asyncio.wait_for(opening.wait(), 2)
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done() and not slot.cleaned
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert closed == [True] and slot.cleaned


@pytest.mark.asyncio
async def test_repeated_cancel_cannot_release_before_cleanup_finishes(bundle, monkeypatch):
    slot = Slot()
    cleaning, release = threading.Event(), threading.Event()
    phases = []

    def cleanup(_lease):
        cleaning.set()
        assert release.wait(3), "test failed to release cleanup"
        slot.cleaned = True

    slot.cleanup = cleanup

    async def close():
        return

    async def open_stores(*args, **kwargs):
        return SimpleNamespace(close=close)

    monkeypatch.setattr("context_graph.workbench.execution.open_stores", open_stores)

    async def run():
        async with runner(slot).open(bundle, [], lambda item: phases.append(item["phase"])):
            pass

    task = asyncio.create_task(run())
    assert await asyncio.to_thread(cleaning.wait, 2)
    for _ in range(2):
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done() and not slot.cleaned
        assert phases[-1] == "cleaning"
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert slot.cleaned and phases[-1] == "released"


@pytest.mark.asyncio
async def test_shutdown_attempts_every_owned_handle_even_when_one_close_fails(monkeypatch):
    closed = []
    slots = tuple(
        SimpleNamespace(resource=name, pool_id="pool", database=name) for name in ("a", "b")
    )

    def close(database):
        closed.append(database)
        if database == "a":
            raise RuntimeError("injected close failure")

    monkeypatch.setattr("context_graph.adapters.spanner.lifecycle.close_database", close)
    execution = SpannerExecution(SandboxPool(slots), Settings(), owns_handles=True)
    with pytest.raises(ExceptionGroup, match="handle cleanup"):
        await execution.close()
    assert closed == ["a", "b"]


def test_claim_skips_unreachable_sibling_without_memory_fallback(bundle):
    from google.api_core.exceptions import ServiceUnavailable

    class OfflineSlot(Slot):
        resource = "projects/test-project/instances/test-instance/databases/offline-sandbox"

        def claim(self, **kwargs):
            raise ServiceUnavailable("injected transport failure")

    healthy = Slot()
    execution = SpannerExecution(SandboxPool((OfflineSlot(), healthy)), Settings())
    slot, lease, binding = execution._claim(bundle, ["pagerduty"], "run-healthy")
    assert slot is healthy
    assert binding.binding_id == lease.fence.binding_id == "run-healthy"
    assert binding.settings().storage.graph == "spanner"
