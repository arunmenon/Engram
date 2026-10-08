"""#52 normalized source-declared remediation at the generic projection seam."""

from tests.unit.test_pack_projection import Harness


async def test_explicit_corrective_pr_links_only_the_named_scoped_incident() -> None:
    h = Harness()
    incident = {"repo": "acme/auth", "service": "reset", "incident_id": "INC-51"}
    await h.ingest("pdlc.incident.detected", {**incident, "description": "expired token accepted"})
    await h.ingest(
        "pdlc.incident.detected",
        {**incident, "incident_id": "INC-52", "description": "expired token accepted"},
    )
    for number in (8, 9):
        await h.ingest(
            "pdlc.change.created",
            {
                "repo": "acme/auth",
                "number": number,
                "title": "expired token accepted",
                "head_sha": "shared",
            },
        )
    declared = await h.ingest(
        "pdlc.incident.remediation_recorded",
        {"change": {"repo": "acme/auth", "number": 8}, "incident": incident},
    )
    assert set(h.edges("REMEDIATES")) == {("Change:acme/auth|8", "Incident:acme/auth|reset|INC-51")}
    edge = h.edges("REMEDIATES")[("Change:acme/auth|8", "Incident:acme/auth|reset|INC-51")]
    assert edge["source_event_id"] == str(declared.event_id)
    assert edge["pinned_position"] == declared.global_position
    assert edge["link_status"] == "confirmed"
    assert h.edges("ATTRIBUTED_TO") == {}


async def test_retrieval_separates_correction_merge_and_resolution_evidence() -> None:
    from context_graph.retrieval.artifacts import ArtifactQuery, ArtifactRetriever
    from tests.unit.test_pack_projection import REGISTRY

    h = Harness()
    incident = {"repo": "acme/auth", "service": "reset", "incident_id": "INC-51"}
    await h.ingest("pdlc.incident.detected", incident, at_minute=10)
    await h.ingest("pdlc.change.created", {"repo": "acme/auth", "number": 8})
    declared = await h.ingest(
        "pdlc.incident.remediation_recorded",
        {"change": {"repo": "acme/auth", "number": 8}, "incident": incident},
    )
    merged = await h.ingest(
        "pdlc.change.merged", {"repo": "acme/auth", "number": 8, "merge_sha": "fix"}, at_minute=20
    )
    assert h.node("Incident:acme/auth|reset|INC-51")["status"] == "detected"
    resolved = await h.ingest(
        "pdlc.incident.resolved", {**incident, "summary": "verified token expiry"}, at_minute=30
    )
    await h.ingest("pdlc.incident.detected", incident, at_minute=15)
    retriever = ArtifactRetriever(
        h.graph,
        REGISTRY,
        default_max_depth=3,
        seed_limit=10,
        neighbor_limit=200,
        provenance_source="memory",
    )
    for seed in ("Incident:acme/auth|reset|INC-51", "Change:acme/auth|8"):
        response = await retriever.retrieve(
            ArtifactQuery("incident correction", seed_node_ids=(seed,), intent="incident")
        )
        assert set(response.nodes) == {
            "Incident:acme/auth|reset|INC-51",
            "Change:acme/auth|8",
            "Component:reset",
        }
        assert response.nodes["Incident:acme/auth|reset|INC-51"].attributes["status"] == "resolved"
        remediation = next(e for e in response.edges if e.edge_type == "REMEDIATES")
        assert remediation.properties["source_event_id"] == str(declared.event_id)
        assert response.nodes["Change:acme/auth|8"].provenance.event_id == str(merged.event_id)
        assert response.nodes["Incident:acme/auth|reset|INC-51"].provenance.event_id == str(
            resolved.event_id
        )

    from pathlib import Path

    from context_graph.ontology.evaluation import load_eval_set, run_eval_set

    evaluation = load_eval_set(
        Path(__file__).parents[1] / "fixtures/ontology/pdlc-remediation.eval.yaml"
    )
    report = await run_eval_set(evaluation, retriever, max_nodes=100)
    assert report.passed
    assert report.mean_f1 == 1.0


async def test_early_remediation_keeps_reference_stubs_without_artifact_evidence() -> None:
    from context_graph.retrieval.artifacts import ArtifactQuery, ArtifactRetriever
    from tests.unit.test_pack_projection import REGISTRY

    h = Harness()
    incident = {"repo": "acme/auth", "service": "reset", "incident_id": "INC-EARLY"}
    await h.ingest(
        "pdlc.incident.remediation_recorded",
        {"change": {"repo": "acme/auth", "number": 88}, "incident": incident},
    )
    change_id = "Change:acme/auth|88"
    incident_id = "Incident:acme/auth|reset|INC-EARLY"
    assert set(h.edges("REMEDIATES")) == {(change_id, incident_id)}
    assert h.edges("DERIVED_FROM") == {}
    retriever = ArtifactRetriever(
        h.graph,
        REGISTRY,
        default_max_depth=3,
        seed_limit=10,
        neighbor_limit=200,
        provenance_source="memory",
    )
    response = await retriever.retrieve(
        ArtifactQuery(
            "incident", seed_node_ids=(change_id,), intent="incident", include_untrusted=True
        )
    )
    assert set(response.nodes) == {change_id, incident_id}
    assert all(n.provenance is None for n in response.nodes.values())
    assert response.nodes[change_id].attributes["status"] == "open"
    assert response.nodes[incident_id].attributes["status"] == "detected"
    observed = await h.ingest("pdlc.incident.detected", incident)
    created = await h.ingest("pdlc.change.created", {"repo": "acme/auth", "number": 88})
    response = await retriever.retrieve(
        ArtifactQuery("incident", seed_node_ids=(change_id,), intent="incident")
    )
    assert response.nodes[incident_id].provenance.event_id == str(observed.event_id)
    assert response.nodes[change_id].provenance.event_id == str(created.event_id)


def test_remediation_contract_rejects_incomplete_or_ill_typed_references() -> None:
    import copy

    import pytest
    from pydantic import ValidationError

    from tests.unit.test_pack_projection import REGISTRY

    contract = REGISTRY.event_types[
        "pdlc.incident.remediation_recorded"
    ].definition.payload_contract
    valid = {
        "change": {"repo": "acme/auth", "number": 8},
        "incident": {"repo": "acme/auth", "service": "reset", "incident_id": "INC-51"},
    }
    contract.validate_payload(valid)
    for reference, field, invalids in (
        ("change", "repo", (None, [], "")),
        ("change", "number", (None, "8", True, 0, 9223372036854775808)),
        ("incident", "repo", (None, [], "")),
        ("incident", "service", (None, [], "")),
        ("incident", "incident_id", (None, [], "")),
    ):
        missing = copy.deepcopy(valid)
        del missing[reference][field]
        with pytest.raises(ValidationError):
            contract.validate_payload(missing)
        for invalid in invalids:
            malformed = copy.deepcopy(valid)
            malformed[reference][field] = invalid
            with pytest.raises(ValidationError):
                contract.validate_payload(malformed)
