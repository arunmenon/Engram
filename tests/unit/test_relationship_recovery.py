"""Required-link and exact-endpoint recovery at validated planner/worker/store seams."""

import asyncio
import hashlib
import json
from contextlib import suppress
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.adapters.memory.log import MemoryEventLog
from context_graph.adapters.memory.subscription import MemorySubscription
from context_graph.domain.event_acceptance import (
    AdmissionContext,
    EventInterpretation,
    stamp_acceptance,
)
from context_graph.domain.models import Event
from context_graph.domain.ontology import OntologyError, OntologyRegistry, Pack
from context_graph.domain.pack_expressions import IdentityOperandError
from context_graph.domain.pack_projection import PackProjector, RequiredRelationshipError
from context_graph.domain.source_trust import (
    AcceptedRecord,
    SourceTrustPolicy,
    VerifiedSourceProvenance,
)
from context_graph.ontology import BUILTIN_PACK_DIR, load_pack_file
from context_graph.ontology.rebuild import project_ledger, rebuild
from context_graph.ontology.versioning import read_state, replay_event_types
from context_graph.ports.errors import RuntimeFencedError, UnavailableError
from context_graph.ports.pack_graph import EdgeWrite, NodeRef, NodeWrite
from context_graph.ports.relationship_recovery import CURSOR_LABEL
from context_graph.settings import Settings
from context_graph.worker.pack_projection import apply_plan
from context_graph.worker.projection import ProjectionConsumer
from context_graph.worker.relationship_recovery import RelationshipRecovery
from tests.unit.test_pack_versioning import _event

CORE = load_pack_file(BUILTIN_PACK_DIR / "core.pack.yaml")
CRM = load_pack_file(Path("tests/fixtures/packs/crm/crm.pack.yaml"))


def registry(*, required=True, target=None):
    data = CRM.model_dump(by_alias=True)
    edge = data["projection"][1]["edges"][0]
    edge["required"] = required
    edge["to"] = target or {"type": "Account", "match": {"account_id": "$.account_id"}}
    return OntologyRegistry([CORE, Pack.model_validate(data)])


def contact(reg):
    event = Event(
        event_id=uuid4(),
        event_type="crm.contact.added",
        occurred_at=datetime(2026, 11, 1, tzinfo=UTC),
        session_id="s",
        agent_id="webhook:crm",
        trace_id="t",
        payload_ref="p",
        global_position="1-0",
    )
    document = {
        **event.model_dump(mode="json"),
        "payload": {"email": "ann@example.test", "account_id": "acme"},
    }
    return PackProjector(reg, frozenset()).plan(event, document)


def test_required_key_lookup_waits_for_the_exact_record_without_creating_a_stub():
    plan = contact(registry())
    assert not any(n.ref.label == "Account" for n in plan.nodes)
    edges = [e for e in plan.edges if e.edge_type == "WORKS_AT"]
    assert len(edges) == 1
    assert edges[0].target.key == "Account:acme"
    assert edges[0].required is True
    assert plan.lookups == []


async def test_required_missing_target_recovers_in_the_same_fresh_rebuild():

    reg = registry()
    log, graph = MemoryEventLog(), MemoryGraphStore()
    for kind, payload, minute in [
        ("crm.contact.added", {"email": "ann@example.test", "account_id": "acme"}, 1),
        ("crm.account.created", {"account_id": "acme", "name": "Acme"}, 2),
    ]:
        event, payload = _event(kind, payload, minute)
        await log.append(event, payload)
    settings = Settings()
    settings.ontology.replay_batch_size = 1
    settings.consumer.projection_batch_size = 1
    report = await rebuild(
        log, graph, PackProjector(reg, frozenset()), settings, eval_dirs=[], skip_gate=True
    )
    rows = await graph.neighbors(
        [NodeRef("Contact", "Contact:ann@example.test")], ["WORKS_AT"], "out", 10
    )
    assert [r["target_key"] for r in rows] == ["Account:acme"]
    assert report.projection_complete


@pytest.mark.parametrize("required,complete", [(False, True), (True, False)])
async def test_absent_reference_is_counted_and_only_required_link_blocks_completeness(
    required, complete
):

    reg = registry(required=required, target={"node_id": "$.account_node_id"})
    log, graph = MemoryEventLog(), MemoryGraphStore()
    event, payload = _event(
        "crm.contact.added", {"email": "ann@example.test", "account_node_id": "Account:absent"}, 1
    )
    await log.append(event, payload)
    result = await rebuild(
        log, graph, PackProjector(reg, frozenset()), Settings(), eval_dirs=[], skip_gate=True
    )
    assert result.projection_complete is complete
    assert result.as_dict()["waiting_relationships"] == 1
    state = await read_state(graph)
    assert state.properties["rebuild_complete"] is complete
    assert state.properties["waiting_relationships"] == 1


async def test_redelivery_of_a_deferred_event_keeps_a_person_reviewed_relationship():

    reg = registry(target={"node_id": "$.account_node_id"})
    log, graph = MemoryEventLog(), MemoryGraphStore()
    event, payload = _event(
        "crm.contact.added", {"email": "ann@example.test", "account_node_id": "Account:acme"}, 1
    )
    position = await log.append(event, payload)
    settings = Settings()
    settings.consumer.projection_batch_size = 1
    await project_ledger(log, graph, PackProjector(reg, frozenset()), settings, batch_size=1)
    source, target = (
        NodeRef("Contact", "Contact:ann@example.test"),
        NodeRef("Account", "Account:acme"),
    )
    await graph.upsert_nodes([NodeWrite(target, {"name": "Acme"})])
    await graph.upsert_edges(
        [
            EdgeWrite(
                "WORKS_AT", source, target, {"link_status": "rejected", "source_trust": "trusted"}
            )
        ]
    )
    before = await graph.neighbors([source], ["WORKS_AT"], "out", 10)
    sub = MemorySubscription(log.stream, "recovery-test", "restart")
    await sub.ensure_group()
    consumer = ProjectionConsumer(sub, log, graph, settings, PackProjector(reg, frozenset()))
    await consumer.process_message(position, {"event_id": str(event.event_id)})
    after = await graph.neighbors([source], ["WORKS_AT"], "out", 10)
    assert after == before


@pytest.mark.parametrize(
    "form,match",
    [
        ("to", {"type": "Account", "match": {"industry": "$.industry"}}),
        ("to_each", {"type": "Account", "match_any_prefix": {"account_id": "$.account"}}),
        ("to_latest", {"type": "Account", "match": {"account_id": "$.account_id"}}),
    ],
)
def test_required_mutable_or_temporal_lookup_is_explicitly_unsupported(form, match):

    data = CRM.model_dump(by_alias=True)
    edge = data["projection"][1]["edges"][0]
    edge.pop("to")
    edge[form] = match
    edge["required"] = True
    with pytest.raises(OntologyError, match="required_relationship_needs_exact_identity"):
        OntologyRegistry([CORE, Pack.model_validate(data)])


def test_legacy_pack_digest_does_not_change_when_required_is_absent():

    assert (
        hashlib.sha256(CRM.canonical_json().encode()).hexdigest()
        == "e4168338a7ecc35bafa7c6fda70dd85fe3ccdd639f59bc866cb78533f2ca2455"
    )


