"""Predeclared normalized G04 payloads and exact graph/retrieval expectations."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5


def fixtures(run_id):
    prefix = "g04/" + run_id
    repo, other_repo = prefix + "/payments", prefix + "/newsletter"
    service, other_service = repo + "/api", other_repo + "/api"
    start = (datetime.now(UTC) - timedelta(minutes=5)).replace(microsecond=0)
    ids, steps = {}, []

    def add(
        sid,
        event,
        payload,
        key=None,
        label=None,
        key_values=(),
        props=None,
        edges=(),
        extra=None,
        at=None,
        status=201,
    ):
        at = at or start + timedelta(seconds=len(steps))
        nid = label + ":" + "|".join(map(str, key_values)) if label else None
        if key:
            ids[key] = nid
        step = dict(
            scenario=sid,
            request=dict(
                event_id=str(uuid5(NAMESPACE_URL, run_id + ":" + sid)),
                event_type=event,
                occurred_at=at.isoformat(),
                session_id=prefix,
                agent_id="release.publisher",
                trace_id=run_id,
                payload_ref="synthetic:" + run_id + ":" + sid,
                payload=deepcopy(payload),
            ),
            expected_status=status,
            expected_node=nid,
            expected_props=props or {},
            expected_edges=[list(e) for e in edges],
            extra_nodes=extra or {},
        )
        steps.append(step)
        return step

    change = dict(repo=repo, number=7, title="Enforce fifteen-minute reset expiry")
    add(
        "RD01-open",
        "pdlc.change.created",
        change,
        "change",
        "Change",
        [repo, 7],
        dict(title=change["title"], status="open"),
    )
    merged = dict(change, merge_sha="reset-sha", body="", files=[])
    add(
        "RD02-merge",
        "pdlc.change.merged",
        merged,
        "change",
        "Change",
        [repo, 7],
        dict(title=change["title"], status="merged", merge_sha="reset-sha"),
    )
    release_id = f"Release:{repo}|v1.0.0"
    add(
        "RD03-release",
        "pdlc.release.published",
        dict(
            repo=repo,
            version="v1.0.0",
            has_breaking=False,
            entries=[dict(pr_number=7, section="fixed")],
        ),
        "release",
        "Release",
        [repo, "v1.0.0"],
        dict(breaking=False),
        [("INCLUDES", release_id, ids["change"])],
    )
    deployment = dict(
        repo=repo,
        service=service,
        environment="production",
        artifact_id="reset-sha",
        release_version="v1.0.0",
        change_numbers=[7],
    )
    failed_time = start + timedelta(seconds=3)

    def deploy(sid, key, payload, outcome, at=None, related=True):
        at = at or start + timedelta(seconds=len(steps))
        nid = "Deployment:" + "|".join(
            [
                payload["repo"],
                payload["service"],
                payload["environment"],
                payload["artifact_id"],
                at.isoformat(),
            ]
        )
        component = "Component:" + payload["service"]
        edges = [("DEPLOYED_TO", nid, component)]
        if related:
            edges += [("DEPLOYS", nid, release_id), ("DEPLOYS", nid, ids["change"])]
        step = add(
            sid,
            "pdlc.service.deployed" if outcome == "succeeded" else "pdlc.service.deployment_failed",
            payload,
            key,
            "Deployment",
            [
                payload["repo"],
                payload["service"],
                payload["environment"],
                payload["artifact_id"],
                at.isoformat(),
            ],
            dict(
                status=outcome,
                repo=payload["repo"],
                service=payload["service"],
                environment=payload["environment"],
                artifact_id=payload["artifact_id"],
            ),
            edges,
            {component: {}},
            at,
        )
        ids.setdefault(
            "component" if payload["service"] == service else key + "_component", component
        )
        return step

    deploy("RD04-failed", "failed", deployment, "failed", failed_time)
    success = deploy("RD05-succeeded", "success", deployment, "succeeded")
    deploy("RD06-staging", "staging", dict(deployment, environment="staging"), "succeeded")
    duplicate = deepcopy(success)
    duplicate.update(scenario="RD07-duplicate", duplicate=True)
    steps.append(duplicate)
    conflict = deepcopy(success)
    conflict.update(
        scenario="RD07-conflict",
        expected_node=None,
        expected_props={},
        expected_edges=[],
        extra_nodes={},
        expected_status=409,
    )
    conflict["request"]["payload"]["environment"] = "conflict-only"
    steps.append(conflict)

    late_change = f"Change:{repo}|9"
    late_release = f"Release:{repo}|v2.0.0"
    placeholder_step = add(
        "RD08-release-first",
        "pdlc.release.published",
        dict(repo=repo, version="v2.0.0", entries=[dict(pr_number=9, section="added")]),
        "late_release",
        "Release",
        [repo, "v2.0.0"],
        {},
        [("INCLUDES", late_release, late_change)],
        {late_change: {}},
    )
    placeholder_step["placeholders"] = [late_change]
    add(
        "RD08-change-arrives",
        "pdlc.change.created",
        dict(repo=repo, number=9, title="Future change"),
        "late_change",
        "Change",
        [repo, 9],
        dict(title="Future change", status="open"),
    )
    late_deployment = dict(
        deployment, artifact_id="future-sha", release_version="v3.0.0", change_numbers=[]
    )
    late = deploy("RD08-deploy-first", "late_deploy", late_deployment, "succeeded", related=False)
    future_release = f"Release:{repo}|v3.0.0"
    late["expected_edges"].append(["DEPLOYS", ids["late_deploy"], future_release])
    late["extra_nodes"][future_release] = {}
    late["placeholders"] = [future_release]
    add(
        "RD08-release-arrives",
        "pdlc.release.published",
        dict(repo=repo, version="v3.0.0", has_breaking=True, entries=[]),
        "future_release",
        "Release",
        [repo, "v3.0.0"],
        dict(breaking=True),
    )

    add(
        "RD09-empty-release",
        "pdlc.release.published",
        dict(repo=repo, version="empty", entries=[]),
        "empty_release",
        "Release",
        [repo, "empty"],
    )
    deploy(
        "RD09-unlinked-deploy",
        "unlinked",
        dict(
            repo=repo,
            service=repo + "/unlinked",
            environment="production",
            artifact_id="unknown-sha",
            change_numbers=[],
        ),
        "succeeded",
        related=False,
    )

    add(
        "RD10-other-change",
        "pdlc.change.created",
        dict(repo=other_repo, number=7, title="Newsletter change"),
        "other_change",
        "Change",
        [other_repo, 7],
        dict(status="open"),
    )
    other_release = f"Release:{other_repo}|v1.0.0"
    add(
        "RD10-other-release",
        "pdlc.release.published",
        dict(repo=other_repo, version="v1.0.0", entries=[dict(pr_number=7, section="docs")]),
        "other_release",
        "Release",
        [other_repo, "v1.0.0"],
        {},
        [("INCLUDES", other_release, ids["other_change"])],
    )
    collision = deploy(
        "RD10-other-repo-same-time",
        "other_deploy",
        dict(deployment, repo=other_repo, service=other_service),
        "succeeded",
        failed_time,
        related=False,
    )
    collision["expected_edges"] += [
        ["DEPLOYS", ids["other_deploy"], other_release],
        ["DEPLOYS", ids["other_deploy"], ids["other_change"]],
    ]
    # Same service/environment/artifact/time across repos must not collide.
    deploy(
        "RD10-other-repo-same-service",
        "other_repo_same_service",
        dict(
            repo=other_repo,
            service=service,
            environment="production",
            artifact_id="reset-sha",
            change_numbers=[],
        ),
        "succeeded",
        failed_time,
        related=False,
    )
    # Same repo/environment/artifact/time, different service; no explicit release.
    # Existing merge_sha matching still legitimately links the same Change.
    same_repo = deploy(
        "RD10-other-service-same-time",
        "other_service_deploy",
        dict(
            repo=repo,
            service=repo + "/worker",
            environment="production",
            artifact_id="reset-sha",
            change_numbers=[],
        ),
        "succeeded",
        failed_time,
        related=False,
    )
    same_repo["expected_edges"].append(["DEPLOYS", ids["other_service_deploy"], ids["change"]])

    for suffix, field, value in [
        ("null-release", "release_version", None),
        ("empty-release", "release_version", ""),
        ("typed-release", "release_version", 1),
        ("missing-environment", "environment", None),
    ]:
        payload = deepcopy(deployment)
        if suffix == "missing-environment":
            del payload[field]
        else:
            payload[field] = value
        add("RD11-" + suffix, "pdlc.service.deployed", payload, status=422)
    for suffix, entry in [
        ("missing-section", dict(pr_number=7)),
        ("bad-section", dict(pr_number=7, section="nonsense")),
        ("bad-number", dict(pr_number=True, section="fixed")),
    ]:
        add(
            "RD11-" + suffix,
            "pdlc.release.published",
            dict(repo=repo, version="invalid-" + suffix, entries=[entry]),
            status=422,
        )
    add("RD11-bogus-event", "pdlc.service.nonexistent", deployment, status=422)

    # Candidate identities and edge properties are fixture-derived before any API calls.
    for step in steps:
        payload = step["request"]["payload"]
        step["expected_edge_properties"] = []
        for kind, source, target in step["expected_edges"]:
            if kind == "INCLUDES":
                number = int(target.rsplit("|", 1)[1])
                section = next(e["section"] for e in payload["entries"] if e["pr_number"] == number)
                step["expected_edge_properties"].append(
                    [kind, source, target, {"section": section}]
                )
            elif kind == "DEPLOYED_TO":
                step["expected_edge_properties"].append(
                    [kind, source, target, {"environment": payload["environment"]}]
                )
        if step["expected_status"] == 422:
            if step["request"]["event_type"] == "pdlc.release.published":
                step["absence_id"] = f"Release:{repo}|{payload['version']}"
            else:
                payload["artifact_id"] = "rejected-" + step["scenario"]
                step["absence_id"] = "Deployment:" + "|".join(
                    [
                        repo,
                        service,
                        payload.get("environment", "missing-environment"),
                        payload["artifact_id"],
                        step["request"]["occurred_at"],
                    ]
                )

    # Freeze exact sets, respecting the existing anti-sibling traversal policy.
    main = [
        ids[k]
        for k in [
            "change",
            "release",
            "failed",
            "success",
            "staging",
            "component",
            "other_service_deploy",
            "other_service_deploy_component",
        ]
    ]
    # Component is a source catalog identity shared explicitly by RD10-other-repo-same-service;
    # it is therefore legitimately reachable from this Component and not an isolation leak.
    component_reachable = [
        ids[k] for k in ["change", "release", "failed", "success", "staging", "component"]
    ] + [
        ids["late_deploy"],
        ids["future_release"],
        ids["other_repo_same_service"],
    ]
    queries = []

    def query(sid, seed, required):
        queries.append(
            dict(
                scenario=sid,
                seed=seed,
                intent="trace",
                required=required,
                forbidden=sorted(set(ids.values()) - set(required)),
                exact=True,
            )
        )

    # Release reaches its three explicit attempts; each Component is reached through deployments.
    query(
        "RD12-release",
        ids["release"],
        [
            ids[k]
            for k in [
                "release",
                "change",
                "failed",
                "success",
                "staging",
                "component",
                "other_service_deploy",
                "other_service_deploy_component",
            ]
        ],
    )
    query("RD12-change", ids["change"], main)
    query(
        "RD12-failed-attempt",
        ids["failed"],
        [ids[k] for k in ["failed", "release", "change", "component"]],
    )
    query("RD12-component", ids["component"], component_reachable)
    return dict(
        ids=ids,
        steps=steps,
        queries=queries,
        fallback_seed=ids["change"],
        source_kind="synthetic normalized producers, not native source adapters",
    )
