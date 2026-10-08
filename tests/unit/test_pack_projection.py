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
    def __init__(
        self, trusted: frozenset[str] = frozenset({"webhook:github"}), lookup_limit: int = 1000
    ) -> None:
        self.graph = MemoryGraphStore()
        self.projector = PackProjector(REGISTRY, trusted)
        self.lookup_limit = lookup_limit
        self.minute = 0
        self.events: list[Event] = []

    async def ingest(
        self,
        event_type: str,
        payload: dict[str, Any],
        agent_id: str = "webhook:github",
        *,
        at_minute: int | None = None,
    ) -> Event:
        """Project one event; it occurs a minute after the last, or at ``at_minute``."""
        self.minute += 1
        event = Event(
            event_id=uuid4(),
            event_type=event_type,
            occurred_at=START + timedelta(minutes=self.minute if at_minute is None else at_minute),
            session_id="pdlc:acme/app",
            agent_id=agent_id,
            trace_id="trace",
            payload_ref="payload",
            global_position=f"{self.minute}-0",
        )
        await self.graph.merge_event_node(event_to_node(event))
        document = orjson.loads(event.model_dump_json())
        document["payload"] = payload
        await apply_plan(self.graph, self.projector.plan(event, document), self.lookup_limit)
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
        """A deployment names a commit; the change merged as it is linked, whichever comes first.

        PDLC 1.4.0 linked deployments projected after the merge; 1.7.0 (review N3) also
        links those projected before it, when the change merges. Never across repositories.
        """
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
        earlier, later = (
            make_node_id(
                "Deployment",
                [
                    "acme/app",
                    "acme/app",
                    "prod",
                    "sha7",
                    (START + timedelta(minutes=m)).isoformat(),
                ],
            )
            for m in (1, 4)
        )
        # Both deployments of the commit, and only to the change in their repo
        assert set(h.edges("DEPLOYS")) == {(earlier, CHANGE), (later, CHANGE)}
        assert h.node(earlier)["repo"] == "acme/app"

    async def test_github_revert_forms_link_the_reverted_change(self) -> None:
        """PDLC 1.5.0: git's quoted-title revert and the revert button's "Reverts owner/repo#N"."""
        h = Harness()
        merged = [
            # git revert of a squash-merged PR (OpenDAL #7943); the title is cut by GitHub
            (
                21,
                'Revert "fix(gcs): stop double-encoding paths',
                'Revert "fix(gcs): stop double-encoding paths (#7)"\n\nThis reverts commit 19e0.',
            ),
            (22, 'Revert "Add retries"', "Reverts acme/app#8"),
            (23, "Undo the cache", "This reverts #9"),
            # a squash that reverted one of its own commits: no PR named, no edge
            (24, "fix: CI", '* Fix lint\n\n* Revert "Fix lint"\n\nThis reverts commit 7f70.'),
        ]
        for number, title, body in merged:
            await h.ingest(
                "pdlc.change.merged",
                {"repo": "acme/app", "number": number, "title": title, "body": body},
            )
        assert set(h.edges("REVERTS")) == {
            ("Change:acme/app|21", "Change:acme/app|7"),
            ("Change:acme/app|22", "Change:acme/app|8"),
            ("Change:acme/app|23", "Change:acme/app|9"),
        }

    async def test_incident_on_the_latest_matching_deployment(self) -> None:
        h = Harness()
        deploy = {
            "repo": "acme/app",
            "service": "payments",
            "environment": "prod",
            "artifact_id": "app:1.2",
        }
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
            "Deployment",
            ["acme/app", "payments", "prod", "app:1.2", (START + timedelta(minutes=2)).isoformat()],
        )
        assert set(h.edges("OCCURRED_ON")) == {("Incident:acme/app|payments|INC-1", second)}
        assert h.edges("AFFECTS")[("Incident:acme/app|payments|INC-1", "Component:payments")][
            "link_status"
        ] == ("confirmed")
        assert h.node(second)["status"] == "succeeded"
        await h.ingest(
            "pdlc.incident.resolved",
            {
                "repo": "acme/app",
                "service": "payments",
                "incident_id": "INC-1",
                "summary": "rolled back",
            },
        )
        assert h.node("Incident:acme/app|payments|INC-1")["status"] == "resolved"

    async def test_the_latest_deployment_however_many_match(self) -> None:
        """Review 3.2: the lookup limit cut matches in key order before picking the latest."""
        h = Harness(lookup_limit=2)
        deploy = {
            "repo": "acme/app",
            "service": "payments",
            "environment": "prod",
            "artifact_id": "app:1.2",
        }
        # Redeployed at minutes 30, 10, 20: key order (by start time) is 10, 20, 30
        for minute in (30, 10, 20):
            await h.ingest(
                "pdlc.service.deployed",
                {**deploy, "repo": "acme/app", "change_numbers": []},
                at_minute=minute,
            )
        await h.ingest(
            "pdlc.incident.detected",
            {**deploy, "incident_id": "INC-2", "severity": "high"},
            at_minute=40,
        )
        latest = make_node_id(
            "Deployment",
            [
                "acme/app",
                "payments",
                "prod",
                "app:1.2",
                (START + timedelta(minutes=30)).isoformat(),
            ],
        )
        assert set(h.edges("OCCURRED_ON")) == {("Incident:acme/app|payments|INC-2", latest)}

    async def test_an_incident_never_occurs_on_a_later_deployment(self) -> None:
        """Review N2: the deployment running when the incident happened, not a later one."""
        h = Harness()
        deploy = {
            "repo": "acme/app",
            "service": "payments",
            "environment": "prod",
            "artifact_id": "app:1.2",
        }
        for minute in (10, 50):  # the second deployment comes after the incident
            await h.ingest(
                "pdlc.service.deployed",
                {**deploy, "repo": "acme/app", "change_numbers": []},
                at_minute=minute,
            )
        await h.ingest(
            "pdlc.incident.detected",
            {**deploy, "incident_id": "INC-3", "severity": "high"},
            at_minute=30,
        )
        running = make_node_id(
            "Deployment",
            [
                "acme/app",
                "payments",
                "prod",
                "app:1.2",
                (START + timedelta(minutes=10)).isoformat(),
            ],
        )
        assert set(h.edges("OCCURRED_ON")) == {("Incident:acme/app|payments|INC-3", running)}
        # Before any deployment of the artifact: no link at all
        await h.ingest(
            "pdlc.incident.detected",
            {**deploy, "incident_id": "INC-4", "severity": "low"},
            at_minute=5,
        )
        assert ("Incident:acme/app|payments|INC-4", running) not in h.edges("OCCURRED_ON")


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
        deploy = {
            "repo": "acme/app",
            "service": "payments",
            "environment": "prod",
            "artifact_id": "a",
        }
        for _ in range(3):
            await h.ingest("pdlc.service.deployed", {**deploy, "change_numbers": []})
        await h.ingest(
            "pdlc.incident.detected",
            {**deploy, "incident_id": "I", "severity": "low", "description": "d"},
        )
        latest = make_node_id(
            "Deployment",
            ["acme/app", "payments", "prod", "a", (START + timedelta(minutes=3)).isoformat()],
        )
        assert set(h.edges("OCCURRED_ON")) == {("Incident:acme/app|payments|I", latest)}

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