@pytest.mark.parametrize("value", [None, "", "not-a-valid-node-id"])
def test_invalid_required_endpoint_refuses_the_event_plan(value):

    reg = registry(target={"node_id": "$.account_id"})
    event = Event(
        event_id=uuid4(),
        event_type="crm.contact.added",
        occurred_at=datetime(2026, 11, 1, tzinfo=UTC),
        session_id="s",
        agent_id="webhook:crm",
        trace_id="t",
        payload_ref="p",
        global_position="1-0",
    )
    doc = {
        **event.model_dump(mode="json"),
        "payload": {"email": "ann@example.test", "account_id": value},
    }
    with pytest.raises(RequiredRelationshipError, match="required_relationship_identity_missing"):
        PackProjector(reg, frozenset()).plan(event, doc)


async def pending_links(count=1, *, log=None, graph=None):

    reg = registry(target={"node_id": "$.account_node_id"})
    log, graph = log or MemoryEventLog(), graph or MemoryGraphStore()
    for n in range(count):
        event, payload = _event(
            "crm.contact.added",
            {"email": f"ann{n}@example.test", "account_node_id": f"Account:A{n}"},
            n + 1,
        )
        await log.append(event, payload)
    settings = Settings()
    settings.consumer.projection_batch_size = 1
    await project_ledger(log, graph, PackProjector(reg, frozenset()), settings, batch_size=1)
    return reg, log, graph


async def test_new_recovery_instances_make_fair_progress_past_missing_targets():

    reg, log, graph = await pending_links(5)
    rows = await graph.relationship_intents(None, 100)
    last = rows[-1]
    target = NodeRef(**last["target"])
    await graph.upsert_nodes(
        [
            NodeWrite(target, {"name": "ready"}),
            NodeWrite(NodeRef(CURSOR_LABEL, "relationships"), {"after": ""}),
        ]
    )
    for _ in range(5):
        report = await RelationshipRecovery(graph, log, PackProjector(reg, frozenset())).page(
            limit=1
        )
        assert report.scanned == 1
    edges = await graph.neighbors([NodeRef(**last["source"])], ["WORKS_AT"], "out", 10)
    assert [e["target_key"] for e in edges] == [target.key]
    assert len(await graph.relationship_intents(None, 100)) == 5


async def test_recovery_leaves_newer_node_values_and_lifecycle_state_untouched():

    reg, log, graph = await pending_links()
    row = (await graph.relationship_intents(None, 100))[0]
    source, target = NodeRef(**row["source"]), NodeRef(**row["target"])
    await graph.upsert_nodes(
        [
            NodeWrite(source, {"name": "newer", "status": "reviewed"}),
            NodeWrite(target, {"name": "ready"}),
        ]
    )
    before = await graph.get_nodes([source])
    result = await RelationshipRecovery(graph, log, PackProjector(reg, frozenset())).finish()
    assert result.complete and result.waiting == 0
    assert await graph.get_nodes([source]) == before
    assert len(await graph.neighbors([source], ["WORKS_AT"], "out", 10)) == 1


async def test_required_recovery_reports_expired_source_without_guessing():

    reg, log, graph = await pending_links()
    row = (await graph.relationship_intents(None, 100))[0]
    await graph.upsert_nodes([NodeWrite(NodeRef(**row["target"]))])
    assert (await log.expire(1))[1] == 1
    result = await RelationshipRecovery(graph, log, PackProjector(reg, frozenset())).finish()
    assert result.blocking == 1
    assert (await graph.relationship_intents(None, 100))[0]["status"] == "missing_source"
    assert await graph.neighbors([NodeRef(**row["source"])], ["WORKS_AT"], "out", 10) == []


async def test_recovery_does_not_claim_a_full_scan_when_the_budget_ends():

    reg, log, graph = await pending_links(3)
    result = await RelationshipRecovery(graph, log, PackProjector(reg, frozenset())).finish(
        budget=1, page_size=1
    )
    assert result.scanned == 1 and not result.complete_scan and not result.complete


@pytest.mark.parametrize("target_first", [False, True])
async def test_deferred_events_for_one_edge_keep_the_last_log_events_properties(target_first):

    data = CRM.model_dump(by_alias=True)
    data["types"]["edges"]["WORKS_AT"]["properties"] = {"note": "string"}
    edge = data["projection"][1]["edges"][0]
    edge["to"] = {"node_id": "$.account_node_id"}
    edge["required"] = True
    edge["set"] = {"note": "$.name"}
    reg = OntologyRegistry([CORE, Pack.model_validate(data)])
    inputs = [
        (
            "crm.contact.added",
            {"email": "ann@example.test", "account_node_id": "Account:acme", "name": "first"},
            1,
        ),
        (
            "crm.contact.added",
            {"email": "ann@example.test", "account_node_id": "Account:acme", "name": "last"},
            2,
        ),
        ("crm.account.created", {"account_id": "acme", "name": "Acme"}, 3),
    ]
    if target_first:
        inputs = [inputs[2], *inputs[:2]]
    log, graph, settings = MemoryEventLog(), MemoryGraphStore(), Settings()
    settings.consumer.projection_batch_size = 1
    for kind, payload, minute in inputs:
        event, payload = _event(kind, payload, minute)
        await log.append(event, payload)
    await project_ledger(log, graph, PackProjector(reg, frozenset()), settings, batch_size=1)
    rows = await graph.neighbors(
        [NodeRef("Contact", "Contact:ann@example.test")], ["WORKS_AT"], "out", 10
    )
    assert len(rows) == 1 and rows[0]["properties"]["note"] == "last"


async def test_a_truncated_optional_search_is_explicitly_incomplete():

    data = CRM.model_dump(by_alias=True)
    edge = data["projection"][1]["edges"][0]
    edge.pop("to")
    edge["to_each"] = {"type": "Account", "match": {"industry": "$.industry"}}
    reg = OntologyRegistry([CORE, Pack.model_validate(data)])
    log, graph, settings = MemoryEventLog(), MemoryGraphStore(), Settings()
    settings.ontology.lookup_limit = 1
    for n, (kind, payload) in enumerate(
        [
            ("crm.account.created", {"account_id": "a1", "industry": "retail"}),
            ("crm.account.created", {"account_id": "a2", "industry": "retail"}),
            ("crm.contact.added", {"email": "ann@example.test", "industry": "retail"}),
        ]
    ):
        event, payload = _event(kind, payload, n + 1)
        await log.append(event, payload)
    report = await rebuild(
        log, graph, PackProjector(reg, frozenset()), settings, eval_dirs=[], skip_gate=True
    )
    assert not report.projection_complete and report.blocking_relationships == 1
    rows = await graph.relationship_intents(None, 100)
    assert rows[0]["status"] == "ambiguous_or_truncated_lookup"


@pytest.mark.parametrize("error_name", ["fence", "transient"])
async def test_recovery_source_read_failure_keeps_the_intent_unchanged(error_name):

    class FailingLog(MemoryEventLog):
        fail = False

        async def get_documents(self, ids):
            if self.fail:
                raise (
                    RuntimeFencedError("fenced")
                    if error_name == "fence"
                    else UnavailableError("temporary")
                )
            return await super().get_documents(ids)

    reg, log, graph = await pending_links(log=FailingLog())
    before = await graph.relationship_intents(None, 100)
    log.fail = True
    with pytest.raises(RuntimeFencedError if error_name == "fence" else UnavailableError):
        await RelationshipRecovery(graph, log, PackProjector(reg, frozenset())).finish()
    assert await graph.relationship_intents(None, 100) == before


