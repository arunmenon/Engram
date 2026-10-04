"""Pack parsing and registry validation (ADR-0018 phase 0)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from context_graph.domain.ontology import OntologyError, OntologyRegistry, Pack
from context_graph.ontology import BUILTIN_PACK_DIR, load_pack_file, load_registry, parse_pack

if TYPE_CHECKING:
    from pathlib import Path

CORE = load_pack_file(BUILTIN_PACK_DIR / "core.pack.yaml")

DEMO = """
pack: {name: demo, version: 1.2.0, requires: [core>=1.0]}
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
    RESOLVES: {from: [Fix], to: [Ticket], requires: [confidence]}
    MENTIONS: {from: ["core:Event"], to: [Ticket]}
events:
  demo.ticket.closed: {}
projection:
  - event: demo.ticket.closed
    upsert:
      - {type: Ticket, key: {tracker: $.tracker, number: $.number}, set: {title: $.title}}
    transition: {type: Ticket, to: closed, only_from: [open]}
    edges:
      - type: RESOLVES
        from: {type: Fix, key: {sha: $.sha}}
        to: {type: Ticket, key: {tracker: $.tracker, number: $.number}}
        set: {confidence: 1.0}
retrieval:
  intents:
    ticket_status:
      keywords: [ticket]
      weights: {RESOLVES: 3.0}
  core_intent_weights:
    why: {RESOLVES: 2.0}
