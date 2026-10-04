"""KeywordIndex and VectorIndex conformance suite (ADR-0019 C4, §5).

Every index returns hits best first with ranks 0..n-1 and scores in
[0, 1] that never increase down the list, honours limits and thresholds,
and declares whether its scores are native.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from context_graph.adapters.search import GraphVectorIndex
from tests.conformance.graph_fixtures import entity_node, unit_vector
from tests.fixtures.events import make_event

if TYPE_CHECKING:
    from context_graph.ports.graph_backend import GraphBackend
    from context_graph.ports.search import SearchHit
    from tests.conformance.conftest import LogHarness


def _assert_well_formed(hits: list[SearchHit]) -> None:
    assert [hit.rank for hit in hits] == list(range(len(hits)))
    scores = [hit.score for hit in hits]
    assert all(0.0 <= score <= 1.0 for score in scores)
    assert scores == sorted(scores, reverse=True)


class TestKeywordIndex:
    async def test_hits_are_well_formed(self, log_harness: LogHarness) -> None:
        session = f"conf-{uuid4().hex[:8]}"
        events = [make_event(session_id=session) for _ in range(3)]
        for event in events:
            await log_harness.log.append(event)
            await log_harness.set_document_fields(
                str(event.event_id), {"summary": "build failed on ci"}
            )
        index = log_harness.keyword_index
        assert index is not None

        hits = await index.search("build", session_id=session, limit=10)
        _assert_well_formed(hits)
        assert {hit.id for hit in hits} == {str(e.event_id) for e in events}
        assert len(await index.search("build", session_id=session, limit=2)) == 2
        assert await index.search("nothing-matches-this", session_id=session) == []
        assert isinstance(index.scores_are_native, bool)

    async def test_question_finds_payload_text(self, log_harness: LogHarness) -> None:
        """A natural-language question matches events by any of its terms.

        Events carry no summary or keywords: the text comes from their
        payload at ingest, as it does for every real event.
        """
        session = f"conf-{uuid4().hex[:8]}"
        texts = {
            "most": "Payment declined for card 4242 after the fraud check",
            "some": "Card details updated on the profile page",
            "none": "Weather forecast requested for Lisbon",
        }
        events = {key: make_event(session_id=session) for key in texts}
        for key, event in events.items():
            await log_harness.log.append(event, payload={"content": texts[key]})
        elsewhere = make_event(session_id=f"conf-{uuid4().hex[:8]}")
        await log_harness.log.append(elsewhere, payload={"content": texts["most"]})
        index = log_harness.keyword_index
        assert index is not None

        question = "Why was the payment for card 4242 declined?"
        hits = await index.search(question, session_id=session, limit=10)

        _assert_well_formed(hits)
        assert [hit.id for hit in hits] == [
            str(events["most"].event_id),
            str(events["some"].event_id),
        ]
        anywhere = await index.search(question, limit=10)
        assert str(elsewhere.event_id) in {hit.id for hit in anywhere}
        assert await index.search("why did it?", session_id=session) == []

    async def test_search_text_is_stored_at_ingest(self, log_harness: LogHarness) -> None:
        event = make_event(session_id=f"conf-{uuid4().hex[:8]}", tool_name="web_search")
        payload = {"input": {"query": "spanner pricing"}, "output": "Enterprise edition"}
        await log_harness.log.append(event, payload=payload)

        (document,) = await log_harness.log.get_documents([str(event.event_id)])

        assert document is not None
        assert document["search_text"] == "web_search spanner pricing Enterprise edition"
        assert document["payload"] == payload


class TestVectorIndex:
    async def test_hits_are_well_formed(self, graph: GraphBackend) -> None:
        await graph.merge_entity_node(entity_node("same", embedding=unit_vector(0)))
        await graph.merge_entity_node(entity_node("near", embedding=unit_vector(0, tilt=0.3)))
        await graph.merge_entity_node(entity_node("far", embedding=unit_vector(5)))
        index = GraphVectorIndex(graph)

        hits = await index.nearest(unit_vector(0), top_k=3, threshold=0.0)
        _assert_well_formed(hits)
        assert [hit.id for hit in hits][:2] == ["same", "near"]
        assert hits[0].fields["name"] == "same"
        assert index.scores_are_native is True

    async def test_threshold_and_top_k(self, graph: GraphBackend) -> None:
        await graph.merge_entity_node(entity_node("same", embedding=unit_vector(0)))
        await graph.merge_entity_node(entity_node("far", embedding=unit_vector(5)))
        index = GraphVectorIndex(graph)

        close_only = await index.nearest(unit_vector(0), top_k=5, threshold=0.9)
        assert [hit.id for hit in close_only] == ["same"]
        assert len(await index.nearest(unit_vector(0), top_k=1, threshold=0.0)) == 1