async def test_concurrent_recovery_sweeps_create_one_relationship():

    class YieldingLog(MemoryEventLog):
        async def get_documents(self, ids):
            await asyncio.sleep(0)
            return await super().get_documents(ids)

    reg, log, graph = await pending_links(log=YieldingLog())
    row = (await graph.relationship_intents(None, 100))[0]
    await graph.upsert_nodes([NodeWrite(NodeRef(**row["target"]))])
    await asyncio.gather(
        *(
            RelationshipRecovery(graph, log, PackProjector(reg, frozenset())).finish()
            for _ in range(2)
        )
    )
    assert len(await graph.neighbors([NodeRef(**row["source"])], ["WORKS_AT"], "out", 10)) == 1
    assert len(await graph.relationship_intents(None, 100)) == 1


async def test_compatible_epoch_recovery_revalidates_receipt_but_foreign_tenant_cannot_rebind():

    class AcceptedLog(MemoryEventLog):
        async def get_accepted_records(self, ids):
            docs = await self.get_documents(ids)
            return [
                AcceptedRecord(doc, VerifiedSourceProvenance(key, receipt))
                for key, doc in zip(ids, docs, strict=True)
            ]

    reg = registry(target={"node_id": "$.account_node_id"})
    log, graph = AcceptedLog(), MemoryGraphStore()
    event, payload = _event(
        "crm.contact.added", {"email": "ann@example.test", "account_node_id": "Account:acme"}, 1
    )
    position = await log.append(event, payload)
    event = event.model_copy(update={"global_position": position})
    authority = EventInterpretation(
        "a", "projects/p/instances/i/databases/d", "binding", 1, "sha256:" + "a" * 64, "engine"
    )
    receipt = stamp_acceptance(
        AdmissionContext(
            tenant_id="a",
            database_resource=authority.database_resource,
            binding_id="binding",
            accepted_epoch=1,
            bundle_digest=authority.bundle_digest,
            engine_revision="engine",
            source_id="producer",
        ),
        event,
        payload,
    )
    from context_graph.domain.projection import event_to_node

    await graph.merge_event_node(event_to_node(event))
    initial = PackProjector(
        reg,
        frozenset(),
        source_policy=SourceTrustPolicy(authority, frozenset({"producer"}), reg.version),
    )
    record = (await log.get_accepted_records([str(event.event_id)]))[0]
    await apply_plan(
        graph,
        initial.plan(event, record.document, provenance=record.provenance),
        100,
        recovery=RelationshipRecovery(graph, log, initial),
    )
    source, target = (
        NodeRef("Contact", "Contact:ann@example.test"),
        NodeRef("Account", "Account:acme"),
    )
    await graph.upsert_nodes([NodeWrite(target)])
    foreign = PackProjector(
        reg,
        frozenset(),
        source_policy=SourceTrustPolicy(
            replace(authority, tenant_id="other"), frozenset({"producer"}), reg.version
        ),
    )
    blocked = await RelationshipRecovery(graph, log, foreign).finish()
    assert blocked.blocking == 1
    assert await graph.neighbors([source], ["WORKS_AT"], "out", 10) == []
    advanced = PackProjector(
        reg,
        frozenset(),
        source_policy=SourceTrustPolicy(
            replace(authority, epoch=2), frozenset({"producer"}), reg.version
        ),
    )
    recovered = await RelationshipRecovery(graph, log, advanced).finish()
    assert recovered.complete and recovered.waiting == 0
    links = await graph.neighbors([source], ["WORKS_AT"], "out", 10)
    assert len(links) == 1 and links[0]["properties"]["source_trust"] == "trusted"


async def test_optional_latest_recovery_uses_the_original_selected_target_without_requery():

    data = CRM.model_dump(by_alias=True)
    rule = data["projection"][1]
    rule["upsert"] = []
    edge = rule["edges"][0]
    edge["from"] = {"node_id": "$.contact_node_id"}
    edge.pop("to")
    edge["to_latest"] = {"type": "Account", "match": {"industry": "$.industry"}}
    reg = OntologyRegistry([CORE, Pack.model_validate(data)])
    log, graph = MemoryEventLog(), MemoryGraphStore()
    first, second, contact_ref = (
        NodeRef("Account", "Account:a1"),
        NodeRef("Account", "Account:a2"),
        NodeRef("Contact", "Contact:ann"),
    )
    await graph.upsert_nodes(
        [NodeWrite(first, {"industry": "retail", "updated_at": "2026-10-01T00:00:00+00:00"})]
    )
    event, payload = _event(
        "crm.contact.added", {"contact_node_id": "Contact:ann", "industry": "retail"}, 1
    )
    await log.append(event, payload)
    await project_ledger(log, graph, PackProjector(reg, frozenset()), Settings(), batch_size=1)
    await graph.upsert_nodes(
        [
            NodeWrite(first, {"industry": "other", "updated_at": "2026-11-01T00:00:00+00:00"}),
            NodeWrite(second, {"industry": "retail", "updated_at": "2026-10-02T00:00:00+00:00"}),
            NodeWrite(contact_ref),
        ]
    )
    result = await RelationshipRecovery(graph, log, PackProjector(reg, frozenset())).finish()
    assert result.complete
    links = await graph.neighbors([contact_ref], ["WORKS_AT"], "out", 10)
    assert [e["target_key"] for e in links] == ["Account:a1"]


@pytest.mark.parametrize("changed_effect", [False, True])
async def test_new_bundle_only_recovers_if_the_original_effect_is_identical(changed_effect):

    reg, log, graph = await pending_links()
    row = (await graph.relationship_intents(None, 100))[0]
    await graph.upsert_nodes([NodeWrite(NodeRef(**row["target"]))])
    data = reg.pack("crm").model_dump(by_alias=True)
    data["pack"]["version"] = "2.0.0"
    if changed_effect:
        data["types"]["edges"]["WORKS_AT"]["properties"] = {"note": "string"}
        data["projection"][1]["edges"][0]["set"] = {"note": "new effect"}
    updated = OntologyRegistry([CORE, Pack.model_validate(data)])
    report = await RelationshipRecovery(graph, log, PackProjector(updated, frozenset())).finish()
    links = await graph.neighbors([NodeRef(**row["source"])], ["WORKS_AT"], "out", 10)
    assert bool(links) is not changed_effect
    assert report.complete is not changed_effect
    if changed_effect:
        assert (await graph.relationship_intents(None, 100))[0]["status"] == "changed_bundle"


async def test_a_new_consumer_recovers_on_idle_without_a_new_delivery():

    reg, log, graph = await pending_links()
    row = (await graph.relationship_intents(None, 100))[0]
    await graph.upsert_nodes([NodeWrite(NodeRef(**row["target"]))])
    sub = MemorySubscription(log.stream, "restart-test", "new-process")
    await sub.ensure_group()
    consumer = ProjectionConsumer(sub, log, graph, Settings(), PackProjector(reg, frozenset()))
    await consumer.on_idle()
    links = await graph.neighbors([NodeRef(**row["source"])], ["WORKS_AT"], "out", 10)
    assert len(links) == 1


