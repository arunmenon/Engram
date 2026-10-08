"""Compose existing normalized producers into one connected G05 graph.

Expected retrieval sets are fixed here, never inferred from returned data.
"""

from copy import deepcopy
from datetime import datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

from engram_goal03_fixtures import fixtures as implementation_fixtures
from engram_goal04_fixtures import fixtures as release_fixtures


def _replace(value, changes):
    if isinstance(value, str):
        for before, after in changes:
            value = value.replace(before, after)
        return value
    if isinstance(value, list):
        return [_replace(item, changes) for item in value]
    if isinstance(value, dict):
        return {_replace(key, changes): _replace(item, changes) for key, item in value.items()}
    return value


def fixtures(run_id):
    prefix = "g05/" + run_id
    planning = _replace(implementation_fixtures(run_id), [("g03/" + run_id, prefix)])
    shipping = release_fixtures(run_id)
    times = sorted({step["request"]["occurred_at"] for step in shipping["steps"]})
    changes = [("g04/" + run_id, prefix), ("reset-sha", "abc123")]
    changes += [
        (value, (datetime.fromisoformat(value) + timedelta(minutes=2)).isoformat())
        for value in times
    ]
    shipping = _replace(shipping, changes)
    steps = [step for step in planning["steps"] if not step["scenario"].startswith("IM12")]
    # One planning-contract rejection is enough here; previous G03/G04 tests retain their own scope.
    steps.append(next(step for step in planning["steps"] if step["scenario"] == "IM12-revision"))
    wanted = {
        "RD02-merge",
        "RD03-release",
        "RD04-failed",
        "RD05-succeeded",
        "RD06-staging",
        "RD09-unlinked-deploy",
        "RD09-empty-release",
        "RD10-other-release",
        "RD10-other-repo-same-time",
        "RD11-null-release",
    }
    steps += [step for step in shipping["steps"] if step["scenario"] in wanted]
    ids = dict(planning["ids"])
    ids.update(
        {
            key: shipping["ids"][key]
            for key in [
                "release",
                "failed",
                "success",
                "staging",
                "component",
                "empty_release",
                "unlinked",
                "unlinked_component",
                "other_release",
                "other_deploy",
                "other_deploy_component",
            ]
        }
    )
    # The G03 unlinked PR and G04 unlinked deployment need separate dictionary names.
    ids["unlinked_change"] = planning["ids"]["unlinked"]
    approval_id = prefix + "-hld-approval"
    ids["design_approval"] = "DesignApproval:" + approval_id
    source = deepcopy(steps[3]["request"])
    source.update(
        event_id=str(uuid5(NAMESPACE_URL, run_id + ":CJ-approval")),
        event_type="pdlc.design.approval_recorded",
        occurred_at=(
            datetime.fromisoformat(source["occurred_at"]) + timedelta(milliseconds=500)
        ).isoformat(),
        payload_ref="synthetic:" + run_id + ":CJ-approval",
        payload=dict(
            approval_id=approval_id,
            reviewer="Alice",
            verdict="approved",
            doc_id=prefix + "-hld",
            section_path="tokens",
            version="1",
        ),
    )
    steps.insert(
        4,
        dict(
            scenario="CJ-approval",
            request=source,
            expected_status=201,
            expected_node=ids["design_approval"],
            expected_props=dict(reviewer="Alice", verdict="approved"),
            expected_edges=[["APPROVES", ids["design_approval"], ids["hld"]]],
            extra_nodes={},
        ),
    )
    # Keep the earlier unlinked PR key; shipping.unlinked is a deployment.
    for step in steps:
        if step["scenario"] == "IM11-duplicate":
            step["duplicate"] = True
        if step["expected_status"] == 422 and not step.get("absence_id"):
            step["request"]["payload"]["key"] = prefix + "-invalid-reference"
            step["absence_id"] = "WorkItem:jira|" + prefix + "-invalid-reference"
    main = [
        ids[key]
        for key in [
            "spec",
            "expiry",
            "hld",
            "lld",
            "design_approval",
            "ticket",
            "change",
            "review_bad",
            "review_good",
            "test",
            "run_bad",
            "run_good",
            "release",
            "failed",
            "success",
            "staging",
            "component",
        ]
    ]
    other = [
        ids[key]
        for key in [
            "other_spec",
            "other_req",
            "other_ticket",
            "other_change",
            "other_test",
            "other_run",
            "other_release",
            "other_deploy",
            "other_deploy_component",
        ]
    ]
    queries = []

    def query(sid, seeds, required, text):
        queries.append(
            dict(
                scenario=sid,
                seeds=seeds,
                seed=seeds[0] if seeds else None,
                intent="trace",
                text=text,
                required=required,
                forbidden=sorted(set(ids.values()) - set(required)),
                exact=True,
                max_depth=6,
            )
        )

    query(
        "CQ1-requirement-to-production",
        [ids["expiry"]],
        main,
        "Where did " + ids["expiry"] + " reach production?",
    )
    query(
        "CQ2-release-to-requirements",
        [ids["release"]],
        main,
        "Which requirements shipped in " + ids["release"] + "?",
    )
    query(
        "CQ3-deployment-to-verification",
        [ids["success"]],
        [nid for nid in main if nid not in {ids["failed"], ids["staging"]}],
        "What code, design and verification support " + ids["success"] + "?",
    )
    query(
        "CQ4-production-outcomes",
        [ids["failed"], ids["success"]],
        [nid for nid in main if nid != ids["staging"]],
        "Compare production deployment outcomes",
    )
    query(
        "CQ5-design-to-shipping",
        [ids["lld"]],
        main,
        "Trace " + ids["lld"] + " to its released code and deployment outcomes",
    )
    query("CQ6-text-discovery", [], main, "fifteen minutes")
    query(
        "CQ7-unrelated-feature",
        [ids["other_req"]],
        other,
        "Trace " + ids["other_req"] + " to its code and deployment",
    )
    query(
        "CQ8-unlinked-deployment",
        [ids["unlinked"]],
        [ids["unlinked"], ids["unlinked_component"]],
        "Trace " + ids["unlinked"],
    )
    return dict(
        ids=ids,
        steps=steps,
        queries=queries,
        fallback_seed=ids["spec"],
        main_ids=main,
        unrelated_ids=other,
        source_kind="Composed synthetic normalized G03/G04 producers; no raw adapter inference",
    )
