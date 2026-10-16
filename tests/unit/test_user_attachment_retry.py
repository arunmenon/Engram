"""User extraction through worker and public storage/read seams.

Reference storage tests supplement, never replace, real-Spanner acceptance.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.adapters.memory.log import MemoryEventLog
from context_graph.adapters.memory.subscription import MemorySubscription
from context_graph.domain.models import Event
from context_graph.domain.projection import event_to_node
from context_graph.ports.pack_graph import NodeRef
from context_graph.settings import OntologySettings, Settings
from context_graph.worker.extraction import ExtractionConsumer


async def test_session_extraction_attaches_interest_to_its_real_source_events():
    graph, ledger = MemoryGraphStore(), MemoryEventLog()
    sources = []
    for number, kind, payload in [
        (1, "observation.input", {"content": "I am interested in Rust language development."}),
        (2, "system.session_end", {}),
    ]:
        event = Event(
            event_id=UUID(int=number),
            event_type=kind,
            occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
            session_id="interest-session",
            agent_id="alice",
            trace_id="t",
            payload_ref="user:test",
        )
        position = await ledger.append(event, payload)
        await graph.merge_event_node(
            event_to_node(event.model_copy(update={"global_position": position}))
        )
        sources.append((event, position))
    provider = AsyncMock()
    provider.extract_from_session.return_value = {
        "entities": [],
        "persona": None,
        "preferences": [],
        "skills": [],
        "interests": [
            {
                "entity_name": "Rust",
                "entity_type": "tool",
                "weight": 0.8,
                "source": "explicit",
                "source_quote": "interested in Rust language development",
            }
        ],
    }
    subscription = MemorySubscription(ledger.stream, "extraction", "user-test")
    await subscription.ensure_group()
    settings = Settings(ontology=OntologySettings(builtin_packs=["user"]))
    worker = ExtractionConsumer(
        subscription, ledger, provider, settings, graph_store=graph, user_store=graph
    )
    await worker.process_message(sources[-1][1], {"event_id": str(sources[-1][0].event_id)})
    interests = await graph.get_user_interests("user:alice")
    assert len(interests) == 1 and interests[0]["entity_id"] == "entity:Rust"
    links = await graph.neighbors(
        [NodeRef("Entity", "entity:Rust", "entity_id")], ["DERIVED_FROM"], "out", 10
    )
    assert {link["target_key"] for link in links} == {str(sources[0][0].event_id)}
    assert all(link["properties"]["method"] == "llm_extraction" for link in links)


async def test_new_profile_is_same_node_through_specialized_and_composed_reads():
    from context_graph.adapters.composed_reads import ComposedReadView, ReadScope
    from context_graph.domain.pack_bundle import resolve_bundle
    from context_graph.ontology.loader import load_registry

    graph = MemoryGraphStore()
    await graph.write_user_profile(
        {"user_id": "user:alice", "display_name": "Alice", "communication_style": "concise"}
    )
    selected = ComposedReadView(
        graph, ReadScope.from_bundle(resolve_bundle(load_registry([], builtin_packs=["user"])))
    )
    specialized = await graph.get_user_profile("user:alice")
    composed = await selected.get_user_profile("user:alice")
    assert specialized is not None and composed == specialized
    assert composed["profile_id"] == "profile:user:alice"
    ref = NodeRef("UserProfile", "profile:user:alice", "profile_id")
    assert (await graph.get_nodes([ref]))[ref] == composed


async def test_first_prepared_extraction_wins_even_if_retry_model_result_changes():
    from context_graph.domain.user_extraction import prepare_extraction_receipt

    graph = MemoryGraphStore()
    source = Event(
        event_id=UUID(int=11),
        event_type="observation.input",
        occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
        session_id="snapshot",
        agent_id="alice",
        trace_id="t",
        payload_ref="user:snapshot",
        global_position="1000-11",
    )
    trigger = source.model_copy(
        update={
            "event_id": UUID(int=12),
            "event_type": "system.session_end",
            "global_position": "1000-12",
        }
    )
    for event in (source, trigger):
        await graph.merge_event_node(event_to_node(event))
    docs = [
        {
            **source.model_dump(mode="json"),
            "payload": {"content": "I prefer short answers and dislike long answers."},
        },
        {**trigger.model_dump(mode="json"), "payload": {}},
    ]
    result = {
        "entities": [],
        "preferences": [
            dict(
                category="communication",
                key="answer-length",
                polarity="positive",
                strength=0.8,
                confidence=0.9,
                source="explicit",
                context="support",
                source_quote="I prefer short answers",
            )
        ],
        "skills": [],
        "interests": [],
        "persona": None,
    }
    first = prepare_extraction_receipt(trigger, [source, trigger], docs, result)
    stored = await graph.prepare_user_extraction(trigger, first)
    changed = {
        **result,
        "preferences": [
            {
                **result["preferences"][0],
                "polarity": "negative",
                "source_quote": "dislike long answers",
            }
        ],
    }
    second = prepare_extraction_receipt(trigger, [source, trigger], docs, changed)
    assert await graph.prepare_user_extraction(trigger, second) == stored
    assert (await graph.get_user_extraction(trigger))["result"]["preferences"][0][
        "polarity"
    ] == "positive"
    assert not await graph.get_user_preferences("user:alice")


async def test_applying_prepared_user_output_twice_keeps_one_preference_and_one_support():
    from context_graph.domain.user_extraction import prepare_extraction_receipt

    graph = MemoryGraphStore()
    source = Event(
        event_id=UUID(int=21),
        event_type="observation.input",
        occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
        session_id="apply",
        agent_id="alice",
        trace_id="t",
        payload_ref="user:apply",
        global_position="1000-21",
    )
    trigger = source.model_copy(
        update={
            "event_id": UUID(int=22),
            "event_type": "system.session_end",
            "global_position": "1000-22",
        }
    )
    for event in (source, trigger):
        await graph.merge_event_node(event_to_node(event))
    docs = [
        {**source.model_dump(mode="json"), "payload": {"content": "I prefer short answers."}},
        {**trigger.model_dump(mode="json"), "payload": {}},
    ]
    result = {
        "preferences": [
            dict(
                category="communication",
                key="answer-length",
                polarity="positive",
                strength=0.8,
                confidence=0.9,
                source="explicit",
                context="support",
                source_quote="I prefer short answers",
            )
        ]
    }
    prepared = prepare_extraction_receipt(trigger, [source, trigger], docs, result)
    await graph.prepare_user_extraction(trigger, prepared)
    assert await graph.apply_user_extraction(trigger) == "applied"
    assert await graph.apply_user_extraction(trigger) == "duplicate"
    preferences = await graph.get_user_preferences("user:alice")
    assert len(preferences) == 1 and preferences[0]["observation_count"] == 1
    assert preferences[0]["support_event_ids"] == [str(source.event_id)]
    links = await graph.neighbors(
        [NodeRef("Preference", preferences[0]["preference_id"], "preference_id")],
        ["DERIVED_FROM"],
        "out",
        10,
    )
    assert {link["target_key"] for link in links} == {str(source.event_id)}
    assert (await graph.get_user_extraction(trigger))["status"] == "applied"


async def test_worker_restart_reuses_applied_result_without_another_model_call():
    graph, ledger = MemoryGraphStore(), MemoryEventLog()
    events = []
    for number, kind, payload in [
        (31, "observation.input", {"content": "I prefer short answers."}),
        (32, "system.session_end", {}),
    ]:
        event = Event(
            event_id=UUID(int=number),
            event_type=kind,
            occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
            session_id="restart",
            agent_id="alice",
            trace_id="t",
            payload_ref="user:restart",
        )
        position = await ledger.append(event, payload)
        await graph.merge_event_node(
            event_to_node(event.model_copy(update={"global_position": position}))
        )
        events.append((event, position))
    provider = AsyncMock()
    provider.extract_from_session.return_value = {
        "preferences": [
            dict(
                category="communication",
                key="answer-length",
                polarity="positive",
                strength=0.8,
                confidence=0.9,
                source="explicit",
                source_quote="I prefer short answers",
            )
        ]
    }
    settings = Settings(ontology=OntologySettings(packs=[], builtin_packs=["user"]))
    for _ in range(2):
        worker = ExtractionConsumer(
            MemorySubscription(ledger.stream, "extraction", "user-test"),
            ledger,
            provider,
            settings,
            graph_store=graph,
            user_store=graph,
        )
        await worker.process_message(events[-1][1], {"event_id": str(events[-1][0].event_id)})
    provider.extract_from_session.assert_awaited_once()
    preferences = await graph.get_user_preferences("user:alice")
    assert len(preferences) == 1 and preferences[0]["observation_count"] == 1


async def test_prepared_receipt_is_private_exported_and_removable_before_user_outputs():
    from context_graph.domain.models import NodeScores
    from context_graph.domain.user_extraction import prepare_extraction_receipt
    from context_graph.retrieval.atlas import build_atlas_node

    graph = MemoryGraphStore()
    event = Event(
        event_id=UUID(int=41),
        event_type="system.session_end",
        occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
        session_id="privacy",
        agent_id="alice",
        trace_id="t",
        payload_ref="user:privacy",
        global_position="1000-41",
    )
    await graph.merge_event_node(event_to_node(event))
    receipt = prepare_extraction_receipt(
        event, [event], [{**event.model_dump(mode="json"), "payload": {}}], {}
    )
    await graph.prepare_user_extraction(event, receipt)
    props = (await graph.get_nodes([NodeRef("Event", str(event.event_id), "event_id")]))[
        NodeRef("Event", str(event.event_id), "event_id")
    ]
    assert "user_extraction_receipt" not in build_atlas_node(props, NodeScores()).attributes
    exported = await graph.export_user_data("user:alice")
    assert exported["extraction_receipts"][0]["trigger_event_id"] == str(event.event_id)
    await graph.delete_user_data("user:alice")
    props = (await graph.get_nodes([NodeRef("Event", str(event.event_id), "event_id")]))[
        NodeRef("Event", str(event.event_id), "event_id")
    ]
    assert "user_extraction_receipt" not in props


async def test_declared_correction_preserves_history_and_unrelated_context():
    from context_graph.domain.user_extraction import prepare_extraction_receipt

    graph = MemoryGraphStore()

    async def apply(number, content, context, polarity, extra=None):
        source = Event(
            event_id=UUID(int=number),
            event_type="observation.input",
            occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
            session_id="correction",
            agent_id="alice",
            trace_id="t",
            payload_ref="user:correction",
            global_position=f"1000-{number}",
        )
        trigger = source.model_copy(
            update={
                "event_id": UUID(int=number + 1),
                "event_type": "system.session_end",
                "global_position": f"1000-{number + 1}",
            }
        )
        for event in (source, trigger):
            await graph.merge_event_node(event_to_node(event))
        docs = [
            {**source.model_dump(mode="json"), "payload": {"content": content, **(extra or {})}},
            {**trigger.model_dump(mode="json"), "payload": {}},
        ]
        result = {
            "preferences": [
                dict(
                    category="communication",
                    key="answer-length",
                    polarity=polarity,
                    strength=0.8,
                    confidence=0.9,
                    source="explicit",
                    context=context,
                    source_quote=content,
                )
            ]
        }
        prepared = prepare_extraction_receipt(trigger, [source, trigger], docs, result)
        await graph.prepare_user_extraction(trigger, prepared)
        await graph.apply_user_extraction(trigger)
        return prepared["result"]["preferences"][0]["preference_id"]

    old = await apply(51, "In support I prefer short answers.", "support", "positive")
    other = await apply(53, "In reviews I prefer short answers.", "reviews", "positive")
    new = await apply(
        55,
        "In support I no longer prefer short answers.",
        "support",
        "negative",
        {
            "preference_corrections": [
                dict(
                    previous_preference_id=old,
                    replacement_key="answer-length",
                    replacement_polarity="negative",
                    context="support",
                )
            ]
        },
    )
    assert {p["preference_id"] for p in await graph.get_user_preferences("user:alice")} == {
        new,
        other,
    }
    all_preferences = {
        p["preference_id"]: p
        for p in await graph.get_user_preferences("user:alice", active_only=False)
    }
    assert (
        all_preferences[old]["superseded_by"] == new
        and all_preferences[other].get("superseded_by") is None
    )
    links = await graph.neighbors(
        [NodeRef("Preference", new, "preference_id")], ["SUPERSEDES"], "out", 10
    )
    assert (
        len(links) == 1
        and links[0]["target_key"] == old
        and links[0]["properties"]["source_event_id"] == str(UUID(int=55))
    )


async def test_selected_user_provider_failure_is_not_an_empty_success(monkeypatch):
    import sys
    from types import SimpleNamespace

    from context_graph.adapters.llm.client import LLMExtractionClient

    monkeypatch.setitem(
        sys.modules,
        "litellm",
        SimpleNamespace(acompletion=AsyncMock(side_effect=RuntimeError("provider unavailable"))),
    )
    client = LLMExtractionClient(max_retries=0, require_success=True)
    event = Event(
        event_id=UUID(int=61),
        event_type="observation.input",
        occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
        session_id="failure",
        agent_id="alice",
        trace_id="t",
        payload_ref="user:failure",
    )
    with pytest.raises(RuntimeError, match="extraction"):
        await client.extract_from_session(
            [event],
            "failure",
            "alice",
            [{**event.model_dump(mode="json"), "payload": {"content": "I prefer short answers."}}],
        )


async def _prepared(graph, number, payload, result, *, prior=(), owner="alice"):
    from context_graph.domain.user_extraction import prepare_extraction_receipt

    source = Event(
        event_id=UUID(int=number),
        event_type="observation.input",
        occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
        session_id="bounded",
        agent_id=owner,
        trace_id="t",
        payload_ref="test:bounded",
        global_position=f"1000-{number}",
    )
    trigger = source.model_copy(
        update={
            "event_id": UUID(int=number + 1),
            "event_type": "system.session_end",
            "global_position": f"1000-{number + 1}",
        }
    )
    for event in (source, trigger):
        await graph.merge_event_node(event_to_node(event))
    pairs = [
        *prior,
        (source, {**source.model_dump(mode="json"), "payload": payload}),
        (trigger, {**trigger.model_dump(mode="json"), "payload": {}}),
    ]
    receipt = prepare_extraction_receipt(
        trigger, [p[0] for p in pairs], [p[1] for p in pairs], result
    )
    await graph.prepare_user_extraction(trigger, receipt)
    return trigger, receipt, pairs


def _preference(polarity="positive", *, about=None):
    return dict(
        category="communication",
        key="answer-length",
        polarity=polarity,
        strength=0.8,
        confidence=0.9,
        source="explicit",
        context="support",
        source_quote="short answers",
        about_entity=about,
    )


async def test_competing_corrections_rollback_all_user_outputs():
    from context_graph.domain.user_extraction import UserExtractionConflictError

    graph = MemoryGraphStore()
    trigger, receipt, _ = await _prepared(
        graph, 71, {"content": "short answers"}, {"preferences": [_preference()]}
    )
    await graph.apply_user_extraction(trigger)
    old = receipt["result"]["preferences"][0]["preference_id"]
    corrections = [
        dict(
            previous_preference_id=old,
            replacement_key="answer-length",
            replacement_polarity=p,
            context="support",
        )
        for p in ("negative", "neutral")
    ]
    trigger, _, _ = await _prepared(
        graph,
        73,
        {"content": "short answers", "preference_corrections": corrections},
        {"preferences": [_preference("negative"), _preference("neutral")]},
    )
    with pytest.raises(UserExtractionConflictError, match="successor"):
        await graph.apply_user_extraction(trigger)
    preferences = await graph.get_user_preferences("user:alice", active_only=False)
    assert len(preferences) == 1 and preferences[0].get("superseded_by") is None
    assert (await graph.get_user_extraction(trigger))["status"] == "prepared"


async def test_deleting_owned_skills_preserves_other_owner_and_legacy_shared_skill():
    graph = MemoryGraphStore()
    trigger, receipt, _ = await _prepared(
        graph,
        81,
        {"content": "I know Python"},
        {
            "skills": [
                dict(
                    category="programming_language",
                    name="Python",
                    proficiency=0.8,
                    confidence=0.9,
                    source="declared",
                    source_quote="I know Python",
                )
            ]
        },
    )
    await graph.apply_user_extraction(trigger)
    owned = NodeRef("Skill", receipt["result"]["skills"][0]["skill_id"], "skill_id")
    bob_trigger, _, _ = await _prepared(
        graph,
        83,
        {"content": "I know Python"},
        {
            "skills": [
                dict(
                    category="programming_language",
                    name="Python",
                    proficiency=0.8,
                    confidence=0.9,
                    source="declared",
                    source_quote="I know Python",
                )
            ]
        },
        owner="bob",
    )
    await graph.apply_user_extraction(bob_trigger)
    await graph.write_skill_with_edges(
        "user:carol", {"skill_id": "legacy-python", "name": "Python"}, [], {}
    )
    carol_skills = await graph.get_user_skills("user:carol")
    bob_skills = await graph.get_user_skills("user:bob")
    await graph.delete_user_data("user:alice")
    assert owned not in await graph.get_nodes([owned])
    assert await graph.get_user_skills("user:bob") == bob_skills
    assert await graph.get_user_skills("user:carol") == carol_skills


async def test_missing_accepted_trigger_document_is_retryable_not_success():
    from context_graph.ports.errors import UnavailableError

    graph, ledger = MemoryGraphStore(), MemoryEventLog()
    worker = ExtractionConsumer(
        MemorySubscription(ledger.stream, "extraction", "test"),
        ledger,
        AsyncMock(),
        Settings(ontology=OntologySettings(builtin_packs=["user"])),
        graph_store=graph,
        user_store=graph,
    )
    with pytest.raises(UnavailableError):
        await worker.process_message("1000-91", {"event_id": str(UUID(int=91))})


async def test_later_trigger_does_not_reinterpret_applied_historical_correction():
    graph, ledger = MemoryGraphStore(), MemoryEventLog()
    trigger, receipt, _ = await _prepared(
        graph, 101, {"content": "short answers"}, {"preferences": [_preference()]}
    )
    await graph.apply_user_extraction(trigger)
    old = receipt["result"]["preferences"][0]["preference_id"]
    provider = AsyncMock()
    provider.extract_from_session.side_effect = [
        {"preferences": [_preference("negative")]},
        {},
    ]
    settings = Settings(ontology=OntologySettings(builtin_packs=["user"]))
    worker = ExtractionConsumer(
        MemorySubscription(ledger.stream, "extraction", "test"),
        ledger,
        provider,
        settings,
        graph_store=graph,
        user_store=graph,
    )
    for number, kind, payload in [
        (
            103,
            "observation.input",
            {
                "content": "short answers",
                "preference_corrections": [
                    dict(
                        previous_preference_id=old,
                        replacement_key="answer-length",
                        replacement_polarity="negative",
                        context="support",
                    )
                ],
            },
        ),
        (104, "system.session_end", {}),
        (105, "observation.input", {"content": "No new preference today."}),
        (106, "system.session_end", {}),
    ]:
        event = trigger.model_copy(
            update={"event_id": UUID(int=number), "event_type": kind, "global_position": None}
        )
        position = await ledger.append(event, payload)
        await graph.merge_event_node(
            event_to_node(event.model_copy(update={"global_position": position}))
        )
        if kind == "system.session_end":
            await worker.process_message(position, {"event_id": str(event.event_id)})
    preferences = await graph.get_user_preferences("user:alice", active_only=False)
    assert len(preferences) == 2
    assert sum(p.get("superseded_by") is not None for p in preferences) == 1


async def test_mid_session_trigger_is_stable_after_restart_and_excludes_other_owner():
    graph, ledger = MemoryGraphStore(), MemoryEventLog()
    settings = Settings(ontology=OntologySettings(builtin_packs=["user"]))
    settings.consumer.extraction_mid_session_interval = 2
    provider = AsyncMock()
    provider.extract_from_session.return_value = {"preferences": [_preference()]}
    positions = []
    for number, owner, content in [
        (111, "alice", "short answers"),
        (112, "bob", "long answers"),
        (113, "alice", "Nothing new"),
    ]:
        event = Event(
            event_id=UUID(int=number),
            event_type="observation.input",
            occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
            session_id="shared",
            agent_id=owner,
            trace_id="t",
            payload_ref="test:mid",
        )
        position = await ledger.append(event, {"content": content})
        await graph.merge_event_node(
            event_to_node(event.model_copy(update={"global_position": position}))
        )
        positions.append((event, position))
    for _ in range(2):
        worker = ExtractionConsumer(
            MemorySubscription(ledger.stream, "extraction", "test"),
            ledger,
            provider,
            settings,
            graph_store=graph,
            user_store=graph,
        )
        await worker.process_message(positions[-1][1], {"event_id": str(positions[-1][0].event_id)})
    provider.extract_from_session.assert_awaited_once()
    inputs = provider.extract_from_session.call_args.kwargs["events"]
    assert [e.agent_id for e in inputs] == ["alice", "alice"]
    preferences = await graph.get_user_preferences("user:alice")
    assert preferences[0]["support_event_ids"] == [str(UUID(int=111))]
    assert not await graph.get_user_preferences("user:bob")


async def test_returned_prepared_result_cannot_mutate_durable_first_winner():
    graph = MemoryGraphStore()
    trigger, receipt, _ = await _prepared(
        graph, 121, {"content": "short answers"}, {"preferences": [_preference()]}
    )
    returned = await graph.prepare_user_extraction(trigger, receipt)
    returned["result"]["preferences"].clear()
    stored = await graph.get_user_extraction(trigger)
    assert len(stored["result"]["preferences"]) == 1


@pytest.mark.parametrize("failure", ["budget", "schedule"])
async def test_spanner_user_transaction_cannot_fallback_to_partial_commit(failure):
    from unittest.mock import MagicMock

    from context_graph.adapters.spanner.commits import CommitBudget, CommitTooLarge
    from context_graph.adapters.spanner.graph import SpannerGraphStore
    from context_graph.domain.user_extraction import event_ref, extraction_refs

    reference = MemoryGraphStore()
    trigger, receipt, _ = await _prepared(
        reference, 131, {"content": "short answers"}, {"preferences": [_preference()]}
    )
    stored = await reference.get_nodes(extraction_refs(receipt))
    trigger_row = ("Event", str(trigger.event_id), stored[event_ref(trigger)], None)
    rows = [(ref.label, ref.key, props, None) for ref, props in stored.items()]
    database, transaction = MagicMock(), MagicMock()
    transaction.read.side_effect = [[trigger_row], rows]
    scheduled, committed = [], []

    def schedule(table, columns, values):
        scheduled.append(table)
        if table == "GraphEdges":
            raise RuntimeError("Injected SDK scheduling failure")

    def boundary(callback):
        result = callback(transaction)
        committed.extend(scheduled)
        return result

    transaction.insert_or_update.side_effect = schedule
    database.run_in_transaction.side_effect = boundary
    graph = SpannerGraphStore(
        database, commit_budget=CommitBudget(max_mutations=1) if failure == "budget" else None
    )
    with pytest.raises(CommitTooLarge if failure == "budget" else RuntimeError):
        await graph.apply_user_extraction(trigger)
    assert not committed and database.run_in_transaction.call_count == 1
    assert scheduled == ([] if failure == "budget" else ["GraphNodes", "GraphEdges"])


async def test_cross_context_correction_rejects_without_half_written_replacement():
    from context_graph.domain.user_extraction import UserExtractionConflictError

    graph = MemoryGraphStore()
    trigger, receipt, _ = await _prepared(
        graph, 141, {"content": "short answers"}, {"preferences": [_preference()]}
    )
    await graph.apply_user_extraction(trigger)
    old = receipt["result"]["preferences"][0]["preference_id"]
    changed = {**_preference("negative"), "context": "reviews"}
    trigger, _, _ = await _prepared(
        graph,
        143,
        {
            "content": "short answers",
            "preference_corrections": [
                dict(
                    previous_preference_id=old,
                    replacement_key="answer-length",
                    replacement_polarity="negative",
                    context="reviews",
                )
            ],
        },
        {"preferences": [changed]},
    )
    with pytest.raises(UserExtractionConflictError, match="context"):
        await graph.apply_user_extraction(trigger)
    rows = await graph.get_user_preferences("user:alice", active_only=False)
    assert len(rows) == 1 and rows[0]["preference_id"] == old
    assert rows[0].get("superseded_by") is None


def _user_engine(graph, enabled=True):
    from context_graph.adapters.composed_reads import (
        ComposedGraphReads,
        ComposedReadView,
        ReadScope,
    )
    from context_graph.domain.pack_bundle import resolve_bundle
    from context_graph.domain.pack_intents import RegistryIntents
    from context_graph.ontology.loader import load_registry
    from context_graph.retrieval.engine import RetrievalEngine
    from context_graph.settings import DecaySettings

    bundle = resolve_bundle(load_registry([], builtin_packs=["user"] if enabled else []))
    selected = ComposedReadView(graph, ReadScope.from_bundle(bundle))
    return RetrievalEngine(
        ComposedGraphReads(selected),
        decay=DecaySettings(),
        bundle=bundle,
        intents=RegistryIntents.for_events(bundle.registry),
        pack_graph=selected,
    )


async def test_personalization_returns_owned_profile_preference_and_exact_evidence():
    from context_graph.domain.models import SubgraphQuery

    graph = MemoryGraphStore()
    trigger, receipt, _ = await _prepared(
        graph,
        151,
        {"content": "My name is Alice. I prefer short answers"},
        {
            "persona": {"name": "Alice", "source_quote": "My name is Alice"},
            "preferences": [_preference()],
        },
    )
    await graph.apply_user_extraction(trigger)
    other, _, _ = await _prepared(
        graph,
        153,
        {"content": "My name is Bob"},
        {"persona": {"name": "Bob", "source_quote": "My name is Bob"}},
        owner="bob",
    )
    await graph.apply_user_extraction(other)
    query = SubgraphQuery(
        query="How does Alice prefer answers?",
        session_id="bounded",
        agent_id="alice",
        intent="personalize",
    )
    answer = await _user_engine(graph).get_subgraph(query)
    pref = receipt["result"]["preferences"][0]["preference_id"]
    assert {"profile:user:alice", pref} <= answer.nodes.keys()
    assert "profile:user:bob" not in answer.nodes
    assert answer.nodes[pref].provenance.event_id == str(UUID(int=151))
    assert (pref, "DERIVED_FROM", str(UUID(int=151))) in {
        (e.source, e.edge_type, e.target) for e in answer.edges
    }
    disabled = await _user_engine(graph, False).get_subgraph(
        query.model_copy(update={"intent": "who_is"})
    )
    assert not any(
        n.node_type in {"UserProfile", "Preference", "Skill"} for n in disabled.nodes.values()
    )


@pytest.mark.parametrize("fault", ["missing-evidence", "foreign-source", "wrong-count"])
async def test_personalization_excludes_incomplete_or_foreign_user_evidence(fault):
    from context_graph.domain.models import SubgraphQuery
    from context_graph.ports.pack_graph import NodeWrite

    graph = MemoryGraphStore()
    trigger, receipt, _ = await _prepared(
        graph, 161, {"content": "short answers"}, {"preferences": [_preference()]}
    )
    await graph.apply_user_extraction(trigger)
    pref = receipt["result"]["preferences"][0]["preference_id"]
    source_id = str(UUID(int=161))
    # Reference-backend fault injection only, never an acceptance repair.
    if fault == "missing-evidence":
        graph.edges.pop((("Preference", pref), "DERIVED_FROM", ("Event", source_id)))
    else:
        ref = (
            NodeRef("Event", source_id, "event_id")
            if fault == "foreign-source"
            else NodeRef("Preference", pref, "preference_id")
        )
        await graph.upsert_nodes(
            [
                NodeWrite(
                    ref,
                    {"agent_id": "bob"}
                    if fault == "foreign-source"
                    else {"observation_count": 999},
                )
            ]
        )
    answer = await _user_engine(graph).get_subgraph(
        SubgraphQuery(
            query="My preferences", session_id="bounded", agent_id="alice", intent="personalize"
        )
    )
    assert pref not in answer.nodes and answer.meta.truncated


async def test_personalization_rejects_noncanonical_profile_even_with_valid_owned_evidence():
    from context_graph.domain.models import SubgraphQuery
    from context_graph.ports.pack_graph import EdgeWrite, NodeWrite

    graph = MemoryGraphStore()
    trigger, _, _ = await _prepared(
        graph,
        171,
        {"content": "My name is Alice"},
        {"persona": {"name": "Alice", "source_quote": "My name is Alice"}},
    )
    await graph.apply_user_extraction(trigger)
    # Deliberately inconsistent reference-backend data, not a cloud repair.
    wrong = NodeRef("UserProfile", "profile:wrong", "profile_id")
    source = NodeRef("Event", str(UUID(int=171)), "event_id")
    await graph.upsert_nodes(
        [
            NodeWrite(
                wrong,
                {
                    "user_id": "user:alice",
                    "display_name": "Wrong",
                    "support_event_ids": [source.key],
                },
            )
        ]
    )
    await graph.upsert_edges(
        [
            EdgeWrite("HAS_PROFILE", NodeRef("Entity", "user:alice", "entity_id"), wrong),
            EdgeWrite("DERIVED_FROM", wrong, source),
        ]
    )
    answer = await _user_engine(graph).get_subgraph(
        SubgraphQuery(
            query="Who is Alice?", session_id="bounded", agent_id="alice", intent="personalize"
        )
    )
    assert "profile:user:alice" in answer.nodes
    assert wrong.key not in answer.nodes and answer.meta.truncated


@pytest.mark.parametrize("seen", ["2026-10-13T12:00:00+00:00", "2026-10-12T23:00:00-04:00"])
async def test_user_worker_and_replay_preserve_existing_shared_entity_timestamps_and_counts(seen):
    graph, ledger = MemoryGraphStore(), MemoryEventLog()
    await graph.merge_entity_node_raw("entity:Rust", "Rust", "tool", seen, seen, 7)
    provider = AsyncMock()
    provider.extract_from_session.return_value = {
        "preferences": [{**_preference(), "about_entity": "Rust"}],
        "interests": [
            dict(
                entity_name="Rust",
                entity_type="concept",
                weight=0.8,
                source="explicit",
                source_quote="interested in Rust",
            )
        ],
    }
    settings = Settings(ontology=OntologySettings(builtin_packs=["user"]))
    for number, kind, payload in [
        (181, "observation.input", {"content": "short answers; interested in Rust"}),
        (182, "system.session_end", {}),
    ]:
        event = Event(
            event_id=UUID(int=number),
            event_type=kind,
            occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
            session_id="shared-entity",
            agent_id="alice",
            trace_id="t",
            payload_ref="test:shared-entity",
        )
        position = await ledger.append(event, payload)
        await graph.merge_event_node(
            event_to_node(event.model_copy(update={"global_position": position}))
        )
    for _ in range(2):
        worker = ExtractionConsumer(
            MemorySubscription(ledger.stream, "extraction", "test"),
            ledger,
            provider,
            settings,
            graph_store=graph,
            user_store=graph,
        )
        await worker.process_message(position, {"event_id": str(event.event_id)})
        ref = NodeRef("Entity", "entity:Rust", "entity_id")
        props = (await graph.get_nodes([ref]))[ref]
        assert props["first_seen"] == seen and props["last_seen"] == seen
        assert props["mention_count"] == 7 and props["entity_type"] == "tool"
    provider.extract_from_session.assert_awaited_once()


async def test_declared_correction_canonicalizes_descriptive_context_without_stale_identity():
    from context_graph.domain.user_extraction import artifact_identity

    graph = MemoryGraphStore()
    trigger, original, _ = await _prepared(
        graph, 151, {"content": "short answers"}, {"preferences": [_preference()]}
    )
    await graph.apply_user_extraction(trigger)
    previous = original["result"]["preferences"][0]["preference_id"]
    trigger, receipt, _ = await _prepared(
        graph,
        153,
        {
            "content": "I no longer prefer short answers in support.",
            "preference_corrections": [
                dict(
                    previous_preference_id=previous,
                    replacement_key="answer-length",
                    replacement_polarity="negative",
                    context="support",
                )
            ],
        },
        {
            "preferences": [
                {
                    **_preference("negative"),
                    "context": "No longer prefers brief responses during support.",
                    "source_quote": "I no longer prefer short answers in support",
                }
            ]
        },
    )
    replacement = receipt["result"]["preferences"][0]
    assert replacement["context"] == "support"
    expected = artifact_identity("Preference", "user:alice", replacement)
    assert receipt["corrections"][0]["replacement_id"] == expected == replacement["preference_id"]
    await graph.apply_user_extraction(trigger)
    active = await graph.get_user_preferences("user:alice")
    assert len(active) == 1 and active[0]["polarity"] == "negative"
    assert active[0]["preference_id"] == expected


@pytest.mark.parametrize("failure", ["ambiguous", "contexts", "predecessors", "context-type"])
async def test_correction_normalization_rejects_ambiguous_or_conflicting_metadata(failure):
    graph = MemoryGraphStore()
    metadata = dict(
        previous_preference_id="preference:old",
        replacement_key="answer-length",
        replacement_polarity="negative",
        context="support",
    )
    preferences = [{**_preference("negative"), "context": "Prefers longer support responses."}]
    declared = [metadata]
    if failure == "ambiguous":
        preferences.append({**preferences[0], "context": "Avoids brief support responses."})
    elif failure in ("contexts", "predecessors"):
        field = "context" if failure == "contexts" else "previous_preference_id"
        declared.append({**metadata, field: "different"})
    else:
        declared = [{**metadata, "context": ["invalid"]}]
    with pytest.raises(ValueError):
        await _prepared(
            graph,
            155,
            {"content": "short answers", "preference_corrections": declared},
            {"preferences": preferences},
        )


async def test_exact_context_selection_preserves_undeclared_preference_context():
    graph = MemoryGraphStore()
    trigger, receipt, _ = await _prepared(
        graph,
        157,
        {
            "content": "short answers",
            "preference_corrections": [
                dict(
                    previous_preference_id="preference:old",
                    replacement_key="answer-length",
                    replacement_polarity="negative",
                    context="support",
                )
            ],
        },
        {
            "preferences": [
                _preference("negative"),
                {**_preference("negative"), "context": "reviews"},
            ]
        },
    )
    assert [p["context"] for p in receipt["result"]["preferences"]] == ["support", "reviews"]
    assert (
        receipt["corrections"][0]["replacement_id"]
        == (receipt["result"]["preferences"][0]["preference_id"])
    )


async def test_canonical_correction_cannot_replace_another_owners_preference():
    from context_graph.domain.user_extraction import UserExtractionConflictError

    graph = MemoryGraphStore()
    trigger, original, _ = await _prepared(
        graph, 161, {"content": "short answers"}, {"preferences": [_preference()]}, owner="bob"
    )
    await graph.apply_user_extraction(trigger)
    previous = original["result"]["preferences"][0]["preference_id"]
    trigger, _, _ = await _prepared(
        graph,
        163,
        {
            "content": "short answers",
            "preference_corrections": [
                dict(
                    previous_preference_id=previous,
                    replacement_key="answer-length",
                    replacement_polarity="negative",
                    context="support",
                )
            ],
        },
        {"preferences": [{**_preference("negative"), "context": "avoid brief support answers"}]},
    )
    with pytest.raises(UserExtractionConflictError, match="owner or context"):
        await graph.apply_user_extraction(trigger)
    assert not await graph.get_user_preferences("user:alice", active_only=False)
    assert (await graph.get_user_preferences("user:bob"))[0]["preference_id"] == previous
