"""Small completion stories with independently declared graph/read expectations.

Business data is never inserted here. The existing pilot runner ingests these
Events and verifies them through Engram's public flows on retained Spanner.
"""

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from engram_goal03_implementation_demo import fixture_observations


def decoded_snapshot_cell(value):
    """Use the storage codec for both live cells and serialized evidence."""
    from context_graph.adapters.spanner.log import json_value

    return json_value(
        value if hasattr(value, "serialize") or isinstance(value, str) else json.dumps(value)
    )


def recovery_documents(state, inputs):
    """Reconstruct the unchanged accepted input window, including read positions."""
    from context_graph.domain.models import Event

    ledger = {row[0]: decoded_snapshot_cell(row[1]) for row in state["events"]}
    nodes = {row[1]: decoded_snapshot_cell(row[2]) for row in state["nodes"] if row[0] == "Event"}
    acceptances = {
        row[0]: decoded_snapshot_cell(row[2])
        for row in state["events"]
        if len(row) > 2 and row[2] is not None
    }
    documents = []
    for expected in inputs:
        eid = expected["event_id"]
        actual = dict(ledger[eid])
        original = Event.model_validate(expected, strict=False)
        stored = Event.model_validate(actual, strict=False)
        if original.model_copy(update={"global_position": None}) != stored.model_copy(
            update={"global_position": None}
        ) or actual.get("payload") != expected.get("payload"):
            raise ValueError("Recovery source differs from the frozen accepted input")
        if eid in acceptances:
            actual["acceptance"] = acceptances[eid]
        actual["global_position"] = nodes[eid]["global_position"]
        documents.append(actual)
    return documents


