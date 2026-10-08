"""G07-B commit parsing and existing lifecycle behavior at public boundaries."""

from datetime import UTC, datetime
from uuid import UUID

from context_graph.domain.models import Event
from context_graph.domain.pack_projection import PackProjector
from context_graph.domain.projection import event_to_node
from context_graph.ontology import load_registry

REGISTRY = load_registry(["pdlc"])
AT = datetime(2026, 10, 8, tzinfo=UTC)
EVENT_ID = UUID("07000000-0000-0000-0000-000000000055")


def plan(event_type, payload):
    REGISTRY.event_types[event_type].definition.payload_contract.validate_payload(payload)
    event = Event(
        event_id=EVENT_ID,
        event_type=event_type,
        occurred_at=AT,
        session_id="g07-b",
        agent_id="fixture",
        trace_id="g07-b",
        payload_ref="fixture",
        global_position="1-0",
    )
    return PackProjector(REGISTRY, frozenset({"fixture"})).plan(event, {"payload": payload})


def test_commit_without_pr_suffix_is_ledger_only_even_with_tickets_and_reviewers():
    result = plan(
        "pdlc.change.committed",
        dict(
            repo="g07/auth",
            subject="fix(tokens): enforce expiry",
            body="Fixes RESET-17\nReviewers: Ann <a@x>",
            files=["src/token.py"],
        ),
    )
    assert result.empty
    assert result.rejected == []


def test_pr_commit_retains_declared_ticket_link_and_bounded_reviewer_records():
    result = plan(
        "pdlc.change.committed",
        dict(
            repo="g07/auth",
            subject="fix(tokens): enforce expiry (#17)",
            body="Fixes RESET-17\nReviewers: Ann <a@x>, Bo <b@x>",
            files=["src/token.py"],
        ),
    )
    observed = {n.ref.key: n.properties for n in result.nodes if "source_trust" in n.properties}
    assert set(observed) == {
        "Change:g07/auth|17",
        "Review:g07/auth|17|Ann <a@x>",
        "Review:g07/auth|17|Bo <b@x>",
    }
    change = observed["Change:g07/auth|17"]
    assert (change["change_type"], change["scope"], change["ticket_exempt"]) == (
        "fix",
        "tokens",
        False,
    )
    assert change["files"] == ["src/token.py"]
    domain = [e for e in result.edges if e.edge_type != "DERIVED_FROM"]
    assert [(e.edge_type, e.source.key, e.target.key) for e in domain] == [
        ("IMPLEMENTS", "Change:g07/auth|17", "WorkItem:jira|RESET-17")
    ]
    assert domain[0].properties == dict(
        confidence=1.0, method="declared", link_status="confirmed", source_trust="trusted"
    )
    for key in ("Review:g07/auth|17|Ann <a@x>", "Review:g07/auth|17|Bo <b@x>"):
        assert observed[key]["verdict"] == "approved"
        assert "reviewer" not in observed[key]
    # These text-derived records have no REVIEWS relation and no approval authentication.
    assert not any(e.edge_type == "REVIEWS" for e in result.edges)


async def test_ticket_progression_and_closure_preserve_identity_and_evidence():
    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.worker.pack_projection import apply_plan

    graph = MemoryGraphStore()
    projector = PackProjector(REGISTRY, frozenset({"fixture"}))

    async def ingest(sequence, event_type, payload):
        REGISTRY.event_types[event_type].definition.payload_contract.validate_payload(payload)
        event = Event(
            event_id=UUID(int=sequence),
            event_type=event_type,
            occurred_at=AT,
            session_id="g07-b",
            agent_id="fixture",
            trace_id="g07-b",
            payload_ref="fixture",
            global_position="1-0",
        )
        await graph.merge_event_node(event_to_node(event))
        await apply_plan(graph, projector.plan(event, {"payload": payload}), 100)

    base = dict(tracker="jira", key="RESET-17", title="Reset", work_type="story")
    await ingest(1, "pdlc.ticket.created", dict(base, status="To Do", parent_key="RESET-1"))
    await ingest(2, "pdlc.ticket.updated", dict(base, title="Enforce expiry", status="In Progress"))
    assert graph.nodes[("WorkItem", "WorkItem:jira|RESET-17")]["status"] == "in_progress"
    assert graph.nodes[("WorkItem", "WorkItem:jira|RESET-17")]["title"] == "Enforce expiry"
    await ingest(3, "pdlc.ticket.closed", dict(base, status="Done", resolution="Fixed"))
    await ingest(
        4,
        "pdlc.ticket.closed",
        dict(base, key="RESET-18", status="Won't Do", resolution="Declined"),
    )
    assert graph.nodes[("WorkItem", "WorkItem:jira|RESET-17")]["status"] == "done"
    assert graph.nodes[("WorkItem", "WorkItem:jira|RESET-17")]["resolution"] == "Fixed"
    assert graph.nodes[("WorkItem", "WorkItem:jira|RESET-18")]["status"] == "cancelled"
    assert graph.nodes[("WorkItem", "WorkItem:jira|RESET-18")]["resolution"] == "Declined"
    assert (
        ("WorkItem", "WorkItem:jira|RESET-1"),
        "DECOMPOSES_INTO",
        ("WorkItem", "WorkItem:jira|RESET-17"),
    ) in graph.edges
    evidence = {
        target[1]
        for (source, kind, target) in graph.edges
        if source[1] == "WorkItem:jira|RESET-17" and kind == "DERIVED_FROM"
    }
    assert evidence == {str(UUID(int=1)), str(UUID(int=2)), str(UUID(int=3))}
    assert all(kind not in {"IMPLEMENTS", "EXECUTES", "RAN_AGAINST"} for _, kind, _ in graph.edges)


async def test_abandon_reopen_and_late_abandon_after_merge_obey_existing_guards():
    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.worker.pack_projection import apply_plan

    graph = MemoryGraphStore()
    projector = PackProjector(REGISTRY, frozenset({"fixture"}))
    base = dict(repo="g07/auth", number=17, title="Reset")
    for sequence, (event_type, expected) in enumerate(
        [
            ("pdlc.change.created", "open"),
            ("pdlc.change.abandoned", "abandoned"),
            ("pdlc.change.created", "open"),
            ("pdlc.change.merged", "merged"),
            ("pdlc.change.abandoned", "merged"),
            ("pdlc.change.created", "merged"),
        ],
        1,
    ):
        event = Event(
            event_id=UUID(int=sequence),
            event_type=event_type,
            occurred_at=AT,
            session_id="g07-b",
            agent_id="fixture",
            trace_id="g07-b",
            payload_ref="fixture",
            global_position="1-0",
        )
        REGISTRY.event_types[event_type].definition.payload_contract.validate_payload(base)
        await graph.merge_event_node(event_to_node(event))
        await apply_plan(graph, projector.plan(event, {"payload": base}), 100)
        assert graph.nodes[("Change", "Change:g07/auth|17")]["status"] == expected
    assert {key for kind, key in graph.nodes if kind == "Change"} == {"Change:g07/auth|17"}
    evidence = {target[1] for (source, kind, target) in graph.edges if kind == "DERIVED_FROM"}
    assert evidence == {str(UUID(int=i)) for i in range(1, 7)}
