"""Authenticated trust through typed fenced reads; local evidence, no cloud claim."""

from dataclasses import replace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from context_graph.domain.event_acceptance import stamp_acceptance
from context_graph.domain.pack_projection import PackProjector
from context_graph.domain.source_trust import SourceTrustPolicy, VerifiedSourceProvenance
from context_graph.ontology import load_registry
from context_graph.ontology.versioning import replay_event_types
from context_graph.ports.errors import RuntimeFencedError
from context_graph.settings import OntologySettings
from context_graph.worker.projection import ProjectionConsumer
from tests.unit.test_event_acceptance import context, event
from tests.unit.test_spanner_event_acceptance import setup
from tests.unit.test_tenant_catalog import bind, configuration
from tests.unit.test_worker_fences import subscription


def binding(*, trusted=("producer",), packs=()):
    settings = configuration()
    settings.ontology.packs = list(packs)
    settings.ontology.trusted_sources = ["forged-agent", "webhook:github"]
    settings.ontology.trusted_source_ids = list(trusted)
    return bind(settings=settings)


def projector(bound):
    return PackProjector(
        bound.bundle.registry,
        frozenset(bound.settings().ontology.trusted_sources),
        source_policy=SourceTrustPolicy.from_binding(bound),
    )


def attributed(bound, *, source="producer", agent="forged-agent"):
    item = event().model_copy(update={"agent_id": agent})
    payload = {"content": "original", "source_trust": "trusted"}
    doc = {**item.model_dump(mode="json"), "payload": payload}
    receipt = stamp_acceptance(context(bound, source=source), item, payload)
    return item, doc, VerifiedSourceProvenance(str(item.event_id), receipt)


@pytest.mark.parametrize(
    "source,agent,expected",
    [
        ("producer", "arbitrary-agent", True),
        ("other", "forged-agent", False),
        ("other", "webhook:github", False),
        ("producer", "forged-agent", True),
    ],
)
def test_authenticated_source_determines_trust_not_agent_or_payload(source, agent, expected):
    bound = binding()
    item, doc, provenance = attributed(bound, source=source, agent=agent)
    assert projector(bound).source_trusted(item, doc, provenance) is expected


def test_empty_source_policy_never_uses_legacy_default_allowlist():
    bound = binding(trusted=())
    assert not projector(bound).source_trusted(*attributed(bound))


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "json_receipt",
        "wrong_receipt_type",
        "event_id",
        "payload",
        "event",
        "tenant",
        "database",
        "binding",
        "bundle",
        "engine",
        "future_epoch",
    ],
)
def test_bad_provenance_refuses_even_core_event_without_domain_rules(fault):
    bound = binding()
    item, doc, provenance = attributed(bound)
    if fault == "missing":
        provenance = None
    elif fault == "json_receipt":
        doc["acceptance"] = provenance.acceptance.model_dump()
        provenance = doc["acceptance"]
    elif fault == "wrong_receipt_type":
        provenance = replace(provenance, acceptance={})
    elif fault == "event_id":
        provenance = replace(provenance, event_id=str(uuid4()))
    elif fault == "payload":
        doc["payload"]["content"] = "changed"
    elif fault == "event":
        item = item.model_copy(update={"agent_id": "changed"})
    else:
        field, value = {
            "tenant": ("tenant_id", "other"),
            "database": ("database_resource", "projects/p/instances/i/databases/d"),
            "binding": ("binding_id", "other"),
            "bundle": ("bundle_digest", "sha256:" + "0" * 64),
            "engine": ("engine_revision", "other"),
            "future_epoch": ("accepted_epoch", bound.epoch + 1),
        }[fault]
        provenance = replace(
            provenance, acceptance=provenance.acceptance.model_copy(update={field: value})
        )
    with pytest.raises(RuntimeFencedError):
        projector(bound).plan(item, doc, provenance=provenance)


def test_epoch_only_advance_preserves_trust_but_changed_allowlist_blocks_old_receipt():
    bound = binding()
    item, doc, provenance = attributed(bound)
    assert projector(replace(bound, epoch=2)).source_trusted(item, doc, provenance)
    changed = binding(trusted=())
    assert changed.bundle_digest != bound.bundle_digest
    with pytest.raises(RuntimeFencedError):
        projector(changed).source_trusted(item, doc, provenance)


