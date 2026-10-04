"""PDLC retrieval evaluation (ADR-0018 phase 2 exit check).

A payments project is built in the in-memory graph: most of it by
projecting PDLC events through the pack rules; catalog entries,
requirements, test links, design sections and an extracted contradiction
are upserted directly, standing in for the catalog importer and LLM
extraction (phase 3).

MOOSEDev-style questions (supersession, set completeness, negation) are
answered by the artifact retriever and by a top-k text baseline: the same
seed types searched with the question's words, best five per type, no
edges. No embedding model runs in tests, so the baseline is lexical, a
stand-in for top-k vector retrieval. Each question has an answer set; an
answer is read from a response the way an agent would read it:

- supersession: nodes of the asked type not marked ``superseded``;
- completeness: nodes reported ``no_link``;
- negation: nodes joined by a ``CONTRADICTS`` edge in the response.

The baseline has no edges or marks, so its answer is the nodes of the
asked type it returns. Retrieval must beat it on every category (F1).
Trace, preflight, impact and trust questions check that traversal finds
the right artifacts (no baseline).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import orjson
import pytest

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.domain.models import AtlasResponse, Event
from context_graph.domain.pack_projection import PackProjector
from context_graph.domain.projection import event_to_node
from context_graph.ontology import load_registry
from context_graph.ports.pack_graph import EdgeWrite, NodeRef, NodeWrite
from context_graph.retrieval.artifacts import ArtifactQuery, ArtifactRetriever
from context_graph.worker.pack_projection import apply_plan

REGISTRY = load_registry(["pdlc"])
START = datetime(2026, 9, 1, 9, 0, tzinfo=UTC)
BASELINE_TOP_K = 5


def _decision(statement: str) -> str:
    return "Decision:" + hashlib.sha256(statement.encode()).hexdigest()


D1 = "Retry failed refunds once"
D2 = "Retry failed refunds up to three times with idempotency keys"
D3 = "Refunds must be processed synchronously"
D4 = "Refunds must be processed asynchronously"


async def build_graph() -> MemoryGraphStore:
    graph = MemoryGraphStore()
    projector = PackProjector(REGISTRY, frozenset({"webhook:github", "webhook:jira"}))
    minute = 0

    async def event(
        event_type: str, payload: dict[str, Any], agent: str = "webhook:github"
    ) -> None:
        nonlocal minute
        minute += 1
        record = Event(
            event_id=uuid4(),
            event_type=event_type,
            occurred_at=START + timedelta(minutes=minute),
            session_id="pdlc:acme/app",
            agent_id=agent,
            trace_id="t",
            payload_ref="p",
            global_position=f"{minute}-0",
        )
        await graph.merge_event_node(event_to_node(record))
        document = orjson.loads(record.model_dump_json()) | {"payload": payload}
        await apply_plan(graph, projector.plan(record, document), 1000)

    # Catalog import stand-in: components with the paths they own
    payments, ledger = (
        NodeRef("Component", "Component:payments"),
        NodeRef("Component", "Component:ledger"),
    )
    await graph.upsert_nodes(
        [
            NodeWrite(
                payments,
                {
                    "catalog_name": "payments",
                    "repo": "acme/app",
                    "path_prefixes": ["refund/"],
                    "source_trust": "trusted",
                },
            ),
            NodeWrite(
                ledger,
                {
                    "catalog_name": "ledger",
                    "repo": "acme/app",
                    "path_prefixes": ["ledger/"],
                    "source_trust": "trusted",
                },
            ),
        ]
    )
    await graph.upsert_edges([EdgeWrite("DEPENDS_ON", payments, ledger, {"kind": "needs"})])

    jira = "webhook:jira"
    await event(
        "pdlc.ticket.created",
        {
            "tracker": "jira",
            "key": "PAY-300",
            "title": "Refund reliability",
            "work_type": "epic",
            "status": "In Progress",
        },
        jira,
    )
    await event(
        "pdlc.ticket.created",
        {
            "tracker": "jira",
            "key": "PAY-341",
            "title": "Retry failed refunds",
            "work_type": "story",
            "status": "To Do",
            "parent_key": "PAY-300",
        },
        jira,
    )
    await event(
        "pdlc.ticket.created",
        {
            "tracker": "jira",
            "key": "PAY-342",
            "title": "Refund idempotency",
            "work_type": "story",
            "status": "In Progress",
            "parent_key": "PAY-300",
        },
        jira,
    )
    await event(
        "pdlc.ticket.created",
        {
            "tracker": "jira",
            "key": "PAY-999",
            "title": "Refund everything twice",
            "work_type": "story",
            "status": "To Do",
        },
        "unknown-bot",
    )
    await event(
        "pdlc.spec.approved",
        {
            "doc_id": "refunds",
            "version": "2",
            "title": "Refunds",
            "request_system": "jira",
            "request_ids": ["REQ-1"],
        },
    )
    change = {"repo": "acme/app"}
    await event(
        "pdlc.change.merged",
        {
            **change,
            "number": 7,
            "title": "Fix refund retry",
            "body": "Fixes PAY-341",
            "merge_sha": "a7",
            "files": ["refund/retry.py"],
        },
    )
    await event(
        "pdlc.change.merged",
        {
            **change,
            "number": 8,
            "title": "Tidy logs",
            "body": "",
            "merge_sha": "a8",
            "files": ["logs/format.py"],
        },
    )
    await event(
        "pdlc.change.merged",
        {
            **change,
            "number": 9,
            "title": "Refund idempotency keys",
            "body": "Closes PAY-342",
            "merge_sha": "a9",
            "files": ["refund/idempotency.py"],
        },
    )
    for number, review in ((7, "r7"), (9, "r9")):
        await event(
            "pdlc.change.reviewed",
            {**change, "number": number, "review_id": review, "verdict": "approved"},
        )
    await event(
        "pdlc.testcaserun.finished",
        {
            **change,
            "test_id": "test_retry",
            "name": "test_retry",
            "run_id": "run-1",
            "outcome": "success",
            "change_number": 7,
        },
    )
    await event(
        "pdlc.release.published",
        {
            **change,
            "version": "v1.4.0",
            "has_breaking": False,
            "entries": [{"pr_number": 7, "section": "fixed"}, {"pr_number": 9, "section": "added"}],
        },
    )
    await event(
        "pdlc.service.deployed",
        {
            "service": "payments",
            "environment": "prod",
            "artifact_id": "app:1.4",
            "repo": "acme/app",
            "change_numbers": [7, 9],
        },
    )
    await event(
        "pdlc.incident.detected",
        {
            "incident_id": "INC-77",
            "severity": "high",
            "description": "Duplicate refunds after retry",
            "service": "payments",
            "environment": "prod",
            "artifact_id": "app:1.4",
        },
    )
    await event(
        "pdlc.decision.recorded",
        {
            "statement": D1,
            "rationale": "keep it simple",
            "applies_to_node_ids": ["Component:payments"],
        },
    )
    await event(
        "pdlc.decision.recorded",
        {
            "statement": D2,
            "rationale": "INC-77 showed one retry is not enough",
            "supersedes_hash": hashlib.sha256(D1.encode()).hexdigest(),
            "applies_to_node_ids": ["Component:payments"],
        },
    )
    await event(
        "pdlc.decision.recorded",
        {
            "statement": D3,
            "rationale": "simpler error handling",
            "applies_to_node_ids": ["Component:payments"],
        },
    )
    await event(
        "pdlc.decision.recorded",
        {
            "statement": D4,
            "rationale": "provider rate limits",
            "applies_to_node_ids": ["Component:payments"],
        },
    )

    # Requirements, test links and design sections (importer and extraction stand-ins)
    spec = NodeRef("Spec", "Spec:refunds|2")
    requirements = {
        "R1": "Retry a failed refund",
        "R2": "Never refund more than the captured amount",
        "R3": "Refund within 24 hours",
    }
    writes = [
        NodeWrite(
            NodeRef("Requirement", f"Requirement:refunds|{key}"),
            {
                "spec_id": "refunds",
                "local_id": key,
                "statement": text,
                "status": "accepted",
                "source_trust": "trusted",
            },
        )
        for key, text in requirements.items()
    ]
    test_window = NodeRef("TestCase", "TestCase:acme/app|test_window")
    hld_old = NodeRef("DesignElement", "DesignElement:refunds-hld|retry-v1")
    hld_new = NodeRef("DesignElement", "DesignElement:refunds-hld|retry-v2")
    constraint = NodeRef("Constraint", "Constraint:never-exceed")
    lesson = NodeRef("Lesson", "Lesson:idempotency")
    writes += [
        NodeWrite(
            test_window, {"repo": "acme/app", "test_id": "test_window", "name": "test_window"}
        ),
        NodeWrite(
            hld_old,
            {
                "doc_id": "refunds-hld",
                "section_path": "retry-v1",
                "title": "Refund retry design",
                "body": "Retry once",
                "status": "approved",
                "source_trust": "trusted",
            },
        ),
        NodeWrite(
            hld_new,
            {
                "doc_id": "refunds-hld",
                "section_path": "retry-v2",
                "title": "Refund retry design",
                "body": "Retry three times with idempotency keys",
                "status": "approved",
                "source_trust": "trusted",
            },
        ),
        NodeWrite(
            constraint,
            {
                "statement": "Refunds must never exceed the captured amount",
                "status": "active",
                "source_trust": "trusted",
            },
        ),
        NodeWrite(
            lesson,
            {
                "statement": "Avoid retrying refunds without idempotency keys",
                "polarity": "avoid",
                "status": "validated",
                "source_trust": "trusted",
            },
        ),
    ]
    await graph.upsert_nodes(writes)
    declared = {"confidence": 1.0, "method": "declared", "link_status": "confirmed"}
    await graph.upsert_edges(
        [
            *(
                EdgeWrite(
                    "REFINES", NodeRef("Requirement", f"Requirement:refunds|{k}"), spec, declared
                )
                for k in requirements
            ),
            EdgeWrite(
                "VERIFIES",
                NodeRef("TestCase", "TestCase:acme/app|test_retry"),
                NodeRef("Requirement", "Requirement:refunds|R1"),
                declared,
            ),
            EdgeWrite(
                "VERIFIES",
                test_window,
                NodeRef("Requirement", "Requirement:refunds|R3"),
                {"confidence": 0.3, "method": "co_change", "link_status": "proposed"},
            ),
            EdgeWrite("SUPERSEDES", hld_new, hld_old),
            EdgeWrite(
                "CONTRADICTS",
                NodeRef("Decision", _decision(D3)),
                NodeRef("Decision", _decision(D4)),
            ),
            EdgeWrite("CONSTRAINS", constraint, payments, {"scope": "refunds"}),
            EdgeWrite("LEARNED_FROM", lesson, NodeRef("Incident", "Incident:INC-77")),
        ]
    )
    return graph


@pytest.fixture(scope="module")
async def setup() -> tuple[MemoryGraphStore, ArtifactRetriever]:
    graph = await build_graph()
    retriever = ArtifactRetriever(
        graph,
        REGISTRY,
        default_max_depth=3,
        seed_limit=10,
        neighbor_limit=200,
        provenance_source="memory",
    )
    return graph, retriever


# ---------------------------------------------------------------------------
# Baseline and scoring
# ---------------------------------------------------------------------------


async def baseline(
    graph: MemoryGraphStore, retriever: ArtifactRetriever, question: str
) -> AtlasResponse:
    """Top-k text retrieval: question words against each seed type's fields; no edges."""
    words = [w for w in question.lower().replace("?", " ").split() if len(w) > 3]
    response = AtlasResponse()
    for label in retriever._seed_types:
        node_type = REGISTRY.node_type(label)
        rows = await graph.search_nodes(
            label, retriever._search_fields(node_type), words, BASELINE_TOP_K
        )
        for props, _hits in rows:
            key = props.get(node_type.key_property)
            response.nodes[str(key)] = response.nodes.get(str(key)) or _atlas_node(
                str(key), label, props
            )
    return response


