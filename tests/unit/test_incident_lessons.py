"""#53 authored lessons and explicit specification reuse through public seams."""

from uuid import UUID

from tests.unit.test_pack_projection import Harness

LESSON = "Lesson:ffb16a4316632c432747bd88f60e759b85315cb41b75a60d48ae6c76c63e0a7c:authored"


async def test_authored_lesson_remains_tentative_with_explicit_incident_and_fix_evidence(
    monkeypatch,
) -> None:
    h = Harness()
    incident = {"repo": "acme/auth", "service": "reset", "incident_id": "INC-51"}
    await h.ingest("pdlc.incident.detected", incident)
    await h.ingest("pdlc.change.created", {"repo": "acme/auth", "number": 8})
    monkeypatch.setattr(
        "tests.unit.test_pack_projection.uuid4",
        lambda: UUID("00000000-0000-0000-0000-000000000053"),
    )
    authored = await h.ingest(
        "pdlc.incident.lesson_recorded",
        {
            "statement": "Check token expiry server-side",
            "incident": incident,
            "change": {"repo": "acme/auth", "number": 8},
        },
    )
    assert h.node(LESSON)["statement"] == "Check token expiry server-side"
    assert h.node(LESSON)["status"] == "tentative"
    assert set(h.edges("LEARNED_FROM")) == {
        (LESSON, "Incident:acme/auth|reset|INC-51"),
        (LESSON, "Change:acme/auth|8"),
    }
    assert (LESSON, str(authored.event_id)) in h.edges("DERIVED_FROM")
    for properties in h.edges("LEARNED_FROM").values():
        assert properties["source_event_id"] == str(authored.event_id)
        assert properties["pinned_position"] == authored.global_position


async def test_identical_lessons_for_distinct_incidents_preserve_separate_assertions(
    monkeypatch,
) -> None:
    h = Harness()
    ids = iter(
        (UUID("00000000-0000-0000-0000-000000000053"), UUID("00000000-0000-0000-0000-000000000054"))
    )
    monkeypatch.setattr("tests.unit.test_pack_projection.uuid4", lambda: next(ids))
    first = await h.ingest(
        "pdlc.incident.lesson_recorded",
        {
            "statement": "Check token expiry server-side",
            "incident": {"repo": "acme/auth", "service": "reset", "incident_id": "INC-51"},
        },
    )
    second = await h.ingest(
        "pdlc.incident.lesson_recorded",
        {
            "statement": "Check token expiry server-side",
            "incident": {"repo": "acme/other", "service": "other", "incident_id": "INC-51"},
        },
    )
    other = "Lesson:e091df92db4424a680552b841613a45a3568479fc3087fadcc6df15cc4529252:authored"
    assert set(h.edges("LEARNED_FROM")) == {
        (LESSON, "Incident:acme/auth|reset|INC-51"),
        (other, "Incident:acme/other|other|INC-51"),
    }
    assert h.node(LESSON)["status"] == h.node(other)["status"] == "tentative"
    assert (LESSON, str(first.event_id)) in h.edges("DERIVED_FROM")
    assert (other, str(second.event_id)) in h.edges("DERIVED_FROM")


async def test_typed_spec_citation_preserves_revision_and_unknown_lesson_reference() -> None:
    h = Harness()
    cited = await h.ingest(
        "pdlc.spec.approved",
        {
            "doc_id": "expiry-v2",
            "version": "2",
            "title": "Check token expiry server-side",
            "lesson_refs": [{"content_hash": LESSON.removeprefix("Lesson:")}],
        },
    )
    await h.ingest(
        "pdlc.spec.approved",
        {"doc_id": "unrelated", "version": "1", "title": "Check token expiry server-side"},
    )
    assert set(h.edges("CITES")) == {("Spec:expiry-v2|2", LESSON)}
    assert (
        h.edges("CITES")[("Spec:expiry-v2|2", LESSON)]["pinned_position"] == cited.global_position
    )
    assert (LESSON, str(cited.event_id)) not in h.edges("DERIVED_FROM")
    assert h.node(LESSON)["status"] == "tentative"