def test_source_ids_validate_without_silent_webhook_aliases(monkeypatch):
    for bad in ("webhook:github", "", "two words", "x" * 129):
        with pytest.raises(ValidationError):
            OntologySettings(trusted_source_ids=[bad])
    monkeypatch.setenv("CG_ONTOLOGY_TRUSTED_SOURCE_IDS", "github-install-1,importer.crm")
    assert OntologySettings().trusted_source_ids == ["github-install-1", "importer.crm"]


def test_projector_policy_cannot_pair_with_another_ontology():
    with pytest.raises(RuntimeFencedError):
        PackProjector(
            load_registry(["pdlc"]),
            frozenset(),
            source_policy=SourceTrustPolicy.from_binding(binding()),
        )


@pytest.mark.asyncio
async def test_authoritative_records_are_separate_from_json_and_preserve_duplicate_input_order():
    bound, db, store = setup(binding())
    item, doc, _ = attributed(bound)
    await store.append(item, doc["payload"], admission_context=context(bound))
    records = await store.get_accepted_records([str(item.event_id)] * 2)
    assert [r.provenance.event_id for r in records] == [str(item.event_id)] * 2
    assert projector(bound).source_trusted(item, records[0].document, records[0].provenance)
    records[0].document["acceptance"]["source_id"] = "forged"
    assert records[0].provenance.acceptance.source_id == "producer"
    assert projector(bound).source_trusted(item, records[0].document, records[0].provenance)
    records[0].document["payload"]["content"] = "changed"
    with pytest.raises(RuntimeFencedError):
        projector(bound).source_trusted(item, records[0].document, records[0].provenance)
    assert projector(bound).requires_provenance is True
    assert len(db.rows) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", ["missing", "receipt", "payload", "frozen"])
async def test_accepted_reader_refuses_unverifiable_records(fault):
    bound, db, store = setup(binding())
    item, doc, _ = attributed(bound)
    await store.append(item, doc["payload"], admission_context=context(bound))
    row = db.rows[str(item.event_id)]
    if fault == "missing":
        db.rows.clear()
    elif fault == "receipt":
        row["acceptance"] = None
    elif fault == "payload":
        from context_graph.adapters.spanner.log import json_value

        body = json_value(row["document"])
        body["payload"]["content"] = "changed"
        row["document"] = body
    else:
        db.owner[-1] = "frozen"
    with pytest.raises(RuntimeFencedError):
        await store.get_accepted_records([str(item.event_id)])


@pytest.mark.asyncio
async def test_projection_validates_before_any_graph_writes_or_disposition():
    bound, db, store = setup(binding())
    item, doc, _ = attributed(bound)
    await store.append(item, doc["payload"], admission_context=context(bound))
    port, graph = subscription(), AsyncMock()
    settings = bound.settings()
    settings.consumer.projection_batch_size = 1
    consumer = ProjectionConsumer(port, store, graph, settings, projector(bound))
    consumer._previous_event = AsyncMock(return_value=None)
    await consumer.process_message("position", {"event_id": str(item.event_id)})
    graph.merge_event_nodes_batch.assert_awaited_once()
    port.ack.assert_awaited_once()
    graph.reset_mock()
    port.reset_mock()
    db.rows[str(item.event_id)]["acceptance"] = None
    with pytest.raises(RuntimeFencedError):
        await consumer.process_message("position", {"event_id": str(item.event_id)})
    graph.merge_event_nodes_batch.assert_not_awaited()
    port.ack.assert_not_awaited()
    port.dead_letter.assert_not_awaited()


def test_bound_projection_refuses_plain_document_only_reader():
    class PlainReader:
        async def get_documents(self, ids):
            return []

    with pytest.raises(RuntimeFencedError):
        ProjectionConsumer(
            subscription(), PlainReader(), AsyncMock(), binding().settings(), projector(binding())
        )


