"""Pack projection: PDLC rules applied to the in-memory graph (ADR-0018 phase 1).

The projector (domain/pack_projection.py) plans the writes; apply_plan
(worker/pack_projection.py) writes them through the PackGraph port. These
run every PDLC rule against the in-memory backend; the same operations are
pinned for Neo4j and Spanner by tests/conformance/test_pack_graph.py.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import orjson
import pytest

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.domain.models import Event
from context_graph.domain.pack_projection import PackProjector, coerce, make_node_id
from context_graph.domain.projection import event_to_node
from context_graph.ontology import load_registry
from context_graph.ports.pack_graph import NodeRef, NodeWrite
from context_graph.worker.pack_projection import apply_plan

REGISTRY = load_registry(["pdlc"])
START = datetime(2026, 10, 4, 10, 0, tzinfo=UTC)


class Harness:
    def __init__(self, trusted: frozenset[str] = frozenset({"webhook:github"})) -> None:
        self.graph = MemoryGraphStore()
        self.projector = PackProjector(REGISTRY, trusted)
        self.minute = 0
        self.events: list[Event] = []

    async def ingest(
        self, event_type: str, payload: dict[str, Any], agent_id: str = "webhook:github"
    ) -> Event:
        self.minute += 1
        event = Event(
            event_id=uuid4(),
            event_type=event_type,
            occurred_at=START + timedelta(minutes=self.minute),
            session_id="pdlc:acme/app",
            agent_id=agent_id,
            trace_id="trace",
            payload_ref="payload",
            global_position=f"{self.minute}-0",
        )
        await self.graph.merge_event_node(event_to_node(event))
        document = orjson.loads(event.model_dump_json())
        document["payload"] = payload
        await apply_plan(self.graph, self.projector.plan(event, document), 1000)
        self.events.append(event)
        return event

    def node(self, node_id: str) -> dict[str, Any]:
        label = node_id.split(":")[0]
        return self.graph.nodes[(label, node_id)]

    def edges(
        self, edge_type: str, *, with_trust: bool = False
    ) -> dict[tuple[str, str], dict[str, Any]]:
        """Edge properties; ``source_trust`` (on every rule edge) only when asked."""
        return {
            (source[1], target[1]): {
                k: v for k, v in props.items() if with_trust or k != "source_trust"
            }
            for (source, kind, target), props in self.graph.edges.items()
            if kind == edge_type
        }


CHANGE = "Change:acme/app|7"


class TestChanges:
    async def test_lifecycle_links_and_provenance(self) -> None:
        h = Harness()
        created = await h.ingest(
            "pdlc.change.created",
            {
                "repo": "acme/app",
                "number": 7,
                "title": "Fix refund retry",
                "body": "Fixes PAY-341",
                "head_sha": "abc",
                "files": ["refund/retry.py"],
            },
        )
        await h.ingest(
            "pdlc.change.reviewed",
            {"repo": "acme/app", "number": 7, "review_id": "r1", "verdict": "approved"},
        )
        await h.ingest(
            "pdlc.change.merged",
            {
                "repo": "acme/app",
                "number": 7,
                "title": "Fix refund retry",
                "body": "Fixes PAY-341. This reverts #5",
                "merge_sha": "def",
                "files": ["refund/retry.py"],
            },
        )

        change = h.node(CHANGE)
        assert change["status"] == "merged"
        assert change["number"] == 7
        assert change["files"] == ["refund/retry.py"]
        assert change["node_type"] == "Change"
        assert change["ontology_version"] == REGISTRY.version
        assert change["source_trust"] == "trusted"
        assert h.node("Review:acme/app|7|r1")["verdict"] == "approved"
        assert ("Review:acme/app|7|r1", CHANGE) in h.edges("REVIEWS")
        # A declared link: confirmed, with the declared-link fields
        assert h.edges("IMPLEMENTS")[(CHANGE, "WorkItem:jira|PAY-341")] == {
            "confidence": 1.0,
            "method": "declared",
            "link_status": "confirmed",
        }
        stub = h.node("WorkItem:jira|PAY-341")
        assert stub["status"] == "open"  # created as a stub, lifecycle initial state
        assert "source_trust" not in stub  # not observed, only referenced
        assert (CHANGE, "Change:acme/app|5") in h.edges("REVERTS")
        assert (CHANGE, str(created.event_id)) in h.edges("DERIVED_FROM")

    async def test_review_only_moves_an_open_change(self) -> None:
        h = Harness()
        payload = {"repo": "acme/app", "number": 7, "title": "t", "body": "", "files": []}
        await h.ingest("pdlc.change.merged", {**payload, "merge_sha": "x"})
        await h.ingest(
            "pdlc.change.reviewed",
            {"repo": "acme/app", "number": 7, "review_id": "late", "verdict": "commented"},
        )
        assert h.node(CHANGE)["status"] == "merged"

    async def test_abandoned_and_untrusted_source(self) -> None:
        h = Harness()
        await h.ingest(
            "pdlc.change.created",
            {"repo": "acme/app", "number": 7, "title": "t", "body": "", "files": []},
            agent_id="someone-else",
        )
        await h.ingest("pdlc.change.abandoned", {"repo": "acme/app", "number": 7, "title": "t"})
        assert h.node(CHANGE)["status"] == "abandoned"
        assert h.node(CHANGE)["source_trust"] == "trusted"  # the later trusted write wins
        h2 = Harness(trusted=frozenset())
        await h2.ingest("pdlc.change.updated", {"repo": "acme/app", "number": 7, "title": "x"})
        assert h2.node(CHANGE)["source_trust"] == "untrusted"

    async def test_git_only_commits(self) -> None:
        h = Harness()
        await h.ingest(
            "pdlc.change.committed",
            {
                "repo": "apache/kafka",
                "subject": "MINOR: fix(streams): handle retries (#41)",
                "body": "KAFKA-1 and KAFKA-2\nReviewers: Ann <a@x>, Bo <b@x>",
                "files": ["streams/a.java"],
            },
        )
        change = h.node("Change:apache/kafka|41")
        assert change["ticket_exempt"] is True
        assert change["change_type"] == "MINOR"
        assert set(h.edges("IMPLEMENTS")) == {
            ("Change:apache/kafka|41", "WorkItem:jira|KAFKA-1"),
            ("Change:apache/kafka|41", "WorkItem:jira|KAFKA-2"),
        }
        assert {k for k in h.graph.nodes if k[0] == "Review"} == {
            ("Review", "Review:apache/kafka|41|Ann <a@x>"),
            ("Review", "Review:apache/kafka|41|Bo <b@x>"),
        }

    async def test_a_missing_key_writes_nothing(self) -> None:
        h = Harness()
        await h.ingest("pdlc.change.created", {"repo": "acme/app", "title": "no number"})
        assert not [k for k in h.graph.nodes if k[0] == "Change"]

    async def test_touches_components_by_path_prefix(self) -> None:
        h = Harness()
        component = "Component:payments"
        await h.graph.upsert_nodes(
            [
                NodeWrite(
                    NodeRef("Component", component),
                    {"catalog_name": "payments", "repo": "acme/app", "path_prefixes": ["refund/"]},
                ),
                NodeWrite(
                    NodeRef("Component", "Component:ledger"),
                    {"catalog_name": "ledger", "repo": "acme/app", "path_prefixes": ["ledger/"]},
                ),
            ]
        )
        await h.ingest(
            "pdlc.change.merged",
            {"repo": "acme/app", "number": 7, "body": "", "files": ["refund/retry.py"]},
        )
        assert set(h.edges("TOUCHES")) == {(CHANGE, component)}


class TestTickets:
    async def test_created_updated_closed_with_parent(self) -> None:
        h = Harness()
        ticket = {"tracker": "jira", "key": "PAY-2", "title": "Retry", "work_type": "story"}
        await h.ingest("pdlc.ticket.created", {**ticket, "status": "To Do", "parent_key": "PAY-1"})
        assert h.node("WorkItem:jira|PAY-2")["status"] == "open"
        assert ("WorkItem:jira|PAY-1", "WorkItem:jira|PAY-2") in h.edges("DECOMPOSES_INTO")
        await h.ingest("pdlc.ticket.updated", {**ticket, "status": "In Progress"})
        assert h.node("WorkItem:jira|PAY-2")["status"] == "in_progress"
        await h.ingest("pdlc.ticket.updated", {**ticket, "status": "Blocked by legal"})
        assert h.node("WorkItem:jira|PAY-2")["status"] == "in_progress"  # unmapped: unchanged
        await h.ingest("pdlc.ticket.closed", {**ticket, "status": "Done", "resolution": "Fixed"})
        node = h.node("WorkItem:jira|PAY-2")
        assert node["status"] == "done"
        assert node["resolution"] == "Fixed"
        assert node["status_changed_at"] == (START + timedelta(minutes=4)).isoformat()


class TestReleasesTestsDeployments:
    async def test_release_includes_each_entry(self) -> None:
        h = Harness()
        await h.ingest(
            "pdlc.release.published",
            {
                "repo": "acme/app",
                "version": "v1.2.0",
                "has_breaking": False,
                "entries": [
                    {"pr_number": 7, "section": "fixed"},
                    {"pr_number": 9, "section": "added"},
                ],
            },
        )
        includes = h.edges("INCLUDES")
        assert includes[("Release:acme/app|v1.2.0", CHANGE)] == {"section": "fixed"}
        assert includes[("Release:acme/app|v1.2.0", "Change:acme/app|9")] == {"section": "added"}
        assert h.node("Release:acme/app|v1.2.0")["breaking"] is False

    async def test_test_runs(self) -> None:
        h = Harness()
        run = {"repo": "acme/app", "test_id": "ci/unit", "name": "unit", "outcome": "failure"}
        await h.ingest("pdlc.testcaserun.finished", {**run, "run_id": "1", "change_number": 7})
        await h.ingest("pdlc.testcaserun.finished", {**run, "run_id": "2"})
        assert ("TestRun:1", "TestCase:acme/app|ci/unit") in h.edges("EXECUTES")
        assert set(h.edges("RAN_AGAINST")) == {("TestRun:1", CHANGE)}
        assert h.node("TestRun:2")["outcome"] == "failure"

    async def test_a_deployed_commit_links_its_merged_change(self) -> None:
        """PDLC 1.4.0: a GitHub deployment names a commit; the change merged as it is linked."""
        h = Harness()
        deploy = {
            "service": "acme/app",
            "environment": "prod",
            "repo": "acme/app",
            "change_numbers": [],
        }
        await h.ingest("pdlc.service.deployed", {**deploy, "artifact_id": "sha7"})  # before merge
        await h.ingest(
            "pdlc.change.merged",
            {"repo": "acme/app", "number": 7, "title": "Fix", "merge_sha": "sha7"},
        )
        await h.ingest(
            "pdlc.change.merged",
            {
                "repo": "acme/other",
                "number": 9,
                "title": "Same sha, other repo",
                "merge_sha": "sha7",
            },
        )
        await h.ingest("pdlc.service.deployed", {**deploy, "artifact_id": "sha7"})
        await h.ingest("pdlc.service.deployed", {**deploy, "artifact_id": "unknown"})
        later = make_node_id(
            "Deployment", ["prod", "sha7", (START + timedelta(minutes=4)).isoformat()]
        )
        # Only the deployment projected after the merge, and only to the change in its repo
        assert set(h.edges("DEPLOYS")) == {(later, CHANGE)}

    async def test_incident_on_the_latest_matching_deployment(self) -> None:
        h = Harness()
        deploy = {"service": "payments", "environment": "prod", "artifact_id": "app:1.2"}
        await h.ingest(
            "pdlc.service.deployed", {**deploy, "repo": "acme/app", "change_numbers": [7]}
        )
        await h.ingest(
            "pdlc.service.deployed", {**deploy, "repo": "acme/app", "change_numbers": []}
        )
        await h.ingest(
            "pdlc.incident.detected",
            {**deploy, "incident_id": "INC-1", "severity": "high", "description": "failing"},
        )
        second = make_node_id(
            "Deployment", ["prod", "app:1.2", (START + timedelta(minutes=2)).isoformat()]
        )
        assert set(h.edges("OCCURRED_ON")) == {("Incident:INC-1", second)}
        assert h.edges("AFFECTS")[("Incident:INC-1", "Component:payments")]["link_status"] == (
            "confirmed"
        )
        assert h.node(second)["status"] == "succeeded"
        await h.ingest("pdlc.incident.resolved", {"incident_id": "INC-1", "summary": "rolled back"})
        assert h.node("Incident:INC-1")["status"] == "resolved"


class TestKnowledge:
    async def test_decisions_supersede_and_apply(self) -> None:
        h = Harness()
        await h.ingest("pdlc.decision.recorded", {"statement": "Use idempotency keys"})
        old_hash = hashlib.sha256(b"Use idempotency keys").hexdigest()
        await h.ingest(
            "pdlc.decision.recorded",
            {
                "statement": "Use idempotency keys with a 24h window",
                "rationale": "duplicates after retries",
                "supersedes_hash": old_hash,
                "applies_to_node_ids": ["Component:payments", "Nope:x", "Event:missing"],
            },
        )
        new_hash = hashlib.sha256(b"Use idempotency keys with a 24h window").hexdigest()
        assert set(h.edges("SUPERSEDES")) == {(f"Decision:{new_hash}", f"Decision:{old_hash}")}
        assert h.node(f"Decision:{new_hash}")["status"] == "accepted"
        # node_id targets must exist and be allowed: Component is not created by reference
        assert h.edges("APPLIES_TO") == {}

    async def test_specs_refine_requests_and_cite_pinned(self) -> None:
        h = Harness()
        await h.graph.upsert_nodes(
            [NodeWrite(NodeRef("Constraint", "Constraint:c1"), {"statement": "never exceed"})]
        )
        event = await h.ingest(
            "pdlc.spec.approved",
            {
                "doc_id": "refunds",
                "version": "2",
                "title": "Refunds",
                "request_system": "jira",
                "request_ids": ["REQ-1", "REQ-2"],
                "cited_node_ids": ["Constraint:c1"],
            },
        )
        spec = "Spec:refunds|2"
        assert set(h.edges("REFINES")) == {
            (spec, "Request:jira|REQ-1"),
            (spec, "Request:jira|REQ-2"),
        }
        assert h.edges("CITES")[(spec, "Constraint:c1")] == {
            "pinned_position": event.global_position
        }


class TestValues:
    def test_node_ids_are_canonical_and_escaped(self) -> None:
        assert make_node_id("Change", ["acme/app", 7]) == "Change:acme/app|7"
        assert make_node_id("WorkItem", ["a|b", "50%"]) == "WorkItem:a%7Cb|50%25"

    @pytest.mark.parametrize(
        ("value", "spec", "expected"),
        [
            ("41", "int", 41),
            (41.0, "int", 41),
            ("4.5", "int", None),
            ("x", "float", None),
            ("true", "bool", True),
            ("2026-10-04T10:00:00Z", "datetime", "2026-10-04T10:00:00+00:00"),
            ("not a date", "datetime", None),
            ("a", "list<string>", ["a"]),
            ([1, "x"], "list<int>", [1]),
            (["a"], "string", None),
        ],
    )
    def test_coercion(self, value: object, spec: str, expected: object) -> None:
        assert coerce(value, spec) == expected

    def test_events_without_rules_plan_nothing(self) -> None:
        projector = PackProjector(REGISTRY, frozenset())
        assert not projector.handles("tool.execute")


class TestReviewFindings:
    """Regression cases from the phase 1 review (ADR-0018 implementation notes)."""

    async def test_oversized_integers_write_nothing(self) -> None:
        h = Harness()
        await h.ingest(
            "pdlc.change.created", {"repo": "acme/app", "number": "1" + "0" * 25, "title": "x"}
        )
        await h.ingest("pdlc.change.created", {"repo": "acme/app", "number": 2**63, "title": "x"})
        assert not [k for k in h.graph.nodes if k[0] == "Change"]
        assert coerce("9007199254740993", "int") == 9007199254740993  # exact, past 2**53

    async def test_fan_out_keeps_positions(self) -> None:
        h = Harness()
        await h.ingest(
            "pdlc.release.published",
            {
                "repo": "acme/app",
                "version": "v1",
                "entries": [{"pr_number": 7, "section": "fixed"}],
            },
        )
        await h.ingest(
            "pdlc.release.published",
            {
                "repo": "acme/app",
                "version": "v2",
                "entries": [
                    {"section": "breaking"},
                    {"pr_number": 8, "section": "added"},
                    {"pr_number": 9, "section": "fixed"},
                ],
            },
        )
        includes = h.edges("INCLUDES")
        assert includes[("Release:acme/app|v1", CHANGE)] == {"section": "fixed"}
        assert includes[("Release:acme/app|v2", "Change:acme/app|8")] == {"section": "added"}
        assert includes[("Release:acme/app|v2", "Change:acme/app|9")] == {"section": "fixed"}

    async def test_a_late_opened_does_not_undo_a_merge(self) -> None:
        h = Harness()
        change = {"repo": "acme/app", "number": 7, "title": "t", "body": "", "files": []}
        await h.ingest("pdlc.change.merged", {**change, "merge_sha": "x"})
        await h.ingest("pdlc.change.created", change)
        assert h.node(CHANGE)["status"] == "merged"
        await h.ingest("pdlc.change.abandoned", {"repo": "acme/app", "number": 9})
        await h.ingest("pdlc.change.created", {**change, "number": 9})
        assert h.node("Change:acme/app|9")["status"] == "open"  # reopened

    async def test_latest_deployment_regardless_of_write_order(self) -> None:
        h = Harness()
        deploy = {"service": "payments", "environment": "prod", "artifact_id": "a"}
        for _ in range(3):
            await h.ingest("pdlc.service.deployed", {**deploy, "change_numbers": []})
        await h.ingest(
            "pdlc.incident.detected",
            {**deploy, "incident_id": "I", "severity": "low", "description": "d"},
        )
        latest = make_node_id(
            "Deployment", ["prod", "a", (START + timedelta(minutes=3)).isoformat()]
        )
        assert set(h.edges("OCCURRED_ON")) == {("Incident:I", latest)}

    async def test_prefixes_match_on_path_boundaries(self) -> None:
        h = Harness()
        await h.graph.upsert_nodes(
            [
                NodeWrite(
                    NodeRef("Component", "Component:src"),
                    {"catalog_name": "src", "repo": "acme/app", "path_prefixes": ["src"]},
                )
            ]
        )
        await h.ingest(
            "pdlc.change.merged",
            {"repo": "acme/app", "number": 7, "body": "", "files": ["src2/a.py"]},
        )
        assert h.edges("TOUCHES") == {}
        await h.ingest(
            "pdlc.change.merged",
            {"repo": "acme/app", "number": 8, "body": "", "files": ["src/a.py"]},
        )
        assert set(h.edges("TOUCHES")) == {("Change:acme/app|8", "Component:src")}
