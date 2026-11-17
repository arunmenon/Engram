"""Bounded projection-expansion experiment on the pinned empty reserved target.

Synthetic unfamiliar pack and subscriber, real bound ledger/consumer/graph.
No DDL, native provider translation, production activation or history grant.
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
from context_graph.adapters.spanner.log import SpannerEventLog, json_value
from context_graph.adapters.spanner.subscription import SpannerSubscription
from context_graph.adapters.spanner.tenant_control import TenantFence
from context_graph.domain.models import Event
from context_graph.domain.pack_projection import (
    PackProjector,
    ProjectionExpansionError,
    make_node_id,
)
from context_graph.domain.source_trust import SourceTrustPolicy
from context_graph.ports.pack_graph import NodeRef
from context_graph.tenancy import Principal, TenantBinding
from context_graph.worker.projection import ProjectionConsumer

OLD = [
    "compat-control",
    RESOURCE,
    "compat-control-binding",
    8,
    "sha256:f57ffb649f7ab0197d21f45b9397203887f8cb103e32efd784f4e52ce4c3f7b1",
    "active",
]
PRIOR = Path(
    "docs/review/spanner-compatibility/runs/20261007-cloud-authenticated-source-trust-01/"
    "schema-evidence.json"
)
ENGINE = "tenant-control-conformance-v2-projection-expansion"


def binding(settings, epoch):
    return TenantBinding.from_settings(
        "compat-control", "compat-control-binding", epoch, settings, engine_revision=ENGINE
    )


def active(bound):
    return [*TenantFence.from_binding(bound)._identity(), "active"]


def fixture_inputs(run_id):
    """Independent exact effect oracle; no projector output used to bless itself."""
    events = [str(uuid5(NAMESPACE_URL, run_id + f"/expansion/{i}")) for i in range(5)]
    names = ["unequal", "product", "cumulative", "valid", "correlated"]
    items = [f"{run_id}-cumulative-{i}" for i in range(2100)]
    payloads = [
        {"groups": [run_id, run_id], "items": [run_id + "-unequal"]},
        {
            "sources": [f"{run_id}-s{i}" for i in range(101)],
            "targets": [f"{run_id}-t{i}" for i in range(100)],
        },
        {"groups": [run_id] * len(items), "items": items},
        {"groups": [run_id + "-valid"], "items": [run_id + "-valid-item"]},
        {
            "sources": [run_id + "-a", "", run_id + "-c"],
            "targets": [run_id + "-x", run_id + "-y", run_id + "-z"],
        },
    ]
    kinds = [
        "expansion.recorded",
        "expansion.stubbed",
        "expansion.recorded",
        "expansion.recorded",
        "expansion.stubbed",
    ]
    domain = [
        (run_id + "-valid", run_id + "-valid-item", "ready", "trusted"),
        ("observer", run_id + "-valid-item", "new", "trusted"),
        ("left", run_id + "-a", "new", None),
        ("left", run_id + "-c", "new", None),
        ("right", run_id + "-x", "new", None),
        ("right", run_id + "-y", "new", None),
        ("right", run_id + "-z", "new", None),
    ]
    node_ids = [make_node_id("ExpansionRecord", [group, item]) for group, item, *_ in domain]
    edges = [
        ["ExpansionRecord", nid, "DERIVED_FROM", "Event", events[3]] for nid in node_ids[:2]
    ] + [
        ["ExpansionRecord", node_ids[2], "EXPANSION_LINK", "ExpansionRecord", node_ids[4]],
        ["ExpansionRecord", node_ids[3], "EXPANSION_LINK", "ExpansionRecord", node_ids[6]],
    ]
    group = "expansion-" + uuid5(NAMESPACE_URL, run_id).hex
    return events, names, payloads, kinds, domain, node_ids, edges, group


async def verify_expansion(database, values, run_id, evidence, checks, fingerprint, persist):
    try:
        return await await_settled(
            _verify(database, values, run_id, evidence, checks, fingerprint, persist)
        )
    except asyncio.CancelledError:
        checks.append(
            {"name": "expansion_cancelled_after_cleanup", "passed": False, "scenarios": []}
        )
        persist(evidence)
        raise


async def _verify(database, values, run_id, evidence, checks, fingerprint, persist):
    prior = json.loads(PRIOR.read_text())
    if prior.get("control_after") != [OLD] or any(
        row["count"] for row in prior["after_rows"].values()
    ):
        raise ActivationRefusedError("Retained predecessor differs from pinned plan")
    if await asyncio.to_thread(read_owner, database) != [OLD]:
        raise ActivationRefusedError("Current owner differs from pinned predecessor")
    before = await asyncio.to_thread(fingerprint, database)
    if any(row["count"] for row in before.values()):
        raise ActivationRefusedError("Experiment requires empty target")
    settings = runtime_settings(values)
    settings.ontology.packs = ["expansion", "expansion_observer"]
    settings.ontology.pack_dirs = [str(Path("tests/fixtures/pack_contracts").resolve())]
    settings.ontology.trusted_source_ids = ["verified-producer"]
    settings.consumer.projection_batch_size = 2
    experimental = binding(settings, 9)
    core_settings = runtime_settings(values)
    restore, recovery = binding(core_settings, 10), binding(core_settings, 9)
    new, restored, recovered = active(experimental), active(restore), active(recovery)
    frozen_old, frozen_new = [*OLD[:-1], "frozen"], [*new[:-1], "frozen"]
    ids, names, payloads, kinds, domain, node_ids, edges, group = fixture_inputs(run_id)
    allowed = {table: [] for table in KEYS}
    allowed.update(
        {
            "Events": [[eid] for eid in ids],
            "GraphNodes": [["Event", eid] for eid in ids]
            + [["ExpansionRecord", nid] for nid in node_ids],
            "GraphEdges": edges,
            "ConsumerGroups": [[group]],
            "ConsumerCursors": [[group, shard] for shard in range(settings.spanner.shards)],
            "ConsumerDeliveries": [[group, eid] for eid in ids],
            "ConsumerDeadLetters": [[group, eid] for eid in ids],
        }
    )
    expected = {table: list(keys) for table, keys in allowed.items()}
    expected["ConsumerDeliveries"] = []
    expected["ConsumerDeadLetters"] = [[group, eid] for eid in ids[:3]]
    events = [
        Event(
            event_id=UUID(eid),
            event_type=kind,
            occurred_at=datetime(2026, 10, 7, tzinfo=UTC),
            session_id=eid,
            agent_id="untrusted-display-name",
            trace_id=run_id,
            payload_ref="fixture:" + eid,
        )
        for eid, kind in zip(ids, kinds, strict=True)
    ]
    # Compile/validate every synthetic payload and compute all owner intents before CAS.
    for event, payload in zip(events, payloads, strict=True):
        experimental.bundle.registry.event_types[
            event.event_type
        ].definition.payload_contract.validate_payload(payload)
    evidence["expansion_intent"] = {
        "expected_old": OLD,
        "frozen_old": frozen_old,
        "experimental": new,
        "frozen_experimental": frozen_new,
        "restored": restored,
        "preactivation_recovery": recovered,
        "prior_evidence": str(PRIOR),
        "prior_sha256": hashlib.sha256(PRIOR.read_bytes()).hexdigest(),
        "engine_revision": ENGINE,
        "production_activation": False,
        "historical_grant": False,
        "fixture_kind": "synthetic normalized unfamiliar pack plus subscriber; no native adapter",
        "payloads": dict(zip(names, payloads, strict=True)),
        "event_ids": dict(zip(names, ids, strict=True)),
        "allowed_cleanup_keys": allowed,
        "expected_final_keys": expected,
        "expected_domain": domain,
        "settings": settings.model_dump(
            mode="json", exclude={"auth", "redis", "neo4j", "llm", "webhooks"}
        ),
        "restoration_settings": core_settings.model_dump(
            mode="json", exclude={"auth", "redis", "neo4j", "llm", "webhooks"}
        ),
    }
    persist(evidence)

    def record(name):
        checks.append({"name": name, "passed": True, "scenarios": []})
        persist(evidence)

    async def operator(name, old, intended, function, *args):
        evidence.setdefault("operator_intents", []).append(
            {"operation": name, "expected": old, "intended": intended, "state": "submitting"}
        )
        persist(evidence)
        result = await asyncio.to_thread(function, database, *args)
        observed = await asyncio.to_thread(read_owner, database)
        if observed != [intended]:
            raise ActivationRefusedError("Operator result differs from registered intent")
        evidence["operator_intents"][-1].update(state="verified", observed=observed)
        persist(evidence)
        return result

    consumer = None
    try:
        await operator("freeze_predecessor", OLD, frozen_old, freeze_target, OLD)
        await operator(
            "activate_expansion", frozen_old, new, activate_empty_target, frozen_old, experimental
        )
        fence = TenantFence.from_binding(experimental)
        ledger = SpannerEventLog(
            database,
            tenant_fence=fence,
            tenant_engine_revision=ENGINE,
            tenant_binding=experimental,
            tenant_read_operation="processing",
        )
        graph = SpannerGraphStore(database, tenant_fence=fence, tenant_read_operation="processing")
        subscription = SpannerSubscription(
            database,
            group,
            "owned-worker",
            tenant_fence=fence,
            tenant_engine_revision=ENGINE,
            tenant_read_operation="processing",
        )
        await subscription.ensure_group()
        principal = Principal(
            "fixture-credential", experimental.tenant_id, frozenset({"api"}), "verified-producer"
        )
        outcomes = await ledger.admission_writer(
            experimental.admission_context(principal)
        ).append_batch_outcomes(events, payloads)
        if [outcome.status for outcome in outcomes] != ["created"] * 5:
            raise AssertionError("Fixture admission differs from registered inputs")
        records = await ledger.get_accepted_records(ids)
        if len(records) != 5 or [r.provenance.event_id for r in records] != ids:
            raise AssertionError("Accepted record membership/order differs from inputs")
        evidence["accepted_receipts"] = [r.provenance.acceptance.model_dump() for r in records]
        record("five_contract_valid_events_accepted_under_new_engine_and_two_packs")
        projector = PackProjector(
            experimental.bundle.registry,
            frozenset(),
            source_policy=SourceTrustPolicy.from_binding(experimental),
        )
        reasons = []
        for event, accepted in zip(events[:3], records[:3], strict=True):
            try:
                projector.plan(event, accepted.document, provenance=accepted.provenance)
            except ProjectionExpansionError as exc:
                reasons.append(exc.reason)
            else:
                raise AssertionError("Invalid fixture unexpectedly produced a plan")
        if reasons != ["unequal_key_lengths", "plan_limit_exceeded", "plan_limit_exceeded"]:
            raise AssertionError("Planner refusal reasons differ")
        evidence["refusal_reasons"] = dict(zip(names[:3], reasons, strict=True))
        record("real_accepted_records_refuse_unequal_product_and_cross_pack_overflow")
        consumer = ProjectionConsumer(subscription, ledger, graph, settings, projector)
        deliveries = await subscription.read_new(10, 0)
        if {d.fields["event_id"] for d in deliveries} != set(ids):
            raise AssertionError("Delivery membership differs from fixtures")
        for delivery in deliveries:
            await consumer.process_message(delivery.position, delivery.fields)
        await consumer.on_stop()
        dead_letters = await subscription.dead_letters()
        evidence["dead_letters"] = dead_letters
        if {row["event_id"] for row in dead_letters} != set(ids[:3]) or len(dead_letters) != 3:
            raise AssertionError("Terminal failures differ from registered invalid events")
        if any(
            row["engine_revision"] != ENGINE
            or row["bundle_digest"] != experimental.bundle_digest
            or row["disposition_epoch"] != "9"
            for row in dead_letters
        ):
            raise AssertionError("DLQ authority differs from active interpretation")
        record("actual_projection_consumer_dead_letters_only_three_invalid_events")
        common = await graph.get_nodes([NodeRef("Event", eid) for eid in ids])
        evidence["common_events"] = [common.get(NodeRef("Event", eid)) for eid in ids]
        for eid, kind in zip(ids, kinds, strict=True):
            node = common.get(NodeRef("Event", eid), {})
            if any(
                node.get(k) != v
                for k, v in {
                    "event_id": eid,
                    "event_type": kind,
                    "session_id": eid,
                    "agent_id": "untrusted-display-name",
                    "trace_id": run_id,
                }.items()
            ):
                raise AssertionError("Common Event properties differ from accepted inputs")
        record("all_five_common_event_properties_preserved_including_domain_refusals")
        nodes = await graph.get_nodes([NodeRef("ExpansionRecord", nid) for nid in node_ids])
        evidence["domain_nodes"] = [nodes.get(NodeRef("ExpansionRecord", nid)) for nid in node_ids]
        for nid, (group_value, item, status, trust) in zip(node_ids, domain, strict=True):
            node = nodes.get(NodeRef("ExpansionRecord", nid), {})
            if any(
                node.get(k) != v
                for k, v in {
                    "group": group_value,
                    "item": item,
                    "status": status,
                    "source_trust": trust,
                    "node_type": "ExpansionRecord",
                    "ontology_version": experimental.bundle.registry.version,
                }.items()
            ):
                raise AssertionError("Stored domain properties differ from exact oracle")
        record("valid_owner_subscriber_and_gap_correlated_stub_properties_match_oracle")
        with database.snapshot(multi_use=True) as snapshot:
            actual_keys = {
                table: [
                    list(row)
                    for row in snapshot.execute_sql(f"SELECT {', '.join(columns)} FROM {table}")
                ]
                for table, columns in KEYS.items()
            }
        evidence["observed_final_keys"] = actual_keys
        if any({tuple(k) for k in actual_keys[t]} != {tuple(k) for k in expected[t]} for t in KEYS):
            raise AssertionError("Exact graph/ledger/delivery/DLQ keys differ; forbidden effect")
        record("all_seven_table_keys_match_exact_outputs_and_forbidden_effects")
        with database.snapshot(multi_use=True) as snapshot:
            stored_edges = [
                list(row[:5]) + [json_value(row[5])]
                for row in snapshot.execute_sql(
                    "SELECT src_label, src_id, edge_type, dst_label, dst_id, props FROM GraphEdges"
                )
            ]
        evidence["stored_edge_properties"] = stored_edges
        for row in stored_edges:
            expected_props = {} if row[2] == "DERIVED_FROM" else {"source_trust": "trusted"}
            if row[5] != expected_props:
                raise AssertionError("Stored edge properties differ from independent oracle")
        record("exact_evidence_and_correlated_edge_properties_match_oracle")
    finally:
        if consumer is not None:
            consumer.stop()
        observed = await asyncio.to_thread(read_owner, database)
        if observed == [new]:
            await operator("freeze_expansion", new, frozen_new, freeze_target, new)
            observed = [frozen_new]
        if observed == [frozen_new]:
            evidence["cleanup_intent"] = {
                "expected": frozen_new,
                "keys": allowed,
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
                restored,
                activate_empty_target,
                frozen_new,
                restore,
            )
        elif observed == [frozen_old]:
            await operator(
                "recover_pre_activation",
                frozen_old,
                recovered,
                activate_empty_target,
                frozen_old,
                recovery,
            )
        elif observed not in ([OLD], [restored], [recovered]):
            raise ActivationRefusedError("Unknown ownership; no adoption or cleanup")
        evidence["control_after"] = await asyncio.to_thread(read_owner, database)
        evidence["rows_after_cleanup"] = await asyncio.to_thread(fingerprint, database)
        if evidence["rows_after_cleanup"] != before:
            raise ActivationRefusedError("Application preservation failed")
        record("exact_owned_cleanup_and_latest_core_monotonic_restoration")
