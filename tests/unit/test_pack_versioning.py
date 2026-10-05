"""Pack versioning: change classification, reconcile, blue/green rebuild (ADR-0018 phase 3)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.adapters.memory.log import MemoryEventLog
from context_graph.domain.models import Event
from context_graph.domain.ontology import OntologyRegistry, Pack
from context_graph.domain.pack_projection import PackProjector
from context_graph.domain.pack_versioning import classify_change
from context_graph.ontology import BUILTIN_PACK_DIR, load_pack_file, load_registry, parse_pack
from context_graph.ontology.evaluation import f1_score
from context_graph.ontology.rebuild import RebuildRefusedError, rebuild
from context_graph.ontology.versioning import (
    STATE_REF,
    OntologyChangeRefusedError,
    read_state,
    reconcile,
    record_state,
)
from context_graph.ports.pack_graph import NodeRef, NodeWrite
from context_graph.settings import Settings

if TYPE_CHECKING:
    from pathlib import Path

CORE = load_pack_file(BUILTIN_PACK_DIR / "core.pack.yaml")

DEMO = """
pack: {name: demo, version: 1.0.0, requires: [core>=1.0]}
types:
  nodes:
    Ticket:
      key: [tracker, number]
      properties: {tracker: string, number: int, title: string}
      lifecycle: {initial: open, states: [open, closed]}
    Fix:
      key: [sha]
      properties: {sha: string}
  edges:
    RESOLVES: {from: [Fix], to: [Ticket]}
events:
  demo.ticket.opened: {}
  demo.ticket.closed: {}
projection:
  - event: demo.ticket.opened
    upsert:
      - {type: Ticket, key: {tracker: $.tracker, number: $.number}, set: {title: $.title}}
  - event: demo.ticket.closed
    transition: {type: Ticket, to: closed, key: {tracker: $.tracker, number: $.number}}