async def test_a_lost_reply_after_atomic_recovery_is_safe_after_restart():

    class LostReplyGraph(MemoryGraphStore):
        lose_reply = True

        async def settle_relationship_intent(self, key, generation, status, edge=None):
            result = await super().settle_relationship_intent(key, generation, status, edge)
            if result == "recovered" and self.lose_reply:
                self.lose_reply = False
                raise UnavailableError("commit succeeded but response was lost")
            return result

    reg, log, graph = await pending_links(graph=LostReplyGraph())
    row = (await graph.relationship_intents(None, 100))[0]
    await graph.upsert_nodes([NodeWrite(NodeRef(**row["target"]))])
    with pytest.raises(UnavailableError):
        await RelationshipRecovery(graph, log, PackProjector(reg, frozenset())).finish()
    result = await RelationshipRecovery(graph, log, PackProjector(reg, frozenset())).finish()
    assert result.complete
    assert len(await graph.neighbors([NodeRef(**row["source"])], ["WORKS_AT"], "out", 10)) == 1
    assert len(await graph.relationship_intents(None, 100)) == 1


async def test_source_ack_failure_keeps_the_recovery_intent_for_a_restarted_consumer():

    class StopBeforeAck(MemorySubscription):
        async def ack(self, *positions):
            raise RuntimeFencedError("process stopped before source acknowledgement")

    reg, log, graph = (
        registry(target={"node_id": "$.account_node_id"}),
        MemoryEventLog(),
        MemoryGraphStore(),
    )
    event, payload = _event(
        "crm.contact.added", {"email": "ann@example.test", "account_node_id": "Account:acme"}, 1
    )
    position = await log.append(event, payload)
    sub = StopBeforeAck(log.stream, "ack-test", "first")
    await sub.ensure_group()
    delivery = (await sub.read_new(1, 0))[0]
    settings = Settings()
    settings.consumer.projection_batch_size = 1
    first = ProjectionConsumer(sub, log, graph, settings, PackProjector(reg, frozenset()))
    with pytest.raises(RuntimeFencedError):
        await first.process_message(delivery.position, delivery.fields)
    assert (await sub.delivery_counts(10))[position] == 1
    assert len(await graph.relationship_intents(None, 100)) == 1
    await graph.upsert_nodes([NodeWrite(NodeRef("Account", "Account:acme"))])
    restarted = MemorySubscription(log.stream, "ack-test", "second")
    await restarted.ensure_group()
    second = ProjectionConsumer(restarted, log, graph, settings, PackProjector(reg, frozenset()))
    await second.on_idle()
    await second.process_message(delivery.position, delivery.fields)
    assert await restarted.delivery_counts(10) == {}
    links = await graph.neighbors(
        [NodeRef("Contact", "Contact:ann@example.test")], ["WORKS_AT"], "out", 10
    )
    assert len(links) == 1 and len(await graph.relationship_intents(None, 100)) == 1


@pytest.mark.parametrize(
    "name", ["ProjectionRecovery", "Projectionrecovery", "ProjectionRecoveryCursor"]
)
def test_pack_cannot_shadow_internal_recovery_storage(name):

    data = CRM.model_dump(by_alias=True)
    data["types"]["nodes"][name] = {"key": ["id"], "properties": {"id": "string"}}
    with pytest.raises(OntologyError, match="reserved"):
        OntologyRegistry([CORE, Pack.model_validate(data)])


def test_required_key_lookup_uses_s4_complete_identity_operand_checks():

    reg = registry(
        target={"type": "Account", "match": {"account_id": "$.merchant + '|' + $.payment"}}
    )
    event = Event(
        event_id=uuid4(),
        event_type="crm.contact.added",
        occurred_at=datetime(2026, 11, 1, tzinfo=UTC),
        session_id="s",
        agent_id="webhook:crm",
        trace_id="t",
        payload_ref="p",
        global_position="1-0",
    )
    document = {
        **event.model_dump(mode="json"),
        "payload": {"email": "ann@example.test", "merchant": "acme"},
    }
    with pytest.raises(IdentityOperandError):
        PackProjector(reg, frozenset()).plan(event, document)


async def test_required_missing_link_refuses_an_unconfigured_direct_writer_before_domain_writes():

    graph = MemoryGraphStore()
    plan = contact(registry())
    with pytest.raises(RuntimeFencedError, match="durable relationship recovery"):
        await apply_plan(graph, plan, 100)
    assert await graph.get_nodes([NodeRef("Contact", "Contact:ann@example.test")]) == {}


@pytest.mark.parametrize("target_position", [0, 1, 2])
async def test_deferred_partial_link_updates_preserve_each_fields_latest_value(target_position):
    data = CRM.model_dump(by_alias=True)
    data["types"]["edges"]["WORKS_AT"]["properties"] = {
        "first_note": "string",
        "second_note": "string",
    }
    edge = data["projection"][1]["edges"][0]
    edge["to"] = {"node_id": "$.account_node_id"}
    edge["required"] = True
    edge["set"] = {"first_note": "$.first_note", "second_note": "$.second_note"}
    reg = OntologyRegistry([CORE, Pack.model_validate(data)])
    inputs = [
        (
            "crm.contact.added",
            {"email": "ann@example.test", "account_node_id": "Account:acme", "first_note": "kept"},
            1,
        ),
        (
            "crm.contact.added",
            {"email": "ann@example.test", "account_node_id": "Account:acme", "second_note": "new"},
            2,
        ),
    ]
    inputs.insert(
        target_position, ("crm.account.created", {"account_id": "acme", "name": "Acme"}, 3)
    )
    log, graph, settings = MemoryEventLog(), MemoryGraphStore(), Settings()
    settings.consumer.projection_batch_size = 1
    for kind, payload, minute in inputs:
        event, payload = _event(kind, payload, minute)
        await log.append(event, payload)
    await project_ledger(log, graph, PackProjector(reg, frozenset()), settings, batch_size=1)
    rows = await graph.neighbors(
        [NodeRef("Contact", "Contact:ann@example.test")], ["WORKS_AT"], "out", 10
    )
    assert rows[0]["properties"] == {
        "first_note": "kept",
        "second_note": "new",
        "source_trust": "untrusted",
    }


async def test_mixed_lookup_and_exact_link_writes_keep_event_order_within_a_flush():
    data = CRM.model_dump(by_alias=True)
    data["types"]["edges"]["WORKS_AT"]["properties"] = {"note": "string"}
    edge = data["projection"][1]["edges"][0]
    edge["to"] = {"type": "Account", "match": {"account_id": "$.account_id"}}
    edge["set"] = {"note": "$.note"}
    later = deepcopy(data["projection"][1])
    later["event"] = "crm.contact.refreshed"
    later["edges"][0]["to"] = {"node_id": "$.account_node_id"}
    data["events"]["crm.contact.refreshed"] = {}
    data["projection"].append(later)
    reg = OntologyRegistry([CORE, Pack.model_validate(data)])
    log, graph, settings = MemoryEventLog(), MemoryGraphStore(), Settings()
    settings.consumer.projection_batch_size = 10
    for n, (kind, payload) in enumerate(
        [
            ("crm.account.created", {"account_id": "acme"}),
            (
                "crm.contact.added",
                {"email": "ann@example.test", "account_id": "acme", "note": "older"},
            ),
            (
                "crm.contact.refreshed",
                {"email": "ann@example.test", "account_node_id": "Account:acme", "note": "newer"},
            ),
        ]
    ):
        event, payload = _event(kind, payload, n + 1)
        await log.append(event, payload)
    await project_ledger(log, graph, PackProjector(reg, frozenset()), settings, batch_size=10)
    rows = await graph.neighbors(
        [NodeRef("Contact", "Contact:ann@example.test")], ["WORKS_AT"], "out", 10
    )
    assert rows[0]["properties"]["note"] == "newer"


