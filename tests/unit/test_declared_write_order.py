"""Business ordering at the validated-pack/planner/writer/stored-graph seam."""

from copy import deepcopy

import pytest

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.domain.ontology import OntologyRegistry, Pack
from context_graph.domain.pack_projection import PackProjector
from context_graph.ports.pack_graph import NodeRef
from context_graph.worker.pack_projection import apply_plan
from tests.unit.test_pack_versioning import CORE, _event

PACK = {
    "pack": {"name": "orderlab", "version": "1.0.0", "requires": ["core>=1.1"]},
    "types": {
        "nodes": {
            "Payment": {
                "key": ["id"],
                "interfaces": ["Lifecycled"],
                "properties": {"id": "string", "description": "string", "amount": "int"},
                "ordering": {"source": "webhook:payments", "by": "$.sequence", "kind": "sequence"},
                "lifecycle": {"initial": "pending", "states": ["pending", "succeeded"]},
            },
            "Account": {"key": ["id"], "properties": {"id": "string"}},
        },
        "edges": {
            "POSTED_TO": {
                "from": ["Payment"],
                "to": ["Account"],
                "properties": {"description": "string"},
            }
        },
    },
    "events": {"orderlab.payment.updated": {}},
    "projection": [
        {
            "event": "orderlab.payment.updated",
            "upsert": [
                {
                    "type": "Payment",
                    "key": {"id": "$.id"},
                    "set": {"description": "$.description", "amount": "$.amount"},
                }
            ],
            "transition": {"type": "Payment", "to": "$.state"},
            "edges": [
                {
                    "type": "POSTED_TO",
                    "from": {"type": "Payment", "key": {"id": "$.id"}},
                    "to": {"type": "Account", "key": {"id": "$.account"}},
                    "set": {"description": "$.description"},
                }
            ],
        }
    ],
}


def projector(data=None):
    return PackProjector(
        OntologyRegistry([CORE, Pack.model_validate(data or deepcopy(PACK))]),
        frozenset({"webhook:payments"}),
    )


def inputs():
    records = []
    for sequence, description, state in [(1, "older", "pending"), (2, "newer", "succeeded")]:
        event, payload = _event(
            "orderlab.payment.updated",
            {
                "id": "P1",
                "account": "A1",
                "description": description,
                "state": state,
                "sequence": sequence,
            },
            sequence,
        )
        event = event.model_copy(
            update={"agent_id": "webhook:payments", "global_position": f"{sequence}-0"}
        )
        records.append((event, {**event.model_dump(mode="json"), "payload": payload}))
    return records


@pytest.mark.parametrize("backend", ["memory", "spanner_transaction_fake"])
@pytest.mark.parametrize("order", [(0, 1), (1, 0), (0, 1, 0)])
async def test_delayed_payment_and_original_retry_cannot_undo_newer_record_state_or_link(
    order, backend
):
    if backend == "spanner_transaction_fake":
        from tests.unit.test_relationship_recovery_spanner import setup

        _database, graph = setup()
    else:
        graph = MemoryGraphStore()
    planner = projector()
    records = inputs()
    for index in order:
        event, document = records[index]
        await apply_plan(graph, planner.plan(event, document), 100)
    ref = NodeRef("Payment", "Payment:P1")
    stored = (await graph.get_nodes([ref]))[ref]
    assert stored["description"] == "newer"
    assert stored["status"] == "succeeded"
    links = await graph.neighbors([ref], ["POSTED_TO"], "out", 10)
    assert links[0]["properties"]["description"] == "newer"


async def test_a_late_partial_patch_fills_unwritten_fields_without_regressing_newer_fields():
    graph, planner = MemoryGraphStore(), projector()
    older, newer = inputs()
    newer[1]["payload"].pop("description")
    newer[1]["payload"]["amount"] = 200
    for event, document in [newer, older]:
        await apply_plan(graph, planner.plan(event, document), 100)
    ref = NodeRef("Payment", "Payment:P1")
    stored = (await graph.get_nodes([ref]))[ref]
    assert stored["description"] == "older"
    assert stored["amount"] == 200 and stored["status"] == "succeeded"
    assert stored["updated_at"] == newer[0].occurred_at.isoformat()


