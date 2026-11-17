"""Writer-bound admission using the transaction fake, never a cloud sign-off."""

import copy
from uuid import uuid4

import pytest

from context_graph.adapters.spanner.log import SpannerEventLog, json_value
from context_graph.adapters.spanner.tenant_control import TenantFence
from context_graph.domain.ontology import OntologyRegistry
from context_graph.domain.pack_admission import compile_admission_policy
from context_graph.domain.pack_bundle import resolve_bundle
from context_graph.ports.errors import InvalidRequestError, RuntimeFencedError
from tests.unit.test_event_acceptance import context, event
from tests.unit.test_pack_admission import CASES, core, unfamiliar
from tests.unit.test_spanner_event_acceptance import Database, setup
from tests.unit.test_tenant_catalog import bind, configuration


def pdlc_binding():
    settings = configuration()
    settings.ontology.packs = ["pdlc"]
    return bind(settings=settings)


def domain_event(kind, *, fresh=False):
    return event().model_copy(
        update={"event_type": kind, **({"event_id": uuid4()} if fresh else {})}
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES, ids=lambda case: case["event_type"])
async def test_all_pdlc_contracts_at_actual_writer_boundary(case):
    binding, db, store = setup(pdlc_binding())
    payload = copy.deepcopy(case["payload"])
    (outcome,) = await store.append_batch_outcomes(
        [domain_event(case["event_type"])], [payload], admission_context=context(binding)
    )
    if case["classification"] == "missing_mapping":
        assert outcome.status == "rejected" and outcome.reason == "event_unsupported"
        assert not db.rows
    else:
        assert outcome.status == "created"
        assert json_value(next(iter(db.rows.values()))["document"])["payload"] == payload
        assert payload == case["payload"]


@pytest.mark.asyncio
async def test_mixed_batch_rejects_missing_fields_preserving_siblings_and_original_order():
    binding, db, store = setup(pdlc_binding())
    valid = domain_event("pdlc.change.created")
    invalid = domain_event("pdlc.change.created", fresh=True)
    payload = CASES[0]["payload"]
    outcomes = await store.append_batch_outcomes(
        [invalid, valid, invalid, valid],
        [{}, payload, payload, payload],
        admission_context=context(binding),
    )
    assert [x.status for x in outcomes] == ["rejected", "created", "created", "duplicate"]
    assert outcomes[0].reason == "payload_invalid" and outcomes[0].problems
    assert outcomes[1].position == outcomes[3].position
    assert set(db.rows) == {str(valid.event_id), str(invalid.event_id)}
    assert sum(len(t.effects) for t in db.transactions) == 2


@pytest.mark.asyncio
async def test_historical_duplicate_and_conflict_precede_new_contract_decision():
    binding, db, store = setup(pdlc_binding())
    item, payload = domain_event("pdlc.change.created"), CASES[0]["payload"]
    first = await store.append(item, payload, admission_context=context(binding))
    original = copy.deepcopy(db.rows)
    # Simulate a later policy refusing this event type, without changing stored identity.
    store._admission_policy = compile_admission_policy(resolve_bundle(OntologyRegistry([core()])))
    results = await store.append_batch_outcomes(
        [item, item, item.model_copy(update={"event_id": uuid4()})],
        [payload, {**payload, "title": "changed"}, payload],
        admission_context=context(binding),
    )
    assert [x.status for x in results] == ["duplicate", "conflict", "rejected"]
    assert results[0].position == first and db.rows == original
    (other,) = await store.append_batch_outcomes(
        [item], [payload], admission_context=context(binding, source="other")
    )
    assert other.status == "conflict" and db.rows == original


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["append", "append_batch", "append_batch_outcomes"])
async def test_all_direct_and_authenticated_proxy_methods_guard_new_events(method):
    binding, db, store = setup(pdlc_binding())
    item = domain_event("pdlc.change.created")
    for writer, kwargs in (
        (store, {"admission_context": context(binding)}),
        (store.admission_writer(context(binding)), {}),
    ):
        args = (item, {}) if method == "append" else ([item], [{}])
        if method == "append_batch_outcomes":
            result = await getattr(writer, method)(*args, **kwargs)
            assert result[0].status == "rejected"
        else:
            with pytest.raises(InvalidRequestError):
                await getattr(writer, method)(*args, **kwargs)
        assert not db.rows


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["append_batch", "append_batch_outcomes"])
@pytest.mark.parametrize("payloads", [[], [{}, {}]])
async def test_payload_count_mismatch_refuses_before_any_transaction(method, payloads):
    binding, db, store = setup()
    with pytest.raises(InvalidRequestError, match="counts"):
        await getattr(store, method)([event()], payloads, admission_context=context(binding))
    assert not db.transactions


@pytest.mark.asyncio
async def test_bound_writer_without_compiled_bundle_fails_closed():
    binding = bind()
    db = Database(binding)
    store = SpannerEventLog(
        db,
        tenant_fence=TenantFence.from_binding(binding),
        tenant_engine_revision=binding.engine_revision,
    )
    with pytest.raises(RuntimeFencedError):
        store.admission_writer(context(binding))
    with pytest.raises(RuntimeFencedError):
        await store.append(event(), admission_context=context(binding))
    assert not db.transactions