def _atlas_node(key: str, label: str, props: dict[str, Any]) -> Any:
    from context_graph.domain.models import AtlasNode

    return AtlasNode(node_id=key, node_type=label, attributes=props)


def _f1(found: set[str], expected: set[str]) -> float:
    if not found or not expected:
        return 0.0
    hit = len(found & expected)
    if hit == 0:
        return 0.0
    precision, recall = hit / len(found), hit / len(expected)
    return 2 * precision * recall / (precision + recall)


@dataclass(frozen=True)
class Question:
    category: str
    text: str
    asked_type: str
    expected: frozenset[str]


QUESTIONS = [
    Question(
        "supersession",
        "Is the refund retry design still the approved version, and what replaced the old one?",
        "DesignElement",
        frozenset({"DesignElement:refunds-hld|retry-v2"}),
    ),
    Question(
        "supersession",
        "Is the decision about retrying failed refunds still valid?",
        "Decision",
        frozenset({_decision(D2)}),
    ),
    Question(
        "completeness",
        "Which requirements have no tests?",
        "Requirement",
        frozenset({"Requirement:refunds|R2"}),
    ),
    Question(
        "completeness",
        "Which merged changes are not linked to any ticket?",
        "Change",
        frozenset({"Change:acme/app|8"}),
    ),
    Question(
        "completeness",
        "Which pull requests were merged without an approving review?",
        "Change",
        frozenset({"Change:acme/app|8"}),
    ),
    Question(
        "negation",
        "Do any two current decisions about refunds contradict each other?",
        "Decision",
        frozenset({_decision(D3), _decision(D4)}),
    ),
]