@pytest.mark.parametrize("value", [None, "", True, -1, 1.5, "2", 2**63])
def test_missing_or_invalid_declared_sequence_is_not_replaced_with_arrival_time(value):
    event, document = inputs()[0]
    document["payload"]["sequence"] = value
    with pytest.raises(ValueError, match="write_order_requires_nonnegative_int64_sequence"):
        projector().plan(event, document)


async def test_a_different_event_at_equal_authority_is_refused_without_changing_records():
    from uuid import uuid4

    graph, planner = MemoryGraphStore(), projector()
    event, document = inputs()[1]
    await apply_plan(graph, planner.plan(event, document), 100)
    ref = NodeRef("Payment", "Payment:P1")
    before = await graph.get_nodes([ref])
    other = event.model_copy(update={"event_id": uuid4()})
    other_document = {
        **other.model_dump(mode="json"),
        "payload": {**document["payload"], "description": "conflicting"},
    }
    with pytest.raises(ValueError, match="write_order_equal_authority_conflict"):
        await apply_plan(graph, planner.plan(other, other_document), 100)
    assert await graph.get_nodes([ref]) == before


async def test_a_guarded_transition_duplicate_does_not_fail_after_its_first_success():
    data = deepcopy(PACK)
    data["projection"][0]["transition"]["only_from"] = ["pending"]
    planner, graph = projector(data), MemoryGraphStore()
    older, newer = inputs()
    # An already-created payment with a newer transition retried remains idempotent.
    await apply_plan(graph, planner.plan(*older), 100)
    await apply_plan(graph, planner.plan(*newer), 100)
    await apply_plan(graph, planner.plan(*newer), 100)
    ref = NodeRef("Payment", "Payment:P1")
    assert (await graph.get_nodes([ref]))[ref]["status"] == "succeeded"


async def test_guarded_transition_refuses_missing_predecessor_and_succeeds_on_explicit_retry():
    from uuid import uuid4

    data = deepcopy(PACK)
    data["types"]["nodes"]["Payment"]["lifecycle"]["states"].append("authorized")
    data["projection"][0]["transition"]["only_from"] = ["authorized"]
    prior_rule = deepcopy(data["projection"][0])
    prior_rule["event"] = "orderlab.payment.authorized"
    prior_rule["transition"]["only_from"] = ["pending"]
    data["events"]["orderlab.payment.authorized"] = {}
    data["projection"].append(prior_rule)
    planner, graph = projector(data), MemoryGraphStore()
    older, newer = inputs()
    before_event = older[0].model_copy(
        update={"event_type": "orderlab.payment.authorized", "event_id": uuid4()}
    )
    before_document = {
        **before_event.model_dump(mode="json"),
        "payload": {**older[1]["payload"], "state": "authorized"},
    }
    with pytest.raises(ValueError, match="write_order_state_prerequisite_missing"):
        await apply_plan(graph, planner.plan(*newer), 100)
    ref = NodeRef("Payment", "Payment:P1")
    assert await graph.get_nodes([ref]) == {}
    await apply_plan(graph, planner.plan(before_event, before_document), 100)
    await apply_plan(graph, planner.plan(*newer), 100)
    assert (await graph.get_nodes([ref]))[ref]["status"] == "succeeded"


def test_enabling_or_changing_order_policy_requires_explicit_rebuild():
    from context_graph.domain.pack_versioning import classify_change

    data = deepcopy(PACK)
    data["types"]["nodes"]["Payment"].pop("ordering")
    old = projector(data).registry
    changed = deepcopy(PACK)
    changed["pack"]["version"] = "1.1.0"
    change = classify_change(old, projector(changed).registry)
    assert change.kind == "breaking"
    assert any("ordering" in reason for reason in change.reasons)
    assert change.version_problems


