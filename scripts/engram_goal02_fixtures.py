"""Predeclared synthetic password-reset source examples and G02 expectations."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5


def fixtures(run_id):
    prefix = "g02/" + run_id
    spec = prefix + "-reset"
    hld = prefix + "-hld"
    lld = prefix + "-lld"
    other = prefix + "-newsletter"
    ids = dict(
        spec=f"Spec:{spec}|1",
        expiry=f"Requirement:{spec}|1|expiry",
        single=f"Requirement:{spec}|1|single",
        hld1=f"DesignElement:{hld}|tokens|1",
        hld2=f"DesignElement:{hld}|tokens|2",
        lld=f"DesignElement:{lld}|storage|1",
        approval=f"DesignApproval:{prefix}-approval",
        late=f"DesignElement:{hld}|late|1",
        late_lld=f"DesignElement:{lld}|late-storage|1",
        other_spec=f"Spec:{other}|1",
        other_req=f"Requirement:{other}|1|expiry",
        other_design=f"DesignElement:{other}-hld|subscriptions|1",
    )

    def req(key):
        return dict(spec_id=spec, spec_version="1", local_id=key)

    def des(section="tokens", version="1"):
        return dict(doc_id=hld, section_path=section, version=version)

    steps = []
    start = datetime.now(UTC) - timedelta(minutes=5)

    def add(sid, event_type, payload, expected_node=None, props=None, edges=(), status=201):
        # Producer explicitly supplies the common envelope. This is not a native webhook adapter.
        event = dict(
            event_id=str(uuid5(NAMESPACE_URL, run_id + ":" + sid)),
            event_type=event_type,
            occurred_at=(start + timedelta(seconds=len(steps))).isoformat(),
            session_id="planning:" + prefix,
            agent_id="planning.publisher",
            trace_id=run_id,
            payload_ref="synthetic:" + run_id + ":" + sid,
            payload=payload,
        )
        steps.append(
            dict(
                scenario=sid,
                request=event,
                expected_status=status,
                expected_node=expected_node,
                expected_props=props or {},
                expected_edges=[list(e) for e in edges],
            )
        )

    add(
        "PL01",
        "pdlc.spec.changed",
        dict(
            doc_id=spec,
            version="1",
            title="Password reset PRD",
            scope="Reset a forgotten password",
            acceptance_criteria="Expiry and single-use token",
            source_uri="fixture://password-reset/prd/v1",
        ),
        ids["spec"],
        dict(title="Password reset PRD", status="draft"),
    )
    for sid, key, statement in [
        ("PL02-expiry", "expiry", "Password reset token expires in fifteen minutes"),
        ("PL02-single", "single", "Password reset token can be used only once"),
    ]:
        nid = ids["expiry" if key == "expiry" else "single"]
        add(
            sid,
            "pdlc.requirement.changed",
            dict(req(key), statement=statement),
            nid,
            dict(statement=statement),
            [("REFINES", nid, ids["spec"])],
        )
    hld_payload = dict(
        des(),
        kind="hld",
        title="Reset token architecture",
        body="Reset service issues a short-lived token and consumes it once.",
        requirements=[req("expiry"), req("single")],
        source_uri="fixture://password-reset/hld/v1",
    )
    add(
        "PL03",
        "pdlc.design.section_changed",
        hld_payload,
        ids["hld1"],
        dict(kind="hld", body=hld_payload["body"]),
        [("REFINES", ids["hld1"], ids["expiry"]), ("REFINES", ids["hld1"], ids["single"])],
    )
    lld_payload = dict(
        doc_id=lld,
        section_path="storage",
        version="1",
        kind="lld",
        title="Token storage details",
        body="Store a token digest and expire it after fifteen minutes.",
        requirements=[req("expiry")],
        refines_designs=[des()],
    )
    add(
        "PL04",
        "pdlc.design.section_changed",
        lld_payload,
        ids["lld"],
        dict(kind="lld", body=lld_payload["body"]),
        [("REFINES", ids["lld"], ids["hld1"]), ("REFINES", ids["lld"], ids["expiry"])],
    )
    add(
        "PL05",
        "pdlc.design.approval_recorded",
        dict(
            des(),
            approval_id=prefix + "-approval",
            reviewer="alex@example.test",
            verdict="approved",
        ),
        ids["approval"],
        dict(verdict="approved"),
        [("APPROVES", ids["approval"], ids["hld1"])],
    )
    add(
        "PL05-not-approved",
        "pdlc.design.approval_recorded",
        dict(
            des(),
            approval_id=prefix + "-rejected",
            reviewer="alex@example.test",
            verdict="changes_requested",
        ),
        status=422,
    )
    newer = dict(
        hld_payload,
        version="2",
        body="Reset service also rate-limits token issuance.",
        supersedes_version="1",
    )
    add(
        "PL06",
        "pdlc.design.section_changed",
        newer,
        ids["hld2"],
        dict(body=newer["body"]),
        [
            ("SUPERSEDES", ids["hld2"], ids["hld1"]),
            ("REFINES", ids["hld2"], ids["expiry"]),
            ("REFINES", ids["hld2"], ids["single"]),
        ],
    )
    duplicate = deepcopy(steps[-1])
    duplicate.update(scenario="PL07-duplicate", expected_edges=[], expected_node=None)
    steps.append(duplicate)
    conflict = deepcopy(duplicate)
    conflict["scenario"] = "PL07-conflict"
    conflict["request"]["payload"]["body"] = "Conflicting replacement"
    conflict["expected_status"] = 409
    steps.append(conflict)
    invalid = dict(hld_payload)
    invalid.pop("version")
    add("PL08-version", "pdlc.design.section_changed", invalid, status=422)
    add("PL08-kind", "pdlc.design.section_changed", dict(hld_payload, kind="unknown"), status=422)
    add(
        "PL09-before",
        "pdlc.design.section_changed",
        dict(
            doc_id=lld,
            section_path="late-storage",
            version="1",
            kind="lld",
            title="Late parent example",
            body="Storage layout for a parent that arrives later.",
            refines_designs=[des("late")],
        ),
        ids["late_lld"],
        dict(kind="lld"),
        [("REFINES", ids["late_lld"], ids["late"])],
    )
    add(
        "PL09-after",
        "pdlc.design.section_changed",
        dict(des("late"), kind="hld", body="Late-arriving storage architecture"),
        ids["late"],
        dict(body="Late-arriving storage architecture"),
    )
    add(
        "PL10-spec",
        "pdlc.spec.changed",
        dict(doc_id=other, version="1", title="Newsletter subscription PRD"),
        ids["other_spec"],
        dict(title="Newsletter subscription PRD"),
    )
    other_ref = dict(spec_id=other, spec_version="1", local_id="expiry")
    add(
        "PL10-requirement",
        "pdlc.requirement.changed",
        dict(other_ref, statement="Newsletter unsubscribe link expires after seven days"),
        ids["other_req"],
        {},
        [("REFINES", ids["other_req"], ids["other_spec"])],
    )
    add(
        "PL10-design",
        "pdlc.design.section_changed",
        dict(
            doc_id=other + "-hld",
            section_path="subscriptions",
            version="1",
            kind="hld",
            body="Newsletter subscription architecture",
            requirements=[other_ref],
        ),
        ids["other_design"],
        {},
        [("REFINES", ids["other_design"], ids["other_req"])],
    )
    queries = [
        dict(
            scenario="PL11-hld-v1",
            seed=ids["hld1"],
            intent="status",
            required=[ids[k] for k in ["hld1", "hld2", "approval", "expiry", "spec", "lld"]],
            forbidden=[ids[k] for k in ["other_spec", "other_req", "other_design"]],
        ),
        dict(
            scenario="PL11-requirement",
            seed=ids["expiry"],
            intent="trace",
            required=[ids[k] for k in ["expiry", "spec", "hld2"]],
            forbidden=[ids[k] for k in ["other_spec", "other_req", "other_design"]],
        ),
        dict(
            scenario="PL11-history",
            seed=ids["hld2"],
            intent="status",
            required=[ids[k] for k in ["hld1", "hld2", "approval"]],
            forbidden=[],
        ),
        dict(
            scenario="PL11-lld",
            seed=ids["lld"],
            intent="status",
            required=[ids["lld"]],
            forbidden=[],
        ),
        dict(
            scenario="PL12",
            seed=None,
            text="fifteen minutes",
            intent="trace",
            required=[ids["expiry"]],
            forbidden=[ids[k] for k in ["other_spec", "other_req", "other_design"]],
        ),
    ]
    return dict(
        source=(
            "Synthetic normalized producer examples; "
            "no captured native document-service payloads or public-source claim."
        ),
        ids=ids,
        steps=steps,
        queries=queries,
    )
