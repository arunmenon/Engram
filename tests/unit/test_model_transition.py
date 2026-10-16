"""Model-only grants never relax ownership or immutable source evidence."""

import copy
from dataclasses import replace

import pytest

from context_graph.adapters.spanner.log import SpannerEventLog, json_value
from context_graph.adapters.spanner.subscription import SpannerSubscription
from context_graph.adapters.spanner.tenant_control import (
    TenantFence,
    TenantFenceError,
    activate_model_successor,
)
from context_graph.domain.event_acceptance import EventInterpretationError, stamp_acceptance
from context_graph.domain.source_trust import SourceTrustPolicy, VerifiedSourceProvenance
from context_graph.ports.errors import RuntimeFencedError
from context_graph.tenancy import TenantBinding, TenantConfigurationError
from tests.unit.test_event_acceptance import context, event
from tests.unit.test_spanner_terminal_disposition import setup
from tests.unit.test_tenant_catalog import bind


def successor(old):
    settings = old.settings()
    settings.llm.model_id = "successor-model"
    return TenantBinding.from_settings(
        old.tenant_id,
        old.binding_id,
        old.epoch + 1,
        settings,
        engine_revision=old.engine_revision,
        predecessor=old,
    )


def test_grant_is_pinned_and_exact_epoch_scoped():
    old = bind()
    new = successor(old)
    without_grant = replace(new, predecessor=None)
    assert new.bundle_digest != without_grant.bundle_digest
    receipt = stamp_acceptance(context(old), event(), {"content": "original"})
    receipt.require_interpretation(new.interpretation())
    with pytest.raises(EventInterpretationError):
        receipt.require_interpretation(without_grant.interpretation())
    with pytest.raises(EventInterpretationError):
        receipt.model_copy(update={"accepted_epoch": old.epoch + 1}).require_interpretation(
            new.interpretation()
        )
    with pytest.raises(EventInterpretationError):
        receipt.model_copy(update={"tenant_id": "foreign"}).require_interpretation(
            new.interpretation()
        )


@pytest.mark.parametrize(
    "change",
    [
        lambda s: setattr(s.llm, "temperature", 0.9),
        lambda s: setattr(s.retention, "hot_hours", s.retention.hot_hours + 1),
        lambda s: setattr(s.spanner, "database", "other"),
        lambda s: setattr(s.ontology, "trusted_source_ids", ["other"]),
    ],
)
def test_model_transition_rejects_unrelated_policy_changes(change):
    old = bind()
    s = old.settings()
    s.llm.model_id = "next-model"
    change(s)
    with pytest.raises(TenantConfigurationError):
        TenantBinding.from_settings(
            old.tenant_id,
            old.binding_id,
            old.epoch + 1,
            s,
            engine_revision=old.engine_revision,
            predecessor=old,
        )


def test_no_chaining_or_epoch_skip():
    old = bind()
    with pytest.raises(TenantConfigurationError):
        replace(successor(old), epoch=old.epoch + 2)
    with pytest.raises(TenantConfigurationError):
        successor(successor(old))


@pytest.mark.asyncio
async def test_successor_reads_and_acks_old_pending_without_rewriting_acceptance():
    old, db, old_log, old_sub, delivery, key = await setup()
    new = successor(old)
    original = copy.deepcopy(db.rows)
    db.owner = [new.tenant_id, db.name, new.binding_id, new.epoch, new.bundle_digest, "active"]
    kwargs = dict(
        tenant_fence=TenantFence.from_binding(new),
        tenant_engine_revision=new.engine_revision,
        tenant_binding=new,
    )
    log = SpannerEventLog(db, **kwargs)
    doc = await log.get_by_id(str(event().event_id))
    assert doc is not None
    acceptance = json_value(db.rows[str(event().event_id)]["acceptance"])
    policy = SourceTrustPolicy.from_binding(new)
    source_doc = log._validated_document(
        db.rows[str(event().event_id)]["document"],
        str(event().event_id),
        acceptance,
    )
    policy.trusted(
        event(),
        source_doc,
        VerifiedSourceProvenance(
            str(event().event_id),
            stamp_acceptance(context(old), event(), {"content": "original"}),
        ),
    )
    sub = SpannerSubscription(db, "group", "worker", **kwargs)
    await sub.ack(delivery.position)
    assert key not in db.pending
    assert db.rows == original
    with pytest.raises(RuntimeFencedError):
        await old_sub.ack(delivery.position)
    with pytest.raises(RuntimeFencedError):
        await old_log.get_by_id(str(event().event_id))