@pytest.mark.asyncio
async def test_replay_preserves_typed_source_and_refuses_document_receipt_copy():
    from context_graph.ports.event_log import LogEntry

    bound = binding(packs=["pdlc"])
    item = event().model_copy(update={"event_type": "pdlc.change.created"})
    payload = {"repo": "example/payments", "number": 7, "title": "Change"}
    doc = {**item.model_dump(mode="json"), "payload": payload}
    receipt = stamp_acceptance(context(bound), item, payload)
    provenance = VerifiedSourceProvenance(str(item.event_id), receipt)
    reader = AsyncMock()
    reader.get_accepted_records = AsyncMock(side_effect=AssertionError("replay uses typed entries"))
    reader.read_after.side_effect = [
        [LogEntry("position", str(item.event_id), doc, provenance)],
        [],
    ]
    with patch("context_graph.ontology.versioning.apply_plan", new_callable=AsyncMock) as apply:
        report = await replay_event_types(
            reader, AsyncMock(), projector(bound), {item.event_type}, batch_size=10, lookup_limit=10
        )
        assert report.replayed == 1
        plan = apply.await_args.args[1]
        assert any(write.properties.get("source_trust") == "trusted" for write in plan.nodes)
    doc["acceptance"] = receipt.model_dump()
    reader.read_after.side_effect = [[LogEntry("position", str(item.event_id), doc)], []]
    with patch("context_graph.ontology.versioning.apply_plan", new_callable=AsyncMock) as apply:
        with pytest.raises(RuntimeFencedError):
            await replay_event_types(
                reader,
                AsyncMock(),
                projector(bound),
                {item.event_type},
                batch_size=10,
                lookup_limit=10,
            )
        apply.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("source,expected", [("producer", "trusted"), ("other", "untrusted")])
async def test_pack_extraction_uses_verified_source_not_spoofed_agent(source, expected):
    import json

    from context_graph.domain.pack_extraction import extraction_profiles
    from context_graph.worker.pack_extraction import PackExtractionConsumer
    from tests.unit.test_pack_admission import CASES
    from tests.unit.test_pack_extraction import ScriptedModel, _answer

    bound, _, store = setup(binding(packs=["pdlc"]))
    payload = next(
        case["payload"] for case in CASES if case["event_type"] == "pdlc.design.section_changed"
    )
    payload = {**payload, "text": "We will retry failed refunds with idempotency keys"}
    item = event().model_copy(
        update={"event_type": "pdlc.design.section_changed", "agent_id": "forged-agent"}
    )
    await store.append(item, payload, admission_context=context(bound, source=source))
    graph = AsyncMock()
    graph.get_nodes.return_value = {}
    graph.search_nodes.return_value = []
    answer = _answer(links=[])
    answer["nodes"][0]["source_trust"] = "trusted"
    model = ScriptedModel(json.dumps(answer))
    consumer = PackExtractionConsumer(
        subscription(),
        store,
        graph,
        extraction_profiles(bound.bundle.registry, max_nodes=3, max_links=3, max_text_chars=500),
        projector(bound),
        model,
        bound.settings(),
    )
    with patch("context_graph.worker.pack_extraction.apply_plan", new_callable=AsyncMock) as apply:
        await consumer.process_message("position", {"event_id": str(item.event_id)})
        assert len(model.prompts) == 1
        plan = apply.await_args.args[1]
        assert any(write.defaults.get("source_trust") == expected for write in plan.nodes)


@pytest.mark.asyncio
async def test_bound_workers_refuse_legacy_projector_even_with_authoritative_ledger():
    from context_graph.worker.pack_extraction import PackExtractionConsumer

    bound, _, store = setup(binding())
    legacy = PackProjector(bound.bundle.registry, frozenset({"forged-agent"}))
    with pytest.raises(RuntimeFencedError):
        ProjectionConsumer(subscription(), store, AsyncMock(), bound.settings(), legacy)
    with pytest.raises(RuntimeFencedError):
        PackExtractionConsumer(
            subscription(), store, AsyncMock(), [], legacy, AsyncMock(), bound.settings()
        )


@pytest.mark.asyncio
async def test_bound_replay_refuses_legacy_projector_before_any_read_or_write():
    bound, db, store = setup(binding())
    legacy = PackProjector(bound.bundle.registry, frozenset({"forged-agent"}))
    store.read_after = AsyncMock()
    graph = AsyncMock()
    with pytest.raises(RuntimeFencedError):
        await replay_event_types(
            store, graph, legacy, {"tool.execute"}, batch_size=10, lookup_limit=10
        )
    store.read_after.assert_not_awaited()
    assert not graph.mock_calls and not db.transactions
