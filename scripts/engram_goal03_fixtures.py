"""G03 synthetic normalized producer inputs and predeclared exact expectations."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5


def fixtures(run_id):
    prefix = "g03/" + run_id
    repo = prefix + "/payments"
    other_repo = prefix + "/newsletter"
    spec = prefix + "-reset"
    other_spec = prefix + "-newsletter"
    req = dict(spec_id=spec, spec_version="1", local_id="expiry")
    design = dict(doc_id=prefix + "-lld", section_path="storage", version="1")
    ticket = dict(tracker="jira", external_key=prefix + "-17")
    other_ticket = dict(tracker="linear", external_key=prefix + "-17")
    ids = dict(
        spec=f"Spec:{spec}|1",
        expiry=f"Requirement:{spec}|1|expiry",
        hld=f"DesignElement:{prefix}-hld|tokens|1",
        lld=f"DesignElement:{prefix}-lld|storage|1",
        ticket=f"WorkItem:jira|{prefix}-17",
        change=f"Change:{repo}|7",
        review_bad=f"Review:{repo}|7|alex-1",
        review_good=f"Review:{repo}|7|robin-2",
        test=f"TestCase:{repo}|expiry",
        run_bad=f"TestRun:{prefix}-failure",
        run_good=f"TestRun:{prefix}-success",
        other_spec=f"Spec:{other_spec}|1",
        other_req=f"Requirement:{other_spec}|1|expiry",
        other_ticket=f"WorkItem:linear|{prefix}-17",
        other_change=f"Change:{other_repo}|7",
        other_test=f"TestCase:{other_repo}|expiry",
        other_run=f"TestRun:{prefix}-other",
        unlinked=f"Change:{repo}|8",
        unlinked_test=f"TestCase:{repo}|unmapped",
        unlinked_run=f"TestRun:{prefix}-unmapped",
    )
    steps = []
    start = datetime.now(UTC) - timedelta(minutes=5)

    def add(sid, event_type, payload, node=None, props=None, edges=(), status=201, extra=None):
        steps.append(
            dict(
                scenario=sid,
                request=dict(
                    event_id=str(uuid5(NAMESPACE_URL, run_id + ":" + sid)),
                    event_type=event_type,
                    occurred_at=(start + timedelta(seconds=len(steps))).isoformat(),
                    session_id="implementation:" + prefix,
                    agent_id="implementation.publisher",
                    trace_id=run_id,
                    payload_ref="synthetic:" + run_id + ":" + sid,
                    payload=payload,
                ),
                expected_status=status,
                expected_node=node,
                expected_props=props or {},
                expected_edges=[list(e) for e in edges],
                extra_nodes=extra or {},
            )
        )

    add(
        "IM01",
        "pdlc.spec.changed",
        dict(doc_id=spec, version="1", title="Password reset PRD"),
        ids["spec"],
        dict(title="Password reset PRD"),
    )
    add(
        "IM02",
        "pdlc.requirement.changed",
        dict(req, statement="Reset token expires in fifteen minutes"),
        ids["expiry"],
        dict(statement="Reset token expires in fifteen minutes"),
        [("REFINES", ids["expiry"], ids["spec"])],
    )
    add(
        "IM03",
        "pdlc.design.section_changed",
        dict(
            doc_id=prefix + "-hld",
            section_path="tokens",
            version="1",
            kind="hld",
            body="Reset service validates token expiry.",
            requirements=[req],
        ),
        ids["hld"],
        dict(kind="hld"),
        [("REFINES", ids["hld"], ids["expiry"])],
    )
    add(
        "IM04",
        "pdlc.design.section_changed",
        dict(
            design,
            kind="lld",
            body="Store a token digest and expires_at; reject expired tokens.",
            requirements=[req],
            refines_designs=[dict(doc_id=prefix + "-hld", section_path="tokens", version="1")],
        ),
        ids["lld"],
        dict(kind="lld"),
        [("REFINES", ids["lld"], ids["hld"]), ("REFINES", ids["lld"], ids["expiry"])],
    )
    ticket_payload = dict(
        tracker=ticket["tracker"],
        key=ticket["external_key"],
        title="Implement reset expiry",
        work_type="task",
        status="To Do",
        requirements=[req],
        designs=[design],
    )
    add(
        "IM05",
        "pdlc.ticket.created",
        ticket_payload,
        ids["ticket"],
        dict(title="Implement reset expiry"),
        [("IMPLEMENTS", ids["ticket"], ids["expiry"]), ("IMPLEMENTS", ids["ticket"], ids["lld"])],
    )
    change = dict(
        repo=repo,
        number=7,
        title="Reject expired password-reset tokens",
        head_sha="abc123",
        work_items=[ticket],
    )
    add(
        "IM06",
        "pdlc.change.created",
        change,
        ids["change"],
        dict(head_sha="abc123", title="Reject expired password-reset tokens"),
        [("IMPLEMENTS", ids["change"], ids["ticket"])],
    )
    for sid, key, reviewer, verdict in [
        ("IM07-requested", "review_bad", "Alex", "changes_requested"),
        ("IM07-approved", "review_good", "Robin", "approved"),
    ]:
        review_id = "alex-1" if key == "review_bad" else "robin-2"
        add(
            sid,
            "pdlc.change.reviewed",
            dict(repo=repo, number=7, review_id=review_id, reviewer=reviewer, verdict=verdict),
            ids[key],
            dict(verdict=verdict, reviewer=reviewer),
            [("REVIEWS", ids[key], ids["change"])],
        )
    for sid, key, outcome in [
        ("IM08-failure", "run_bad", "failure"),
        ("IM08-success", "run_good", "success"),
    ]:
        payload = dict(
            repo=repo,
            test_id="expiry",
            run_id=ids[key].removeprefix("TestRun:"),
            outcome=outcome,
            name="Reject expired reset token",
            path="tests/test_expiry.py",
            commit_sha="abc123",
            change_number=7,
            requirements=[req],
        )
        add(
            sid,
            "pdlc.testcaserun.finished",
            payload,
            ids[key],
            dict(outcome=outcome, commit_sha="abc123"),
            [
                ("EXECUTES", ids[key], ids["test"]),
                ("RAN_AGAINST", ids[key], ids["change"]),
                ("VERIFIES", ids["test"], ids["expiry"]),
            ],
            extra={
                ids["test"]: dict(name="Reject expired reset token", path="tests/test_expiry.py")
            },
        )
    add(
        "IM09-spec",
        "pdlc.spec.changed",
        dict(doc_id=other_spec, version="1", title="Newsletter PRD"),
        ids["other_spec"],
        dict(title="Newsletter PRD"),
    )
    other_req = dict(spec_id=other_spec, spec_version="1", local_id="expiry")
    add(
        "IM09-requirement",
        "pdlc.requirement.changed",
        dict(other_req, statement="Newsletter link lasts seven days"),
        ids["other_req"],
        dict(statement="Newsletter link lasts seven days"),
        [("REFINES", ids["other_req"], ids["other_spec"])],
    )
    add(
        "IM09-ticket",
        "pdlc.ticket.created",
        dict(
            tracker="linear",
            key=ticket["external_key"],
            title="Newsletter expiry",
            requirements=[other_req],
        ),
        ids["other_ticket"],
        dict(title="Newsletter expiry"),
        [("IMPLEMENTS", ids["other_ticket"], ids["other_req"])],
    )
    add(
        "IM09-change",
        "pdlc.change.created",
        dict(repo=other_repo, number=7, title="Newsletter expiry", work_items=[other_ticket]),
        ids["other_change"],
        dict(title="Newsletter expiry"),
        [("IMPLEMENTS", ids["other_change"], ids["other_ticket"])],
    )
    add(
        "IM09-test",
        "pdlc.testcaserun.finished",
        dict(
            repo=other_repo,
            test_id="expiry",
            run_id=prefix + "-other",
            outcome="success",
            commit_sha="def456",
            change_number=7,
            requirements=[other_req],
        ),
        ids["other_run"],
        dict(outcome="success", commit_sha="def456"),
        [
            ("EXECUTES", ids["other_run"], ids["other_test"]),
            ("RAN_AGAINST", ids["other_run"], ids["other_change"]),
            ("VERIFIES", ids["other_test"], ids["other_req"]),
        ],
        extra={ids["other_test"]: {}},
    )
    add(
        "IM10-change",
        "pdlc.change.created",
        dict(repo=repo, number=8, title="Unlinked maintenance"),
        ids["unlinked"],
        dict(title="Unlinked maintenance"),
    )
    add(
        "IM10-test",
        "pdlc.testcaserun.finished",
        dict(repo=repo, test_id="unmapped", run_id=prefix + "-unmapped", outcome="failure"),
        ids["unlinked_run"],
        dict(outcome="failure"),
        [("EXECUTES", ids["unlinked_run"], ids["unlinked_test"])],
        extra={ids["unlinked_test"]: {}},
    )
    duplicate = deepcopy(steps[9])
    duplicate.update(
        scenario="IM11-duplicate", expected_node=None, expected_edges=[], extra_nodes={}
    )
    steps.append(duplicate)
    conflict = deepcopy(duplicate)
    conflict.update(scenario="IM11-conflict", expected_status=409)
    conflict["request"]["payload"]["outcome"] = "failure"
    steps.append(conflict)
    bad_req = dict(req)
    bad_req.pop("spec_version")
    add(
        "IM12-revision",
        "pdlc.ticket.created",
        dict(ticket_payload, requirements=[bad_req]),
        status=422,
    )
    add(
        "IM12-ticket",
        "pdlc.change.created",
        dict(change, work_items=[dict(tracker="jira")]),
        status=422,
    )
    add(
        "IM12-review",
        "pdlc.change.reviewed",
        dict(repo=repo, number=7, review_id="invalid", verdict="unknown"),
        status=422,
    )
    add(
        "IM12-test",
        "pdlc.testcaserun.finished",
        dict(repo=repo, test_id="expiry", run_id=prefix + "-invalid", outcome="passed"),
        status=422,
    )
    required = [
        ids[k]
        for k in [
            "spec",
            "expiry",
            "hld",
            "lld",
            "ticket",
            "change",
            "review_bad",
            "review_good",
            "test",
            "run_bad",
            "run_good",
        ]
    ]
    forbidden = [
        ids[k]
        for k in [
            "other_spec",
            "other_req",
            "other_ticket",
            "other_change",
            "other_test",
            "other_run",
            "unlinked",
            "unlinked_test",
            "unlinked_run",
        ]
    ]
    queries = [
        dict(
            scenario="IM13-" + key,
            seed=ids[key],
            intent="trace",
            required=required,
            forbidden=forbidden,
        )
        for key in ["expiry", "lld", "change", "test"]
    ]
    queries.append(
        dict(
            scenario="IM13-text",
            seed=None,
            text="fifteen minutes",
            intent="trace",
            required=[ids["expiry"]],
            forbidden=forbidden,
        )
    )
    return dict(
        source="Synthetic explicitly normalized producer records; no captured native-source claim.",
        ids=ids,
        steps=steps,
        queries=queries,
    )