def recovery_input_hash(state, inputs):
    documents = recovery_documents(state, inputs)
    return sha256(json.dumps(documents, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def verified_recovered_user_receipt(state, group):
    from context_graph.domain.models import Event
    from context_graph.domain.user_extraction import receipt_from_event

    inputs = group.get("recover_user_inputs") or group["verify_user_inputs"]
    documents = recovery_documents(state, inputs)
    event = Event.model_validate(documents[-1], strict=False)
    props = decoded_snapshot_cell(
        next(r[2] for r in state["nodes"] if r[0] == "Event" and r[1] == str(event.event_id))
    )
    receipt = receipt_from_event(event, props)
    if (
        not receipt
        or props.get("user_extraction_owner") != "user:" + event.agent_id
        or props.get("user_extraction_status") != "applied"
        or receipt["status"] != "applied"
        or receipt["input_event_ids"] != [r["event_id"] for r in documents]
        or receipt["input_hash"] != group["recovery_input_hash"]
        or recovery_input_hash(state, inputs) != group["recovery_input_hash"]
    ):
        raise ValueError("Recovered User receipt differs from its frozen source window")
    return receipt


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
                    "Actual model attribution control; diagnostic behavior is not a capability pass"
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


def verified_user_correction(state, group):
    """Validate an applied correction independently of its mutation baseline."""
    inputs = (
        group.get("recover_user_inputs")
        or group.get("verify_user_inputs")
        or [s["request"] for s in group["steps"]]
    )
    receipt = verified_recovered_user_receipt(
        state,
        {
            "verify_user_inputs": inputs,
            "recovery_input_hash": recovery_input_hash(state, inputs),
        },
    )
    source = inputs[0]["event_id"]
    old_id, new_id = group["expected_previous"], group["expected_replacement"]
    preferences = receipt["result"]["preferences"]
    if len(preferences) != 1:
        raise ValueError("Correction must produce its single declared replacement")
    replacement = preferences[0]
    if (
        receipt["result"]["model_id"] != "gpt-6-luna"
        or replacement["preference_id"] != new_id
        or any(replacement.get(k) != v for k, v in group["identity_fields"].items())
        or group["required_negative_quote"].lower() not in replacement["source_quote"].lower()
        or replacement["support_event_ids"] != [source]
        or receipt["result"]["skills"]
        or receipt["result"]["interests"]
        or receipt["corrections"]
        != [dict(previous_preference_id=old_id, replacement_id=new_id, source_event_id=source)]
    ):
        raise ValueError("Correction output differs from its frozen identity/negative evidence")
    nodes = {(r[0], r[1]): decoded_snapshot_cell(r[2]) for r in state["nodes"]}
    old_ref = ("Preference", old_id)
    if (
        nodes[old_ref].get("superseded_by") != new_id
        or nodes[old_ref].get("user_id") != "user:" + group["owner"]
    ):
        raise ValueError("Correction did not supersede its exact predecessor")
    new_props = nodes[("Preference", new_id)]
    if (
        new_props.get("user_id") != "user:" + group["owner"]
        or new_props.get("support_event_ids") != [source]
        or new_props.get("observation_count") != 1
        or any(
            new_props.get(k) != replacement.get(k)
            for k in (
                "category",
                "key",
                "polarity",
                "context",
                "scope",
                "scope_id",
                "strength",
                "confidence",
                "source",
            )
        )
    ):
        raise ValueError("Replacement owner/source/count differs")
    expected_edges = {
        ("Preference", new_id, "ABOUT", "Entity", "entity:" + replacement["about_entity"]),
        ("Preference", new_id, "SUPERSEDES", "Preference", old_id),
        ("Preference", new_id, "DERIVED_FROM", "Event", source),
        ("Preference", old_id, "DERIVED_FROM", "Event", source),
    }
    edges = {tuple(e[:5]): decoded_snapshot_cell(e[5]) for e in state["edges"]}
    if (
        not expected_edges <= edges.keys()
        or edges[("Preference", new_id, "SUPERSEDES", "Preference", old_id)].get("source_event_id")
        != source
    ):
        raise ValueError("Correction lifecycle/source links differ")
    evidence = edges[("Preference", new_id, "DERIVED_FROM", "Event", source)]
    if (
        evidence.get("evidence_quote") != replacement["source_quote"]
        or evidence.get("extraction_event_id") != inputs[-1]["event_id"]
    ):
        raise ValueError("Persisted correction evidence differs from validated replacement")
    return receipt


def correction_expected_updates(before, after, group):
    """Exact permitted prior-node changes for one frozen producer correction."""
    receipt = verified_user_correction(after, group)
    old_id, new_id = group["expected_previous"], group["expected_replacement"]
    old_nodes = {(r[0], r[1]): dict(r[2]) for r in before["nodes"]}
    old_ref = ("Preference", old_id)
    if old_nodes[old_ref].get("superseded_by") or ("Preference", new_id) in old_nodes:
        raise ValueError("Correction predecessor must be active and replacement fresh")
    expected_old = {**old_nodes[old_ref], "superseded_by": new_id}
    updates = {old_ref: expected_old}
    profile_ref = ("UserProfile", "profile:user:" + group["owner"])
    profile = dict(old_nodes[profile_ref])
    persona = receipt["result"]["persona"]
    if persona:
        supports = set(persona["support_event_ids"])
        known = set(profile.get("support_event_ids", []))
        profile["support_event_ids"] = sorted(known | supports)
        if supports - known:
            name = persona.get("name") or group["owner"]
            if persona.get("role") and persona.get("name"):
                name += " (" + persona["role"] + ")"
            profile.update(
                display_name=name,
                communication_style=persona.get("communication_style"),
                technical_level=persona.get("tech_level"),
                updated_at=receipt["effective_at"],
            )
    updates[profile_ref] = profile
    return updates, receipt


def declared_dead_letters(state, groups, tenant, *, require_all=False):
    """Only frozen negative deliveries are allowed; validate their bound source.

    Reason lives on the Event diagnostic: bound subscription metadata deliberately
    reconstructs the accepted delivery rather than trusting arbitrary caller fields.
    No declaration is inferred from observed dead letters.
    """
    expected = {
        (step["expected_worker_rejection"]["group"], step["request"]["event_id"]): step
        for group in groups
        if group["tenant"] == tenant
        for step in group["steps"]
        if step.get("expected_worker_rejection")
    }
    actual = {tuple(row) for row in state["dead_letters"]}
    if not actual <= expected.keys() or (require_all and actual != expected.keys()):
        return False
    if len(actual) != len(state["dead_letters"]):
        return False
    details = {
        (r[0], r[1]): decoded_snapshot_cell(r[2]) for r in state.get("dead_letter_fields", [])
    }
    nodes = {r[1]: decoded_snapshot_cell(r[2]) for r in state["nodes"] if r[0] == "Event"}
    ledger = {r[0]: r for r in state["events"]}
    for key in actual:
        step, fields = expected[key], details.get(key, {})
        eid = key[1]
        node = nodes.get(eid, {})
        if eid not in ledger or len(ledger[eid]) < 3:
            return False
        accepted = decoded_snapshot_cell(ledger[eid][2])
        acceptance = fields.get("acceptance")
        try:
            acceptance = json.loads(acceptance) if isinstance(acceptance, str) else acceptance
        except ValueError:
            return False
        if not (
            node.get("memory_status") == "conflict"
            and node.get("memory_reason") == step["expected_worker_rejection"]["reason"]
            and fields.get("event_id") == eid
            and fields.get("group") == key[0]
            and fields.get("consumer") == "projection-1"
            and fields.get("disposition_epoch")
            == str(step["expected_worker_rejection"]["disposition_epoch"])
            and fields.get("original_entry_id") == node.get("global_position")
            and acceptance == accepted
            and all(
                fields.get(k) == accepted.get(k)
                for k in (
                    "tenant_id",
                    "database_resource",
                    "binding_id",
                    "bundle_digest",
                    "engine_revision",
                )
            )
            and [key[0], eid] not in state["pending"]
        ):
            return False
    return True


def memory_subject_snapshot(state, subject):
    """Exact Memory state and all incident edges, including lifecycle/evidence."""
    return {
        "nodes": [r for r in state["nodes"] if r[1] == subject],
        "edges": sorted(
            json.dumps(r, sort_keys=True, default=str)
            for r in state["edges"]
            if r[1] == subject or r[4] == subject
        ),
    }


def p04_memory(run_id):
    from copy import deepcopy

    from engram_memory_actions_demo import identity
    from engram_pilot_spectrum import freeze

    group = next(g for g in freeze(run_id)["groups"] if g["name"] == "a-memory")
    steps = group["steps"]
    confirmed = steps[1]
    stale = deepcopy(confirmed)
    stale.update(
        scenario="stale-belief-confirmation",
        observes_node=False,
        expected_worker_rejection=dict(
            group="assessment-projection", reason="state_conflict", disposition_epoch=53
        ),
        unchanged_subject=confirmed["expected_node"],
    )
    stale["request"]["event_id"] = str(uuid5(NAMESPACE_URL, run_id + ":stale"))
    steps.insert(2, stale)
    owner = confirmed["request"]["agent_id"]
    session = run_id + ":scope:first"
    second = run_id + ":scope:second"
    other = owner + ":other"
    agent_goal = identity("Goal", owner, "agent", session, "study")
    session_goal = identity("Goal", owner, "session", second, "study")
    other_goal = identity("Goal", other, "agent", session, "study")

    def add(key, kind, payload, subject, props, *, sid=session, agent=owner, observed=True):
        req = deepcopy(confirmed["request"])
        req.update(
            event_id=str(uuid5(NAMESPACE_URL, run_id + ":" + key)),
            event_type=kind,
            session_id=sid,
            agent_id=agent,
            payload=payload,
            payload_ref="pilot-p04:" + key,
        )
        step = dict(
            scenario=key,
            request=req,
            expected_status=201,
            expected_node=subject,
            expected_props=props,
            expected_edges=[],
            extra_nodes={},
            memory_intent="when",
            observes_node=observed,
        )
        steps.append(step)
        return step

    add(
        "agent-goal-created",
        "memory.goal.created",
        dict(key="study", scope="agent", description="Finish the reliability course"),
        agent_goal,
        dict(status="active", state_revision=0, evidence_count=1, scope="agent"),
    )
    add(
        "other-owner-goal",
        "memory.goal.created",
        dict(key="study", scope="agent", description="Finish the reliability course"),
        other_goal,
        dict(status="active", scope="agent"),
        agent=other,
    )
    add(
        "session-goal-created",
        "memory.goal.created",
        dict(key="study", scope="session", description="Finish the reliability course"),
        session_goal,
        dict(status="active", scope="session"),
        sid=second,
    )
    progress = add(
        "ordinary-progress",
        "observation.input",
        dict(
            content="I finished chapter one of the reliability course; the course is not complete."
        ),
        agent_goal,
        dict(status="active", state_revision=0, evidence_count=1),
        sid=second,
        observed=False,
    )
    progress["unchanged_subject"] = agent_goal
    progress["expected_observed_node_ids"] = []
    completed = add(
        "agent-goal-completed-second-session",
        "memory.goal.completed",
        dict(key="study", scope="agent", expected_revision=0),
        agent_goal,
        dict(status="completed", state_revision=1, evidence_count=2),
        sid=second,
    )
    completed["node_assertions"] = {
        session_goal: dict(status="active"),
        other_goal: dict(status="active"),
    }
    malformed = deepcopy(completed)
    malformed.update(scenario="malformed-goal-completion", expected_status=422)
    malformed["request"]["event_id"] = str(uuid5(NAMESPACE_URL, run_id + ":malformed"))
    malformed["request"]["payload"].pop("expected_revision")
    steps.append(malformed)
    for index, step in enumerate(steps):
        step["request"]["occurred_at"] = (
            datetime.now(UTC) - timedelta(minutes=5) + timedelta(seconds=index)
        ).isoformat()
    group["final_queries"].extend(
        [
            dict(
                query="What goals do I have?",
                intent="goals",
                session_id=second,
                agent_id=owner,
                required=[session_goal, agent_goal],
                forbidden=[other_goal],
            ),
            dict(
                query="Show my goal history",
                intent="when",
                session_id=second,
                agent_id=owner,
                required=[agent_goal, session_goal],
                forbidden=[other_goal],
            ),
            dict(
                query="What goals do I have?",
                intent="goals",
                session_id=session,
                agent_id=other,
                required=[other_goal],
                forbidden=[agent_goal, session_goal],
            ),
        ]
    )
    group["final_queries"].append(
        dict(
            query="Show my goal across sessions",
            intent="when",
            session_id=session,
            agent_id=owner,
            required=[agent_goal],
            forbidden=[session_goal, other_goal],
        )
    )
    group["source_expectations"] = {}
    for step in steps:
        if step["expected_status"] < 400 and step.get("observes_node", True):
            group["source_expectations"].setdefault(
                step["expected_node"], [step["request"]["event_id"]]
            )
    return dict(
        coverage="P04 explicit Memory lifecycle, conflict, owner and session/agent scope",
        groups=[group],
    )
