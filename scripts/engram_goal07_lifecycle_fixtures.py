"""Independent G07-B ticket/PR/commit producers and literal graph oracles (#55).

Reviewer text declares Review records only, not REVIEWS or authenticated approval.
No-PR commits are ledger-only; their expected artifact set is empty.
"""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5


def fixtures(run_id, *, start=None):
    prefix = "g07/" + run_id
    repo = prefix + "/auth"
    start = start or (datetime.now(UTC) - timedelta(minutes=10)).replace(microsecond=0)
    parent, child, cancelled = (
        "WorkItem:jira|RESET-1",
        "WorkItem:jira|RESET-17",
        "WorkItem:jira|RESET-18",
    )
    requirement = "Requirement:" + prefix + "/requirements|1|expiry"
    design = "DesignElement:" + prefix + "/design|tokens|1"
    change, merged, reviewed = (
        "Change:" + repo + "|17",
        "Change:" + repo + "|18",
        "Change:" + repo + "|19",
    )
    ann, bo = "Review:" + repo + "|19|Ann <a@x>", "Review:" + repo + "|19|Bo <b@x>"
    ids = dict(
        parent=parent,
        child=child,
        cancelled=cancelled,
        requirement=requirement,
        design=design,
        change=change,
        merged=merged,
        reviewer_change=reviewed,
        ann=ann,
        bo=bo,
    )
    steps = []

    def add(sid, event_type, payload, node=None, props=None, edges=(), extra=None, **flags):
        request = dict(
            event_id=str(uuid5(NAMESPACE_URL, prefix + "/lifecycle:" + sid)),
            event_type="pdlc." + event_type,
            occurred_at=(start + timedelta(seconds=len(steps))).isoformat(),
            session_id=prefix + "/lifecycle",
            agent_id="lifecycle.publisher",
            trace_id=run_id,
            payload_ref="synthetic:" + prefix + ":" + sid,
            payload=deepcopy(payload),
        )
        step = dict(
            scenario=sid,
            request=request,
            expected_status=201,
            expected_node=node,
            expected_props=props or {},
            expected_edges=[list(e) for e in edges],
            extra_nodes=extra or {},
            **flags,
        )
        if "expected_observed_node_ids" not in step:
            step["expected_observed_node_ids"] = sorted(
                ([node] if node else [])
                + (
                    [key for key in step["extra_nodes"] if key.startswith("Review:")]
                    if event_type == "change.committed"
                    else []
                )
            )
        steps.append(step)
        return step

    add(
        "B01-parent",
        "ticket.created",
        dict(tracker="jira", key="RESET-1", title="Reset epic", work_type="epic", status="To Do"),
        parent,
        dict(title="Reset epic", status="open"),
    )
    ticket = dict(
        tracker="jira",
        key="RESET-17",
        title="Reset story",
        work_type="story",
        parent_key="RESET-1",
        requirements=[dict(spec_id=prefix + "/requirements", spec_version="1", local_id="expiry")],
        designs=[dict(doc_id=prefix + "/design", section_path="tokens", version="1")],
    )
    ticket_edges = [
        ("DECOMPOSES_INTO", parent, child),
        ("IMPLEMENTS", child, requirement),
        ("IMPLEMENTS", child, design),
    ]
    extra = {requirement: {}, design: {}}
    add(
        "B01-child",
        "ticket.created",
        dict(ticket, status="To Do"),
        child,
        dict(title="Reset story", status="open"),
        ticket_edges,
        extra,
    )
    updated = add(
        "B01-update",
        "ticket.updated",
        dict(ticket, title="Enforce token expiry", status="In Progress"),
        child,
        dict(title="Enforce token expiry", status="in_progress"),
        ticket_edges,
        extra,
    )
    retry = deepcopy(updated)
    retry.update(scenario="B01-update-retry", duplicate=True)
    steps.append(retry)
    add(
        "B02-done",
        "ticket.closed",
        dict(tracker="jira", key="RESET-17", status="Done", resolution="Fixed"),
        child,
        dict(title="Enforce token expiry", status="done", resolution="Fixed"),
        forbidden_edge_types=["EXECUTES", "RAN_AGAINST"],
    )
    add(
        "B02-cancelled",
        "ticket.closed",
        dict(
            tracker="jira",
            key="RESET-18",
            title="Alternative reset",
            status="Won't Do",
            resolution="Declined",
        ),
        cancelled,
        dict(status="cancelled", resolution="Declined"),
    )
    base = dict(
        repo=repo,
        number=17,
        title="Enforce expiry",
        work_items=[dict(tracker="jira", external_key="RESET-17")],
    )
    add(
        "B03-open",
        "change.created",
        base,
        change,
        dict(status="open"),
        [("IMPLEMENTS", change, child)],
    )
    add(
        "B03-abandon",
        "change.abandoned",
        dict(repo=repo, number=17, title="Enforce expiry"),
        change,
        dict(status="abandoned"),
    )
    add(
        "B03-reopen",
        "change.created",
        base,
        change,
        dict(status="open"),
        [("IMPLEMENTS", change, child)],
    )
    add(
        "B03-merged",
        "change.merged",
        dict(repo=repo, number=18, title="Merged control", body="", files=[]),
        merged,
        dict(status="merged"),
    )
    add(
        "B03-late-abandon",
        "change.abandoned",
        dict(repo=repo, number=18, title="Merged control"),
        merged,
        dict(status="merged"),
    )
    add(
        "B04-commit",
        "change.committed",
        dict(
            repo=repo,
            subject="fix(tokens): enforce expiry (#17)",
            body="Fixes RESET-17",
            files=["src/token.py"],
        ),
        change,
        dict(
            status="open",
            change_type="fix",
            scope="tokens",
            ticket_exempt=False,
            files=["src/token.py"],
            title="fix(tokens): enforce expiry (#17)",
        ),
        [("IMPLEMENTS", change, child)],
    )
    add(
        "B05-no-pr",
        "change.committed",
        dict(
            repo=repo,
            subject="fix(tokens): enforce expiry",
            body="Fixes RESET-999\nReviewers: Eve <e@x>",
            files=["src/token.py"],
        ),
        ledger_only=True,
        expected_observed_node_ids=[],
        forbidden_nodes=["WorkItem:jira|RESET-999"],
        forbidden_node_types=["Change", "Review", "WorkItem"],
    )
    add(
        "B06-reviewer-text",
        "change.committed",
        dict(
            repo=repo,
            subject="fix(tokens): reviewer text (#19)",
            body="Reviewers: Ann <a@x>, Bo <b@x>",
            files=[],
        ),
        reviewed,
        dict(status="open", change_type="fix", scope="tokens", ticket_exempt=False),
        extra={ann: dict(verdict="approved"), bo: dict(verdict="approved")},
        forbidden_edge_types=["REVIEWS"],
        semantic_limit=(
            "Text-derived Review verdict approved is neither REVIEWS nor authenticated approval"
        ),
    )

    queries = [
        dict(
            scenario="BQ1-ticket-trace",
            seed=parent,
            seeds=[parent],
            intent="trace",
            text="trace reset ticket implementation",
            required=[parent, child, requirement, design, change],
            forbidden=[cancelled, merged, reviewed, ann, bo],
            exact=True,
            max_depth=3,
            expected_edges=[list(e) for e in ticket_edges + [("IMPLEMENTS", change, child)]],
        ),
        dict(
            scenario="BQ2-cancelled",
            seed=cancelled,
            seeds=[cancelled],
            intent="trace",
            text="trace cancelled alternative",
            required=[cancelled],
            forbidden=[parent, child, requirement, design, change, merged, reviewed, ann, bo],
            exact=True,
            max_depth=3,
            expected_edges=[],
        ),
        dict(
            scenario="BQ3-merged-guard",
            seed=merged,
            seeds=[merged],
            intent="trace",
            text="trace merged control",
            required=[merged],
            forbidden=[parent, child, requirement, design, change, cancelled, reviewed, ann, bo],
            exact=True,
            max_depth=3,
            expected_edges=[],
        ),
        dict(
            scenario="BQ4-reviewer-text-is-disconnected",
            seed=ann,
            seeds=[ann],
            intent="trace",
            text="trace reviewer text",
            required=[ann],
            forbidden=[parent, child, requirement, design, change, cancelled, merged, reviewed, bo],
            exact=True,
            max_depth=3,
            expected_edges=[],
        ),
    ]
    return dict(
        ids=ids,
        steps=steps,
        queries=queries,
        fallback_seed=child,
        source_kind=(
            "Synthetic normalized ticket/PR/commit producers; bounded text reviewer records"
        ),
    )
