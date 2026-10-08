"""Independent G07-C normalized and reconstructed webhook oracles (#56).

This module builds inputs and fixed expectations only; it runs no backend.
Webhook cases deliberately remain separate from normalized event requests.
"""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5


def fixtures(run_id, *, start=None):
    prefix = "g07/" + run_id + "/skipped"
    repo = prefix + "/auth"
    start = start or (datetime.now(UTC) - timedelta(minutes=10)).replace(microsecond=0)
    case = "TestCase:" + repo + "|reset-tests"
    change = "Change:" + repo + "|56"
    ids = {"case": case, "change": change}
    steps = []

    def add(sid, event_type, payload, node=None, props=None, edges=(), extra=None, status=201):
        request = dict(
            event_id=str(uuid5(NAMESPACE_URL, prefix + ":" + sid)),
            event_type="pdlc." + event_type,
            occurred_at=(start + timedelta(seconds=len(steps))).isoformat(),
            session_id=prefix,
            agent_id="verification.publisher",
            trace_id=run_id,
            payload_ref="synthetic:" + prefix + ":" + sid,
            payload=deepcopy(payload),
        )
        step = dict(
            scenario=sid,
            request=request,
            expected_status=status,
            expected_node=node,
            expected_props=props or {},
            expected_edges=[list(e) for e in edges],
            extra_nodes=extra or {},
        )
        if node:
            step["forbidden_edge_types"] = ["VERIFIES"]
        if event_type.startswith("testcaserun.") and status == 201:
            step["expected_edge_properties"] = [
                [
                    kind,
                    source,
                    target,
                    dict(
                        source_event_id=request["event_id"],
                        pinned_position="$receipt",
                        **({"commit_sha": "reset-sha"} if kind == "RAN_AGAINST" else {}),
                    ),
                ]
                for kind, source, target in edges
            ]
        steps.append(step)
        return step

    add(
        "C01-change",
        "change.created",
        dict(repo=repo, number=56, title="Reset verifier"),
        change,
        dict(status="open"),
    )
    base = dict(
        repo=repo,
        test_id="reset-tests",
        name="Reset tests",
        path="tests/reset.py",
        commit_sha="reset-sha",
        change_number=56,
    )

    def run(sid, outcome, *, linked=True):
        rid = prefix + "/" + sid
        nid = "TestRun:" + rid
        ids[sid] = nid
        payload = dict(base, run_id=rid, outcome=outcome)
        if not linked:
            payload.pop("change_number")
            payload.pop("commit_sha")
        edges = [("EXECUTES", nid, case)]
        if linked:
            edges.append(("RAN_AGAINST", nid, change))
        props = dict(outcome=outcome)
        if linked:
            props["commit_sha"] = "reset-sha"
        step = add(
            sid,
            "testcaserun.skipped" if outcome == "skipped" else "testcaserun.finished",
            payload,
            nid,
            props,
            edges,
            {case: dict(path="tests/reset.py", name="Reset tests")},
        )
        step["expected_props"]["finished_at"] = step["request"]["occurred_at"]
        if not linked:
            step["forbidden_edge_types"].append("RAN_AGAINST")
        return step

    skipped = run("C01-skipped", "skipped")
    retry = deepcopy(skipped)
    retry.update(scenario="C01-skipped-retry", duplicate=True)
    steps.append(retry)
    conflict = deepcopy(skipped)
    conflict.update(
        scenario="C01-skipped-conflict",
        expected_status=409,
        expected_node=None,
        expected_props={},
        expected_edges=[],
        extra_nodes={},
        expected_edge_properties=[],
    )
    conflict["request"]["payload"]["name"] = "Changed content"
    steps.append(conflict)
    run("C03-no-reference", "skipped", linked=False)
    for outcome in ("success", "failure", "cancel", "error"):
        run("C04-" + outcome, outcome)
    for field, value in (("repo", ""), ("test_id", ""), ("run_id", ""), ("outcome", "success")):
        add(
            "C03-invalid-" + field,
            "testcaserun.skipped",
            dict(base, run_id=prefix + "/invalid-" + field, outcome="skipped") | {field: value},
            status=422,
        )

    # These are reconstructed wrappers, not historical delivery evidence.
    webhook_cases = []
    for conclusion, number in (("skipped", 56001), ("neutral", 56002)):
        # Namespace check IDs by this run so independent cloud attempts cannot collide.
        check_id = uuid5(NAMESPACE_URL, prefix + "/check/" + str(number)).int % (2**63 - 1)
        nid = "TestRun:" + str(check_id)
        ids["webhook-" + conclusion] = nid
        body = dict(
            action="completed",
            repository=dict(full_name=repo),
            check_run=dict(
                id=check_id,
                name="reset-tests",
                conclusion=conclusion,
                head_sha="reset-sha",
                completed_at=(start + timedelta(seconds=30)).isoformat(),
                pull_requests=[dict(number=56)],
            ),
        )
        webhook_cases.append(
            dict(
                scenario="C02-webhook-" + conclusion,
                source_kind="reconstructed GitHub check_run wrapper",
                event="check_run",
                body=body,
                expected_event_type="pdlc.testcaserun.skipped",
                expected_payload=dict(
                    repo=repo,
                    test_id="reset-tests",
                    name="reset-tests",
                    path=None,
                    run_id=str(check_id),
                    outcome="skipped",
                    commit_sha="reset-sha",
                    change_number=56,
                ),
                expected_node=nid,
                expected_props=dict(outcome="skipped", commit_sha="reset-sha"),
                expected_edges=[["EXECUTES", nid, case], ["RAN_AGAINST", nid, change]],
                extra_nodes={case: {}},
                forbidden_edge_types=["VERIFIES"],
            )
        )

    # All linked runs are reachable through their shared TestCase and Change.
    linked = [change, case, ids["C01-skipped"], ids["C03-no-reference"]]
    linked += [ids["C04-" + outcome] for outcome in ("success", "failure", "cancel", "error")]
    linked += [ids["webhook-skipped"], ids["webhook-neutral"]]
    expected_edges = [
        e
        for step in steps
        if step["expected_status"] == 201 and not step.get("duplicate")
        for e in step["expected_edges"]
    ]
    expected_edges += [e for step in webhook_cases for e in step["expected_edges"]]
    queries = [
        dict(
            scenario="CQ1-exact-outcomes",
            seed=change,
            seeds=[change],
            intent="trace",
            text="trace the reset verification outcomes",
            required=linked,
            forbidden=[],
            exact=True,
            max_depth=3,
            expected_edges=expected_edges,
        )
    ]
    return dict(
        ids=ids,
        steps=steps,
        queries=queries,
        webhook_cases=webhook_cases,
        fallback_seed=change,
        source_kind="Synthetic normalized test producers and reconstructed check wrappers",
    )
