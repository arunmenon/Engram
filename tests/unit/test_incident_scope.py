"""G06 #51: normalized incident events through the generic projection seam."""

from tests.unit.test_pack_projection import Harness


async def test_incident_selects_only_its_repository_and_service() -> None:
    h = Harness()
    shared = {"environment": "prod", "artifact_id": "sha-reset"}
    await h.ingest("pdlc.service.deployed", {**shared, "repo": "acme/auth", "service": "reset"})
    await h.ingest("pdlc.service.deployed", {**shared, "repo": "acme/other", "service": "reset"})
    await h.ingest("pdlc.service.deployed", {**shared, "repo": "acme/auth", "service": "billing"})
    await h.ingest(
        "pdlc.incident.detected",
        {**shared, "repo": "acme/auth", "service": "reset", "incident_id": "INC-1"},
    )
    assert set(h.edges("OCCURRED_ON")) == {
        (
            "Incident:acme/auth|reset|INC-1",
            "Deployment:acme/auth|reset|prod|sha-reset|2026-10-04T10:01:00+00:00",
        )
    }


async def test_reported_incident_has_service_state_and_event_evidence_without_deployment() -> None:
    h = Harness()
    event = await h.ingest(
        "pdlc.incident.reported",
        {
            "repo": "acme/auth",
            "service": "reset",
            "incident_id": "OUTAGE-73",
            "description": "expired tokens accepted",
        },
    )
    incident = h.node("Incident:acme/auth|reset|OUTAGE-73")
    assert incident["status"] == "detected"
    assert incident["title"] == "expired tokens accepted"
    assert set(h.edges("AFFECTS")) == {("Incident:acme/auth|reset|OUTAGE-73", "Component:reset")}
    assert ("Incident:acme/auth|reset|OUTAGE-73", str(event.event_id)) in h.edges("DERIVED_FROM")
    assert h.edges("OCCURRED_ON") == {}


async def test_late_detection_preserves_resolution_and_separates_local_ids_by_scope() -> None:
    h = Harness()
    first = {"repo": "acme/auth", "service": "reset", "incident_id": "UNFAMILIAR-88"}
    second = {**first, "repo": "acme/other"}
    await h.ingest("pdlc.incident.reported", first, at_minute=10)
    await h.ingest("pdlc.incident.resolved", {**first, "summary": "rolled back"}, at_minute=30)
    await h.ingest("pdlc.incident.detected", first, at_minute=20)
    await h.ingest("pdlc.incident.detected", second, at_minute=40)
    assert h.node("Incident:acme/auth|reset|UNFAMILIAR-88")["status"] == "resolved"
    assert h.node("Incident:acme/other|reset|UNFAMILIAR-88")["status"] == "detected"


async def test_incident_retrieval_returns_exact_scoped_deployment_in_both_directions() -> None:
    from context_graph.retrieval.artifacts import ArtifactQuery, ArtifactRetriever
    from tests.unit.test_pack_projection import REGISTRY

    h = Harness()
    shared = {"environment": "prod", "artifact_id": "sha-reset"}
    deployed = await h.ingest(
        "pdlc.service.deployed", {**shared, "repo": "acme/auth", "service": "reset"}
    )
    await h.ingest("pdlc.service.deployed", {**shared, "repo": "acme/other", "service": "reset"})
    await h.ingest("pdlc.service.deployed", {**shared, "repo": "acme/other", "service": "other"})
    detected = await h.ingest(
        "pdlc.incident.detected",
        {**shared, "repo": "acme/auth", "service": "reset", "incident_id": "INC-1"},
    )
    retriever = ArtifactRetriever(
        h.graph,
        REGISTRY,
        default_max_depth=3,
        seed_limit=10,
        neighbor_limit=200,
        provenance_source="memory",
    )
    incident = "Incident:acme/auth|reset|INC-1"
    deployment = "Deployment:acme/auth|reset|prod|sha-reset|2026-10-04T10:01:00+00:00"
    for seed in (incident, deployment):
        response = await retriever.retrieve(
            ArtifactQuery("incident", seed_node_ids=(seed,), intent="incident")
        )
        assert set(response.nodes) == {incident, deployment, "Component:reset"}
        assert {(e.edge_type, e.source, e.target) for e in response.edges} == {
            ("OCCURRED_ON", incident, deployment),
            ("AFFECTS", incident, "Component:reset"),
        }
        assert response.nodes[incident].provenance.event_id == str(detected.event_id)
        assert response.nodes[deployment].provenance.event_id == str(deployed.event_id)

    from pathlib import Path

    from context_graph.ontology.evaluation import load_eval_set, run_eval_set

    evaluation = load_eval_set(
        Path(__file__).parents[1] / "fixtures/ontology/pdlc-incident.eval.yaml"
    )
    report = await run_eval_set(evaluation, retriever, max_nodes=100)
    assert report.passed
    assert report.mean_f1 == 1.0