async def test_feedback_retrieval_from_incident_future_spec_and_natural_language(
    monkeypatch,
) -> None:
    from context_graph.retrieval.artifacts import ArtifactQuery, ArtifactRetriever
    from tests.unit.test_pack_projection import REGISTRY

    h = Harness()
    incident = {"repo": "acme/auth", "service": "reset", "incident_id": "INC-51"}
    await h.ingest("pdlc.incident.resolved", {**incident, "summary": "expiry checked"})
    await h.ingest("pdlc.change.merged", {"repo": "acme/auth", "number": 8, "merge_sha": "fix"})
    await h.ingest(
        "pdlc.incident.remediation_recorded",
        {"incident": incident, "change": {"repo": "acme/auth", "number": 8}},
    )
    with monkeypatch.context() as patch:
        patch.setattr(
            "tests.unit.test_pack_projection.uuid4",
            lambda: UUID("00000000-0000-0000-0000-000000000053"),
        )
        await h.ingest(
            "pdlc.incident.lesson_recorded",
            {
                "statement": "Check token expiry server-side",
                "incident": incident,
                "change": {"repo": "acme/auth", "number": 8},
            },
        )
    await h.ingest(
        "pdlc.spec.approved",
        {
            "doc_id": "TOKEN-EXPIRY-2027",
            "version": "2",
            "lesson_refs": [{"content_hash": LESSON.removeprefix("Lesson:")}],
        },
    )
    await h.ingest(
        "pdlc.spec.approved",
        {"doc_id": "unrelated", "version": "1", "title": "Check token expiry server-side"},
    )
    retriever = ArtifactRetriever(
        h.graph,
        REGISTRY,
        default_max_depth=3,
        seed_limit=10,
        neighbor_limit=200,
        provenance_source="memory",
    )
    queries = (
        ArtifactQuery(
            "incident lesson", seed_node_ids=("Incident:acme/auth|reset|INC-51",), intent="incident"
        ),
        ArtifactQuery(
            "incident lesson", seed_node_ids=("Spec:TOKEN-EXPIRY-2027|2",), intent="incident"
        ),
        ArtifactQuery("What incident lesson does TOKEN-EXPIRY-2027 cite?"),
    )
    for query in queries:
        response = await retriever.retrieve(query)
        assert set(response.nodes) == {
            LESSON,
            "Incident:acme/auth|reset|INC-51",
            "Change:acme/auth|8",
            "Spec:TOKEN-EXPIRY-2027|2",
        }
        assert response.nodes[LESSON].attributes["status"] == "tentative"
        assert {e.edge_type for e in response.edges} == {"LEARNED_FROM", "CITES", "REMEDIATES"}

    from pathlib import Path

    from context_graph.ontology.evaluation import load_eval_set, run_eval_set

    evaluation = load_eval_set(
        Path(__file__).parents[1] / "fixtures/ontology/pdlc-lesson.eval.yaml"
    )
    report = await run_eval_set(evaluation, retriever, max_nodes=100)
    assert report.passed
    assert report.mean_f1 == 1.0


async def test_producer_rejected_lesson_support_is_retained_but_excluded_from_retrieval(
    monkeypatch,
) -> None:
    from context_graph.retrieval.artifacts import ArtifactQuery, ArtifactRetriever
    from tests.unit.test_pack_projection import REGISTRY

    h = Harness()
    incident = {"repo": "acme/auth", "service": "reset", "incident_id": "INC-51"}
    await h.ingest("pdlc.incident.detected", incident)
    monkeypatch.setattr(
        "tests.unit.test_pack_projection.uuid4",
        lambda: UUID("00000000-0000-0000-0000-000000000053"),
    )
    await h.ingest(
        "pdlc.incident.lesson_recorded",
        {
            "statement": "Check token expiry server-side",
            "incident": incident,
            "link_status": "rejected",
        },
    )
    retriever = ArtifactRetriever(
        h.graph,
        REGISTRY,
        default_max_depth=3,
        seed_limit=10,
        neighbor_limit=200,
        provenance_source="memory",
    )
    response = await retriever.retrieve(
        ArtifactQuery("incident lesson", seed_node_ids=(LESSON,), intent="incident")
    )
    assert set(response.nodes) == {LESSON}
    assert response.edges == []
    assert (
        h.edges("LEARNED_FROM")[(LESSON, "Incident:acme/auth|reset|INC-51")]["link_status"]
        == "rejected"
    )


def test_lesson_and_typed_citation_contracts_reject_malformed_references() -> None:
    import copy

    import pytest
    from pydantic import ValidationError

    from tests.unit.test_pack_projection import REGISTRY

    lesson_contract = REGISTRY.event_types[
        "pdlc.incident.lesson_recorded"
    ].definition.payload_contract
    valid = {
        "statement": "Check token expiry server-side",
        "incident": {"repo": "acme/auth", "service": "reset", "incident_id": "INC-51"},
        "change": {"repo": "acme/auth", "number": 8},
    }
    lesson_contract.validate_payload(valid)
    for reference, fields in (
        ("incident", ("repo", "service", "incident_id")),
        ("change", ("repo", "number")),
    ):
        for field in fields:
            missing = copy.deepcopy(valid)
            del missing[reference][field]
            with pytest.raises(ValidationError):
                lesson_contract.validate_payload(missing)
            malformed = copy.deepcopy(valid)
            malformed[reference][field] = []
            with pytest.raises(ValidationError):
                lesson_contract.validate_payload(malformed)
    spec_contract = REGISTRY.event_types["pdlc.spec.approved"].definition.payload_contract
    for invalid in (
        {},
        {"content_hash": []},
        {"content_hash": "short"},
        {"content_hash": "g" * 64 + ":authored"},
    ):
        with pytest.raises(ValidationError):
            spec_contract.validate_payload(
                {"doc_id": "future", "version": "2", "lesson_refs": [invalid]}
            )


def test_citation_pattern_support_refuses_nonstring_and_backtracking_syntax() -> None:
    import pytest

    from context_graph.domain.pack_contracts import PayloadContract

    for field in ({"type": "integer", "pattern": "x"}, {"type": "string", "pattern": "(?=x)x"}):
        with pytest.raises(ValueError):
            PayloadContract.model_validate({"properties": {"reference": field}})