@pytest.mark.parametrize("delivery", [(0, 1), (1, 0), (0, 1, 0)])
async def test_required_deferred_link_uses_business_order_and_allows_a_later_update(delivery):
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.ontology.rebuild import rebuild
    from context_graph.settings import Settings

    data = deepcopy(PACK)
    edge = data["projection"][0]["edges"][0]
    edge["to"] = {"node_id": "$.account_node_id"}
    edge["required"] = True
    data["events"]["orderlab.account.created"] = {}
    data["projection"].append(
        {
            "event": "orderlab.account.created",
            "upsert": [{"type": "Account", "key": {"id": "$.id"}}],
        }
    )
    planner, graph, log = projector(data), MemoryGraphStore(), MemoryEventLog()
    records = inputs()
    for index in delivery:
        event, document = records[index]
        payload = {**document["payload"], "account_node_id": "Account:A1"}
        await log.append(event, payload)
    account, payload = _event("orderlab.account.created", {"id": "A1"}, 3)
    await log.append(account, payload)
    settings = Settings()
    settings.consumer.projection_batch_size = 1
    settings.ontology.replay_batch_size = 1
    report = await rebuild(log, graph, planner, settings, eval_dirs=[], skip_gate=True)
    assert report.projection_complete
    ref = NodeRef("Payment", "Payment:P1")
    rows = await graph.neighbors([ref], ["POSTED_TO"], "out", 10)
    assert rows[0]["properties"]["description"] == "newer"
    event, document = inputs()[1]
    from uuid import uuid4

    event = event.model_copy(update={"event_id": uuid4(), "global_position": "4-0"})
    document = {
        **event.model_dump(mode="json"),
        "payload": {
            **document["payload"],
            "sequence": 3,
            "description": "latest",
            "account_node_id": "Account:A1",
        },
    }
    await apply_plan(graph, planner.plan(event, document), 100)
    rows = await graph.neighbors([ref], ["POSTED_TO"], "out", 10)
    assert rows[0]["properties"]["description"] == "latest"


async def test_spanner_transaction_fake_recovery_commits_edge_clock_and_later_write():
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.ports.pack_graph import NodeWrite
    from context_graph.worker.relationship_recovery import RelationshipRecovery
    from tests.unit.test_relationship_recovery_spanner import setup

    _db, graph = setup()
    data = deepcopy(PACK)
    data["projection"][0]["edges"][0].update(to={"node_id": "$.account_node_id"}, required=True)
    planner, log = projector(data), MemoryEventLog()
    recovery = RelationshipRecovery(graph, log, planner)
    event, document = inputs()[1]
    payload = {**document["payload"], "account_node_id": "Account:A1"}
    position = await log.append(event, payload)
    document = (await log.get_documents([str(event.event_id)]))[0]
    await apply_plan(
        graph,
        planner.plan(event.model_copy(update={"global_position": position}), document),
        100,
        recovery=recovery,
    )
    await graph.upsert_nodes([NodeWrite(NodeRef("Account", "Account:A1"))])
    assert (await recovery.finish()).complete
    from uuid import uuid4

    event = event.model_copy(update={"event_id": uuid4(), "global_position": "3-0"})
    document = {
        **event.model_dump(mode="json"),
        "payload": {**payload, "sequence": 3, "description": "latest"},
    }
    await apply_plan(graph, planner.plan(event, document), 100)
    rows = await graph.neighbors([NodeRef("Payment", "Payment:P1")], ["POSTED_TO"], "out", 10)
    assert rows[0]["properties"]["description"] == "latest"


@pytest.mark.parametrize(
    "source,agent,allowed",
    [
        ("payments-producer", "arbitrary-display-agent", True),
        ("other", "webhook:payments", False),
    ],
)
def test_ordering_uses_authenticated_producer_not_claimed_agent(tmp_path, source, agent, allowed):
    import yaml

    from context_graph.domain.event_acceptance import stamp_acceptance
    from context_graph.domain.source_trust import SourceTrustPolicy, VerifiedSourceProvenance
    from tests.unit.test_event_acceptance import context
    from tests.unit.test_tenant_catalog import bind, configuration

    data = deepcopy(PACK)
    data["types"]["nodes"]["Payment"]["ordering"]["source"] = "payments-producer"
    path = tmp_path / "orderlab.pack.yaml"
    path.write_text(yaml.safe_dump(data))
    settings = configuration()
    settings.ontology.packs = ["orderlab"]
    settings.ontology.pack_dirs = [str(tmp_path)]
    settings.ontology.trusted_source_ids = ["payments-producer"]
    bound = bind(settings=settings)
    planner = PackProjector(
        bound.bundle.registry,
        frozenset({"webhook:payments"}),
        source_policy=SourceTrustPolicy.from_binding(bound),
    )
    event, document = inputs()[0]
    event = event.model_copy(update={"agent_id": agent})
    document = {**event.model_dump(mode="json"), "payload": document["payload"]}
    receipt = stamp_acceptance(context(bound, source=source), event, document["payload"])
    provenance = VerifiedSourceProvenance(str(event.event_id), receipt)
    if allowed:
        assert planner.plan(event, document, provenance=provenance).nodes
    else:
        with pytest.raises(ValueError, match="write_order_untrusted_or_competing_source"):
            planner.plan(event, document, provenance=provenance)


