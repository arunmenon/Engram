"""Real Engram/Spanner trust handoffs; normalized synthetic PDLC + stubbed model.

Only the reserved empty target, pinned predecessor, bounded registered fixtures.
No source database writes, DDL, production activation or historical replay grant.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from engram_spanner_acceptance_cases import await_settled
from engram_spanner_empty_activation import (
    KEYS,
    RESOURCE,
    ActivationRefusedError,
    activate_empty_target,
    clean_registered_target,
    freeze_target,
)
from engram_spanner_tenant_control_cases import read_owner
from engram_spanner_tenant_runtime_cases import runtime_settings

from context_graph.adapters.spanner.graph import SpannerGraphStore
from context_graph.adapters.spanner.log import SpannerEventLog
from context_graph.adapters.spanner.subscription import SpannerSubscription
from context_graph.adapters.spanner.tenant_control import TenantFence
from context_graph.domain.models import Event
from context_graph.domain.pack_extraction import extraction_profiles
from context_graph.domain.pack_projection import PackProjector, make_node_id
from context_graph.domain.source_trust import SourceTrustPolicy
from context_graph.ports.errors import RuntimeFencedError
from context_graph.ports.pack_graph import NodeRef
from context_graph.tenancy import Principal, TenantBinding
from context_graph.worker.pack_extraction import PackExtractionConsumer
from context_graph.worker.projection import ProjectionConsumer

OLD = [
    "compat-control",
    RESOURCE,
    "compat-control-binding",
    6,
    "sha256:7c4c2c9cb07539c5841b80b5cb5adfcb9b14d23f350258eb29f1c00325134b6d",
    "active",
]
PRIOR = Path(
    "docs/review/spanner-compatibility/runs/20261007-cloud-writer-admission-01/schema-evidence.json"
)


def bind(settings, epoch):
    return TenantBinding.from_settings(
        "compat-control",
        "compat-control-binding",
        epoch,
        settings,
        engine_revision="tenant-control-conformance-v1",
    )


def active(binding):
    return [*TenantFence.from_binding(binding)._identity(), "active"]


async def verify_source_trust(database, values, run_id, evidence, checks, fingerprint, persist):
    try:
        return await await_settled(
            _verify(database, values, run_id, evidence, checks, fingerprint, persist)
        )
    except asyncio.CancelledError:
        checks.append(
            {
                "name": "source_trust_cancelled_after_cleanup",
                "passed": False,
                "scenarios": [],
            }
        )
        persist(evidence)
        raise


async def _verify(database, values, run_id, evidence, checks, fingerprint, persist):
    prior = json.loads(PRIOR.read_text())
    if prior.get("control_after") != [OLD] or any(
        row["count"] for row in prior["after_rows"].values()
    ):
        raise ActivationRefusedError("Retained predecessor evidence differs from reviewed plan")
    if await asyncio.to_thread(read_owner, database) != [OLD]:
        raise ActivationRefusedError("Current owner differs from pinned predecessor")
    before = await asyncio.to_thread(fingerprint, database)
    if any(row["count"] for row in before.values()):
        raise ActivationRefusedError("Experiment requires empty target")
    settings = runtime_settings(values)
    settings.ontology.packs = ["pdlc"]
    settings.ontology.trusted_source_ids = ["verified-producer"]
    settings.ontology.trusted_sources = ["forged-agent", "webhook:github"]
    settings.consumer.projection_batch_size = 1
    experimental = bind(settings, 7)
    core_settings = runtime_settings(values)
    restore = bind(core_settings, 8)
    recovery = bind(core_settings, 7)
    new_owner, restored_owner, recovery_owner = (
        active(experimental),
        active(restore),
        active(recovery),
    )
    frozen_old, frozen_new = [*OLD[:-1], "frozen"], [*new_owner[:-1], "frozen"]
    event_ids = [str(uuid5(NAMESPACE_URL, run_id + f"/event/{i}")) for i in range(4)]
    repo = "fixture/" + run_id
    statements = [f"Use verified producer evidence {run_id} {i}" for i in range(2)]
    change_ids = [make_node_id("Change", [repo, i + 1]) for i in range(2)]
    decision_ids = [
        make_node_id("Decision", [hashlib.sha256(s.encode()).hexdigest()]) for s in statements
    ]
    groups = [
        "source-trust-projection-" + uuid5(NAMESPACE_URL, run_id).hex,
        "source-trust-extraction-" + uuid5(NAMESPACE_URL, run_id).hex,
    ]
    allowed = {table: [] for table in KEYS}
    allowed["Events"] = [[eid] for eid in event_ids]
    allowed["GraphNodes"] = (
        [["Event", eid] for eid in event_ids]
        + [["Change", nid] for nid in change_ids]
        + [["Decision", nid] for nid in decision_ids]
    )
    allowed["GraphEdges"] = [
        [kind, nid, "DERIVED_FROM", "Event", eid]
        for kind, ids, events in (
            ("Change", change_ids, event_ids[:2]),
            ("Decision", decision_ids, event_ids[2:]),
        )
        for nid, eid in zip(ids, events, strict=True)
    ]
    allowed["ConsumerGroups"] = [[group] for group in groups]
    allowed["ConsumerCursors"] = [
        [group, shard] for group in groups for shard in range(settings.spanner.shards)
    ]
    allowed["ConsumerDeliveries"] = [[group, eid] for group in groups for eid in event_ids]
    allowed["ConsumerDeadLetters"] = [[group, eid] for group in groups for eid in event_ids]
    evidence["source_trust_intent"] = {
        "prior_evidence": str(PRIOR),
        "prior_sha256": hashlib.sha256(PRIOR.read_bytes()).hexdigest(),
        "expected_old": OLD,
        "frozen_old": frozen_old,
        "experiment": new_owner,
        "frozen_experiment": frozen_new,
        "restore": restored_owner,
        "preactivation_recovery": recovery_owner,
        "experimental_config": settings.model_dump(
            mode="json", exclude={"auth", "redis", "neo4j", "llm", "webhooks"}
        ),
        "restoration_config": core_settings.model_dump(
            mode="json", exclude={"auth", "redis", "neo4j", "llm", "webhooks"}
        ),
        "allowed_cleanup_keys": allowed,
        "model": "deterministic two-answer stub, no external LLM",
        "fixture_kind": "normalized synthetic events, not native/public webhook adapters",
        "expected_domain_trust": dict(
            zip(change_ids + decision_ids, ["trusted", "untrusted"] * 2, strict=True)
        ),
        "production_activation": False,
    }
    persist(evidence)

    def record(name):
        checks.append({"name": name, "passed": True, "scenarios": []})
        persist(evidence)

    async def operator(name, expected, intended, function, *args):
        evidence.setdefault("operator_intents", []).append(
            {"operation": name, "expected": expected, "intended": intended, "state": "submitting"}
        )
        persist(evidence)
        result = await asyncio.to_thread(function, database, *args)
        observed = await asyncio.to_thread(read_owner, database)
        if observed != [intended]:
            raise ActivationRefusedError("Operator result differs from known intent")
        evidence["operator_intents"][-1].update(state="verified", observed=observed)
        persist(evidence)
        return result

    consumers = []
    try:
        await operator("freeze_predecessor", OLD, frozen_old, freeze_target, OLD)
        await operator(
            "activate_experiment",
            frozen_old,
            new_owner,
            activate_empty_target,
            frozen_old,
            experimental,
        )
        fence = TenantFence.from_binding(experimental)
        ledger = SpannerEventLog(
            database,
            tenant_fence=fence,
            tenant_engine_revision=experimental.engine_revision,
            tenant_binding=experimental,
            tenant_read_operation="processing",
        )
        graph = SpannerGraphStore(database, tenant_fence=fence, tenant_read_operation="processing")
        projector = PackProjector(
            experimental.bundle.registry,
            frozenset(settings.ontology.trusted_sources),
            source_policy=SourceTrustPolicy.from_binding(experimental),
        )
        subscriptions = [
            SpannerSubscription(
                database,
                group,
                "owned-worker",
                tenant_fence=fence,
                tenant_engine_revision=experimental.engine_revision,
                tenant_read_operation="processing",
            )
            for group in groups
        ]
        for subscription in subscriptions:
            await subscription.ensure_group()
        events, payloads = [], []
        for i, eid in enumerate(event_ids):
            events.append(
                Event(
                    event_id=UUID(eid),
                    event_type="pdlc.change.created" if i < 2 else "pdlc.design.section_changed",
                    occurred_at=datetime.now(UTC),
                    session_id=eid,
                    agent_id="forged-agent" if i != 3 else "webhook:github",
                    trace_id=run_id,
                    payload_ref="fixture:" + eid,
                )
            )
            payloads.append(
                {
                    "repo": repo,
                    "number": i + 1,
                    "title": "Source-trust fixture",
                    "body": "",
                    "files": [],
                }
                if i < 2
                else {
                    "doc_id": "fixture-" + eid,
                    "section_path": "Decision",
                    "body": statements[i - 2],
                    "source_trust": "trusted",
                    "acceptance": {"source_id": "verified-producer"},
                }
            )
            source = "verified-producer" if i % 2 == 0 else "untrusted-producer"
            principal = Principal(
                "fixture-credential", experimental.tenant_id, frozenset({"api"}), source
            )
            await ledger.admission_writer(experimental.admission_context(principal)).append(
                events[-1], payloads[-1]
            )
        record("authenticated_admission_of_four_normalized_pdlc_events")
        records = await ledger.get_accepted_records(event_ids)
        evidence["accepted_provenance"] = [r.provenance.acceptance.model_dump() for r in records]
        if [r.provenance.acceptance.source_id for r in records] != [
            "verified-producer",
            "untrusted-producer",
        ] * 2:
            raise AssertionError("Accepted producer identity differs")
        record("real_fenced_records_keep_authenticated_producer_separate_from_payload")
        try:
            projector.plan(events[0], records[0].document, provenance=records[1].provenance)
        except RuntimeFencedError:
            record("another_events_provenance_refused_before_planning")
        else:
            raise AssertionError("Mismatched source provenance accepted")
        projection = ProjectionConsumer(subscriptions[0], ledger, graph, settings, projector)
        consumers.append(projection)
        deliveries = await subscriptions[0].read_new(10, 0)
        if {d.fields["event_id"] for d in deliveries} != set(event_ids):
            raise AssertionError("Projection deliveries differ from registered inputs")
        for delivery in deliveries:
            await projection.process_message(delivery.position, delivery.fields)
        await projection.on_stop()
        record("actual_projection_consumer_builds_common_and_pdlc_graph_on_spanner")

        class Model:
            calls = 0

            async def generate_text(self, prompt):
                matches = [statement for statement in statements if statement in prompt]
                if len(matches) != 1:
                    raise AssertionError("Unregistered extraction prompt")
                self.calls += 1
                return json.dumps(
                    {
                        "nodes": [
                            {
                                "ref": "n1",
                                "type": "Decision",
                                "statement": matches[0],
                                "rationale": "fixture",
                                "confidence": 0.95,
                                "evidence": matches[0],
                                "source_trust": "trusted",
                            }
                        ],
                        "links": [],
                    }
                )

        model = Model()
        extraction = PackExtractionConsumer(
            subscriptions[1],
            ledger,
            graph,
            extraction_profiles(
                experimental.bundle.registry, max_nodes=3, max_links=3, max_text_chars=2000
            ),
            projector,
            model,
            settings,
        )
        consumers.append(extraction)
        deliveries = await subscriptions[1].read_new(10, 0)
        if {d.fields["event_id"] for d in deliveries} != set(event_ids):
            raise AssertionError("Extraction deliveries differ from registered inputs")
        for delivery in deliveries:
            await extraction.process_message(delivery.position, delivery.fields)
            await subscriptions[1].ack(delivery.position)
        if model.calls != 2:
            raise AssertionError("Unexpected model invocation count")
        record("actual_pack_extraction_consumer_writes_two_decisions_stubbed_model")
        refs = [NodeRef("Change", nid) for nid in change_ids] + [
            NodeRef("Decision", nid) for nid in decision_ids
        ]
        nodes = await graph.get_nodes(refs)
        evidence["domain_nodes"] = [nodes.get(ref) for ref in refs]
        for ref, expected in zip(refs, ["trusted", "untrusted"] * 2, strict=True):
            if nodes.get(ref, {}).get("source_trust") != expected:
                raise AssertionError("Graph trust differs from authenticated producer policy")
        record("stored_change_and_extracted_decision_trust_matches_receipts_not_spoofing")
        with database.snapshot(multi_use=True) as snapshot:
            edges = list(
                snapshot.execute_sql(
                    "SELECT src_label, src_id, edge_type, dst_label, dst_id FROM GraphEdges"
                )
            )
        if {tuple(edge) for edge in edges} != {tuple(key) for key in allowed["GraphEdges"]}:
            raise AssertionError("Evidence edges differ from exact registered expectations")
        evidence["evidence_edges"] = edges
        record("exact_four_derived_from_edges_reference_original_accepted_events")
    finally:
        for consumer in consumers:
            consumer.stop()
        observed = await asyncio.to_thread(read_owner, database)
        if observed == [new_owner]:
            await operator("freeze_experiment", new_owner, frozen_new, freeze_target, new_owner)
            observed = [frozen_new]
        if observed == [frozen_new]:
            evidence["cleanup_intent"] = {
                "expected_owner": frozen_new,
                "exact_keys": allowed,
                "state": "submitting",
            }
            persist(evidence)
            evidence["cleanup_removed"] = await asyncio.to_thread(
                clean_registered_target, database, frozen_new, allowed
            )
            persist(evidence)
            await operator(
                "restore_latest_core",
                frozen_new,
                restored_owner,
                activate_empty_target,
                frozen_new,
                restore,
            )
        elif observed == [frozen_old]:
            await operator(
                "recover_pre_activation_latest_core",
                frozen_old,
                recovery_owner,
                activate_empty_target,
                frozen_old,
                recovery,
            )
        elif observed not in ([OLD], [restored_owner], [recovery_owner]):
            raise ActivationRefusedError("Unknown ownership; no cleanup or adoption")
        evidence["control_after"] = await asyncio.to_thread(read_owner, database)
        evidence["rows_after_cleanup"] = await asyncio.to_thread(fingerprint, database)
        if evidence["rows_after_cleanup"] != before:
            raise ActivationRefusedError("Application table preservation failed")
        record("exact_fixture_cleanup_and_monotonic_core_configuration_restoration")
