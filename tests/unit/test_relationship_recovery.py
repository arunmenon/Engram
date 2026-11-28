"""Required-link and exact-endpoint recovery at validated planner/worker/store seams."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from context_graph.domain.models import Event
from context_graph.domain.ontology import OntologyRegistry, Pack
from context_graph.domain.pack_projection import PackProjector
from context_graph.ontology import BUILTIN_PACK_DIR, load_pack_file

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
    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.ontology.rebuild import rebuild
    from context_graph.ports.pack_graph import NodeRef
    from context_graph.settings import Settings
    from tests.unit.test_pack_versioning import _event

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
    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.ontology.rebuild import rebuild
    from context_graph.ontology.versioning import read_state
    from context_graph.settings import Settings
    from tests.unit.test_pack_versioning import _event

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
    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.adapters.memory.subscription import MemorySubscription
    from context_graph.ontology.rebuild import project_ledger
    from context_graph.ports.pack_graph import EdgeWrite, NodeRef, NodeWrite
    from context_graph.settings import Settings
    from context_graph.worker.projection import ProjectionConsumer
    from tests.unit.test_pack_versioning import _event

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
    from context_graph.domain.ontology import OntologyError

    data = CRM.model_dump(by_alias=True)
    edge = data["projection"][1]["edges"][0]
    edge.pop("to")
    edge[form] = match
    edge["required"] = True
    with pytest.raises(OntologyError, match="required_relationship_needs_exact_identity"):
        OntologyRegistry([CORE, Pack.model_validate(data)])


def test_legacy_pack_digest_does_not_change_when_required_is_absent():
    import hashlib

    assert (
        hashlib.sha256(CRM.canonical_json().encode()).hexdigest()
        == "e4168338a7ecc35bafa7c6fda70dd85fe3ccdd639f59bc866cb78533f2ca2455"
    )


@pytest.mark.parametrize("value", [None, "", "not-a-valid-node-id"])
def test_invalid_required_endpoint_refuses_the_event_plan(value):
    from context_graph.domain.pack_projection import RequiredRelationshipError

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
    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.ontology.rebuild import project_ledger
    from context_graph.settings import Settings
    from tests.unit.test_pack_versioning import _event

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
    from context_graph.ports.pack_graph import NodeRef, NodeWrite
    from context_graph.ports.relationship_recovery import CURSOR_LABEL
    from context_graph.worker.relationship_recovery import RelationshipRecovery

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
    from context_graph.ports.pack_graph import NodeRef, NodeWrite
    from context_graph.worker.relationship_recovery import RelationshipRecovery

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
    from context_graph.ports.pack_graph import NodeRef, NodeWrite
    from context_graph.worker.relationship_recovery import RelationshipRecovery

    reg, log, graph = await pending_links()
    row = (await graph.relationship_intents(None, 100))[0]
    await graph.upsert_nodes([NodeWrite(NodeRef(**row["target"]))])
    assert (await log.expire(1))[1] == 1
    result = await RelationshipRecovery(graph, log, PackProjector(reg, frozenset())).finish()
    assert result.blocking == 1
    assert (await graph.relationship_intents(None, 100))[0]["status"] == "missing_source"
    assert await graph.neighbors([NodeRef(**row["source"])], ["WORKS_AT"], "out", 10) == []


async def test_recovery_does_not_claim_a_full_scan_when_the_budget_ends():
    from context_graph.worker.relationship_recovery import RelationshipRecovery

    reg, log, graph = await pending_links(3)
    result = await RelationshipRecovery(graph, log, PackProjector(reg, frozenset())).finish(
        budget=1, page_size=1
    )
    assert result.scanned == 1 and not result.complete_scan and not result.complete


@pytest.mark.parametrize("target_first", [False, True])
async def test_deferred_events_for_one_edge_keep_the_last_log_events_properties(target_first):
    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.ontology.rebuild import project_ledger
    from context_graph.ports.pack_graph import NodeRef
    from context_graph.settings import Settings
    from tests.unit.test_pack_versioning import _event

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
    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.ontology.rebuild import rebuild
    from context_graph.settings import Settings
    from tests.unit.test_pack_versioning import _event

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
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.ports.errors import RuntimeFencedError, UnavailableError
    from context_graph.worker.relationship_recovery import RelationshipRecovery

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
    import asyncio

    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.ports.pack_graph import NodeRef, NodeWrite
    from context_graph.worker.relationship_recovery import RelationshipRecovery

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
    from dataclasses import replace

    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.domain.event_acceptance import (
        AdmissionContext,
        EventInterpretation,
        stamp_acceptance,
    )
    from context_graph.domain.source_trust import (
        AcceptedRecord,
        SourceTrustPolicy,
        VerifiedSourceProvenance,
    )
    from context_graph.ports.pack_graph import NodeRef, NodeWrite
    from context_graph.worker.pack_projection import apply_plan
    from context_graph.worker.relationship_recovery import RelationshipRecovery
    from tests.unit.test_pack_versioning import _event

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
    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.ontology.rebuild import project_ledger
    from context_graph.ports.pack_graph import NodeRef, NodeWrite
    from context_graph.settings import Settings
    from context_graph.worker.relationship_recovery import RelationshipRecovery
    from tests.unit.test_pack_versioning import _event

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
    from context_graph.ports.pack_graph import NodeRef, NodeWrite
    from context_graph.worker.relationship_recovery import RelationshipRecovery

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
    from context_graph.adapters.memory.subscription import MemorySubscription
    from context_graph.ports.pack_graph import NodeRef, NodeWrite
    from context_graph.settings import Settings
    from context_graph.worker.projection import ProjectionConsumer

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
    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.ports.errors import UnavailableError
    from context_graph.ports.pack_graph import NodeRef, NodeWrite
    from context_graph.worker.relationship_recovery import RelationshipRecovery

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
    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.adapters.memory.subscription import MemorySubscription
    from context_graph.ports.errors import RuntimeFencedError
    from context_graph.ports.pack_graph import NodeRef, NodeWrite
    from context_graph.settings import Settings
    from context_graph.worker.projection import ProjectionConsumer
    from tests.unit.test_pack_versioning import _event

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
    from context_graph.domain.ontology import OntologyError

    data = CRM.model_dump(by_alias=True)
    data["types"]["nodes"][name] = {"key": ["id"], "properties": {"id": "string"}}
    with pytest.raises(OntologyError, match="reserved"):
        OntologyRegistry([CORE, Pack.model_validate(data)])


def test_required_key_lookup_uses_s4_complete_identity_operand_checks():
    from context_graph.domain.pack_expressions import IdentityOperandError

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
    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.ports.errors import RuntimeFencedError
    from context_graph.ports.pack_graph import NodeRef
    from context_graph.worker.pack_projection import apply_plan

    graph = MemoryGraphStore()
    plan = contact(registry())
    with pytest.raises(RuntimeFencedError, match="durable relationship recovery"):
        await apply_plan(graph, plan, 100)
    assert await graph.get_nodes([NodeRef("Contact", "Contact:ann@example.test")]) == {}