@pytest.mark.parametrize(
    "newer_stamp,older_stamp",
    [
        ("2026-11-28T10:00:00Z", "2026-11-28T09:00:00Z"),
        ("2026-11-28T10:00:00+00:00", "2026-11-28T14:00:00+05:30"),
    ],
)
async def test_declared_timestamp_compares_normalized_instants(newer_stamp, older_stamp):
    data = deepcopy(PACK)
    data["types"]["nodes"]["Payment"]["ordering"].update(kind="timestamp", by="$.changed_at")
    planner, graph = projector(data), MemoryGraphStore()
    older, newer = inputs()
    older[1]["payload"]["changed_at"] = older_stamp
    newer[1]["payload"]["changed_at"] = newer_stamp
    for event, document in [newer, older]:
        await apply_plan(graph, planner.plan(event, document), 100)
    ref = NodeRef("Payment", "Payment:P1")
    assert (await graph.get_nodes([ref]))[ref]["description"] == "newer"


@pytest.mark.parametrize(
    "value", ["2026-11-28T10:00:00", "yesterday", "2026-11-28T10:00:00.1234567Z"]
)
def test_invalid_timestamp_has_no_arrival_clock_fallback(value):
    data = deepcopy(PACK)
    data["types"]["nodes"]["Payment"]["ordering"].update(kind="timestamp", by="$.changed_at")
    event, document = inputs()[0]
    document["payload"]["changed_at"] = value
    with pytest.raises(ValueError, match="write_order_"):
        projector(data).plan(event, document)


async def test_explicit_newer_clear_is_not_undone_by_a_late_original_value():
    data = deepcopy(PACK)
    data["processing"] = {"requires": ["pack.properties.v1"]}
    clear_rule = deepcopy(data["projection"][0])
    clear_rule["event"] = "orderlab.payment.cleared"
    clear_rule["upsert"][0]["set"]["description"] = {"value": None, "on_null": "clear"}
    clear_rule["edges"][0]["set"]["description"] = {"value": None, "on_null": "clear"}
    data["projection"].append(clear_rule)
    data["events"]["orderlab.payment.cleared"] = {}
    planner, graph = projector(data), MemoryGraphStore()
    older, newer = inputs()
    from uuid import uuid4

    event = newer[0].model_copy(
        update={"event_type": "orderlab.payment.cleared", "event_id": uuid4()}
    )
    document = {**event.model_dump(mode="json"), "payload": newer[1]["payload"]}
    await apply_plan(graph, planner.plan(event, document), 100)
    await apply_plan(graph, planner.plan(*older), 100)
    ref = NodeRef("Payment", "Payment:P1")
    assert "description" not in (await graph.get_nodes([ref]))[ref]
    rows = await graph.neighbors([ref], ["POSTED_TO"], "out", 10)
    assert "description" not in rows[0]["properties"]


async def test_new_planner_after_partial_write_failure_cannot_regress_committed_node_fields():
    class FailEdgeOnce(MemoryGraphStore):
        fail = True

        async def apply_ordered_mutations(self, nodes, states, edges, **kwargs):
            if edges and self.fail:
                self.fail = False
                raise RuntimeError("simulated stop after node commit")
            return await super().apply_ordered_mutations(nodes, states, edges, **kwargs)

    graph, planner = FailEdgeOnce(), projector()
    older, newer = inputs()
    with pytest.raises(RuntimeError, match="simulated stop"):
        await apply_plan(graph, planner.plan(*newer), 100)
    restarted = projector()
    await apply_plan(graph, restarted.plan(*older), 100)
    await apply_plan(graph, restarted.plan(*newer), 100)
    ref = NodeRef("Payment", "Payment:P1")
    assert (await graph.get_nodes([ref]))[ref]["description"] == "newer"
    assert (await graph.neighbors([ref], ["POSTED_TO"], "out", 10))[0]["properties"][
        "description"
    ] == "newer"


