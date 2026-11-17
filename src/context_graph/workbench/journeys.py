"""Versioned journey contracts. Assertions are data, never generated executable code."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from context_graph.workbench.models import Strict


class JourneyCheck(Strict):
    id: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=2000)
    source: str = Field(min_length=1, max_length=500)
    kind: Literal[
        "node_present",
        "node_absent",
        "properties",
        "property_absent",
        "edge_present",
        "edge_absent",
        "disposition",
        "unchanged",
        "retrieval",
        "evaluation",
        "retrieval_benchmark",
        "supplemental",
        "graph_exact",
        "evidence_absent",
        "edge_targets",
        "nodes_matching",
    ]
    # Zero-based event checkpoint; None means final graph.
    after_step: int | None = Field(
        default=None,
        ge=0,
        description="Zero-based event index: 0 is the first event; null means final graph.",
    )
    expected: dict[str, Any]


class JourneyEvent(Strict):
    id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=500)
    # Common event envelope retained, including duplicate identities and producer metadata.
    request: dict[str, Any]


class FixtureNode(Strict):
    id: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class FixtureEdge(Strict):
    source: str
    target: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class RetrievalLimits(Strict):
    default_max_depth: int = Field(default=3, ge=0, le=10)
    seed_limit: int = Field(default=10, ge=1, le=100)
    neighbor_limit: int = Field(default=200, ge=1, le=1000)


class QueryOptions(Strict):
    seed_mode: Literal["discover", "explicit"] = "discover"
    max_nodes: int = Field(default=50, ge=1, le=500)
    max_depth: int | None = Field(default=5, ge=0, le=10)
    include_untrusted: bool = False


class GraphFixture(Strict):
    kind: Literal["graph_fixture"] = "graph_fixture"
    nodes: list[FixtureNode] = Field(min_length=1, max_length=500)
    edges: list[FixtureEdge] = Field(default_factory=list, max_length=2000)
    retrieval_limits: RetrievalLimits = Field(default_factory=RetrievalLimits)

    @model_validator(mode="after")
    def validate_edges(self) -> GraphFixture:
        ids = {n.id for n in self.nodes}
        if len(ids) != len(self.nodes):
            raise ValueError("Graph fixture node IDs must be unique")
        if any(e.source not in ids or e.target not in ids for e in self.edges):
            raise ValueError("Graph fixture edge references a missing node")
        return self


class Journey(Strict):
    format_version: Literal[1] = 1
    id: str = Field(pattern=r"^[a-z0-9_-]{1,80}$")
    title: str = Field(min_length=1, max_length=200)
    story: str = Field(min_length=1, max_length=8000)
    source_refs: list[str] = Field(min_length=1, max_length=100)
    pack_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    starting_state: Literal["empty"] | GraphFixture = "empty"
    events: list[JourneyEvent] = Field(max_length=100)
    checks: list[JourneyCheck] = Field(min_length=1, max_length=1000)
    trusted_producers: list[str] = Field(default_factory=list, max_length=30)
    expectations_reviewed: bool = False

    @model_validator(mode="after")
    def validate_references(self) -> Journey:
        if not self.events and self.starting_state == "empty":
            raise ValueError("An empty starting graph needs event deliveries")
        for items in (self.events, self.checks):
            if len({item.id for item in items}) != len(items):
                raise ValueError("Journey event and check IDs must be unique in their lists")
        for check in self.checks:
            if check.after_step is not None and check.after_step >= len(self.events):
                raise ValueError(f"Check {check.id} references a missing event checkpoint")
        return self


class CheckResult(Strict):
    check_id: str
    status: Literal["passed", "failed", "unsupported", "not_run", "error"]
    expected: dict[str, Any]
    actual: dict[str, Any] = Field(default_factory=dict)
    explanation: str = ""


def fixture_journey(name: Literal["implementation", "planning"]) -> Journey:
    """Adapt a frozen journey fixture without regenerating events or its oracle."""
    import hashlib
    import json
    from pathlib import Path

    root = Path(__file__).parent / "fixtures" / "pdlc"
    data = json.loads((root / f"{name}.source.json").read_text())
    bundle_hash = hashlib.sha256()
    for pack_name in ("core", "pdlc"):
        bundle_hash.update((root / f"{pack_name}.pack.yaml").read_bytes())
    source = f"scripts/engram_goal0{3 if name == 'implementation' else 2}_fixtures.py"
    checks: list[JourneyCheck] = []

    def add(kind: str, expected: dict[str, Any], title: str, step: int | None) -> None:
        checks.append(
            JourneyCheck.model_validate(
                dict(
                    id=f"check-{len(checks) + 1}",
                    kind=kind,
                    expected=expected,
                    description=title,
                    source=source,
                    after_step=step,
                )
            )
        )

    events = []
    expected_nodes: dict[str, Any] = {}
    expected_edges: set[tuple[str, str, str]] = set()
    evidence: dict[str, list[str]] = {}
    labels = {
        "PL01": "Create the password-reset specification",
        "PL02-expiry": "Define token expiry",
        "PL02-single": "Define single-use tokens",
        "PL03": "Describe the high-level architecture",
        "PL04": "Refine it into a storage design",
        "PL05": "Approve the first architecture revision",
        "PL05-not-approved": "Reject a non-approval verdict",
        "PL06": "Publish a second architecture revision",
        "PL07-duplicate": "Deliver the same revision again",
        "PL07-conflict": "Reuse an event ID with different design content",
        "PL08-version": "Reject a design missing its version",
        "PL08-kind": "Reject an unknown design kind",
        "PL09-before": "Reference architecture that has not arrived yet",
        "PL09-after": "Receive the missing architecture",
        "PL10-spec": "Create an unrelated specification",
        "PL10-requirement": "Reuse a requirement identifier in another scope",
        "PL10-design": "Design the unrelated feature",
        "IM01": "Create the password-reset specification",
        "IM02": "Define the token-expiry requirement",
        "IM03": "Record the high-level design",
        "IM04": "Record the implementation design",
        "IM05": "Link the implementation ticket",
        "IM06": "Open the implementing pull request",
        "IM07-requested": "Reviewer requests changes",
        "IM07-approved": "Second reviewer approves",
        "IM08-failure": "First test run fails",
        "IM08-success": "Second test run succeeds",
        "IM09-spec": "Create an unrelated specification",
        "IM09-requirement": "Reuse a requirement number in another scope",
        "IM09-ticket": "Reuse a ticket number in another tracker",
        "IM09-change": "Reuse a pull request number in another repository",
        "IM09-test": "Test the unrelated feature",
        "IM10-change": "Open a change without a ticket reference",
        "IM10-test": "Record a test without a requirement reference",
        "IM11-duplicate": "Deliver the same event again",
        "IM11-conflict": "Reuse an event ID with changed content",
        "IM12-revision": "Reject a reference missing its revision",
        "IM12-ticket": "Reject a malformed ticket reference",
        "IM12-review": "Reject an unsupported review verdict",
        "IM12-test": "Reject an unsupported test outcome",
    }
    for index, step in enumerate(data["steps"]):
        scenario = step["scenario"]
        events.append(
            JourneyEvent(
                id=scenario,
                title=labels[scenario],
                request=step["request"],
            )
        )
        add(
            "disposition",
            {"http_status": step["expected_status"]},
            f"{labels[scenario]}: expected acceptance",
            index,
        )
        if step["expected_status"] != 201 or "duplicate" in scenario:
            add("unchanged", {}, f"{scenario}: no persistent changes", index)
            continue
        if step["expected_node"]:
            add(
                "properties",
                {"node": step["expected_node"], "properties": step["expected_props"]},
                f"{scenario}: expected entity properties",
                index,
            )
            add(
                "edge_present",
                {
                    "type": "DERIVED_FROM",
                    "source": step["expected_node"],
                    "target": step["request"]["event_id"],
                },
                f"{scenario}: source event evidence",
                index,
            )
        for node, props in step.get("extra_nodes", {}).items():
            add(
                "properties",
                {"node": node, "properties": props},
                f"{scenario}: linked entity properties",
                index,
            )
        for kind, start, end in step["expected_edges"]:
            add(
                "edge_present",
                {"type": kind, "source": start, "target": end},
                f"{scenario}: {kind}",
                index,
            )
        for node, props in {
            step["expected_node"]: step["expected_props"],
            **step.get("extra_nodes", {}),
        }.items():
            if node:
                expected_nodes[node] = props
                evidence.setdefault(node, []).append(step["request"]["event_id"])
        expected_edges.update(tuple(edge) for edge in step["expected_edges"])
        if scenario == "PL09-before":
            # Existing keyed references create an identity-only placeholder.
            expected_nodes[data["ids"]["late"]] = {}
            add(
                "property_absent",
                {"node": data["ids"]["late"], "property": "body"},
                "Missing architecture has no invented content",
                index,
            )
            add(
                "evidence_absent",
                {"node": data["ids"]["late"]},
                "Placeholder has no invented source event",
                index,
            )
        if scenario == "PL06":
            add(
                "edge_absent",
                {
                    "type": "APPROVES",
                    "source": data["ids"]["approval"],
                    "target": data["ids"]["hld2"],
                },
                "Approval stays with revision one, not revision two",
                index,
            )
        # Deep-copy each checkpoint: later events must not mutate earlier expectations.
        add(
            "graph_exact",
            json.loads(
                json.dumps(
                    {
                        "nodes": expected_nodes,
                        "edges": sorted(expected_edges),
                        "evidence": evidence,
                    }
                )
            ),
            f"{labels[scenario]}: exact domain graph and evidence",
            index,
        )
    for query in data["queries"]:
        required = set(query["required"])
        add(
            "retrieval",
            {
                **query,
                "not_truncated": True,
                "properties": {n: props for n, props in expected_nodes.items() if n in required},
                "edges": [
                    list(e) for e in sorted(expected_edges) if e[1] in required and e[2] in required
                ],
                "evidence": {n: ids for n, ids in evidence.items() if n in required},
            },
            "Find the " + name + " trace · " + query["scenario"],
            None,
        )
    return Journey(
        id=f"pdlc-{name}",
        title=(
            "From requirement to reviewed and tested change"
            if name == "implementation"
            else "From specification to versioned design and approval"
        ),
        story=(
            (
                "Follow requirements into high-level and implementation designs. "
                "Approve one revision, "
                "publish another, and observe a missing parent arrive later. Unrelated work and "
                "malformed events must remain separate."
            )
            if name == "planning"
            else "Follow a password-reset requirement through design, ticket, pull request, "
            "two reviews and failed/successful test runs. An unrelated feature deliberately "
            "reuses local identifiers. Retries and malformed references must not change the graph."
        ),
        source_refs=[source, f"tests/unit/test_{name}_journey.py"],
        pack_digest=bundle_hash.hexdigest(),
        events=events,
        checks=checks,
        trusted_producers=[f"{name}.publisher"],
        expectations_reviewed=True,
    )


def implementation_journey() -> Journey:
    return fixture_journey("implementation")


def planning_journey() -> Journey:
    return fixture_journey("planning")


def reference_journey() -> Journey:
    from pathlib import Path

    return Journey.model_validate_json(
        (Path(__file__).parent / "fixtures/pdlc/references.journey.json").read_text()
    )


def source_coverage(journey: dict[str, Any]) -> list[dict[str, Any]]:
    """Group the reviewed source inventory; coverage is not a test-pass claim."""
    import json
    from pathlib import Path

    from context_graph.workbench.engine import digest

    manifest = json.loads((Path(__file__).parent / "fixtures/pdlc/manifest.json").read_text())
    journey_id = journey["id"]
    pinned = manifest.get("journey_digests", {}).get(journey_id)
    if pinned and pinned != digest(journey):
        return [
            dict(
                source="Prepared journey catalog",
                status="supplemental",
                sites=[],
                reason=(
                    "This saved template predates the coverage audit. Open the current "
                    "prepared journey from All tenants for the audited checks."
                ),
            )
        ]
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in manifest["assertions"]:
        if journey_id not in row.get("journeys", []):
            continue
        key = row["source"], row["status"], row["reason"]
        group = groups.setdefault(key, dict(source=key[0], status=key[1], reason=key[2], sites=[]))
        group["sites"].append(row["line"])
    return list(groups.values())


def retrieval_trust_journey() -> Journey:
    from pathlib import Path

    return Journey.model_validate_json(
        (Path(__file__).parent / "fixtures/pdlc/retrieval-trust.journey.json").read_text()
    )


def release_journey() -> Journey:
    """Frozen adapter output plus the original webhook evaluation artifact."""
    import hashlib
    import json
    from pathlib import Path

    from context_graph.ontology.evaluation import load_eval_set

    root = Path(__file__).parent / "fixtures" / "pdlc"
    deliveries = json.loads((root / "release.source.json").read_text())
    evaluation = load_eval_set(root / "release.eval.yaml")
    checks: list[JourneyCheck] = []

    def add(kind: str, expected: dict[str, Any], title: str, step: int | None = None) -> None:
        checks.append(
            JourneyCheck.model_validate(
                dict(
                    id=f"release-check-{len(checks) + 1}",
                    kind=kind,
                    expected=expected,
                    description=title,
                    source="tests/unit/test_pdlc_end_to_end.py",
                    after_step=step,
                )
            )
        )

    titles = [
        "Open the payment change",
        "Record a failed CI run",
        "Approve the change",
        "Merge the change",
        "Create its linked Jira ticket",
        "Publish the release",
        "Deploy to production",
        "Close the Jira ticket",
    ]
    events = [
        JourneyEvent(id=row["id"], title=titles[i], request=row["request"])
        for i, row in enumerate(deliveries)
    ]
    for i in range(len(events)):
        add("disposition", {"http_status": 201}, "Accept normalized event: " + titles[i], i)
    add(
        "properties",
        {
            "node": "Change:acme/payments|7",
            "properties": {"status": "merged", "merge_sha": "def456", "source_trust": "trusted"},
        },
        "Merged change retains its commit and source trust",
    )
    add(
        "properties",
        {
            "node": "WorkItem:jira|PAY-341",
            "properties": {"status": "done", "title": "Refund retries"},
        },
        "Ticket is closed without losing its title",
    )
    add(
        "properties",
        {"node": "Release:acme/payments|v1.4.0", "properties": {"node_type": "Release"}},
        "Published release exists",
    )
    deployment = "Deployment:production|def456|2026-10-02T09:00:00+00:00"
    add(
        "properties",
        {"node": deployment, "properties": {"status": "succeeded"}},
        "Production deployment succeeded",
    )
    for kind, start, end in [
        ("IMPLEMENTS", "Change:acme/payments|7", "WorkItem:jira|PAY-341"),
        ("INCLUDES", "Release:acme/payments|v1.4.0", "Change:acme/payments|7"),
        ("DECOMPOSES_INTO", "WorkItem:jira|PAY-300", "WorkItem:jira|PAY-341"),
        ("DEPLOYS", deployment, "Change:acme/payments|7"),
        ("REVIEWS", "Review:acme/payments|7|9001", "Change:acme/payments|7"),
        ("RAN_AGAINST", "TestRun:555", "Change:acme/payments|7"),
        ("DERIVED_FROM", "Change:acme/payments|7", events[0].request["event_id"]),
    ]:
        add(
            "edge_present", dict(type=kind, source=start, target=end), f"Verify {kind} relationship"
        )
    add(
        "edge_present",
        dict(
            type="IMPLEMENTS",
            source="Change:acme/payments|7",
            target="WorkItem:jira|PAY-341",
            properties={"link_status": "confirmed"},
        ),
        "Explicit implementation link is confirmed",
    )
    add(
        "edge_targets",
        dict(
            type="DECOMPOSES_INTO",
            node="WorkItem:jira|PAY-341",
            direction="in",
            targets=["WorkItem:jira|PAY-300"],
        ),
        "Ticket has exactly the expected parent",
    )
    add(
        "nodes_matching",
        dict(type="Deployment", properties={"environment": "production"}, ids=[deployment]),
        "Exactly one production deployment exists",
    )
    for q in evaluation.questions:
        # The original test requires every individual F1 to be 1, stricter than its gate.
        add(
            "evaluation",
            {
                # Preserve the frozen legacy journey digest when the source omits the mode.
                "question": q.model_dump(
                    exclude={"seed_mode"} if "seed_mode" not in q.model_fields_set else set()
                ),
                "min_f1": 1.0,
                "declared_gate": evaluation.min_f1,
            },
            q.query,
        )
    add(
        "supplemental",
        {
            "reason": (
                "Signed webhook authentication, spoofed producer rejection, deployment evaluation "
                "gating, extraction and rebuild checks remain in the original end-to-end suite. "
                "This journey executes saved normalized adapter output."
            )
        },
        "Original API and worker checks outside normalized replay",
    )
    return Journey(
        id="pdlc-release",
        title="From pull request to release and deployment",
        story=(
            "Replay eight existing GitHub/Jira fixture deliveries after normalization: "
            "a reviewed change ships in a release and reaches production. Inspect its ticket, "
            "CI result and deployment. Signature verification is not replayed here."
        ),
        source_refs=[
            "tests/unit/test_pdlc_end_to_end.py",
            "tests/fixtures/ontology/pdlc.eval.yaml",
            *[r["source"] for r in deliveries],
        ],
        pack_digest=hashlib.sha256(
            b"".join((root / f"{n}.pack.yaml").read_bytes() for n in ("core", "pdlc"))
        ).hexdigest(),
        events=events,
        checks=checks,
        trusted_producers=["webhook:github", "webhook:jira"],
        expectations_reviewed=True,
    )


RETRIEVAL_VARIANTS = (
    "review-verdict",
    "trust-corroboration",
    "version-precision",
    "number-precision",
    "rare-word",
    "paging-complete",
    "paging-proposed",
    "paging-truncated",
    "paging-traversal",
    "category-evaluation",
    "query-budget",
    "rejected-refinement",
)


def retrieval_variant_journey(name: str) -> Journey:
    from pathlib import Path

    if name not in RETRIEVAL_VARIANTS:
        raise ValueError("Unknown prepared retrieval variant")
    return Journey.model_validate_json(
        (Path(__file__).parent / "fixtures/pdlc" / f"{name}.journey.json").read_text()
    )