@pytest.mark.asyncio
async def test_unfamiliar_pack_uses_same_writer_and_preserves_null_extra_and_omission(tmp_path):
    import yaml

    path = tmp_path / "telemetry.pack.yaml"
    path.write_text(
        yaml.safe_dump(unfamiliar().model_dump(mode="json", by_alias=True, exclude_none=True))
    )
    settings = configuration()
    settings.ontology.packs = ["telemetry"]
    settings.ontology.pack_dirs = [str(tmp_path)]
    binding, db, store = setup(bind(settings=settings))
    item = domain_event("telemetry.reading.recorded")
    payload = {"meter": "west", "reading": 1.25, "note": None, "extra": {"x": 7}}
    outcomes = await store.append_batch_outcomes(
        [item, item.model_copy(update={"event_id": uuid4()})],
        [payload, {"meter": "west", "reading": "SECRET"}],
        admission_context=context(binding),
    )
    assert [x.status for x in outcomes] == ["created", "rejected"]
    assert "SECRET" not in repr(outcomes[1])
    assert json_value(db.rows[str(item.event_id)]["document"])["payload"] == payload


def test_http_admission_rejections_keep_input_indexes_and_no_storage_failure(test_client):
    from context_graph.tenancy import Principal

    binding, db, store = setup(pdlc_binding())
    test_client.app.state.event_store = store
    test_client.app.state.tenant_binding = binding

    @test_client.app.middleware("http")
    async def authenticated(request, call_next):
        request.scope["engram.principal"] = Principal(
            "credential", "a", frozenset({"api"}), "producer"
        )
        return await call_next(request)

    valid = {
        **domain_event("pdlc.change.created").model_dump(mode="json"),
        "payload": CASES[0]["payload"],
    }
    invalid = {**valid, "event_id": str(uuid4()), "payload": {}}
    rejected = test_client.post("/v1/events", json=invalid)
    assert rejected.status_code == 422 and not db.rows
    mixed = test_client.post("/v1/events/batch", json={"events": [{}, invalid, valid]})
    assert mixed.status_code == 201
    body = mixed.json()
    assert body["accepted"] == 1 and body["rejected"] == 2
    assert [x["index"] for x in body["errors"]] == [0, 1]
    assert body["errors"][1]["reason"] == "payload_invalid"
    store._admission_policy = compile_admission_policy(resolve_bundle(OntologyRegistry([core()])))
    retried = test_client.post("/v1/events", json=valid)
    assert retried.status_code == 201 and retried.json()["status"] == "duplicate"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kind", ["pdlc.change.created", "tool.custom", "other.event", "github.pull_request"]
)
async def test_inactive_unknown_and_source_aliases_cannot_bypass_writer(kind):
    binding, db, store = setup()
    (outcome,) = await store.append_batch_outcomes(
        [domain_event(kind)], [{}], admission_context=context(binding)
    )
    assert outcome.status == "rejected" and outcome.reason == "event_unsupported"
    assert not db.rows


@pytest.mark.asyncio
async def test_explicit_ledger_only_has_same_payload_contract(tmp_path):
    import yaml

    pack = unfamiliar(handling="ledger_only", projection=False)
    (tmp_path / "telemetry.pack.yaml").write_text(
        yaml.safe_dump(pack.model_dump(mode="json", by_alias=True, exclude_none=True))
    )
    settings = configuration()
    settings.ontology.packs = ["telemetry"]
    settings.ontology.pack_dirs = [str(tmp_path)]
    binding, db, store = setup(bind(settings=settings))
    item = domain_event("telemetry.reading.recorded")
    outcomes = await store.append_batch_outcomes(
        [item, item.model_copy(update={"event_id": uuid4()})],
        [{"meter": "west", "reading": 1.25}, {}],
        admission_context=context(binding),
    )
    assert [x.status for x in outcomes] == ["created", "rejected"]
    assert outcomes[1].reason == "payload_invalid" and len(db.rows) == 1


@pytest.mark.parametrize(
    "fault", ["bundle", "engine", "tenant", "epoch", "nested_mutation", "missing_fence"]
)
def test_writer_construction_rejects_binding_authority_mismatch_before_io(fault):
    from dataclasses import replace

    binding = bind()
    db = Database(binding)
    fence = TenantFence.from_binding(binding)
    revision = binding.engine_revision
    supplied = binding
    if fault == "bundle":
        supplied = pdlc_binding()
    elif fault == "engine":
        revision = "other-engine"
    elif fault == "tenant":
        supplied = replace(binding, tenant_id="other")
    elif fault == "epoch":
        supplied = replace(binding, epoch=binding.epoch + 1)
    elif fault == "nested_mutation":
        binding.bundle.registry.pack("core").open_event_namespaces.append("tool")
        store = SpannerEventLog(
            db, tenant_fence=fence, tenant_engine_revision=revision, tenant_binding=supplied
        )
        # registry is a detached view; changing it cannot alter the pinned bundle.
        assert not store._admission_policy.decide("tool.custom", {}).allowed
        assert not db.transactions
        return
    else:
        fence = None
    with pytest.raises(RuntimeFencedError, match="binding"):
        SpannerEventLog(
            db, tenant_fence=fence, tenant_engine_revision=revision, tenant_binding=supplied
        )
    assert not db.transactions