async def test_enabling_ordering_over_existing_unclocked_data_refuses_before_changing_it():
    from context_graph.ports.pack_graph import NodeWrite

    graph = MemoryGraphStore()
    ref = NodeRef("Payment", "Payment:P1")
    await graph.upsert_nodes([NodeWrite(ref, {"description": "historical interpretation"})])
    before = await graph.get_nodes([ref])
    with pytest.raises(ValueError, match="write_order_existing_data_needs_explicit_rebuild"):
        await apply_plan(graph, projector().plan(*inputs()[1]), 100)
    assert await graph.get_nodes([ref]) == before


async def test_declared_order_is_independent_for_each_record_and_accepts_zero():
    graph, planner = MemoryGraphStore(), projector()
    event, document = inputs()[1]
    await apply_plan(graph, planner.plan(event, document), 100)
    from uuid import uuid4

    event = event.model_copy(update={"event_id": uuid4()})
    document = {
        **event.model_dump(mode="json"),
        "payload": {
            **document["payload"],
            "id": "P2",
            "sequence": 0,
            "description": "zero is valid",
        },
    }
    await apply_plan(graph, planner.plan(event, document), 100)
    ref = NodeRef("Payment", "Payment:P2")
    assert (await graph.get_nodes([ref]))[ref]["description"] == "zero is valid"


@pytest.mark.parametrize("policy_change", ["source", "by", "kind", "remove"])
def test_every_ordering_policy_amendment_requires_rebuild(policy_change):
    from context_graph.domain.pack_versioning import classify_change

    changed = deepcopy(PACK)
    changed["pack"]["version"] = "2.0.0"
    definition = changed["types"]["nodes"]["Payment"]
    if policy_change == "remove":
        definition.pop("ordering")
    else:
        definition["ordering"][policy_change] = {
            "source": "other-producer",
            "by": "$.new_sequence",
            "kind": "timestamp",
        }[policy_change]
    result = classify_change(projector().registry, projector(changed).registry)
    assert result.kind == "breaking" and not result.version_problems


@pytest.mark.parametrize("batch_order", [(0, 1), (1, 0), (0, 1, 0)])
async def test_flushing_a_batch_preserves_the_same_protected_final_values(batch_order):
    from context_graph.worker.pack_projection import apply_plans

    graph, planner = MemoryGraphStore(), projector()
    records = inputs()
    await apply_plans(graph, [planner.plan(*records[index]) for index in batch_order], 100)
    ref = NodeRef("Payment", "Payment:P1")
    stored = (await graph.get_nodes([ref]))[ref]
    assert stored["description"] == "newer" and stored["status"] == "succeeded"
    assert (await graph.neighbors([ref], ["POSTED_TO"], "out", 10))[0]["properties"][
        "description"
    ] == "newer"


async def test_two_effects_in_one_event_and_its_retry_keep_the_declared_effect_order():
    data = deepcopy(PACK)
    another = deepcopy(data["projection"][0]["upsert"][0])
    another["set"]["description"] = "last declared effect"
    data["projection"][0]["upsert"].append(another)
    planner, graph = projector(data), MemoryGraphStore()
    record = inputs()[1]
    for _ in range(2):
        await apply_plan(graph, planner.plan(*record), 100)
    ref = NodeRef("Payment", "Payment:P1")
    assert (await graph.get_nodes([ref]))[ref]["description"] == "last declared effect"


async def test_explicit_mapping_replay_can_reinterpret_equal_original_order_under_new_bundle():
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.ontology.versioning import replay_event_types
    from context_graph.ports.pack_graph import NodeWrite

    graph, log, planner = MemoryGraphStore(), MemoryEventLog(), projector()
    await graph.upsert_nodes([NodeWrite(NodeRef("Account", "Account:A1"))])
    event, document = inputs()[1]
    position = await log.append(event, document["payload"])
    event = event.model_copy(update={"global_position": position})
    document = (await log.get_documents([str(event.event_id)]))[0]
    await apply_plan(graph, planner.plan(event, document), 100)
    data = deepcopy(PACK)
    data["pack"]["version"] = "1.1.0"
    data["projection"][0]["upsert"][0]["set"]["description"] = "reinterpreted rule"
    data["projection"][0]["edges"][0]["set"]["description"] = "reinterpreted link"
    updated = projector(data)
    with pytest.raises(ValueError, match="write_order_changed_effect_without_explicit_replay"):
        await apply_plan(graph, updated.plan(event, document), 100)
    report = await replay_event_types(
        log, graph, updated, {"orderlab.payment.updated"}, batch_size=1, lookup_limit=100
    )
    assert not report.failed and report.relationships_complete
    ref = NodeRef("Payment", "Payment:P1")
    assert (await graph.get_nodes([ref]))[ref]["description"] == "reinterpreted rule"
    assert (await graph.neighbors([ref], ["POSTED_TO"], "out", 10))[0]["properties"][
        "description"
    ] == "reinterpreted link"