@pytest.mark.parametrize("target_first", [False, True])
async def test_deferred_clear_removes_one_field_and_preserves_earlier_other_fields(target_first):
    data = CRM.model_dump(by_alias=True)
    data["processing"]["requires"] = ["pack.properties.v1"]
    data["types"]["edges"]["WORKS_AT"]["properties"] = {"note": "string", "kept": "string"}
    first = data["projection"][1]
    first["edges"][0]["required"] = True
    first["edges"][0]["to"] = {"node_id": "$.account_node_id"}
    first["edges"][0]["set"] = {"note": "$.note", "kept": "$.kept"}
    later = deepcopy(first)
    later["event"] = "crm.contact.cleared"
    later["edges"][0]["set"] = {"note": {"value": None, "on_null": "clear"}}
    data["events"]["crm.contact.cleared"] = {}
    data["projection"].append(later)
    reg = OntologyRegistry([CORE, Pack.model_validate(data)])
    inputs = [
        (
            "crm.contact.added",
            {
                "email": "ann@example.test",
                "account_node_id": "Account:acme",
                "note": "private-note-value",
                "kept": "private-kept-value",
            },
            1,
        ),
        (
            "crm.contact.cleared",
            {"email": "ann@example.test", "account_node_id": "Account:acme"},
            2,
        ),
        ("crm.account.created", {"account_id": "acme"}, 3),
    ]
    if target_first:
        inputs = [inputs[2], *inputs[:2]]
    log, graph, settings = MemoryEventLog(), MemoryGraphStore(), Settings()
    settings.consumer.projection_batch_size = 1
    for kind, payload, minute in inputs:
        event, payload = _event(kind, payload, minute)
        await log.append(event, payload)
    await project_ledger(log, graph, PackProjector(reg, frozenset()), settings, batch_size=1)
    rows = await graph.neighbors(
        [NodeRef("Contact", "Contact:ann@example.test")], ["WORKS_AT"], "out", 10
    )
    assert rows[0]["properties"] == {"kept": "private-kept-value", "source_trust": "untrusted"}
    metadata = json.dumps(await graph.relationship_intents(None, 100))
    assert "private-note-value" not in metadata and "private-kept-value" not in metadata


async def test_two_effects_from_one_event_are_compacted_in_their_original_order():
    data = CRM.model_dump(by_alias=True)
    data["types"]["edges"]["WORKS_AT"]["properties"] = {"first": "string", "second": "string"}
    edge = data["projection"][1]["edges"][0]
    edge["required"] = True
    edge["to"] = {"node_id": "$.account_node_id"}
    edge["set"] = {"first": "$.first"}
    another = deepcopy(edge)
    another["set"] = {"second": "$.second"}
    data["projection"][1]["edges"].append(another)
    reg = OntologyRegistry([CORE, Pack.model_validate(data)])
    log, graph, settings = MemoryEventLog(), MemoryGraphStore(), Settings()
    settings.consumer.projection_batch_size = 1
    for kind, payload, minute in [
        (
            "crm.contact.added",
            {
                "email": "ann@example.test",
                "account_node_id": "Account:acme",
                "first": "one",
                "second": "two",
            },
            1,
        ),
        ("crm.account.created", {"account_id": "acme"}, 2),
    ]:
        event, payload = _event(kind, payload, minute)
        await log.append(event, payload)
    await project_ledger(log, graph, PackProjector(reg, frozenset()), settings, batch_size=1)
    rows = await graph.neighbors(
        [NodeRef("Contact", "Contact:ann@example.test")], ["WORKS_AT"], "out", 10
    )
    assert rows[0]["properties"] == {"first": "one", "second": "two", "source_trust": "untrusted"}
    assert len(await graph.relationship_intents(None, 100)) == 1


async def test_a_generation_replaced_during_recovery_cannot_be_counted_complete():
    class InterleavingLog(MemoryEventLog):
        callback = None

        async def get_documents(self, ids):
            documents = await super().get_documents(ids)
            callback, self.callback = self.callback, None
            if callback is not None:
                await callback()
            return documents

    reg, log, graph = await pending_links(log=InterleavingLog())
    row = (await graph.relationship_intents(None, 100))[0]
    await graph.upsert_nodes([NodeWrite(NodeRef(**row["target"]))])
    event, payload = _event(
        "crm.contact.added",
        {"email": "ann0@example.test", "account_node_id": row["target"]["key"]},
        2,
    )
    position = await log.append(event, payload)
    document = (await log.get_documents([str(event.event_id)]))[0]
    event = event.model_copy(update={"global_position": position})
    projector = PackProjector(reg, frozenset())

    async def replace_generation():
        await RelationshipRecovery(graph, log, projector).capture(
            [projector.plan(event, document)], {}
        )

    log.callback = replace_generation
    interrupted = await RelationshipRecovery(graph, log, projector).finish()
    assert not interrupted.complete and not interrupted.complete_scan
    assert (await RelationshipRecovery(graph, log, projector).finish()).complete
    assert len(await graph.neighbors([NodeRef(**row["source"])], ["WORKS_AT"], "out", 10)) == 1


async def test_explicit_pack_replay_can_update_a_previously_recovered_relationship():
    data = CRM.model_dump(by_alias=True)
    data["types"]["edges"]["WORKS_AT"]["properties"] = {"note": "string"}
    edge = data["projection"][1]["edges"][0]
    edge["required"] = True
    edge["to"] = {"node_id": "$.account_node_id"}
    edge["set"] = {"note": "$.note"}
    reg = OntologyRegistry([CORE, Pack.model_validate(data)])
    log, graph, settings = MemoryEventLog(), MemoryGraphStore(), Settings()
    settings.consumer.projection_batch_size = 1
    for kind, payload, minute in [
        (
            "crm.contact.added",
            {"email": "ann@example.test", "account_node_id": "Account:acme", "note": "original"},
            1,
        ),
        ("crm.account.created", {"account_id": "acme"}, 2),
    ]:
        event, payload = _event(kind, payload, minute)
        await log.append(event, payload)
    await project_ledger(log, graph, PackProjector(reg, frozenset()), settings, batch_size=1)
    data["pack"]["version"] = "1.1.0"
    data["projection"][1]["edges"][0]["set"] = {"note": "updated rule"}
    updated = OntologyRegistry([CORE, Pack.model_validate(data)])
    report = await replay_event_types(
        log,
        graph,
        PackProjector(updated, frozenset()),
        {"crm.contact.added"},
        batch_size=1,
        lookup_limit=100,
    )
    rows = await graph.neighbors(
        [NodeRef("Contact", "Contact:ann@example.test")], ["WORKS_AT"], "out", 10
    )
    assert report.relationships_complete and rows[0]["properties"]["note"] == "updated rule"


