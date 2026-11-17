"""Catalog compatibility, admission and lifecycle requirements across domains."""

import copy
import json
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from context_graph.domain.pack_admission import compile_admission_policy
from context_graph.domain.pack_bundle import resolve_bundle
from context_graph.ontology.loader import load_registry
from context_graph.workbench.api import create_app, readiness
from context_graph.workbench.catalog import CATALOG_DIR, entries
from context_graph.workbench.draft_stories import draft_story
from context_graph.workbench.engine import composed
from context_graph.workbench.journey_runner import run_journey
from context_graph.workbench.models import Content

FIXTURE = Path(__file__).parents[1] / "fixtures/workbench/incident.json"


def test_catalog_uses_loadable_pack_metadata_and_preserves_pdlc():
    catalog = {item["name"]: item for item in entries()}
    assert set(catalog) == {"crm", "pdlc"}
    assert all(item["has_lifecycle"] for item in catalog.values())
    assert Content(name="old", environment="test", existing_packs=["pdlc"]).existing_packs == [
        "pdlc"
    ]
    assert Content(name="new", environment="test", existing_packs=["crm", "pdlc"])


@pytest.mark.parametrize("names", [["missing"], ["../crm"], ["core"], ["crm", "crm"]])
def test_unavailable_or_duplicate_selection_rejected(names):
    with pytest.raises(ValidationError):
        Content(name="new", environment="test", existing_packs=names)


def test_crm_payload_contracts_enforce_tenant_admission():
    registry = load_registry(["crm"], [CATALOG_DIR], builtin_packs=[])
    policy = compile_admission_policy(resolve_bundle(registry))
    valid = {
        "crm.account.created": {"account_id": "a"},
        "crm.contact.added": {"email": "person@example.test", "account_id": "a"},
        "crm.deal.created": {"deal_id": "d", "account_id": "a", "amount": 12.5},
        "crm.deal.won": {"deal_id": "d"},
        "crm.deal.lost": {"deal_id": "d"},
        "crm.deal.replaced": {"deal_id": "d", "replaced_by": "e"},
    }
    for event, payload in valid.items():
        assert policy.decide(event, payload).allowed
        assert not policy.decide(event, {}).allowed
    assert not policy.decide(
        "crm.deal.created", {"deal_id": "d", "account_id": "a", "amount": "bad"}
    ).allowed


def test_composition_uses_selected_catalog_and_keeps_shadow_dependency_collision_checks():
    fixture = json.loads(FIXTURE.read_text())
    content = Content.model_validate(fixture["content"])
    content.existing_packs = ["crm"]
    pack = fixture["proposal"]["pack"]
    with composed(content, pack) as (_, bundle, _path):
        assert {"core", "crm", pack["pack"]["name"]} <= {p.name for p in bundle.registry.packs}
    shadow = copy.deepcopy(pack)
    shadow["pack"]["name"] = "crm"
    with pytest.raises(ValueError, match="shadow"), composed(content, shadow):
        pass
    missing = copy.deepcopy(pack)
    missing["pack"]["requires"].append("absent>=1.0")
    with pytest.raises(Exception, match="absent"), composed(content, missing):
        pass
    collision = copy.deepcopy(pack)
    collision["types"]["nodes"]["Account"] = {"key": ["id"], "properties": {"id": "string"}}
    with pytest.raises(Exception, match="Account"), composed(content, collision):
        pass


def test_no_lifecycle_does_not_require_confirmation_but_identity_remains():
    fixture = json.loads(FIXTURE.read_text())
    fixture["content"]["decisions"].pop("identity", None)
    fixture["content"]["decisions"].pop("lifecycle", None)
    fixture["review"] = {}
    for node in fixture["proposal"]["pack"]["types"]["nodes"].values():
        node.pop("lifecycle", None)
    missing = readiness(fixture)["run"]["missing"]
    assert "Record the lifecycle policy" not in missing
    assert "Record the identity policy" in missing
    fixture["proposal"]["pack"]["types"]["nodes"]["Incident"]["lifecycle"] = {
        "initial": "open",
        "states": ["open"],
    }
    assert "Record the lifecycle policy" in readiness(fixture)["run"]["missing"]


@pytest.mark.asyncio
async def test_missing_authored_snapshot_cannot_fall_back_to_pdlc():
    fixture = json.loads(FIXTURE.read_text())
    content = Content.model_validate(fixture["content"])
    journey, _snapshot = draft_story(content, fixture["proposal"]["pack"])
    with pytest.raises(ValueError, match="digest differs"):
        await run_journey(journey)


@pytest.mark.asyncio
async def test_capabilities_and_save_support_crm_and_reject_unknown(tmp_path):
    app = create_app(database=tmp_path / "catalog.sqlite", operators={"secret": "operator"})
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer secret"},
    ) as client:
        caps = (await client.get("/admin/capabilities")).json()
        assert caps["packs"] == ["crm", "pdlc"]
        assert len(caps["pack_catalog"]) == 2
        created = await client.post(
            "/admin/tenants",
            json={"name": "CRM operator", "environment": "test", "existing_packs": ["crm"]},
        )
        assert created.status_code == 201, created.text
        assert created.json()["content"]["existing_packs"] == ["crm"]
        invalid = await client.post(
            "/admin/tenants",
            json={"name": "Bad", "environment": "test", "existing_packs": ["absent"]},
        )
        assert invalid.status_code == 422


def test_both_domains_compose_with_independent_authored_extension():
    content = Content(name="Both", environment="test", existing_packs=["crm", "pdlc"])
    extension = {
        "pack": {"name": "directory", "version": "1.0.0", "requires": ["core>=1.1"]},
        "types": {"nodes": {"DirectoryEntry": {"key": ["code"], "properties": {"code": "string"}}}},
    }
    with composed(content, extension) as (_, bundle, _):
        assert {p.name for p in bundle.registry.packs} == {"core", "crm", "pdlc", "directory"}