@pytest.mark.parametrize("backend", ["memory", "spanner_transaction_fake"])
async def test_a_conflict_rolls_back_other_records_in_the_same_ordered_unit(backend):
    if backend == "memory":
        graph = MemoryGraphStore()
    else:
        from tests.unit.test_relationship_recovery_spanner import setup

        _database, graph = setup()
    planner = projector()
    event, document = inputs()[1]
    await apply_plan(graph, planner.plan(event, document), 100)
    ref = NodeRef("Payment", "Payment:P1")
    before = await graph.get_nodes([ref])
    from uuid import uuid4

    event = event.model_copy(update={"event_id": uuid4()})
    document = {
        **event.model_dump(mode="json"),
        "payload": {**document["payload"], "id": ["P2", "P1"], "description": "conflicting"},
    }
    with pytest.raises(ValueError, match="write_order_equal_authority_conflict"):
        await apply_plan(graph, planner.plan(event, document), 100)
    assert await graph.get_nodes([ref]) == before
    assert await graph.get_nodes([NodeRef("Payment", "Payment:P2")]) == {}


async def test_ordered_lookup_after_exact_effect_keeps_the_normal_effect_precedence():
    data = deepcopy(PACK)
    another = deepcopy(data["projection"][0]["edges"][0])
    another["to"] = {"type": "Account", "match": {"id": "$.account"}}
    another["set"] = {"description": "last lookup effect"}
    data["projection"][0]["edges"].append(another)
    graph, planner = MemoryGraphStore(), projector(data)
    await apply_plan(graph, planner.plan(*inputs()[1]), 100)
    rows = await graph.neighbors([NodeRef("Payment", "Payment:P1")], ["POSTED_TO"], "out", 10)
    assert rows[0]["properties"]["description"] == "last lookup effect"


async def test_spanner_ordered_port_keeps_the_tenant_fence_on_clock_and_record_writes():
    from context_graph.adapters.spanner.tenant_control import TenantFenceError
    from tests.unit.test_relationship_recovery_spanner import setup

    database, graph = setup()
    planner = projector()
    older, newer = inputs()
    await apply_plan(graph, planner.plan(*older), 100)
    ref = NodeRef("Payment", "Payment:P1")
    before = await graph.get_nodes([ref])
    database.owner[3] += 1
    with pytest.raises(TenantFenceError):
        await apply_plan(graph, planner.plan(*newer), 100)
    database.owner[3] -= 1
    assert await graph.get_nodes([ref]) == before
    await apply_plan(graph, planner.plan(*newer), 100)
    assert (await graph.get_nodes([ref]))[ref]["description"] == "newer"


async def test_a_distinct_newer_same_state_event_advances_protection_without_failing_its_guard():
    from uuid import uuid4

    data = deepcopy(PACK)
    data["projection"][0]["transition"]["only_from"] = ["pending"]
    planner, graph = projector(data), MemoryGraphStore()
    older, newer = inputs()
    await apply_plan(graph, planner.plan(*older), 100)
    await apply_plan(graph, planner.plan(*newer), 100)
    event = newer[0].model_copy(update={"event_id": uuid4()})
    document = {**event.model_dump(mode="json"), "payload": {**newer[1]["payload"], "sequence": 3}}
    await apply_plan(graph, planner.plan(event, document), 100)
    await apply_plan(graph, planner.plan(*older), 100)
    ref = NodeRef("Payment", "Payment:P1")
    stored = (await graph.get_nodes([ref]))[ref]
    assert stored["status"] == "succeeded"
    assert stored["status_changed_at"] == newer[0].occurred_at.isoformat()