async def test_a_new_event_does_not_reopen_completed_retention_expired_source_work():
    data = CRM.model_dump(by_alias=True)
    data["types"]["edges"]["WORKS_AT"]["properties"] = {"first": "string", "second": "string"}
    edge = data["projection"][1]["edges"][0]
    edge["required"] = True
    edge["to"] = {"node_id": "$.account_node_id"}
    edge["set"] = {"first": "$.first", "second": "$.second"}
    reg = OntologyRegistry([CORE, Pack.model_validate(data)])
    now = datetime(2026, 11, 28, tzinfo=UTC)
    log, graph, settings = (
        MemoryEventLog(clock=lambda: now.timestamp()),
        MemoryGraphStore(),
        Settings(),
    )
    settings.consumer.projection_batch_size = 1
    for kind, payload in [
        (
            "crm.contact.added",
            {"email": "ann@example.test", "account_node_id": "Account:acme", "first": "retained"},
        ),
        ("crm.account.created", {"account_id": "acme"}),
    ]:
        event, payload = _event(kind, payload, 1)
        await log.append(event.model_copy(update={"occurred_at": now - timedelta(days=2)}), payload)
    await project_ledger(log, graph, PackProjector(reg, frozenset()), settings, batch_size=1)
    assert (await log.expire(1))[1] == 2
    event, payload = _event(
        "crm.contact.added",
        {"email": "ann@example.test", "account_node_id": "Account:acme", "second": "new"},
        3,
    )
    event = event.model_copy(update={"occurred_at": now})
    position = await log.append(event, payload)
    sub = MemorySubscription(log.stream, "after-retention", "new-consumer")
    await sub.ensure_group()
    consumer = ProjectionConsumer(sub, log, graph, settings, PackProjector(reg, frozenset()))
    await consumer.process_message(position, {"event_id": str(event.event_id)})
    rows = await graph.neighbors(
        [NodeRef("Contact", "Contact:ann@example.test")], ["WORKS_AT"], "out", 10
    )
    assert rows[0]["properties"] == {
        "first": "retained",
        "second": "new",
        "source_trust": "untrusted",
    }
    assert (await graph.relationship_intents(None, 100))[0]["status"] in {
        "recovered",
        "existing_relationship_kept",
    }


@pytest.mark.parametrize("change", ["agent", "unused_payload"])
async def test_changed_original_source_is_refused_even_when_projected_values_are_equal(change):
    class ChangedSourceLog(MemoryEventLog):
        altered = False

        async def get_documents(self, ids):
            documents = deepcopy(await super().get_documents(ids))
            if self.altered:
                for document in documents:
                    if document is None:
                        continue
                    if change == "agent":
                        document["agent_id"] = "different-source"
                    else:
                        document["payload"]["unused"] = "changed original content"
            return documents

    reg, log, graph = await pending_links(log=ChangedSourceLog())
    row = (await graph.relationship_intents(None, 100))[0]
    await graph.upsert_nodes([NodeWrite(NodeRef(**row["target"]))])
    log.altered = True
    report = await RelationshipRecovery(graph, log, PackProjector(reg, frozenset())).finish()
    assert report.blocking == 1
    assert (await graph.relationship_intents(None, 100))[0]["status"] == "changed_source"
    assert await graph.neighbors([NodeRef(**row["source"])], ["WORKS_AT"], "out", 10) == []


async def test_required_explicit_core_relationship_is_recovered_like_a_domain_link():
    data = CRM.model_dump(by_alias=True)
    edge = data["projection"][1]["edges"][0]
    edge["type"] = "DERIVED_FROM"
    edge["required"] = True
    edge["to"] = {"node_id": "$.earlier_event"}
    reg = OntologyRegistry([CORE, Pack.model_validate(data)])
    target, target_payload = _event("tool.execute", {"text": "arrives later"}, 1)
    source, source_payload = _event(
        "crm.contact.added",
        {"email": "ann@example.test", "earlier_event": f"Event:{target.event_id}"},
        2,
    )
    log, graph, settings = MemoryEventLog(), MemoryGraphStore(), Settings()
    settings.consumer.projection_batch_size = 1
    await log.append(source, source_payload)
    await log.append(target, target_payload)
    report = await rebuild(
        log, graph, PackProjector(reg, frozenset()), settings, eval_dirs=[], skip_gate=True
    )
    rows = await graph.neighbors(
        [NodeRef("Contact", "Contact:ann@example.test")], ["DERIVED_FROM"], "out", 10
    )
    assert {row["target_key"] for row in rows} == {str(source.event_id), str(target.event_id)}
    assert report.projection_complete


async def test_recovery_pages_stay_empty_after_an_explicit_graph_reset():
    _reg, _log, graph = await pending_links(3)
    first = await graph.relationship_intents(None, 1)
    next_page = await graph.relationship_intents(first[0]["node_id"], 1)
    assert len(first) == len(next_page) == 1 and first[0]["node_id"] < next_page[0]["node_id"]
    await graph.delete_all(confirm=True)
    assert await graph.relationship_intents(None, 1) == []


async def test_replay_settles_an_old_bundle_row_when_target_arrived_before_its_page():
    reg, log, graph = await pending_links()
    row = (await graph.relationship_intents(None, 100))[0]
    await graph.upsert_nodes([NodeWrite(NodeRef(**row["target"]))])
    data = reg.packs[-1].model_dump(by_alias=True)
    data["pack"]["version"] = "1.1.0"
    data["types"]["edges"]["WORKS_AT"]["properties"] = {"note": "string"}
    data["projection"][1]["edges"][0]["set"] = {"note": "new effect"}
    updated = OntologyRegistry([CORE, Pack.model_validate(data)])
    report = await replay_event_types(
        log,
        graph,
        PackProjector(updated, frozenset()),
        {"crm.contact.added"},
        batch_size=1,
        lookup_limit=100,
    )
    assert report.relationships_complete
    assert (await graph.relationship_intents(None, 100))[0]["status"] in {
        "recovered",
        "existing_relationship_kept",
    }


async def test_first_delivery_of_older_disjoint_fields_after_recovery_preserves_them():
    data = CRM.model_dump(by_alias=True)
    data["types"]["edges"]["WORKS_AT"]["properties"] = {
        "first_note": "string",
        "second_note": "string",
    }
    edge = data["projection"][1]["edges"][0]
    edge["to"] = {"node_id": "$.account_node_id"}
    edge["required"] = True
    edge["set"] = {"first_note": "$.first_note", "second_note": "$.second_note"}
    reg = OntologyRegistry([CORE, Pack.model_validate(data)])
    graph, log = MemoryGraphStore(), MemoryEventLog()
    projector = PackProjector(reg, frozenset())
    recovery = RelationshipRecovery(graph, log, projector)
    plans = []
    for payload in [
        {"first_note": "older separate field"},
        {"second_note": "newer separate field"},
    ]:
        event, payload = _event(
            "crm.contact.added",
            {"email": "ann@example.test", "account_node_id": "Account:acme", **payload},
            1,
        )
        position = await log.append(event, payload)
        document = (await log.get_documents([str(event.event_id)]))[0]
        plans.append(
            projector.plan(event.model_copy(update={"global_position": position}), document)
        )
    await apply_plan(graph, plans[1], 100, recovery=recovery)
    await graph.upsert_nodes([NodeWrite(NodeRef("Account", "Account:acme"))])
    assert (await recovery.finish()).complete
    await apply_plan(graph, plans[0], 100, recovery=recovery)
    assert (await recovery.finish()).complete
    rows = await graph.neighbors(
        [NodeRef("Contact", "Contact:ann@example.test")], ["WORKS_AT"], "out", 10
    )
    assert rows[0]["properties"]["first_note"] == "older separate field"
    assert rows[0]["properties"]["second_note"] == "newer separate field"