def test_cutover_cas_retry_and_stale_owner_rejection():
    old = bind()
    new = successor(old)

    class DB:
        name = old.database_resource
        owner = [old.tenant_id, name, old.binding_id, old.epoch, old.bundle_digest, "active"]
        updates = 0

        def run_in_transaction(self, callback):
            return callback(self)

        def read(self, *_args):
            return [self.owner]

        def update(self, table, columns, rows):
            assert table == "TenantControl"
            self.owner = list(rows[0][1:])
            self.updates += 1

    db = DB()
    assert activate_model_successor(db, new)
    assert not activate_model_successor(db, new)
    assert db.updates == 1
    db.owner[3] += 1
    with pytest.raises(TenantFenceError):
        activate_model_successor(db, new)


@pytest.mark.parametrize("when", ["construct", "activate"])
def test_mutated_predecessor_registry_is_rejected(when):
    old = bind()
    new = successor(old) if when == "activate" else None
    core = old.bundle.registry.pack("core")
    changed = core.model_dump(mode="json", by_alias=True)
    changed["pack"]["description"] += " changed"
    import json

    snapshots = (json.dumps(changed), *old.bundle._pack_snapshots[1:])
    # Simulate a corrupt internal binding; normal registry views are copies.
    object.__setattr__(old, "bundle", replace(old.bundle, _pack_snapshots=snapshots))
    with pytest.raises(TenantConfigurationError):
        if new is None:
            successor(old)
        else:
            activate_model_successor(None, new)


def test_enumerated_prior_epoch_is_pinned_and_does_not_grant_other_epochs():
    old = replace(bind(), epoch=4)
    new = replace(successor(old), predecessor_epochs=(2, 4))
    receipt = stamp_acceptance(context(old), event(), {})
    receipt.model_copy(update={"accepted_epoch": 2}).require_interpretation(new.interpretation())
    with pytest.raises(EventInterpretationError):
        receipt.model_copy(update={"accepted_epoch": 3}).require_interpretation(
            new.interpretation()
        )
    assert new.bundle_digest != successor(old).bundle_digest


def test_operator_reconstructs_same_successor_after_partial_activation():
    from engram_pilot_model_transition import pilot_binding, prepare_transition

    owner = [
        "isolation-a",
        "projects/portiq-mvp/instances/engram-experiment/databases/engram-assess-1010a-pdlc",
        "pilot-binding",
        52,
        "",
        "active",
    ]
    old = pilot_binding("test", "a", owner, model="gpt-5.2-2025-12-11")
    owner[4] = old.bundle_digest
    previous = {
        "database": owner[1],
        "owner": [owner],
        "fingerprints": {"Events": "fixed"},
        "snapshot": {
            "events": [
                [
                    "e",
                    {},
                    {
                        "accepted_epoch": 51,
                        "bundle_digest": old.bundle_digest,
                        "tenant_id": old.tenant_id,
                        "binding_id": old.binding_id,
                        "database_resource": old.database_resource,
                        "engine_revision": old.engine_revision,
                    },
                ]
            ]
        },
    }
    new, plan = prepare_transition("a", previous, previous)
    current = copy.deepcopy(previous)
    current["owner"][0][3] = new.epoch
    current["owner"][0][4] = new.bundle_digest
    resumed, same_plan = prepare_transition("a", current, previous, plan)
    assert resumed.bundle_digest == new.bundle_digest and same_plan == plan
    with pytest.raises(RuntimeError):
        prepare_transition("a", current, previous)
    current["fingerprints"]["Events"] = "changed"
    with pytest.raises(RuntimeError):
        prepare_transition("a", current, previous, plan)


def test_episode_preservation_detects_added_membership_and_allows_new_episode():
    from engram_pilot_first_run import episode_membership_edges

    original = {"edges": [["Episode", "old", "CONTAINS", "Event", "e1", {}]]}
    changed = copy.deepcopy(original)
    changed["edges"].append(["Episode", "old", "DERIVED_FROM", "Event", "e2", {}])
    assert episode_membership_edges(original, {"old"}) != episode_membership_edges(changed, {"old"})
    changed = copy.deepcopy(original)
    changed["edges"].append(["Episode", "new", "CONTAINS", "Event", "e2", {}])
    assert episode_membership_edges(original, {"old"}) == episode_membership_edges(changed, {"old"})