@pytest.mark.parametrize("backend", ["memory", "spanner_transaction_fake"])
async def test_conflicting_old_sequence_is_detected_after_all_its_original_fields_were_superseded(
    backend,
):
    from uuid import uuid4

    if backend == "memory":
        graph = MemoryGraphStore()
    else:
        from tests.unit.test_relationship_recovery_spanner import setup

        _database, graph = setup()
    planner = projector()
    older, newer = inputs()
    await apply_plan(graph, planner.plan(*older), 100)
    await apply_plan(graph, planner.plan(*newer), 100)
    event = older[0].model_copy(update={"event_id": uuid4()})
    payload = {**older[1]["payload"], "amount": 999}
    payload.pop("description")
    document = {**event.model_dump(mode="json"), "payload": payload}
    with pytest.raises(ValueError, match="write_order_equal_authority_conflict"):
        await apply_plan(graph, planner.plan(event, document), 100)
    ref = NodeRef("Payment", "Payment:P1")
    assert "amount" not in (await graph.get_nodes([ref]))[ref]


@pytest.mark.parametrize("backend", ["memory", "spanner_transaction_fake"])
@pytest.mark.parametrize("multiple_effects", [False, True])
async def test_additive_bundle_change_keeps_exact_original_retry_a_noop(backend, multiple_effects):
    from context_graph.domain.pack_versioning import classify_change

    if backend == "memory":
        graph = MemoryGraphStore()
    else:
        from tests.unit.test_relationship_recovery_spanner import setup

        _database, graph = setup()
    original = deepcopy(PACK)
    if multiple_effects:
        additional = deepcopy(original["projection"][0]["upsert"][0])
        additional["set"]["description"] = "last declared effect"
        original["projection"][0]["upsert"].append(additional)
    planner = projector(original)
    event, document = inputs()[1]
    await apply_plan(graph, planner.plan(event, document), 100)
    refs = [NodeRef("Payment", "Payment:P1"), NodeRef("Account", "Account:A1")]
    before = await graph.get_nodes(refs)
    links = await graph.neighbors(refs[:1], ["POSTED_TO"], "out", 10)
    changed = deepcopy(original)
    changed["pack"]["version"] = "1.1.0"
    changed["types"]["nodes"]["Account"]["properties"]["unrelated"] = "string"
    updated = projector(changed)
    difference = classify_change(planner.registry, updated.registry)
    assert difference.kind == "additive" and not difference.version_problems
    assert await apply_plan(graph, updated.plan(event, document), 100) == 0
    assert await graph.get_nodes(refs) == before
    assert await graph.neighbors(refs[:1], ["POSTED_TO"], "out", 10) == links


@pytest.mark.parametrize("backend", ["memory", "spanner_transaction_fake"])
async def test_shifted_ordinal_does_not_allow_a_changed_mapping_without_replay(backend):
    if backend == "memory":
        graph = MemoryGraphStore()
    else:
        from tests.unit.test_relationship_recovery_spanner import setup

        _database, graph = setup()
    original = deepcopy(PACK)
    original["projection"][0].pop("transition")
    planner = projector(original)
    record = inputs()[1]
    await apply_plan(graph, planner.plan(*record), 100)
    changed = deepcopy(original)
    changed["pack"]["version"] = "1.1.0"
    changed["projection"][0]["upsert"].insert(0, {"type": "Account", "key": {"id": "$.account"}})
    changed["projection"][0]["upsert"][1]["set"]["description"] = "reinterpreted rule"
    with pytest.raises(ValueError, match="write_order_changed_effect_without_explicit_replay"):
        await apply_plan(graph, projector(changed).plan(*record), 100)
    ref = NodeRef("Payment", "Payment:P1")
    assert (await graph.get_nodes([ref]))[ref]["description"] == "newer"


@pytest.mark.parametrize("target", ["Payment", "POSTED_TO"])
def test_extraction_cannot_bypass_the_declared_owner_ordering(target):
    from context_graph.domain.ontology import OntologyError

    data = deepcopy(PACK)
    data["extraction"] = {"propose": {target: {"description": "Candidate domain record or link"}}}
    with pytest.raises(OntologyError, match="ordered_extraction_target_unsupported"):
        projector(data)


