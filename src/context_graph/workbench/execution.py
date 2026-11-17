"""Run-scoped storage ownership shared by authored packs and prepared stories."""

from __future__ import annotations

import asyncio
import hashlib
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from google.api_core.exceptions import GoogleAPICallError

from context_graph.adapters.registry import open_stores
from context_graph.settings import ConsumerSettings, Settings, StorageSettings
from context_graph.tenancy import Principal, TenantBinding
from context_graph.workbench.engine import engine_revision
from context_graph.workbench.spanner_pool import SlotOwnershipError, SlotUnavailableError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from context_graph.adapters.registry import Stores
    from context_graph.domain.models import Event
    from context_graph.domain.pack_bundle import ActiveBundle
    from context_graph.ports.event_log import EventLog
    from context_graph.workbench.spanner_pool import DedicatedSlot, Lease, SandboxPool


class SandboxCleanupError(RuntimeError):
    """No successful run is published when cleanup could not be verified."""


def sandbox_source_id(producer: str) -> str:
    """Separate sample agent aliases from authenticated sandbox identities.

    Map every alias, including already-valid ones, to avoid collisions between
    an encoded legacy alias and a literal sample producer. Original event
    envelopes remain intact. This is synthetic attribution, not external auth.
    """
    return "sample-" + hashlib.sha256(producer.encode("utf-8")).hexdigest()


@dataclass
class RunEnvironment:
    settings: Settings
    stores: Stores
    binding: TenantBinding | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def backend(self) -> str:
        return "spanner" if self.binding else "isolated-memory"

    @property
    def provenance_source(self) -> str:
        return "spanner" if self.binding else "memory"

    def writer(self, event: Event) -> EventLog:
        if self.binding is None:
            return self.stores.event_log
        from context_graph.adapters.spanner.log import SpannerEventLog

        if not isinstance(self.stores.event_log, SpannerEventLog):
            raise RuntimeError("Sandbox binding requires the Spanner ledger")
        principal = Principal(
            "sandbox-example",
            self.binding.tenant_id,
            frozenset({"api"}),
            sandbox_source_id(event.agent_id or "workbench.sample"),
        )
        # Source identity is supplied by the reviewed sample. This tests tenant
        # admission mechanics, not authentication of an external producer.
        return self.stores.event_log.admission_writer(self.binding.admission_context(principal))


async def _settle(task: asyncio.Task[Any]) -> tuple[Any, bool]:
    """Observe a synchronous SDK operation to completion even during cancellation."""
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
    return task.result(), cancelled


