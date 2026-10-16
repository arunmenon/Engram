"""Small completion stories with independently declared graph/read expectations.

Business data is never inserted here. The existing pilot runner ingests these
Events and verifies them through Engram's public flows on retained Spanner.
"""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from engram_goal03_implementation_demo import fixture_observations


def p03_user_stories(run_id):
    """Reuse eight authored stories; add attribution and named-context diagnostics.

    Correction is a second phase: its predecessor must be an actually accepted
    Preference identity. No model output is invented during fixture construction.
    """
    from engram_pilot_spectrum import freeze

    groups = [g for g in freeze(run_id)["groups"] if g.get("user_story")]
    contexts = next(g for g in groups if g["name"] == "user-contexts")
    contexts["diagnostic_queries"] = [
        dict(query="How should you respond to me during incident response?", intent="personalize"),
        dict(query="How should you respond to me during a design review?", intent="personalize"),
    ]
    for key, name, content, diagnostics in (
        (
            "third-person",
            "Leela",
            "Omar prefers trains to flights. That is Omar's preference, not mine. "
            "I have not stated any travel preference.",
            [],
        ),
        (
            "mercury",
            "Dev",
            "Our software project is named Mercury. The planet Mercury is a different thing. "
            "This is a description of two things, not my preference or skill.",
            [dict(query="What do we know about Mercury?", intent="related")],
        ),
    ):
        session, owner = run_id + ":story:" + key, run_id + ":owner:" + key
        start = datetime.now(UTC) - timedelta(minutes=4)
        steps = []
        for suffix, kind, payload in (
            ("source", "observation.input", dict(content=f"My name is {name}. {content}")),
            ("end", "system.session_end", {}),
        ):
            steps.append(
                dict(
                    scenario=key + "-" + suffix,
                    expected_status=201,
                    request=dict(
                        event_id=str(uuid5(NAMESPACE_URL, session + ":" + suffix)),
                        event_type=kind,
                        occurred_at=(start + timedelta(seconds=len(steps))).isoformat(),
                        session_id=session,
                        agent_id=owner,
                        trace_id=run_id,
                        payload_ref="pilot-story:" + key,
                        payload=payload,
                    ),
                )
            )
        groups.append(
            dict(
                name="user-" + key,
                tenant="a",
                user_story=True,
                steps=steps,
                queries=[],
                owner=owner,
                session=session,
                question="What personal preferences did I actually state?",
                expect_user=True,
                expect_preferences=False,
                expected_name=name,
                preference_semantics=[],
                diagnostic_queries=diagnostics,
                source_kind=(
                    "Actual model attribution control; "
                    "diagnostic behavior is not a capability pass"
                ),
            )
        )
    return groups