@pytest.mark.parametrize("value", ["2026-01-01T00:00:00,1234567Z", "2026-01-01T00:00:00,1234568Z"])
def test_comma_fraction_does_not_bypass_the_authority_precision_limit(value):
    data = deepcopy(PACK)
    data["types"]["nodes"]["Payment"]["ordering"].update(kind="timestamp", by="$.changed_at")
    event, document = inputs()[0]
    document["payload"]["changed_at"] = value
    with pytest.raises(ValueError, match="write_order_timestamp_precision_exceeds_microseconds"):
        projector(data).plan(event, document)


@pytest.mark.parametrize("missing", ["node", "edge"])
async def test_surviving_clock_never_certifies_a_deleted_protected_record(missing):
    from tests.unit.test_relationship_recovery_spanner import setup

    database, graph = setup()
    planner = projector()
    record = inputs()[1]
    await apply_plan(graph, planner.plan(*record), 100)
    # Infrastructure fault injection only, in the native adapter's transaction fake.
    # Behavior is verified through the public writer/read ports after the loss.
    if missing == "node":
        database.tables["GraphNodes"].pop(("Payment", "Payment:P1"))
    else:
        database.tables["GraphEdges"].pop(
            ("Payment", "Payment:P1", "POSTED_TO", "Account", "Account:A1")
        )
    with pytest.raises(ValueError, match=f"write_order_{missing}_missing_but_clock_survives"):
        await apply_plan(graph, planner.plan(*record), 100)
    ref = NodeRef("Payment", "Payment:P1")
    if missing == "node":
        assert await graph.get_nodes([ref]) == {}
    else:
        assert await graph.neighbors([ref], ["POSTED_TO"], "out", 10) == []


async def test_an_additive_bump_can_retry_and_recover_an_identical_pending_ordered_link():
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.ports.pack_graph import NodeWrite
    from context_graph.worker.relationship_recovery import RelationshipRecovery

    original = deepcopy(PACK)
    original["projection"][0]["edges"][0].update(to={"node_id": "$.account_node_id"}, required=True)
    planner, graph, log = projector(original), MemoryGraphStore(), MemoryEventLog()
    event, document = inputs()[1]
    payload = {**document["payload"], "account_node_id": "Account:A1"}
    position = await log.append(event, payload)
    event = event.model_copy(update={"global_position": position})
    document = (await log.get_documents([str(event.event_id)]))[0]
    await apply_plan(
        graph,
        planner.plan(event, document),
        100,
        recovery=RelationshipRecovery(graph, log, planner),
    )
    assert not (await RelationshipRecovery(graph, log, planner).finish()).complete
    changed = deepcopy(original)
    changed["pack"]["version"] = "1.1.0"
    changed["types"]["nodes"]["Account"]["properties"]["unrelated"] = "string"
    updated = projector(changed)
    recovery = RelationshipRecovery(graph, log, updated)
    await apply_plan(graph, updated.plan(event, document), 100, recovery=recovery)
    await graph.upsert_nodes([NodeWrite(NodeRef("Account", "Account:A1"))])
    assert (await recovery.finish()).complete
    rows = await graph.neighbors([NodeRef("Payment", "Payment:P1")], ["POSTED_TO"], "out", 10)
    assert rows[0]["properties"]["description"] == "newer"


@pytest.mark.parametrize("backend", ["memory", "spanner_transaction_fake"])
async def test_missing_optional_endpoint_does_not_record_a_completed_edge_receipt(backend):
    from context_graph.ports.pack_graph import NodeWrite

    if backend == "memory":
        graph = MemoryGraphStore()
    else:
        from tests.unit.test_relationship_recovery_spanner import setup

        _database, graph = setup()
    data = deepcopy(PACK)
    data["projection"][0]["edges"][0]["to"] = {"node_id": "$.account_node_id"}
    planner = projector(data)
    event, document = inputs()[1]
    document["payload"]["account_node_id"] = "Account:A1"
    assert await apply_plan(graph, planner.plan(event, document), 100) == 0
    await graph.upsert_nodes([NodeWrite(NodeRef("Account", "Account:A1"))])
    assert await apply_plan(graph, planner.plan(event, document), 100) == 1
    rows = await graph.neighbors([NodeRef("Payment", "Payment:P1")], ["POSTED_TO"], "out", 10)
    assert rows[0]["properties"]["description"] == "newer"
