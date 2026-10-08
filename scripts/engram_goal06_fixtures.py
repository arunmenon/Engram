"""Frozen normalized G06 producers and graph/retrieval expectations (#51–53)."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5


def fixtures(run_id, *, start=None):
    prefix = "g06/" + run_id
    repo, other_repo = prefix + "/auth", prefix + "/other"
    service, other_service = repo + "/reset", other_repo + "/reset"
    start = start or (datetime.now(UTC) - timedelta(minutes=10)).replace(microsecond=0)
    ids, steps = {}, []

    def node(kind, *values):
        return kind + ":" + "|".join(str(v).replace("%", "%25").replace("|", "%7C") for v in values)

    def add(
        sid, event, payload, *, key=None, nid=None, props=None, edges=(), extra=None, second=None
    ):
        request = dict(
            event_id=str(uuid5(NAMESPACE_URL, run_id + ":" + sid)),
            event_type="pdlc." + event,
            occurred_at=(
                start + timedelta(seconds=second if second is not None else 100 + len(steps))
            ).isoformat(),
            session_id=prefix,
            agent_id="incident.publisher",
            trace_id=run_id,
            payload_ref="synthetic:" + run_id + ":" + sid,
            payload=deepcopy(payload),
        )
        step = dict(
            scenario=sid,
            request=request,
            expected_status=201,
            expected_node=nid,
            expected_props=props or {},
            expected_edges=[list(e) for e in edges],
            extra_nodes=extra or {},
        )
        if key:
            ids[key] = nid
        steps.append(step)
        return step

    def edge_evidence(step, kind, source, target, **props):
        step.setdefault("expected_edge_properties", []).append(
            [
                kind,
                source,
                target,
                dict(
                    source_event_id=step["request"]["event_id"], pinned_position="$receipt", **props
                ),
            ]
        )

    def retry_and_conflict(step, field, value):
        retry = deepcopy(step)
        retry.update(scenario=step["scenario"] + "-retry", duplicate=True)
        steps.append(retry)
        conflict = deepcopy(step)
        conflict.update(
            scenario=step["scenario"] + "-conflict",
            expected_status=409,
            expected_node=None,
            expected_props={},
            expected_edges=[],
            extra_nodes={},
            expected_edge_properties=[],
        )
        conflict["request"]["payload"][field] = value
        steps.append(conflict)

    shared = dict(environment="production", artifact_id="reset-bad-sha", change_numbers=[])
    for sid, key, deployment_repo, deployment_service, second in (
        ("IC01-main-deploy", "deployment", repo, service, 10),
        ("IC01-repo-collision", "repo_collision", other_repo, service, 20),
        ("IC01-other-scope", "other_deployment", other_repo, other_service, 30),
        ("IC01-service-collision", "service_collision", repo, service + "/worker", 35),
        ("IC01-future-deploy", "future_deployment", repo, service, 90),
    ):
        at = (start + timedelta(seconds=second)).isoformat()
        nid = node(
            "Deployment", deployment_repo, deployment_service, "production", "reset-bad-sha", at
        )
        component = node("Component", deployment_service)
        ids[
            "component"
            if deployment_service == service
            else "other_component"
            if deployment_service == other_service
            else key + "_component"
        ] = component
        add(
            sid,
            "service.deployed",
            dict(shared, repo=deployment_repo, service=deployment_service),
            key=key,
            nid=nid,
            props=dict(status="succeeded", repo=deployment_repo, service=deployment_service),
            edges=[("DEPLOYED_TO", nid, component)],
            extra={component: {}},
            second=second,
        )

    incident = dict(repo=repo, service=service, incident_id="INC-RESET-51")
    other_incident = dict(repo=other_repo, service=other_service, incident_id="INC-RESET-51")

    def report(
        sid,
        key,
        reference,
        event="incident.detected",
        *,
        second=40,
        deployment=None,
        deployment_fields=True,
    ):
        nid = node("Incident", reference["repo"], reference["service"], reference["incident_id"])
        component = node("Component", reference["service"])
        payload = dict(
            reference, description="Expired password-reset tokens accepted", severity="high"
        )
        if deployment_fields:
            payload.update(environment="production", artifact_id="reset-bad-sha")
        edges = [("AFFECTS", nid, component)]
        if deployment:
            edges.append(("OCCURRED_ON", nid, deployment))
        return add(
            sid,
            event,
            payload,
            key=key,
            nid=nid,
            props=dict(status="detected"),
            edges=edges,
            extra={component: {}},
            second=second,
        )

    detected = report("IC02-detected", "incident", incident, deployment=ids["deployment"])
    retry_and_conflict(detected, "description", "Changed-content event ID reuse")
    report(
        "IC02-reported-other-scope",
        "other_incident",
        other_incident,
        "incident.reported",
        deployment=ids["other_deployment"],
    )
    report(
        "IC03-before-deployment",
        "early_incident",
        dict(incident, incident_id="INC-BEFORE"),
        second=5,
    )
    report(
        "IC03-no-reference",
        "no_reference",
        dict(incident, incident_id="INC-UNKNOWN"),
        deployment_fields=False,
    )

    for number, key in ((8, "fix"), (9, "unlinked_fix")):
        add(
            "IC04-pr-" + str(number),
            "change.created",
            dict(
                repo=repo,
                number=number,
                title="Check token expiry server-side",
                head_sha="same-fix-wording",
            ),
            key=key,
            nid=node("Change", repo, number),
            props=dict(status="open"),
        )
    correction = add(
        "IC05-remediation",
        "incident.remediation_recorded",
        dict(change=dict(repo=repo, number=8), incident=incident),
        edges=[("REMEDIATES", ids["fix"], ids["incident"])],
    )
    edge_evidence(
        correction,
        "REMEDIATES",
        ids["fix"],
        ids["incident"],
        link_status="confirmed",
        method="declared",
        confidence=1.0,
    )
    retry_and_conflict(correction, "change", dict(repo=repo, number=9))
    merged = add(
        "IC06-merge-still-open",
        "change.merged",
        dict(repo=repo, number=8, merge_sha="reset-fix-sha"),
        nid=ids["fix"],
        props=dict(status="merged", merge_sha="reset-fix-sha"),
    )
    merged["node_assertions"] = {ids["incident"]: dict(status="detected")}
    add(
        "IC07-explicit-resolution",
        "incident.resolved",
        dict(incident, summary="Verified server-side expiry enforcement"),
        nid=ids["incident"],
        props=dict(status="resolved", summary="Verified server-side expiry enforcement"),
        second=180,
    )
    late = report(
        "IC07-late-detection", "incident", incident, second=50, deployment=ids["deployment"]
    )
    late["expected_props"] = dict(
        status="resolved", summary="Verified server-side expiry enforcement"
    )

    early_ref = dict(repo=repo, service=repo + "/future", incident_id="INC-FUTURE")
    ids["placeholder_change"] = node("Change", repo, 88)
    ids["placeholder_incident"] = node(
        "Incident", repo, early_ref["service"], early_ref["incident_id"]
    )
    early = add(
        "IC08-reference-first",
        "incident.remediation_recorded",
        dict(change=dict(repo=repo, number=88), incident=early_ref),
        nid=ids["placeholder_change"],
        props=dict(status="open"),
        edges=[("REMEDIATES", ids["placeholder_change"], ids["placeholder_incident"])],
        extra={ids["placeholder_incident"]: dict(status="detected")},
    )
    early.update(
        observes_node=False, placeholders=[ids["placeholder_change"], ids["placeholder_incident"]]
    )
    edge_evidence(
        early,
        "REMEDIATES",
        ids["placeholder_change"],
        ids["placeholder_incident"],
        link_status="confirmed",
    )
    add(
        "IC08-change-arrives",
        "change.created",
        dict(repo=repo, number=88, title="Future correction"),
        nid=ids["placeholder_change"],
        props=dict(status="open"),
    )
    report("IC08-incident-arrives", "placeholder_incident", early_ref, deployment_fields=False)

    def lesson(sid, key, reference, *, change=None, rejected=False):
        payload = dict(
            statement="Check token expiry server-side", incident=reference, link_status="confirmed"
        )
        if change:
            payload["change"] = change
        if rejected:
            payload["link_status"] = "rejected"
        step = add(sid, "incident.lesson_recorded", payload)
        digest = sha256(step["request"]["event_id"].encode()).hexdigest() + ":authored"
        nid = "Lesson:" + digest
        ids[key] = nid
        step.update(
            expected_node=nid,
            expected_props=dict(
                status="tentative", statement=payload["statement"], content_hash=digest
            ),
        )
        targets = [
            node("Incident", reference["repo"], reference["service"], reference["incident_id"])
        ]
        if change:
            targets.append(node("Change", change["repo"], change["number"]))
        for target in targets:
            step["expected_edges"].append(["LEARNED_FROM", nid, target])
            edge_evidence(
                step,
                "LEARNED_FROM",
                nid,
                target,
                link_status="rejected" if rejected else "confirmed",
                method="declared",
                confidence=1.0,
            )
        return step

    authored = lesson("IC09-authored-lesson", "lesson", incident, change=dict(repo=repo, number=8))
    retry_and_conflict(authored, "statement", "Changed lesson event content")
    lesson("IC09-identical-text-other-incident", "other_lesson", other_incident)
    lesson("IC09-rejected-support", "rejected_lesson", incident, rejected=True)
    spec_id = prefix + "-TOKEN-EXPIRY-2027"
    cited = add(
        "IC10-explicit-citation",
        "spec.approved",
        dict(
            doc_id=spec_id,
            version="2",
            title="Explicit future token-expiry specification",
            lesson_refs=[dict(content_hash=ids["lesson"].removeprefix("Lesson:"))],
        ),
        key="future_spec",
        nid=node("Spec", spec_id, "2"),
        props=dict(status="approved"),
        edges=[("CITES", node("Spec", spec_id, "2"), ids["lesson"])],
    )
    cited["expected_edge_properties"] = [
        ["CITES", ids["future_spec"], ids["lesson"], dict(pinned_position="$receipt")]
    ]
    add(
        "IC10-similar-unciting-spec",
        "spec.approved",
        dict(
            doc_id=prefix + "-unrelated-spec", version="1", title="Check token expiry server-side"
        ),
        key="unciting_spec",
        nid=node("Spec", prefix + "-unrelated-spec", "1"),
        props=dict(status="approved"),
    )
    unknown = "Lesson:" + "0" * 64 + ":authored"
    ids["unknown_lesson"] = unknown
    unknown_spec = node("Spec", prefix + "-unknown-reference", "1")
    unknown_step = add(
        "IC10-unknown-lesson-citation",
        "spec.approved",
        dict(
            doc_id=prefix + "-unknown-reference",
            version="1",
            lesson_refs=[dict(content_hash=unknown.removeprefix("Lesson:"))],
        ),
        key="unknown_spec",
        nid=unknown_spec,
        props=dict(status="approved"),
        edges=[("CITES", unknown_spec, unknown)],
        extra={unknown: dict(status="tentative")},
    )
    unknown_step["placeholders"] = [unknown]
    unknown_step["expected_edge_properties"] = [
        ["CITES", unknown_spec, unknown, dict(pinned_position="$receipt")]
    ]

    invalids = [
        (
            "detected-missing-repo",
            "incident.detected",
            dict(service=service, incident_id="INVALID"),
        ),
        ("reported-typed-service", "incident.reported", dict(incident, service=[])),
        ("resolved-typed-id", "incident.resolved", dict(incident, incident_id=[])),
        (
            "remediation-incomplete-pr",
            "incident.remediation_recorded",
            dict(incident=incident, change=dict(repo=repo)),
        ),
        (
            "remediation-typed-incident",
            "incident.remediation_recorded",
            dict(incident=dict(incident, repo=[]), change=dict(repo=repo, number=8)),
        ),
        (
            "lesson-typed-statement",
            "incident.lesson_recorded",
            dict(statement=[], incident=incident),
        ),
        (
            "lesson-incomplete-support",
            "incident.lesson_recorded",
            dict(statement="Invalid", incident=dict(repo=repo, incident_id="INVALID")),
        ),
        (
            "citation-nonhex",
            "spec.approved",
            dict(
                doc_id=prefix + "-invalid-spec",
                version="1",
                lesson_refs=[dict(content_hash="g" * 64 + ":authored")],
            ),
        ),
    ]
    for sid, event, payload in invalids:
        step = add("IC11-" + sid, event, payload)
        step["expected_status"] = 422
        if event == "spec.approved":
            step["absence_id"] = node("Spec", payload["doc_id"], payload["version"])
        elif event == "incident.lesson_recorded":
            step["absence_id"] = (
                "Lesson:" + sha256(step["request"]["event_id"].encode()).hexdigest() + ":authored"
            )

    queries = []
    allowed_query_edges = {"OCCURRED_ON", "AFFECTS", "REMEDIATES", "LEARNED_FROM", "CITES"}
    declared_edges = {
        tuple(e) for step in steps if step["expected_status"] == 201 for e in step["expected_edges"]
    }
    rejected_edges = {
        tuple(e[:3])
        for step in steps
        for e in step.get("expected_edge_properties", [])
        if e[3].get("link_status") == "rejected"
    }

    def query(sid, seed, keys, text=None):
        required = [ids[key] for key in keys]
        queries.append(
            dict(
                scenario=sid,
                seed=seed,
                seeds=[seed] if seed else [],
                intent="incident",
                text=text or "incident " + seed,
                required=required,
                forbidden=sorted(set(ids.values()) - set(required)),
                exact=True,
                max_depth=3,
                expected_edges=[
                    list(e)
                    for e in sorted(declared_edges - rejected_edges)
                    if e[0] in allowed_query_edges and e[1] in required and e[2] in required
                ],
            )
        )

    main_keys = ["incident", "deployment", "component", "fix", "lesson", "future_spec"]
    query("IQ1-incident-feedback", ids["incident"], main_keys)
    query("IQ2-deployment-incident", ids["deployment"], main_keys)
    query("IQ3-corrective-pr-incident", ids["fix"], main_keys)
    query("IQ4-future-spec-back-to-incident", ids["future_spec"], main_keys)
    query(
        "IQ5-natural-language-reuse",
        None,
        main_keys,
        "What incident lesson does " + spec_id + " cite?",
    )
    query(
        "IQ6-other-scope-identical-lesson",
        ids["other_incident"],
        ["other_incident", "other_deployment", "other_component", "other_lesson"],
    )
    query("IQ7-no-deployment-reference", ids["no_reference"], ["no_reference", "component"])
    query("IQ8-before-any-deployment", ids["early_incident"], ["early_incident", "component"])
    query("IQ9-rejected-support-excluded", ids["rejected_lesson"], ["rejected_lesson"])
    query("IQ10-unknown-citation-honest", ids["unknown_spec"], ["unknown_spec", "unknown_lesson"])
    query("IQ11-unciting-spec", ids["unciting_spec"], ["unciting_spec"])
    query("IQ12-unlinked-pr", ids["unlinked_fix"], ["unlinked_fix"])
    return dict(
        ids=ids,
        steps=steps,
        queries=queries,
        fallback_seed=ids["incident"],
        source_kind=(
            "Synthetic normalized incident producers; "
            "no native adapters or automatic validated knowledge"
        ),
    )