class SpannerExecution:
    def __init__(self, pool: SandboxPool, settings: Settings, *, owns_handles: bool = False):
        self.owns_handles = owns_handles
        self.pool = pool
        self.settings = settings.model_copy(deep=True)

    async def recover(self) -> None:
        """Only expired claims may be fenced and cleaned by the recovery sweep."""
        for slot in self.pool.slots:

            def recover_slot(slot: DedicatedSlot = slot) -> None:
                lease = slot.recover_expired()
                if lease is not None:
                    slot.cleanup(lease)

            try:
                _, cancelled = await _settle(asyncio.create_task(asyncio.to_thread(recover_slot)))
                if cancelled:
                    raise asyncio.CancelledError
            except Exception:
                # Failure leaves the slot unavailable; a sibling can still serve.
                # Status reports no credentials or SDK exception text.
                continue

    async def close(self) -> None:
        if self.owns_handles:
            from context_graph.adapters.spanner.lifecycle import close_database

            errors = []
            for slot in self.pool.slots:
                try:
                    await asyncio.to_thread(close_database, slot.database)
                except Exception as exc:
                    errors.append(exc)
            if errors:
                raise ExceptionGroup("Sandbox handle cleanup failed", errors)

    def _claim(
        self, bundle: ActiveBundle, trusted_ids: list[str], run_id: str
    ) -> tuple[DedicatedSlot, Lease, TenantBinding]:
        revision = engine_revision()
        for slot in self.pool.slots:
            settings = self.settings.model_copy(deep=True)
            _, project, _, instance, _, database = slot.resource.split("/")
            settings.spanner.project = project
            settings.spanner.instance = instance
            settings.spanner.database = database
            settings.spanner.create_if_missing = False
            settings.spanner.allow_create_on_instance = False
            settings.spanner.check_schema = True
            settings.spanner.emulator_host = None
            settings.archive.enabled = False
            settings.storage = StorageSettings(
                event_log="spanner",
                subscription="spanner",
                graph="spanner",
                keyword_index="spanner",
                vector_index="spanner",
                archive="",
            )
            settings.consumer = ConsumerSettings(projection_batch_size=1, block_timeout_ms=50)
            settings.ontology.trusted_source_ids = sorted(
                {sandbox_source_id(producer) for producer in trusted_ids}
            )
            settings.ontology.trusted_sources = []
            candidate = TenantBinding(
                "wb-" + slot.pool_id, run_id, 1, revision, settings.model_dump_json(), bundle
            )
            try:
                lease = slot.claim(
                    run_id=run_id, bundle_digest=candidate.bundle_digest, lease_seconds=600
                )
            except (SlotUnavailableError, SlotOwnershipError, GoogleAPICallError):
                # An unavailable/unowned sibling cannot prevent a healthy slot
                # from serving. No claim is returned from the failed transaction.
                continue
            binding = TenantBinding(
                candidate.tenant_id,
                run_id,
                lease.fence.epoch,
                revision,
                settings.model_dump_json(),
                bundle,
            )
            if binding.bundle_digest != lease.fence.bundle_digest:
                slot.quarantine(lease, "run_interrupted")
                raise RuntimeError("Sandbox binding changed during allocation")
            return slot, lease, binding
        raise SlotUnavailableError("All sandbox slots are in use or require cleanup")

    @asynccontextmanager
    async def open(
        self,
        bundle: ActiveBundle,
        trusted_ids: list[str],
        progress: Callable[[dict[str, Any]], None] | None = None,
    ) -> AsyncIterator[RunEnvironment]:
        run_id = "wb-" + str(uuid4())
        evidence: dict[str, Any] = {"backend": "spanner", "run_id": run_id, "phase": "allocating"}

        def report(phase: str) -> None:
            evidence["phase"] = phase
            if progress:
                try:
                    progress(dict(evidence))
                except Exception:
                    # Losing an observer or a draft revision must not skip
                    # revocation/cleanup of a claim already committed in Spanner.
                    evidence["progress_reporting"] = "unavailable"

        report("allocating")
        pending = asyncio.create_task(asyncio.to_thread(self._claim, bundle, trusted_ids, run_id))
        claimed = None
        stores = None
        cancelled = False
        try:
            claimed, cancelled = await _settle(pending)
            slot, lease, binding = claimed
            evidence.update(
                resource=slot.resource,
                epoch=lease.fence.epoch,
                pool_id=slot.pool_id,
                source_identity_mode="synthetic-producer-sha256",
            )
            if cancelled:
                raise asyncio.CancelledError
            report("opening")
            # Settle startup too: cancelling to_thread cannot stop the underlying
            # SDK operation and must not leave a late-opened handle unclosed.
            opening = asyncio.create_task(
                open_stores(
                    binding.settings(), prepare_ingest=True, bundle=bundle, tenant_binding=binding
                )
            )
            stores, opening_cancelled = await _settle(opening)
            cancelled = cancelled or opening_cancelled
            if cancelled:
                raise asyncio.CancelledError
            report("running")
            yield RunEnvironment(binding.settings(), stores, binding, evidence)
        finally:
            if claimed is not None:
                slot, lease, _binding = claimed
                close_error = None
                if stores is not None:
                    try:
                        _, close_cancelled = await _settle(asyncio.create_task(stores.close()))
                        cancelled = cancelled or close_cancelled
                    except Exception as exc:
                        close_error = exc
                report("cleaning")
                try:
                    _, cleanup_cancelled = await _settle(
                        asyncio.create_task(asyncio.to_thread(slot.cleanup, lease))
                    )
                    cancelled = cancelled or cleanup_cancelled
                except Exception as exc:
                    evidence["cleanup"] = "quarantined_or_unavailable"
                    report("cleanup_failed")
                    raise SandboxCleanupError(
                        "Sandbox cleanup could not be verified; slot cannot be reused"
                    ) from exc
                evidence["cleanup"] = "verified"
                report("released")
                if close_error:
                    raise SandboxCleanupError(
                        "Sandbox data was cleaned, but closing a storage handle failed"
                    ) from close_error
                if cancelled:
                    raise asyncio.CancelledError


@asynccontextmanager
async def open_environment(
    bundle: ActiveBundle,
    trusted_ids: list[str],
    execution: SpannerExecution | None = None,
    progress: Callable[[dict[str, Any]], None] | None = None,
) -> AsyncIterator[RunEnvironment]:
    if execution is not None:
        async with execution.open(bundle, trusted_ids, progress) as runtime:
            yield runtime
        return
    settings = Settings(
        storage=StorageSettings(
            event_log="memory",
            subscription="memory",
            graph="memory",
            keyword_index="memory",
            vector_index="memory",
            archive="",
        ),
        consumer=ConsumerSettings(projection_batch_size=1, block_timeout_ms=10),
    )
    stores = await open_stores(settings, prepare_ingest=True, bundle=bundle)
    try:
        yield RunEnvironment(settings, stores, evidence={"backend": "isolated-memory"})
    finally:
        await stores.close()