@pytest.mark.parametrize("method", ["page", "finish"])
async def test_recovery_deadline_returns_incomplete_instead_of_raising(method):
    class SlowGraph(MemoryGraphStore):
        async def relationship_intents(self, after, limit):
            await asyncio.sleep(0.03)
            return await super().relationship_intents(after, limit)

    recovery = RelationshipRecovery(
        SlowGraph(), MemoryEventLog(), PackProjector(registry(), frozenset()), timeout_s=0.001
    )
    result = await getattr(recovery, method)()
    assert not result.complete and not result.complete_scan


async def test_recovery_failure_on_an_unrelated_row_does_not_block_a_healthy_ack():
    class BrokenRecoveryRead(MemoryGraphStore):
        async def relationship_intents(self, after, limit):
            raise ValueError("unrelated damaged recovery row")

    graph, log = BrokenRecoveryRead(), MemoryEventLog()
    event, payload = _event("crm.account.created", {"account_id": "healthy"}, 1)
    await log.append(event, payload)
    sub = MemorySubscription(log.stream, "healthy-recovery", "operator")
    await sub.ensure_group()
    delivery = (await sub.read_new(1, 0))[0]
    settings = Settings()
    settings.consumer.projection_batch_size = 1
    consumer = ProjectionConsumer(sub, log, graph, settings, PackProjector(registry(), frozenset()))
    await consumer.process_message(delivery.position, delivery.fields)
    assert await sub.read_pending(10) == [] and sub.dead_letters == []
    assert NodeRef("Account", "Account:healthy") in await graph.get_nodes(
        [NodeRef("Account", "Account:healthy")]
    )


async def test_explicit_replay_can_retire_its_own_previously_truncated_lookup():
    data = CRM.model_dump(by_alias=True)
    edge = data["projection"][1]["edges"][0]
    edge.pop("to")
    edge["to_each"] = {"type": "Account", "match": {"industry": "$.industry"}}
    reg = OntologyRegistry([CORE, Pack.model_validate(data)])
    graph, log, settings = MemoryGraphStore(), MemoryEventLog(), Settings()
    settings.ontology.lookup_limit = 1
    for index, (kind, payload) in enumerate(
        [
            ("crm.account.created", {"account_id": "a1", "industry": "retail"}),
            ("crm.account.created", {"account_id": "a2", "industry": "retail"}),
            ("crm.contact.added", {"email": "ann@example.test", "industry": "retail"}),
        ]
    ):
        event, payload = _event(kind, payload, index + 1)
        await log.append(event, payload)
    projector = PackProjector(reg, frozenset())
    initial = await rebuild(log, graph, projector, settings, eval_dirs=[], skip_gate=True)
    assert not initial.projection_complete
    report = await replay_event_types(
        log, graph, projector, {"crm.contact.added"}, batch_size=1, lookup_limit=100
    )
    assert report.relationships_complete
    rows = await graph.neighbors(
        [NodeRef("Contact", "Contact:ann@example.test")], ["WORKS_AT"], "out", 10
    )
    assert {r["target_key"] for r in rows} == {"Account:a1", "Account:a2"}


async def test_completed_recovery_status_is_monotonic_even_after_a_late_diagnostic():
    reg, log, graph = await pending_links()
    row = (await graph.relationship_intents(None, 100))[0]
    await graph.upsert_nodes([NodeWrite(NodeRef(**row["target"]))])
    assert (
        await RelationshipRecovery(graph, log, PackProjector(reg, frozenset())).finish()
    ).complete
    status = await graph.settle_relationship_intent(
        row["node_id"], row["generation"], "missing_source"
    )
    assert status == "recovered"
    assert (
        await RelationshipRecovery(graph, log, PackProjector(reg, frozenset())).finish()
    ).complete


async def test_explicit_replay_respects_its_configured_recovery_deadline():
    reg, log, graph = await pending_links()
    result = await replay_event_types(
        log,
        graph,
        PackProjector(reg, frozenset()),
        {"crm.contact.added"},
        batch_size=1,
        lookup_limit=100,
        recovery_timeout_s=0,
        recovery_max_rows=1,
        recovery_page_size=1,
    )
    assert not result.relationships_complete and not result.relationship_scan_complete


async def test_nested_json_null_is_not_equivalent_to_a_missing_field_in_a_pinned_effect():
    data = CRM.model_dump(by_alias=True)
    data["types"]["edges"]["WORKS_AT"]["properties"] = {"data": "json"}
    edge = data["projection"][1]["edges"][0]
    edge.update(to={"node_id": "$.account_node_id"}, required=True, set={"data": "$.one"})
    reg = OntologyRegistry([CORE, Pack.model_validate(data)])
    log, graph = MemoryEventLog(), MemoryGraphStore()
    event, payload = _event(
        "crm.contact.added",
        {
            "email": "ann@example.test",
            "account_node_id": "Account:acme",
            "one": {"x": None},
            "two": {},
        },
        1,
    )
    position = await log.append(event, payload)
    document = (await log.get_documents([str(event.event_id)]))[0]
    event = event.model_copy(update={"global_position": position})
    old = PackProjector(reg, frozenset())
    await apply_plan(
        graph, old.plan(event, document), 100, recovery=RelationshipRecovery(graph, log, old)
    )
    await graph.upsert_nodes([NodeWrite(NodeRef("Account", "Account:acme"))])
    data["pack"]["version"] = "1.1.0"
    data["projection"][1]["edges"][0]["set"] = {"data": "$.two"}
    changed = PackProjector(OntologyRegistry([CORE, Pack.model_validate(data)]), frozenset())
    assert not (await RelationshipRecovery(graph, log, changed).finish()).complete
    ref = NodeRef("Contact", "Contact:ann@example.test")
    assert await graph.neighbors([ref], ["WORKS_AT"], "out", 10) == []
    assert (await RelationshipRecovery(graph, log, old).finish()).complete
    rows = await graph.neighbors([ref], ["WORKS_AT"], "out", 10)
    assert rows[0]["properties"]["data"] == {"x": None}


async def recovery_patch_inputs(backend, *, count=3):
    ordered = backend.startswith("ordered_")
    backend = backend.removeprefix("ordered_")
    if backend == "memory":
        graph = MemoryGraphStore()
    else:
        from tests.unit.test_relationship_recovery_spanner import setup

        _database, graph = setup()
    data = CRM.model_dump(by_alias=True)
    data["types"]["edges"]["WORKS_AT"]["properties"] = {
        "a": "string",
        "b": "string",
        "note": "string",
    }
    edge = data["projection"][1]["edges"][0]
    edge.update(to={"node_id": "$.account_node_id"}, required=True, set={"a": "$.a", "b": "$.b"})
    if ordered:
        data["types"]["nodes"]["Contact"]["ordering"] = {
            "source": "webhook:crm",
            "by": "$.sequence",
            "kind": "sequence",
        }
    planner = PackProjector(
        OntologyRegistry([CORE, Pack.model_validate(data)]),
        frozenset({"webhook:crm"}) if ordered else frozenset(),
    )
    log, plans = MemoryEventLog(), []
    for sequence, values in enumerate(
        [{"a": "one"}, {"a": "two"}, {"b": "three"}][:count], start=1
    ):
        event, payload = _event(
            "crm.contact.added",
            {
                "email": "ann@example.test",
                "account_node_id": "Account:acme",
                "sequence": sequence,
                **values,
            },
            1,
        )
        if ordered:
            event = event.model_copy(update={"agent_id": "webhook:crm"})
        position = await log.append(event, payload)
        document = (await log.get_documents([str(event.event_id)]))[0]
        plans.append(planner.plan(event.model_copy(update={"global_position": position}), document))
    return data, planner, log, graph, plans