class TestStagedFlush:
    """A flush's plans are written in four staged calls, with the same result (review 3.1)."""

    @staticmethod
    def _events(items: list[tuple[str, dict[str, Any]]]) -> list[tuple[Event, dict[str, Any]]]:
        events = []
        for minute, (event_type, payload) in enumerate(items, start=1):
            event = Event(
                event_id=uuid4(),
                event_type=event_type,
                occurred_at=START + timedelta(minutes=minute),
                session_id="pdlc:acme/app",
                agent_id="webhook:github",
                trace_id="trace",
                payload_ref="payload",
                global_position=f"{minute}-0",
            )
            events.append((event, orjson.loads(event.model_dump_json()) | {"payload": payload}))
        return events

    @staticmethod
    async def _plans(h: Harness, events: list[tuple[Event, dict[str, Any]]]) -> list[Any]:
        for event, _document in events:
            await h.graph.merge_event_node(event_to_node(event))
        return [h.projector.plan(event, document) for event, document in events]

    async def test_transitions_apply_in_log_order(self) -> None:
        from context_graph.worker.pack_projection import apply_plans

        change = {"repo": "acme/app", "number": 7, "title": "Fix"}
        items = [
            ("pdlc.change.created", change),
            ("pdlc.change.merged", {**change, "merge_sha": "sha7"}),
            ("pdlc.change.abandoned", change),  # only_from [open, reviewed]: refused
            (
                "pdlc.service.deployed",
                {
                    "service": "acme/app",
                    "environment": "prod",
                    "repo": "acme/app",
                    "artifact_id": "sha7",
                    "change_numbers": [],
                },
            ),
        ]
        events = self._events(items)
        staged, single = Harness(), Harness()
        await apply_plans(staged.graph, await self._plans(staged, events), 1000)
        for plan in await self._plans(single, events):
            await apply_plan(single.graph, plan, 1000)

        assert staged.node(CHANGE)["status"] == "merged"
        assert staged.graph.nodes == single.graph.nodes
        assert staged.graph.edges == single.graph.edges
        assert len(staged.edges("DEPLOYS")) == 1
