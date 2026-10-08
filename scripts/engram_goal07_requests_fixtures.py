"""G07-A normalized HTTP inputs and independent literal graph/query oracles (#54)."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

D1_HASH = "0e5a32cc0b91694dda1beff8480461f5a0750d2fb9b69e31b22c7fa8d67c85d7"
D2_HASH = "f034f628d70ae8e6027dace07e68145ce5887143889b820d6bfc54c79b64d2df"
SIMILAR_HASH = "64bb1e9112824839439cf081d7b449ce96c3d60ee0227edef7d20b6e8327c8f3"


def fixtures(run_id, *, start=None):
    # One isolated owned G07 dataset: keep the specification's exact example IDs.
    start = start or (datetime.now(UTC) - timedelta(minutes=10)).replace(microsecond=0)
    ids = dict(
        request="Request:product|RESET-REQUEST",
        other_request="Request:support|RESET-REQUEST",
        minimal_request="Request:product|MINIMAL",
        spec="Spec:RESET-PRD|1",
        requirement="Requirement:RESET-PRD|1|expiry",
        design="DesignElement:RESET-HLD|tokens|1",
        decision="Decision:" + D1_HASH,
        replacement="Decision:" + D2_HASH,
        similar="Decision:" + SIMILAR_HASH,
        unknown_design="DesignElement:UNKNOWN-HLD|tokens|1",
    )
    steps = []

    def add(sid, event, payload, key=None, props=None, edges=(), extra=None, status=201):
        step = dict(
            scenario=sid,
            request=dict(
                event_id=str(uuid5(NAMESPACE_URL, run_id + ":" + sid)),
                event_type="pdlc." + event,
                occurred_at=(start + timedelta(seconds=len(steps))).isoformat(),
                session_id="g07/" + run_id,
                agent_id="request.publisher",
                trace_id=run_id,
                payload_ref="synthetic:" + run_id + ":" + sid,
                payload=deepcopy(payload),
            ),
            expected_status=status,
            expected_node=ids[key] if key else None,
            expected_props=props or {},
            expected_edges=[list(edge) for edge in edges],
            extra_nodes=extra or {},
        )
        steps.append(step)
        return step

    request = dict(
        source_system="product",
        external_id="RESET-REQUEST",
        title="Prevent expired token use",
        description="Reject password-reset tokens after fifteen minutes",
    )
    created = add("A01-request", "request.created", request, "request", dict(request, status="new"))
    retry = deepcopy(created)
    retry.update(scenario="A01-request-retry", duplicate=True)
    steps.append(retry)
    conflict = deepcopy(created)
    conflict.update(
        scenario="A01-request-conflict",
        expected_status=409,
        expected_node=None,
        expected_props={},
        expected_edges=[],
        extra_nodes={},
    )
    conflict["request"]["payload"]["title"] = "Changed-content event ID reuse"
    steps.append(conflict)
    add(
        "A02-source-collision",
        "request.created",
        dict(request, source_system="support"),
        "other_request",
        dict(request, source_system="support", status="new"),
    )
    add(
        "A02-approved-spec",
        "spec.approved",
        dict(
            doc_id="RESET-PRD",
            version="1",
            title="Token expiry specification",
            request_system="product",
            request_ids=["RESET-REQUEST"],
        ),
        "spec",
        dict(status="approved", title="Token expiry specification"),
        [
            ("REFINES", ids["spec"], ids["request"]),
        ],
    )
    add(
        "A03-requirement",
        "requirement.changed",
        dict(
            spec_id="RESET-PRD",
            spec_version="1",
            local_id="expiry",
            statement="Reject expired tokens",
        ),
        "requirement",
        dict(status="proposed", statement="Reject expired tokens"),
        [
            ("REFINES", ids["requirement"], ids["spec"]),
        ],
    )
    add(
        "A03-design",
        "design.section_changed",
        dict(
            doc_id="RESET-HLD",
            section_path="tokens",
            version="1",
            kind="hld",
            title="Server token expiry",
            body="Validate token expiry before loading the account",
        ),
        "design",
        dict(status="draft", title="Server token expiry"),
    )
    add(
        "A03-scoped-decision",
        "decision.recorded",
        dict(
            statement="Check token expiry on the server",
            rationale="Clients cannot enforce expiry",
            applies_to_node_ids=[ids["requirement"], ids["design"]],
        ),
        "decision",
        dict(
            status="accepted",
            statement="Check token expiry on the server",
            rationale="Clients cannot enforce expiry",
        ),
        [
            ("APPLIES_TO", ids["decision"], ids["requirement"]),
            ("APPLIES_TO", ids["decision"], ids["design"]),
        ],
    )
    add(
        "A04-replacement",
        "decision.recorded",
        dict(
            statement="Validate token expiry before loading the account",
            supersedes_hash=D1_HASH,
            applies_to_node_ids=[ids["requirement"], ids["design"]],
        ),
        "replacement",
        dict(status="accepted", statement="Validate token expiry before loading the account"),
        [
            ("SUPERSEDES", ids["replacement"], ids["decision"]),
            ("APPLIES_TO", ids["replacement"], ids["requirement"]),
            ("APPLIES_TO", ids["replacement"], ids["design"]),
        ],
    )
    # Unknown node_id references are not stubs: only existing permitted endpoints can link.
    add(
        "A05-similar-invalid-and-unknown-references",
        "decision.recorded",
        dict(
            statement="Check token expiry on the server too",
            applies_to_node_ids=[
                ids["other_request"],
                "Undeclared:42",
                "no-type",
                "DesignElement:",
                ids["unknown_design"],
            ],
        ),
        "similar",
        dict(status="accepted", statement="Check token expiry on the server too"),
    )
    add(
        "A05-minimal",
        "request.created",
        dict(source_system="product", external_id="MINIMAL"),
        "minimal_request",
        dict(status="new", source_system="product", external_id="MINIMAL"),
    )
    for field in ("source_system", "external_id"):
        for suffix, value in (("missing", None), ("null", None), ("wrong-type", []), ("empty", "")):
            payload = dict(source_system="product", external_id="INVALID")
            if suffix == "missing":
                del payload[field]
            else:
                payload[field] = value
            add("A05-" + field + "-" + suffix, "request.created", payload, status=422)

    declared_link = dict(confidence=1.0, method="declared", link_status="confirmed")
    for step in steps:
        step["expected_edge_properties"] = [
            [kind, source, target, deepcopy(declared_link)]
            for kind, source, target in step["expected_edges"]
            if kind in ("REFINES", "APPLIES_TO")
        ]

    queries = []

    def query(sid, seed, keys, intent, depth, edges, text=""):
        required = [ids[key] for key in keys]
        queries.append(
            dict(
                scenario=sid,
                seed=ids[seed] if seed else None,
                seeds=[ids[seed]] if seed else [],
                intent=intent,
                text=text,
                max_depth=depth,
                required=required,
                forbidden=sorted(set(ids.values()) - set(required)),
                exact=True,
                expected_edges=[list(edge) for edge in edges],
            )
        )

    query(
        "AQ01-request-forward",
        "request",
        ["request", "spec"],
        "trace",
        1,
        [
            ("REFINES", ids["spec"], ids["request"]),
        ],
        "Which specification addresses this request?",
    )
    query(
        "AQ02-spec-reverse",
        "spec",
        ["request", "spec", "requirement"],
        "trace",
        1,
        [
            ("REFINES", ids["spec"], ids["request"]),
            ("REFINES", ids["requirement"], ids["spec"]),
        ],
        "Which request does this specification address?",
    )
    query(
        "AQ03-decision-history",
        "design",
        ["design", "decision", "replacement"],
        "status",
        2,
        [
            ("APPLIES_TO", ids["decision"], ids["design"]),
            ("APPLIES_TO", ids["replacement"], ids["design"]),
            ("SUPERSEDES", ids["replacement"], ids["decision"]),
        ],
        "What decision applies to this design, and which decision did it replace?",
    )
    queries[-1]["expected_retrieval_reasons"] = {ids["decision"]: "superseded"}
    query("AQ04-source-separation", "other_request", ["other_request"], "trace", 1, [])
    query("AQ05-titleless-exact-id", "minimal_request", ["minimal_request"], "trace", 1, [])
    query(
        "AQ06-request-natural-language",
        None,
        ["request", "other_request", "spec"],
        "trace",
        1,
        [("REFINES", ids["spec"], ids["request"])],
        "Prevent expired token use",
    )
    query("AQ07-similar-no-implicit-links", "similar", ["similar"], "status", 1, [])
    return dict(
        ids=ids,
        steps=steps,
        queries=queries,
        fallback_seed=ids["request"],
        source_kind="Synthetic normalized Request/Spec/Decision producers; no native adapter claim",
    )