"""


def _registry(**replacements: str) -> OntologyRegistry:
    text = DEMO
    for old, new in replacements.items():
        assert old in text, old
        text = text.replace(old, new)
    return OntologyRegistry([CORE, parse_pack(text)])


BASE = _registry()


class TestClassify:
    def test_same_and_initial(self) -> None:
        assert classify_change(BASE, _registry()).kind == "none"
        assert classify_change(None, BASE).kind == "initial"

    def test_additive(self) -> None:
        new = _registry(
            **{
                "version: 1.0.0": "version: 1.1.0",
                "sha: string}": "sha: string, author: string}",
                "RESOLVES: {from: [Fix], to: [Ticket]}": (
                    "RESOLVES: {from: [Fix], to: [Ticket]}\n"
                    "    BLOCKS: {from: [Ticket], to: [Ticket]}"
                ),
                "states: [open, closed]": "states: [open, closed, archived]",
            }
        )
        plan = classify_change(BASE, new)
        assert plan.kind == "additive"
        assert plan.version_problems == []
        assert "edge type BLOCKS added" in plan.reasons
        assert "node type Fix: property author added" in plan.reasons
        assert "node type Ticket: state archived added" in plan.reasons

    def test_mapping_names_the_event_types_to_replay(self) -> None:
        new = _registry(
            **{
                "version: 1.0.0": "version: 1.1.0",
                "set: {title: $.title}": "set: {title: $.summary}",
            }
        )
        plan = classify_change(BASE, new)
        assert plan.kind == "mapping"
        assert plan.replay_event_types == {"demo.ticket.opened"}

    @pytest.mark.parametrize(
        ("replacements", "reason"),
        [
            (
                {"key: [sha]": "key: [sha, repo]", "{sha: string}": "{sha: string, repo: string}"},
                "node type Fix: key changed",
            ),
            ({"number: int": "number: string"}, "node type Ticket: property number changed type"),
            (
                {"states: [open, closed]": "states: [open, done]", "to: closed": "to: done"},
                "node type Ticket: state closed removed",
            ),
            ({"initial: open": "initial: closed"}, "node type Ticket: initial state changed"),
            (
                {
                    "RESOLVES: {from: [Fix], to: [Ticket]}": (
                        "RESOLVES: {from: [Ticket], to: [Ticket]}"
                    )
                },
                "edge type RESOLVES: endpoints removed",
            ),
        ],
    )
    def test_breaking(self, replacements: dict[str, str], reason: str) -> None:
        plan = classify_change(
            BASE, _registry(**{"version: 1.0.0": "version: 2.0.0", **replacements})
        )
        assert plan.kind == "breaking"
        assert any(r.startswith(reason) for r in plan.reasons), plan.reasons
        assert plan.version_problems == []

    def test_removing_a_pack_or_type_is_breaking(self) -> None:
        assert classify_change(BASE, OntologyRegistry([CORE])).kind == "breaking"

    def test_version_must_follow_the_change(self) -> None:
        unchanged_version = classify_change(BASE, _registry(**{"title: string}": "title: text}"}))
        assert unchanged_version.kind == "breaking"
        assert "is not higher than 1.0.0" in unchanged_version.version_problems[0]
        minor_for_breaking = classify_change(
            BASE, _registry(**{"version: 1.0.0": "version: 1.1.0", "number: int": "number: string"})
        )
        assert "needs a major version" in minor_for_breaking.version_problems[0]
        patch_for_additive = classify_change(
            BASE,
            _registry(
                **{"version: 1.0.0": "version: 1.0.1", "sha: string}": "sha: string, x: string}"}
            ),
        )
        assert "needs a minor version" in patch_for_additive.version_problems[0]

    def test_retrieval_changes_require_the_eval_set(self) -> None:
        new = _registry(
            **{
                "version: 1.0.0": "version: 1.1.0",
                "projection:": (
                    "retrieval:\n  intents:\n"
                    "    fixes: {keywords: [fix], weights: {RESOLVES: 2}}\nprojection:"
                ),
            }
        )
        plan = classify_change(BASE, new)
        assert plan.eval_required == {"demo"}

    def test_adding_pdlc_to_a_live_graph_replays_its_events(self) -> None:
        """Before PDLC was active its namespace was open, so the ledger may hold its events."""
        pdlc = load_registry(["pdlc"])
        plan = classify_change(load_registry([]), pdlc)
        assert plan.kind == "mapping"
        assert plan.replay_event_types == set(pdlc.projection_rules)
        assert plan.eval_required == {"pdlc"}


# ---------------------------------------------------------------------------
# Recorded state and reconcile
# ---------------------------------------------------------------------------


def _event(event_type: str, payload: dict[str, Any], minute: int) -> tuple[Event, dict[str, Any]]:
    return (
        Event(
            event_id=uuid4(),
            event_type=event_type,
            occurred_at=datetime(2026, 10, 4, tzinfo=UTC) + timedelta(minutes=minute),
            session_id="s",
            agent_id="webhook:demo",
            trace_id="t",
            payload_ref="p",
        ),
        payload,
    )


async def _ledger() -> MemoryEventLog:
    log = MemoryEventLog()
    for minute, (event, payload) in enumerate(
        [
            _event(
                "demo.ticket.opened",
                {"tracker": "t", "number": 1, "title": "A", "summary": "SA"},
                1,
            ),
            _event(
                "demo.ticket.opened",
                {"tracker": "t", "number": 2, "title": "B", "summary": "SB"},
                2,
            ),
            _event("demo.ticket.closed", {"tracker": "t", "number": 1}, 3),
        ]
    ):
        assert minute >= 0
        await log.append(event, payload)
    return log


async def _project_all(
    log: MemoryEventLog, graph: MemoryGraphStore, registry: OntologyRegistry
) -> None:
    from context_graph.ontology.versioning import replay_event_types

    await replay_event_types(
        log,
        graph,
        PackProjector(registry, frozenset()),
        set(registry.event_types),
        batch_size=2,
        lookup_limit=100,
    )


TICKET = NodeRef("Ticket", "Ticket:t|1")


class TestReconcile:
    async def test_state_round_trip(self) -> None:
        graph = MemoryGraphStore()
        assert await read_state(graph) is None
        await record_state(graph, BASE, applied="initial")
        state = await read_state(graph)
        assert state is not None
        assert state.version == BASE.version
        assert state.registry().version == BASE.version
        assert state.properties["packs"] == ["core@" + CORE.version, "demo@1.0.0"]

    async def test_initial_none_mapping_breaking(self) -> None:
        log, graph = await _ledger(), MemoryGraphStore()
        await _project_all(log, graph, BASE)
        options = {"allow_breaking": False, "batch_size": 2, "lookup_limit": 100}

        first = await reconcile(graph, log, PackProjector(BASE, frozenset()), **options)
        assert first.kind == "initial"
        again = await reconcile(graph, log, PackProjector(BASE, frozenset()), **options)
        assert again.kind == "none"

        mapped = _registry(
            **{
                "version: 1.0.0": "version: 1.1.0",
                "set: {title: $.title}": "set: {title: $.summary}",
            }
        )
        plan = await reconcile(graph, log, PackProjector(mapped, frozenset()), **options)
        assert plan.kind == "mapping"
        node = (await graph.get_nodes([TICKET]))[TICKET]
        assert node["title"] == "SA"  # replayed under the new rule
        assert node["status"] == "closed"  # the transition was not undone
        state = await read_state(graph)
        assert state is not None and state.version == mapped.version
        assert state.properties["replayed_events"] == 3  # every pack event, in log order

        broken = _registry(**{"version: 1.0.0": "version: 2.0.0", "number: int": "number: string"})
        with pytest.raises(OntologyChangeRefusedError, match="number changed type"):
            await reconcile(graph, log, PackProjector(broken, frozenset()), **options)
        allowed = await reconcile(
            graph, log, PackProjector(broken, frozenset()), **(options | {"allow_breaking": True})
        )
        assert allowed.kind == "breaking"
        assert (await read_state(graph)).version == broken.version  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Rebuild and gate
# ---------------------------------------------------------------------------

DEMO_INTENTS = {
    "projection:": (
        "retrieval:\n  seed_types: [Ticket]\n  intents:\n"
        "    fixes: {keywords: [fix, fixes], weights: {RESOLVES: 2}}\nprojection:"
    )
}


def _eval_set(directory: Path, expected: list[str], min_f1: float = 0.8) -> None:
    (directory / "demo.eval.yaml").write_text(
        "pack: demo\n"
        f"min_f1: {min_f1}\n"
        "questions:\n"
        "  - id: ticket\n"
        "    query: What fixes ticket t?\n"
        f"    expected: {expected}\n"
        "    answer: {node_type: Ticket}\n"
        "    seed_node_ids: ['Ticket:t|1']\n"
    )


def _settings() -> Settings:
    return Settings()


class TestRebuild:
    async def test_build_gate_and_record(self, tmp_path: Path) -> None:
        registry = _registry(**DEMO_INTENTS)
        log, target = await _ledger(), MemoryGraphStore()
        _eval_set(tmp_path, ["Ticket:t|1"])
        report = await rebuild(
            log, target, PackProjector(registry, frozenset()), _settings(), eval_dirs=[tmp_path]
        )
        assert report.passed, report.as_dict()
        assert report.events == 3
        assert report.gate[0].mean_f1 == 1.0
        assert (await target.get_nodes([TICKET]))[TICKET]["status"] == "closed"
        state = await read_state(target)
        assert state is not None
        assert state.properties["applied"] == "rebuild"
        assert state.properties["gate_passed"] is True

    async def test_failing_or_missing_gate(self, tmp_path: Path) -> None:
        registry = _registry(**DEMO_INTENTS)
        log = await _ledger()
        with pytest.raises(RebuildRefusedError, match="no evaluation set demo.eval.yaml"):
            await rebuild(
                log,
                MemoryGraphStore(),
                PackProjector(registry, frozenset()),
                _settings(),
                eval_dirs=[],
            )
        _eval_set(tmp_path, ["Ticket:t|2"])
        failing = await rebuild(
            log,
            MemoryGraphStore(),
            PackProjector(registry, frozenset()),
            _settings(),
            eval_dirs=[tmp_path],
        )
        assert not failing.passed
        skipped = await rebuild(
            log,
            MemoryGraphStore(),
            PackProjector(registry, frozenset()),
            _settings(),
            eval_dirs=[],
            skip_gate=True,
        )
        assert skipped.passed and skipped.gate_skipped

    async def test_target_holding_another_version_is_refused(self) -> None:
        target = MemoryGraphStore()
        await record_state(target, BASE, applied="initial")
        registry = _registry(
            **{"version: 1.0.0": "version: 2.0.0", "number: int": "number: string"}
        )
        with pytest.raises(RebuildRefusedError):
            await rebuild(
                await _ledger(),
                target,
                PackProjector(registry, frozenset()),
                _settings(),
                eval_dirs=[],
                skip_gate=True,
            )

    def test_f1(self) -> None:
        assert f1_score(set(), set()) == 1.0
        assert f1_score({"a"}, set()) == 0.0
        assert f1_score({"a", "b"}, {"a"}) == pytest.approx(2 / 3)


def test_pack_model_round_trip_through_canonical_json() -> None:
    import json

    for pack in load_registry(["pdlc"]).packs:
        assert Pack.model_validate(json.loads(pack.canonical_json())).canonical_json() == (
            pack.canonical_json()
        )


# ---------------------------------------------------------------------------
# Phase 3 review regressions (ADR-0018 implementation notes)
# ---------------------------------------------------------------------------

OPENED_UPSERT = (
    "      - {type: Ticket, key: {tracker: $.tracker, number: $.number}, set: {title: $.title}}\n"
)
TRANSITION = {OPENED_UPSERT: OPENED_UPSERT + "    transition: {type: Ticket, to: open}\n"}
OPTIONS: dict[str, Any] = {"allow_breaking": False, "batch_size": 2, "lookup_limit": 100}


class TestReviewFindings:
    async def test_a_mapping_replay_keeps_later_states(self) -> None:
        base = _registry(**TRANSITION)
        log, graph = await _ledger(), MemoryGraphStore()
        await _project_all(log, graph, base)
        await reconcile(graph, log, PackProjector(base, frozenset()), **OPTIONS)
        assert (await graph.get_nodes([TICKET]))[TICKET]["status"] == "closed"
        mapped = _registry(
            **TRANSITION,
            **{
                "version: 1.0.0": "version: 1.1.0",
                "set: {title: $.title}}\n    transition": (
                    "set: {title: $.summary}}\n    transition"
                ),
            },
        )
        plan = await reconcile(graph, log, PackProjector(mapped, frozenset()), **OPTIONS)
        assert plan.kind == "mapping"
        node = (await graph.get_nodes([TICKET]))[TICKET]
        assert node["title"] == "SA"
        assert node["status"] == "closed"  # opened replayed, then closed replayed after it

    async def test_an_unparsable_state_is_breaking_not_a_crash(self) -> None:
        log, graph = await _ledger(), MemoryGraphStore()
        await record_state(graph, BASE, applied="initial")
        await graph.upsert_nodes([NodeWrite(STATE_REF, {"packs_json": "{not json"})])
        with pytest.raises(OntologyChangeRefusedError, match="no longer loads"):
            await reconcile(graph, log, PackProjector(BASE, frozenset()), **OPTIONS)
        plan = await reconcile(
            graph, log, PackProjector(BASE, frozenset()), **(OPTIONS | {"allow_breaking": True})
        )
        assert plan.kind == "breaking"
        assert (await read_state(graph)).packs is not None  # type: ignore[union-attr]

    async def test_allowed_breaking_change_still_replays_changed_rules(self) -> None:
        log, graph = await _ledger(), MemoryGraphStore()
        await _project_all(log, graph, BASE)
        await reconcile(graph, log, PackProjector(BASE, frozenset()), **OPTIONS)
        new = _registry(
            **{
                "version: 1.0.0": "version: 2.0.0",
                "sha: string}": "sha: text}",
                "set: {title: $.title}": "set: {title: $.summary}",
            }
        )
        plan = await reconcile(
            graph, log, PackProjector(new, frozenset()), **(OPTIONS | {"allow_breaking": True})
        )
        assert plan.kind == "breaking"
        assert (await graph.get_nodes([TICKET]))[TICKET]["title"] == "SA"

    async def test_version_problems_refuse_unless_allowed(self) -> None:
        log, graph = await _ledger(), MemoryGraphStore()
        await reconcile(graph, log, PackProjector(BASE, frozenset()), **OPTIONS)
        unbumped = _registry(**{"sha: string}": "sha: string, x: string}"})
        with pytest.raises(OntologyChangeRefusedError, match="pack versions"):
            await reconcile(graph, log, PackProjector(unbumped, frozenset()), **OPTIONS)
        plan = await reconcile(
            graph,
            log,
            PackProjector(unbumped, frozenset()),
            **(OPTIONS | {"allow_version_problems": True}),
        )
        assert plan.kind == "additive"

    async def test_a_graph_whose_gate_failed_is_refused(self, tmp_path: Path) -> None:
        registry = _registry(**DEMO_INTENTS)
        log, target = await _ledger(), MemoryGraphStore()
        _eval_set(tmp_path, ["Ticket:t|2"])
        report = await rebuild(
            log, target, PackProjector(registry, frozenset()), _settings(), eval_dirs=[tmp_path]
        )
        assert not report.passed
        with pytest.raises(OntologyChangeRefusedError, match="evaluation gate failed"):
            await reconcile(target, log, PackProjector(registry, frozenset()), **OPTIONS)

    async def test_eval_required_is_recorded_as_pending(self) -> None:
        log, graph = await _ledger(), MemoryGraphStore()
        await reconcile(graph, log, PackProjector(BASE, frozenset()), **OPTIONS)
        with_intents = _registry(**{"version: 1.0.0": "version: 1.1.0", **DEMO_INTENTS})
        await reconcile(graph, log, PackProjector(with_intents, frozenset()), **OPTIONS)
        assert (await read_state(graph)).properties["eval_pending"] == ["demo"]  # type: ignore[union-attr]

    @pytest.mark.parametrize(
        ("replacements", "kind"),
        [
            # A changed key expression would leave the old nodes behind
            ({"number: $.number}, set": "number: $.title}, set"}, "breaking"),
            # Widening an enum or endpoints to a pack wildcard is additive
            (
                {
                    "title: string}": "title: string, prio: {enum: [low, high, urgent]}}",
                },
                "additive",
            ),
            (
                {"RESOLVES: {from: [Fix], to: [Ticket]}": "RESOLVES: {from: [Fix], to: '*'}"},
                "additive",
            ),
        ],
    )
    def test_classification_of_rule_keys_enums_and_wildcards(
        self, replacements: dict[str, str], kind: str
    ) -> None:
        plan = classify_change(
            BASE, _registry(**{"version: 1.0.0": "version: 2.0.0", **replacements})
        )
        assert plan.kind == kind, plan.reasons

    def test_an_enum_widening_is_additive(self) -> None:
        narrow = _registry(**{"title: string}": "title: string, prio: {enum: [low, high]}}"})
        wide = _registry(
            **{
                "version: 1.0.0": "version: 1.1.0",
                "title: string}": "title: string, prio: {enum: [low, high, urgent]}}",
            }
        )
        assert classify_change(narrow, wide).kind == "additive"
        assert classify_change(wide, narrow).kind == "breaking"

    def test_before_1_0_a_patch_is_enough_for_additive(self) -> None:
        old = _registry(**{"version: 1.0.0": "version: 0.1.0"})
        new = _registry(
            **{"version: 1.0.0": "version: 0.1.1", "sha: string}": "sha: string, x: string}"}
        )
        assert classify_change(old, new).version_problems == []

    async def test_a_target_with_data_but_no_state_is_refused(self) -> None:
        log, target = await _ledger(), MemoryGraphStore()
        await _project_all(log, target, BASE)
        live = await _ledger()
        replay_graph = MemoryGraphStore()
        from context_graph.ontology.rebuild import project_ledger

        await project_ledger(
            live, replay_graph, PackProjector(BASE, frozenset()), _settings(), batch_size=10
        )
        with pytest.raises(RebuildRefusedError, match="not empty"):
            await rebuild(
                live,
                replay_graph,
                PackProjector(BASE, frozenset()),
                _settings(),
                eval_dirs=[],
                skip_gate=True,
            )

    async def test_a_failing_event_is_isolated_and_reported(self) -> None:
        log, target = await _ledger(), MemoryGraphStore()
        (_first, second, _third) = await log.read_after(None, 10)
        original = target.merge_event_nodes_batch

        async def failing(nodes: list[Any]) -> Any:
            if any(str(n.event_id) == second.event_id for n in nodes):
                raise RuntimeError("write failed")
            return await original(nodes)

        target.merge_event_nodes_batch = failing  # type: ignore[method-assign]
        report = await rebuild(
            log, target, PackProjector(BASE, frozenset()), _settings(), eval_dirs=[], skip_gate=True
        )
        assert report.dead_lettered == [second.position]
        assert not report.passed
        assert (await target.get_nodes([TICKET]))[TICKET]["status"] == "closed"


class TestEvalSetFiles:
    def test_the_fixture_set_loads(self) -> None:
        from pathlib import Path

        from context_graph.ontology.evaluation import load_eval_set

        path = Path(__file__).resolve().parents[1] / "fixtures" / "ontology" / "pdlc.eval.yaml"
        eval_set = load_eval_set(path)
        assert eval_set.pack == "pdlc"
        assert len(eval_set.questions) == 11
        assert {q.id for q in eval_set.questions} >= {"deployed-where", "before-editing-pr"}
        assert all("#" in q.query for q in eval_set.questions if "pr" in q.id.split("-"))

    def test_an_unquoted_hash_is_refused(self, tmp_path: Path) -> None:
        from context_graph.domain.ontology import OntologyError
        from context_graph.ontology.evaluation import load_eval_set

        body = "pack: demo\nquestions:\n  - id: q\n    query: {query}\n    expected: []\n"
        unquoted = tmp_path / "unquoted.eval.yaml"
        unquoted.write_text(body.format(query="What does PR #7 do?"))
        with pytest.raises(OntologyError, match="unquoted.eval.yaml:4: quote this query"):
            load_eval_set(unquoted)
        quoted = tmp_path / "quoted.eval.yaml"
        quoted.write_text(body.format(query='"What does PR #7 do?"'))
        assert load_eval_set(quoted).questions[0].query == "What does PR #7 do?"