"""


def _demo(**replacements: str) -> Pack:
    text = DEMO
    for old, new in replacements.items():
        assert old in text, old
        text = text.replace(old, new)
    return parse_pack(text)


def _problems(*packs: Pack) -> list[str]:
    with pytest.raises(OntologyError) as caught:
        OntologyRegistry(list(packs))
    return caught.value.problems


def test_valid_pack_composes() -> None:
    registry = OntologyRegistry([CORE, _demo()])
    assert registry.edge_type("RESOLVES").allows("Fix", "Ticket")
    assert registry.edge_type("RESOLVES").properties["confidence"] == "float"
    assert registry.intent_weights()["why"]["RESOLVES"] == 2.0
    assert [pack for pack, _rule in registry.rules_for("demo.ticket.closed")] == ["demo"]
    assert registry.rules_for("tool.execute") == []


class TestRequirements:
    def test_core_is_required(self) -> None:
        assert "the core pack must be active" in _problems(_demo())

    def test_missing_and_old_packs(self) -> None:
        problems = _problems(
            CORE, _demo(**{"requires: [core>=1.0]": "requires: [core>=2.0, jira]"})
        )
        assert any("requires core>=2.0; core is 1.0.0" in p for p in problems)
        assert any("requires pack 'jira'" in p for p in problems)

    def test_pack_loaded_twice(self) -> None:
        assert _problems(CORE, CORE) == ["pack 'core' is loaded more than once"]


class TestNames:
    def test_collisions_across_packs(self) -> None:
        clash = _demo(
            **{
                "    Fix:\n": "    Event:\n",
                "from: [Fix]": "from: [Event]",
                "type: Fix,": "type: Event,",
                "demo.ticket.closed: {}": "demo.ticket.closed: {}\n  tool.execute: {}",
                "ticket_status:": "why:",
            }
        )
        problems = _problems(CORE, clash)
        assert "node type 'Event' declared by core and demo" in problems
        assert "event 'tool.execute' declared by core and demo" in problems
        assert "intent 'why' declared by core and demo" in problems

    @pytest.mark.parametrize(
        ("old", "new", "message"),
        [
            ("    Fix:\n", "    fix_node:\n", "node type name 'fix_node'"),
            ("RESOLVES: {", "Resolves) DETACH DELETE n //: {", "edge type name"),
            ("{sha: string}", "{'sha) RETURN 1 //': string}", "must be snake_case"),
        ],
    )
    def test_names_that_reach_query_text_are_restricted(
        self, old: str, new: str, message: str
    ) -> None:
        text = DEMO.replace(old, new).replace("RESOLVES", "RESOLVES")
        problems = _problems(CORE, parse_pack(text))
        assert any(message in p for p in problems), problems


class TestReferences:
    def test_dangling_endpoint_and_interface(self) -> None:
        problems = _problems(
            CORE,
            _demo(
                **{
                    "from: [Fix], to: [Ticket]": "from: [Fix], to: [core:Ticket]",
                    "properties: {sha: string}": (
                        "properties: {sha: string}\n      interfaces: [Owned]"
                    ),
                }
            ),
        )
        assert "demo: edge RESOLVES refers to unknown type 'core:Ticket'" in problems
        assert "demo: Fix uses unknown interface 'Owned'" in problems

    def test_fields_must_be_properties(self) -> None:
        problems = _problems(
            CORE, _demo(**{"key: [sha]": "key: [sha, branch]\n      text_fields: [body]"})
        )
        assert "demo: Fix.key names unknown property 'branch'" in problems
        assert "demo: Fix.text_fields names unknown property 'body'" in problems

    def test_unknown_property_type(self) -> None:
        problems = _problems(CORE, _demo(**{"title: string}": "title: varchar}"}))
        assert "demo: Ticket.title: unknown property type 'varchar'" in problems


class TestProjectionRules:
    def test_undeclared_event(self) -> None:
        problems = _problems(CORE, _demo(**{"- event: demo.ticket.closed": "- event: demo.nope"}))
        assert "demo: projection rule for undeclared event 'demo.nope'" in problems

    def test_wrong_key_unknown_field_and_state(self) -> None:
        problems = _problems(
            CORE,
            _demo(
                **{
                    "key: {tracker: $.tracker, number: $.number}, set: {title: $.title}": (
                        "key: {tracker: $.tracker}, set: {colour: $.colour}"
                    ),
                    "to: closed, only_from: [open]": "to: archived, only_from: [open]",
                }
            ),
        )
        assert any("keys Ticket by ['tracker'], not ['number', 'tracker']" in p for p in problems)
        assert any("sets unknown property Ticket.colour" in p for p in problems)
        assert any("unknown Ticket state 'archived'" in p for p in problems)

    def test_edge_between_types_it_does_not_connect(self) -> None:
        problems = _problems(
            CORE,
            _demo(
                **{
                    "from: {type: Fix, key: {sha: $.sha}}\n        to: {type: Ticket, key: "
                    "{tracker: $.tracker, number: $.number}}": (
                        "from: {type: Ticket, key: {tracker: $.tracker, number: $.number}}\n"
                        "        to: {type: Fix, key: {sha: $.sha}}"
                    )
                }
            ),
        )
        assert any("draws RESOLVES from Ticket to Fix, not allowed" in p for p in problems)

    def test_expression_target_state_is_not_checked_at_load(self) -> None:
        pack = _demo(
            **{"to: closed, only_from": "to: \"map($.status, {'Done': closed})\", only_from"}
        )
        OntologyRegistry([CORE, pack])

    def test_transition_needs_a_lifecycle(self) -> None:
        problems = _problems(
            CORE,
            _demo(
                **{
                    "transition: {type: Ticket, to: closed, only_from: [open]}": (
                        "transition: {type: Fix, to: closed}"
                    )
                }
            ),
        )
        assert any("transitions Fix, which has no lifecycle" in p for p in problems)


class TestRetrieval:
    def test_unknown_edges_and_intents(self) -> None:
        problems = _problems(
            CORE,
            _demo(
                **{
                    "weights: {RESOLVES: 3.0}": "weights: {FIXES: 3.0}",
                    "why: {RESOLVES": "nope: {RESOLVES",
                }
            ),
        )
        assert "demo: intent ticket_status weights unknown edge 'FIXES'" in problems
        assert "demo: adds weights to unknown intent 'nope'" in problems

    def test_a_weight_is_set_once(self) -> None:
        problems = _problems(CORE, _demo(**{"why: {RESOLVES: 2.0}": "why: {CAUSED_BY: 2.0}"}))
        assert any("weight for CAUSED_BY on intent 'why' is already set" in p for p in problems)


class TestParsing:
    def test_yaml_11_booleans_and_dates_stay_strings(self) -> None:
        pack = parse_pack(
            "pack: {name: demo, version: 1.0.0, owner: no, description: 2026-10-04}\n"
            "mappings: {words: {on: yes, off: true}}\n"
        )
        assert pack.pack.owner == "no"
        assert pack.pack.description == "2026-10-04"
        assert pack.mappings == {"words": {"on": "yes", "off": True}}

    def test_duplicate_keys_are_rejected(self) -> None:
        with pytest.raises(OntologyError, match="duplicate key 'name'"):
            parse_pack("pack: {name: demo, name: other, version: 1.0.0}\n")

    def test_non_string_keys_are_rejected(self) -> None:
        with pytest.raises(OntologyError, match="non-string key 1"):
            parse_pack("pack: {name: demo, version: 1.0.0}\nmappings: {1: {a: b}}\n")

    def test_unknown_sections_and_bad_versions(self) -> None:
        with pytest.raises(OntologyError) as caught:
            parse_pack("pack: {name: Demo, version: '1.0'}\nextras: {}\n")
        text = "\n".join(caught.value.problems)
        assert "pack.name" in text
        assert "pack.version" in text
        assert "extras" in text


class TestVersion:
    def test_stable_order_independent_and_content_sensitive(self) -> None:
        first = OntologyRegistry([CORE, _demo()]).version
        assert OntologyRegistry([_demo(), CORE]).version == first
        assert first.startswith("sha256:")
        changed = OntologyRegistry(
            [CORE, _demo(**{"weights: {RESOLVES: 3.0}": "weights: {RESOLVES: 2.5}"})]
        )
        assert changed.version != first


class TestLoading:
    def test_requirements_and_core_are_loaded(self, tmp_path: Path) -> None:
        (tmp_path / "demo.pack.yaml").write_text(DEMO)
        registry = load_registry(["demo"], [tmp_path])
        assert [pack.name for pack in registry.packs] == ["core", "demo"]

    def test_file_must_declare_its_own_name(self, tmp_path: Path) -> None:
        (tmp_path / "other.pack.yaml").write_text(DEMO)
        with pytest.raises(OntologyError, match="declares pack 'demo'"):
            load_registry(["other"], [tmp_path])

    def test_unknown_pack(self) -> None:
        with pytest.raises(OntologyError, match="pack 'nope' not found"):
            load_registry(["nope"])