def p02_history(run_id):
    prefix = "p02/" + run_id
    repo = prefix + "/auth"
    spec = prefix + "/spec"
    marker = "coverageprobe" + sha256(run_id.encode()).hexdigest()[:10]
    ticket_key = "P" + sha256(run_id.encode()).hexdigest()[:10].upper() + "-17"
    ids = {
        "spec1": f"Spec:{spec}|1",
        "spec2": f"Spec:{spec}|2",
        "req1": f"Requirement:{spec}|1|expiry",
        "req2": f"Requirement:{spec}|2|expiry",
        "missing": f"Requirement:{spec}|1|missing",
        "proposed": f"Requirement:{spec}|1|proposed",
        "ticket": f"WorkItem:jira|{ticket_key}",
        "change": f"Change:{repo}|17",
        "case": f"TestCase:{repo}|expiry",
        "failed": f"TestRun:{prefix}/failed",
        "passed": f"TestRun:{prefix}/passed",
        "planned_case": f"TestCase:{repo}|{marker}",
        "skipped": f"TestRun:{prefix}/skipped",
        "review": f"Review:{repo}|17|review-1",
        "component": f"Component:{prefix}/tokens",
        "incident": f"Incident:{repo}|{prefix}/tokens|INC-17",
    }
    steps = []
    start = (datetime.now(UTC) - timedelta(minutes=4)).replace(microsecond=0)

    def add(sid, kind, payload, node=None, props=None, edges=(), extra=None, **flags):
        request = {
            "event_id": str(uuid5(NAMESPACE_URL, prefix + ":" + sid)),
            "event_type": kind,
            "occurred_at": (start + timedelta(seconds=len(steps))).isoformat(),
            "session_id": prefix,
            "agent_id": "completion.publisher",
            "trace_id": run_id,
            "payload_ref": "pilot-completion:" + sid,
            "payload": payload,
        }
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
        steps.append(step)
        return step

    def requirement(local, version="1"):
        return dict(spec_id=spec, spec_version=version, local_id=local)

    add(
        "H01-spec1",
        "pdlc.spec.changed",
        dict(doc_id=spec, version="1", title="Password reset hotfix"),
        ids["spec1"],
        dict(title="Password reset hotfix", status="draft"),
    )
    for key, statement in [
        ("expiry", "Token expires in fifteen minutes"),
        ("missing", "No coverage observation supplied for this requirement"),
        ("proposed", marker + " selective coverage assertion"),
    ]:
        nid = ids["req1" if key == "expiry" else key]
        add(
            "H02-" + key,
            "pdlc.requirement.changed",
            dict(requirement(key), statement=statement),
            nid,
            dict(statement=statement),
            [("REFINES", nid, ids["spec1"])],
        )
    add(
        "H03-ticket",
        "pdlc.ticket.created",
        dict(
            tracker="jira",
            key=ticket_key,
            title="Emergency token expiry repair",
            work_type="production_change",
            status="To Do",
            requirements=[requirement("expiry")],
        ),
        ids["ticket"],
        dict(title="Emergency token expiry repair", status="open"),
        [("IMPLEMENTS", ids["ticket"], ids["req1"])],
    )
    add(
        "H04-pr",
        "pdlc.change.created",
        dict(
            repo=repo,
            number=17,
            title="Repair token expiry",
            body="",
            files=[],
            work_items=[dict(tracker="jira", external_key=ticket_key)],
        ),
        ids["change"],
        dict(status="open", title="Repair token expiry"),
        [("IMPLEMENTS", ids["change"], ids["ticket"])],
    )
    add(
        "H05-failed",
        "pdlc.testcaserun.finished",
        dict(
            repo=repo,
            test_id="expiry",
            run_id=prefix + "/failed",
            outcome="failure",
            name="Token expiry regression",
            path="tests/expiry.py",
            commit_sha="broken-sha",
            change_number=17,
            requirements=[requirement("expiry")],
        ),
        ids["failed"],
        dict(outcome="failure", commit_sha="broken-sha"),
        [
            ("EXECUTES", ids["failed"], ids["case"]),
            ("RAN_AGAINST", ids["failed"], ids["change"]),
            ("VERIFIES", ids["case"], ids["req1"]),
        ],
        {ids["case"]: dict(name="Token expiry regression", path="tests/expiry.py")},
    )
    add(
        "H06-spec2",
        "pdlc.spec.changed",
        dict(doc_id=spec, version="2", title="Revised reset policy"),
        ids["spec2"],
        dict(title="Revised reset policy", status="draft"),
    )
    add(
        "H07-req2",
        "pdlc.requirement.changed",
        dict(requirement("expiry", "2"), statement="Token expires in ten minutes"),
        ids["req2"],
        dict(statement="Token expires in ten minutes"),
        [("REFINES", ids["req2"], ids["spec2"])],
    )
    add(
        "H08-planned-case",
        "pdlc.testcaserun.skipped",
        dict(
            repo=repo,
            test_id=marker,
            run_id=prefix + "/skipped",
            outcome="skipped",
            name=marker,
            path="tests/" + marker + ".py",
        ),
        ids["skipped"],
        dict(outcome="skipped"),
        [("EXECUTES", ids["skipped"], ids["planned_case"])],
        {ids["planned_case"]: dict(name=marker, path="tests/" + marker + ".py")},
    )
    prose = add(
        "H09-proposed-coverage",
        "observation.input",
        dict(
            content=(
                f"{marker}: {ids['planned_case']} checks {ids['proposed']}. "
                "This coverage relationship is a proposal; the execution was skipped. "
                "We choose bounded processing because buffering an entire workspace is unsafe. "
                "That engineering choice is a proposal, not an accepted decision."
            )
        ),
        requires_pack_output=True,
        required_proposed_edges=[
            dict(
                kind="VERIFIES",
                source=ids["planned_case"],
                target=ids["proposed"],
                method="inferred",
                link_status="proposed",
            )
        ],
    )
    statement = prefix + ": Explicitly accept bounded token-repair processing"
    decision = "Decision:" + sha256(statement.encode()).hexdigest()
    ids["decision"] = decision
    add(
        "H10-accepted-decision",
        "pdlc.decision.recorded",
        dict(
            statement=statement,
            rationale="Operator-approved engineering policy",
            applies_to_node_ids=[ids["req2"]],
        ),
        decision,
        dict(statement=statement, status="accepted"),
        [("APPLIES_TO", decision, ids["req2"])],
    )
    add(
        "H11-review",
        "pdlc.change.reviewed",
        dict(repo=repo, number=17, review_id="review-1", reviewer="Robin", verdict="approved"),
        ids["review"],
        dict(reviewer="Robin", verdict="approved"),
        [("REVIEWS", ids["review"], ids["change"])],
        node_assertions={ids["change"]: dict(status="reviewed")},
    )
    add(
        "H12-passed",
        "pdlc.testcaserun.finished",
        dict(
            repo=repo,
            test_id="expiry",
            run_id=prefix + "/passed",
            outcome="success",
            name="Token expiry regression",
            path="tests/expiry.py",
            commit_sha="fixed-sha",
            change_number=17,
            requirements=[requirement("expiry")],
        ),
        ids["passed"],
        dict(outcome="success", commit_sha="fixed-sha"),
        [
            ("EXECUTES", ids["passed"], ids["case"]),
            ("RAN_AGAINST", ids["passed"], ids["change"]),
            ("VERIFIES", ids["case"], ids["req1"]),
        ],
        {ids["case"]: dict(name="Token expiry regression", path="tests/expiry.py")},
    )
    add(
        "H13-merge",
        "pdlc.change.merged",
        dict(
            repo=repo,
            number=17,
            title="Repair token expiry",
            body="",
            files=[],
            merge_sha="fixed-sha",
        ),
        ids["change"],
        dict(status="merged", merge_sha="fixed-sha"),
    )
    add(
        "H14-incident",
        "pdlc.incident.detected",
        dict(
            repo=repo,
            service=prefix + "/tokens",
            incident_id="INC-17",
            description="Expired tokens were accepted",
            severity="high",
        ),
        ids["incident"],
        dict(status="detected"),
        [("AFFECTS", ids["incident"], ids["component"])],
        {ids["component"]: {}},
    )
    remediation = add(
        "H15-remediation",
        "pdlc.incident.remediation_recorded",
        dict(
            change=dict(repo=repo, number=17),
            incident=dict(repo=repo, service=prefix + "/tokens", incident_id="INC-17"),
        ),
        edges=[("REMEDIATES", ids["change"], ids["incident"])],
        expected_observed_node_ids=[],
    )
    remediation["expected_edge_properties"] = [
        [
            "REMEDIATES",
            ids["change"],
            ids["incident"],
            dict(source_event_id=remediation["request"]["event_id"], pinned_position="$receipt"),
        ]
    ]
    deployed_at = (start + timedelta(seconds=len(steps))).isoformat()
    ids["deployment"] = f"Deployment:{repo}|{prefix}/tokens|production|fixed-sha|{deployed_at}"
    add(
        "H16-deploy",
        "pdlc.service.deployed",
        dict(
            repo=repo,
            service=prefix + "/tokens",
            environment="production",
            artifact_id="fixed-sha",
            change_numbers=[17],
        ),
        ids["deployment"],
        dict(status="succeeded"),
        [
            ("DEPLOYS", ids["deployment"], ids["change"]),
            ("DEPLOYED_TO", ids["deployment"], ids["component"]),
        ],
        {ids["component"]: {}},
    )
    add(
        "H17-resolved",
        "pdlc.incident.resolved",
        dict(repo=repo, service=prefix + "/tokens", incident_id="INC-17"),
        ids["incident"],
        dict(status="resolved"),
    )
    sources = {}
    for step in steps:
        for nid in fixture_observations(step):
            sources.setdefault(nid, []).append(step["request"]["event_id"])
    queries = [
        dict(
            scenario="HQ1-new-revision-does-not-inherit-work",
            intent="trace",
            text="trace",
            seeds=[ids["req2"]],
            required=[ids["req2"], ids["spec2"]],
            forbidden=[ids[k] for k in ("ticket", "change", "case", "failed", "passed")],
            max_depth=5,
            exact=True,
            after_scenario="H07-req2",
            expected_edges=[["REFINES", ids["req2"], ids["spec2"]]],
        ),
        dict(
            scenario="HQ2-old-revision-retains-work-and-outcomes",
            intent="trace",
            text="trace",
            seeds=[ids["req1"]],
            required=[ids[k] for k in ("req1", "spec1", "ticket", "change", "case", "failed")],
            forbidden=[ids["req2"], ids["spec2"]],
            max_depth=6,
            exact=True,
            after_scenario="H07-req2",
        ),
        dict(
            scenario="HQ3-no-coverage",
            intent="trace",
            text="trace",
            seeds=[ids["missing"]],
            required=[ids["missing"]],
            forbidden=[ids[k] for k in ("case", "planned_case", "failed", "passed", "skipped")],
            max_depth=4,
            exact=False,
        ),
        dict(
            scenario="HQ4-proposed-is-not-a-passing-run",
            intent="trace",
            text="trace",
            seeds=[ids["proposed"]],
            required=[ids["proposed"]],
            forbidden=[ids["passed"], ids["failed"]],
            max_depth=4,
            exact=False,
        ),
        dict(
            scenario="HQ5-hotfix-work-verification-production",
            intent="trace",
            text="trace",
            seeds=[ids["ticket"]],
            required=[
                ids[k]
                for k in (
                    "ticket",
                    "req1",
                    "spec1",
                    "change",
                    "case",
                    "failed",
                    "passed",
                    "review",
                    "deployment",
                    "component",
                )
            ],
            forbidden=[ids["req2"], ids["spec2"], ids["missing"], ids["proposed"]],
            max_depth=6,
            exact=True,
            expected_states={ids["change"]: "merged", ids["deployment"]: "succeeded"},
        ),
        dict(
            scenario="HQ6-explicit-remediation-resolution",
            intent="incident",
            text="trace",
            seeds=[ids["incident"]],
            required=[ids["incident"], ids["change"], ids["component"]],
            forbidden=[ids["req2"]],
            max_depth=3,
            exact=False,
            expected_states={ids["incident"]: "resolved"},
            expected_edges=[["REMEDIATES", ids["change"], ids["incident"]]],
        ),
        dict(
            scenario="HQ7-missing-proposed-confirmed-coverage",
            intent="completeness",
            text="Which requirements have no tests?",
            seeds=[ids["missing"], ids["proposed"], ids["req1"]],
            required=[ids["missing"], ids["proposed"]],
            forbidden=[ids["req1"]],
            exact=True,
            max_depth=3,
            expected_retrieval_reasons={
                ids["missing"]: "no_link",
                ids["proposed"]: "proposed_only",
            },
            expected_channels={
                "completeness.VERIFIES.no_link": 1,
                "completeness.VERIFIES.proposed_only": 1,
                "completeness.VERIFIES.confirmed": 1,
            },
        ),
    ]
    return dict(
        name="p02-history",
        tenant="b",
        steps=steps,
        queries=queries,
        source_expectations=sources,
        model_proposal_check=dict(
            event_id=prose["request"]["event_id"],
            required_type="Decision",
            status="proposed",
            accepted_decision=decision,
        ),
        ids=ids,
        source_kind="Synthetic explicit completion producers",
    )