@pytest.mark.parametrize(
    "backend", ["memory", "spanner_fake", "ordered_memory", "ordered_spanner_fake"]
)
@pytest.mark.parametrize("target_first", [False, True])
async def test_first_delivery_of_middle_order_field_replaces_its_older_winner(
    backend, target_first
):
    _data, planner, log, graph, plans = await recovery_patch_inputs(backend)
    recovery = RelationshipRecovery(graph, log, planner)
    if target_first:
        await graph.upsert_nodes([NodeWrite(NodeRef("Account", "Account:acme"))])
    await apply_plan(graph, plans[0], 100, recovery=recovery)
    await apply_plan(graph, plans[2], 100, recovery=recovery)
    if not target_first:
        await graph.upsert_nodes([NodeWrite(NodeRef("Account", "Account:acme"))])
    assert (await recovery.finish()).complete
    await apply_plan(graph, plans[1], 100, recovery=recovery)
    assert (await recovery.finish()).complete
    rows = await graph.neighbors(
        [NodeRef("Contact", "Contact:ann@example.test")], ["WORKS_AT"], "out", 10
    )
    assert rows[0]["properties"]["a"] == "two"
    assert rows[0]["properties"]["b"] == "three"


@pytest.mark.parametrize(
    "backend", ["memory", "spanner_fake", "ordered_memory", "ordered_spanner_fake"]
)
@pytest.mark.parametrize("replay", [False, True])
async def test_failure_after_capture_never_loses_the_tracked_patch_on_retry(backend, replay):
    data, planner, log, graph, plans = await recovery_patch_inputs(
        backend, count=1 if replay else 3
    )
    recovery = RelationshipRecovery(graph, log, planner)
    await apply_plan(graph, plans[0], 100, recovery=recovery)
    await graph.upsert_nodes([NodeWrite(NodeRef("Account", "Account:acme"))])
    assert (await recovery.finish()).complete
    original = graph.upsert_edges
    failures = 1

    async def unavailable_once(edges):
        nonlocal failures
        if failures:
            failures -= 1
            raise UnavailableError("injected old post-capture write failure")
        return await original(edges)

    graph.upsert_edges = unavailable_once
    if replay:
        data["pack"]["version"] = "1.1.0"
        data["projection"][1]["edges"][0]["set"] = {"note": "new effect"}
        updated = PackProjector(
            OntologyRegistry([CORE, Pack.model_validate(data)]),
            frozenset({"webhook:crm"}) if backend.startswith("ordered_") else frozenset(),
        )
        for _ in range(2):
            replayed = await replay_event_types(
                log, graph, updated, {"crm.contact.added"}, batch_size=1, lookup_limit=100
            )
        assert not replayed.failed and replayed.relationships_complete
        field, expected = "note", "new effect"
    else:
        for _ in range(2):
            with suppress(UnavailableError):
                await apply_plan(graph, plans[2], 100, recovery=recovery)
        field, expected = "b", "three"
    rows = await graph.neighbors(
        [NodeRef("Contact", "Contact:ann@example.test")], ["WORKS_AT"], "out", 10
    )
    assert rows[0]["properties"].get(field) == expected
    assert (
        await RelationshipRecovery(graph, log, updated if replay else planner).finish()
    ).complete


@pytest.mark.parametrize(
    "backend", ["memory", "spanner_fake", "ordered_memory", "ordered_spanner_fake"]
)
@pytest.mark.parametrize("stage", ["before_commit", "lost_reply"])
async def test_tracked_native_patch_and_completion_are_one_retriable_unit(backend, stage):
    _data, planner, log, graph, plans = await recovery_patch_inputs(backend)
    recovery = RelationshipRecovery(graph, log, planner)
    await apply_plan(graph, plans[0], 100, recovery=recovery)
    await graph.upsert_nodes([NodeWrite(NodeRef("Account", "Account:acme"))])
    assert (await recovery.finish()).complete
    original = graph.settle_relationship_intent
    failed = False

    async def stop_once(key, generation, status, edge=None):
        nonlocal failed
        if edge is not None and not failed:
            failed = True
            if stage == "before_commit":
                raise UnavailableError("stop before native patch")
            await original(key, generation, status, edge)
            raise UnavailableError("committed patch reply lost")
        return await original(key, generation, status, edge)

    graph.settle_relationship_intent = stop_once
    with pytest.raises(UnavailableError):
        await apply_plan(graph, plans[2], 100, recovery=recovery)
    if stage == "before_commit":
        rows = await graph.relationship_intents(None, 100)
        assert any(row["status"] not in {"recovered", "existing_relationship_kept"} for row in rows)
    await apply_plan(graph, plans[2], 100, recovery=recovery)
    assert (await recovery.finish()).complete
    rows = await graph.neighbors(
        [NodeRef("Contact", "Contact:ann@example.test")], ["WORKS_AT"], "out", 10
    )
    assert rows[0]["properties"]["a"] == "one" and rows[0]["properties"]["b"] == "three"


async def test_spanner_buffered_patch_failure_rolls_back_both_edge_and_terminal_status():
    _data, planner, log, graph, plans = await recovery_patch_inputs("spanner_fake")
    recovery = RelationshipRecovery(graph, log, planner)
    await apply_plan(graph, plans[0], 100, recovery=recovery)
    await graph.upsert_nodes([NodeWrite(NodeRef("Account", "Account:acme"))])
    assert (await recovery.finish()).complete
    database = graph._database  # Native fake fault injection, not the behavior assertion seam.
    original = database.run_in_transaction
    failed = False

    def fail_buffered(callback):
        def fault(transaction):
            nonlocal failed
            result = callback(transaction)
            if not failed and transaction.tables["GraphEdges"] != database.tables["GraphEdges"]:
                failed = True
                raise UnavailableError("transaction lost before commit")
            return result

        return original(fault)

    database.run_in_transaction = fail_buffered
    with pytest.raises(UnavailableError):
        await apply_plan(graph, plans[2], 100, recovery=recovery)
    ref = NodeRef("Contact", "Contact:ann@example.test")
    assert "b" not in (await graph.neighbors([ref], ["WORKS_AT"], "out", 10))[0]["properties"]
    assert not all(
        row["status"] in {"recovered", "existing_relationship_kept"}
        for row in await graph.relationship_intents(None, 100)
    )
    await apply_plan(graph, plans[2], 100, recovery=recovery)
    assert (await recovery.finish()).complete
    assert (await graph.neighbors([ref], ["WORKS_AT"], "out", 10))[0]["properties"]["b"] == "three"
