"""Frozen procurement business examples, independently specified before pack generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from context_graph.workbench.engine import composed
from context_graph.workbench.models import Content
from context_graph.workbench.sandbox import run_sandbox

ROOT = Path("docs/examples/procurement")
TYPES = {
    "Supplier",
    "PurchaseRequest",
    "PurchaseOrder",
    "PurchaseOrderLine",
    "GoodsReceipt",
    "ProcurementInvoice",
    "MatchAssessment",
}
EDGES = {
    "FULFILLS_REQUEST",
    "ORDERED_FROM",
    "HAS_ORDER_LINE",
    "RECEIVES_LINE",
    "INVOICES_ORDER",
    "BILLS_LINE",
    "ASSESSES_INVOICE",
}


def inputs():
    sources = [
        dict(id=f"source-{i}", name=name, kind=kind, text=(ROOT / name).read_text())
        for i, (name, kind) in enumerate(
            [
                ("01-domain-spec.md", "specification"),
                ("02-event-contracts.json", "schema"),
                ("03-sample-events.json", "samples"),
                ("04-questions-and-expectations.md", "specification"),
            ]
        )
    ]
    content = Content.model_validate(
        dict(
            name="HarborWorks procurement regression",
            environment="test",
            scope="Frozen synthetic purchase-to-invoice pilot",
            sources=sources,
            questions=json.loads((ROOT / "04-questions.json").read_text()),
            min_f1=1.0,
            producer_ids=["procurement-adapter"],
            trusted_ids=["procurement-adapter"],
        )
    )
    pack = yaml.safe_load((ROOT / "procurement_ops.pack.yaml").read_text())
    return content, pack


def domain(snapshot):
    return {n["id"]: n["properties"] for n in snapshot["nodes"] if n["type"] in TYPES}


def verify_business_result(result):
    """Same assertions can be applied to the persisted UI/Spanner result."""
    assert result["passed"], result["evaluation"]
    assert result["evaluation"]["mean_f1"] == 1.0
    assert len(result["evaluation"]["questions"]) == 7
    assert not result["dead_letters"]
    steps = result["steps"]
    assert len(steps) == 29
    nodes = domain(steps[-1])
    assert len(nodes) == 21
    assert nodes["PurchaseRequest:us|PR-100"]["status"] == "approved"
    assert nodes["PurchaseRequest:us|PR-100"]["description"] == "Monitor refresh"
    assert nodes["PurchaseRequest:us|PR-100"]["approver_id"] == "manager-8"
    assert nodes["GoodsReceipt:us|GR-200A|1"]["received_quantity"] == 4
    assert nodes["GoodsReceipt:us|GR-200B|1"]["received_quantity"] == 6
    assert nodes["ProcurementInvoice:us|INV-200"]["quantity"] == 12
    assert nodes["ProcurementInvoice:us|INV-200"]["amount_minor"] == 120000
    assert nodes["MatchAssessment:us|M-200"]["verdict"] == "quantity_mismatch"
    assert nodes["MatchAssessment:us|M-200"]["ordered_quantity"] == 10
    assert nodes["MatchAssessment:us|M-200"]["received_quantity"] == 10
    assert nodes["MatchAssessment:us|M-200"]["invoiced_quantity"] == 12
    assert nodes["MatchAssessment:us|M-100"]["verdict"] == "matched"
    assert nodes["ProcurementInvoice:us|INV-100"]["currency"] == "USD"
    assert nodes["ProcurementInvoice:eu|INV-100"]["currency"] == "EUR"
    assert all("paid" not in n for n in nodes.values())
    # Company fields, rather than names/number substrings, define identity.
    domain_edges = [e for e in steps[-1]["edges"] if e["type"] in EDGES]
    assert len(domain_edges) == 22
    assert all(
        nodes[e["source"]]["company_id"] == nodes[e["target"]]["company_id"] for e in domain_edges
    )
    assert domain(steps[24]) == domain(steps[23])  # ledger-only note
    assert domain(steps[26]) == domain(steps[25])  # exact retry
    assert domain(steps[27]) == domain(steps[26])  # missing company rejected
    assert domain(steps[28]) == domain(steps[27])  # string quantity rejected
    assert [s["admitted"] for s in steps[-2:]] == [False, False]
    assert "ProcurementInvoice:us|INV-BAD" not in nodes
    assert "GoodsReceipt:us|GR-BAD|1" not in nodes


@pytest.mark.parametrize("roots", [[], ["memory"], ["user"], ["memory", "user"]])
def test_procurement_composes_with_optional_roots(roots):
    content, pack = inputs()
    content.roots = roots
    with composed(content, pack) as (loaded, bundle, _):
        assert loaded.name == "procurement_ops"
        assert {
            t.name for t in bundle.registry.node_types.values() if t.pack == loaded.name
        } == TYPES
        assert {p.name for p in bundle.registry.packs} == {"core", "procurement_ops", *roots}


async def test_procurement_business_stories_and_frozen_questions():
    content, pack = inputs()
    result = await run_sandbox(content, pack)
    verify_business_result(result)


def test_frozen_sample_contracts_and_retry_identity():
    from pydantic import ValidationError

    from context_graph.domain.event_acceptance import request_fingerprint
    from context_graph.domain.pack_contracts import PayloadContract
    from context_graph.workbench.engine import event_from_sample

    contracts = json.loads((ROOT / "02-event-contracts.json").read_text())["events"]
    events = json.loads((ROOT / "03-sample-events.json").read_text())
    identities = {}
    retries = 0
    for index, sample in enumerate(events):
        contract = PayloadContract.model_validate(
            contracts[sample["event_type"]]["payload_contract"]
        )
        if sample.get("expect_admitted", True):
            contract.validate_payload(sample["payload"])
        else:
            with pytest.raises(ValidationError):
                contract.validate_payload(sample["payload"])
        fingerprint = request_fingerprint(event_from_sample(sample, index), sample["payload"])
        if sample["event_id"] in identities:
            assert identities[sample["event_id"]] == fingerprint
            retries += 1
        identities[sample["event_id"]] = fingerprint
    assert retries == 1