def answer(category: str, asked_type: str, response: AtlasResponse) -> set[str]:
    if category == "supersession":
        # The asked-about items (seeds) and what supersedes them, unless marked superseded
        asked = {k for k in response.meta.seed_nodes if k in response.nodes}
        asked |= {
            e.source for e in response.edges if e.edge_type == "SUPERSEDES" and e.target in asked
        }
        return {
            k
            for k in asked
            if response.nodes[k].node_type == asked_type
            and response.nodes[k].retrieval_reason != "superseded"
        }
    if category == "completeness":
        return {k for k, n in response.nodes.items() if n.retrieval_reason == "no_link"}
    ends = {e.source for e in response.edges if e.edge_type == "CONTRADICTS"}
    ends |= {e.target for e in response.edges if e.edge_type == "CONTRADICTS"}
    return ends


def baseline_answer(asked_type: str, response: AtlasResponse) -> set[str]:
    return {k for k, n in response.nodes.items() if n.node_type == asked_type}


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


async def evaluate(
    graph: MemoryGraphStore, retriever: ArtifactRetriever
) -> dict[str, dict[str, float]]:
    scores: dict[str, dict[str, list[float]]] = {}
    for question in QUESTIONS:
        ours = await retriever.retrieve(ArtifactQuery(question.text))
        theirs = await baseline(graph, retriever, question.text)
        by_category = scores.setdefault(question.category, {"retrieval": [], "baseline": []})
        by_category["retrieval"].append(
            _f1(answer(question.category, question.asked_type, ours), set(question.expected))
        )
        by_category["baseline"].append(
            _f1(baseline_answer(question.asked_type, theirs), set(question.expected))
        )
    return {
        category: {system: sum(values) / len(values) for system, values in systems.items()}
        for category, systems in scores.items()
    }


async def test_retrieval_beats_top_k_text_on_moose_categories(
    setup: tuple[MemoryGraphStore, ArtifactRetriever],
) -> None:
    graph, retriever = setup
    results = await evaluate(graph, retriever)
    print("PDLC retrieval eval (mean F1):", results)  # noqa: T201 - recorded in ADR-0018
    for category, systems in results.items():
        assert systems["retrieval"] > systems["baseline"], (category, systems)
    assert {c: s["retrieval"] for c, s in results.items()} == {
        "supersession": 1.0,
        "completeness": 1.0,
        "negation": 1.0,
    }


class TestRetrievalBehaviour:
    async def test_proposed_links_are_reported_separately(
        self, setup: tuple[MemoryGraphStore, ArtifactRetriever]
    ) -> None:
        _graph, retriever = setup
        response = await retriever.retrieve(ArtifactQuery("Which requirements have no tests?"))
        reasons = {k: n.retrieval_reason for k, n in response.nodes.items()}
        assert reasons == {
            "Requirement:refunds|R2": "no_link",
            "Requirement:refunds|R3": "proposed_only",
        }
        assert response.meta.retrieval_channels == {
            "completeness.VERIFIES.no_link": 1,
            "completeness.VERIFIES.proposed_only": 1,
            "completeness.VERIFIES.confirmed": 1,
        }

    async def test_trace_a_ticket_to_its_deployment(
        self, setup: tuple[MemoryGraphStore, ArtifactRetriever]
    ) -> None:
        _graph, retriever = setup
        response = await retriever.retrieve(ArtifactQuery("Where is PAY-341 deployed right now?"))
        assert response.meta.inferred_intents == {"trace": 1.0}
        assert response.meta.seed_nodes[0] == "WorkItem:jira|PAY-341"  # its own key ranks first
        types = {n.node_type for n in response.nodes.values()}
        assert {"Change", "Deployment", "Component"} <= types
        deployment = next(n for n in response.nodes.values() if n.node_type == "Deployment")
        assert deployment.attributes["environment"] == "prod"
        assert deployment.provenance is not None  # DERIVED_FROM the deployment event
        assert deployment.provenance.agent_id == "webhook:github"

    async def test_why_a_file_exists(
        self, setup: tuple[MemoryGraphStore, ArtifactRetriever]
    ) -> None:
        _graph, retriever = setup
        response = await retriever.retrieve(ArtifactQuery("Why does refund/retry.py exist?"))
        assert response.meta.seed_nodes == ["Change:acme/app|7"]
        assert "WorkItem:jira|PAY-341" in response.nodes

    async def test_preflight_before_editing_a_file(
        self, setup: tuple[MemoryGraphStore, ArtifactRetriever]
    ) -> None:
        _graph, retriever = setup
        response = await retriever.retrieve(
            ArtifactQuery("Anything I should know before editing refund/retry.py?")
        )
        assert response.meta.inferred_intents == {"preflight": 1.0}
        assert {"Constraint:never-exceed", "Incident:INC-77", "Lesson:idempotency"} <= set(
            response.nodes
        )

    async def test_impact_follows_dependencies_inbound(
        self, setup: tuple[MemoryGraphStore, ArtifactRetriever]
    ) -> None:
        _graph, retriever = setup
        response = await retriever.retrieve(ArtifactQuery("What depends on the ledger service?"))
        assert "Component:payments" in response.nodes

    async def test_untrusted_items_need_corroboration(
        self, setup: tuple[MemoryGraphStore, ArtifactRetriever]
    ) -> None:
        _graph, retriever = setup
        hidden = await retriever.retrieve(ArtifactQuery("Where is PAY-999 deployed?"))
        assert "WorkItem:jira|PAY-999" not in hidden.nodes
        shown = await retriever.retrieve(
            ArtifactQuery("Where is PAY-999 deployed?", include_untrusted=True)
        )
        assert shown.nodes["WorkItem:jira|PAY-999"].attributes["source_trust"] == "untrusted"

    async def test_superseded_items_are_kept_only_for_status_questions(
        self, setup: tuple[MemoryGraphStore, ArtifactRetriever]
    ) -> None:
        _graph, retriever = setup
        status = await retriever.retrieve(
            ArtifactQuery("Is the refund retry design still current?")
        )
        assert status.nodes["DesignElement:refunds-hld|retry-v1"].retrieval_reason == "superseded"
        trace = await retriever.retrieve(
            ArtifactQuery("Trace the refund retry design", intent="trace")
        )
        assert "DesignElement:refunds-hld|retry-v1" not in trace.nodes

    async def test_given_seeds_and_bounds(
        self, setup: tuple[MemoryGraphStore, ArtifactRetriever]
    ) -> None:
        _graph, retriever = setup
        response = await retriever.retrieve(
            ArtifactQuery(
                "trace",
                seed_node_ids=("Change:acme/app|9",),
                intent="trace",
                max_depth=1,
                max_nodes=3,
            )
        )
        assert response.meta.seed_nodes == ["Change:acme/app|9"]
        assert len(response.nodes) <= 3
        assert response.meta.capacity is not None
        assert response.meta.capacity.max_depth == 1
