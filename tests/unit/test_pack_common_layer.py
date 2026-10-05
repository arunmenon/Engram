"""The common layer in core (ADR-0018, core 1.1.0): what a second domain pack gets for free.

A small ``crm`` pack, active next to ``pdlc``, uses the interfaces core
declares (``Lifecycled``, ``Sourced``), gets provenance without declaring
it, and names its own superseded state. Its admission rule merges with
PDLC's. Base packs cannot be replaced from a pack directory.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import orjson
import pytest

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.domain.models import Event
from context_graph.domain.ontology import PROVENANCE_EDGE, OntologyError, OntologyRegistry
from context_graph.domain.pack_projection import PackProjector, make_node_id
from context_graph.domain.projection import event_to_node
from context_graph.ontology import BUILTIN_PACK_DIR, load_registry
from context_graph.retrieval.artifacts import ArtifactQuery, ArtifactRetriever
from context_graph.worker.pack_projection import apply_plan

if TYPE_CHECKING:
    from pathlib import Path

CRM = """\
pack: {name: crm, version: 1.0.0, requires: [core>=1.1]}
types:
  nodes:
    Account:
      key: [account_id]
      interfaces: [Sourced]
      properties: {account_id: string, name: string}
      text_fields: [name]
    Deal:
      key: [deal_id]
      interfaces: [Lifecycled, Sourced]
      properties: {deal_id: string, title: string}
      lifecycle: {initial: open, states: [open, won, lost, replaced], superseded_states: [replaced]}
      text_fields: [title]
  edges:
    BELONGS_TO: {from: [Deal], to: [Account]}
events:
  crm.deal.created: {}
  crm.deal.replaced: {}
projection:
  - event: crm.deal.created
    upsert:
      - {type: Deal, key: {deal_id: $.deal_id}, set: {title: $.title}}
      - {type: Account, key: {account_id: $.account_id}, set: {name: $.account_name}}
    edges:
      - type: BELONGS_TO
        from: {type: Deal, key: {deal_id: $.deal_id}}
        to: {type: Account, key: {account_id: $.account_id}}
  - event: crm.deal.replaced
    upsert:
      - {type: Deal, key: {deal_id: $.deal_id}}
    transition: {type: Deal, to: replaced}
retrieval:
  seed_types: [Deal, Account]
  key_patterns: {Deal: 'D-\\d+'}
  intents:
    pipeline:
      description: "The deals of an account"
      keywords: [pipeline]
      weights: {BELONGS_TO: 5}
  admission:
    superseded_or_reversed:
      {default: exclude, include_for_intents: [pipeline], label_as: superseded}
"""

IMPORTER = "importer:crm"
START = datetime(2026, 10, 5, 9, 0, tzinfo=UTC)


def _registry(
    tmp_path: Path, text: str = CRM, packs: tuple[str, ...] = ("pdlc", "crm")
) -> OntologyRegistry:
    (tmp_path / "crm.pack.yaml").write_text(text, encoding="utf-8")
    return load_registry(list(packs), [tmp_path])


def _problems(tmp_path: Path, text: str) -> list[str]:
    with pytest.raises(OntologyError) as caught:
        _registry(tmp_path, text)
    return caught.value.problems


class _Crm:
    def __init__(self, registry: OntologyRegistry, trusted: frozenset[str]) -> None:
        self.graph = MemoryGraphStore()
        self.projector = PackProjector(registry, trusted)
        self.registry = registry
        self.minute = 0

    async def ingest(self, event_type: str, payload: dict[str, Any], agent: str) -> None:
        self.minute += 1
        event = Event(
            event_id=uuid4(),
            event_type=event_type,
            occurred_at=START + timedelta(minutes=self.minute),
            session_id="crm:acme",
            agent_id=agent,
            trace_id="trace",
            payload_ref="payload",
            global_position=f"{self.minute}-0",
        )
        await self.graph.merge_event_node(event_to_node(event))
        document = orjson.loads(event.model_dump_json()) | {"payload": payload}
        await apply_plan(self.graph, self.projector.plan(event, document), 1000)

    def node(self, node_id: str) -> dict[str, Any]:
        return self.graph.nodes[(node_id.split(":")[0], node_id)]

    def retriever(self) -> ArtifactRetriever:
        return ArtifactRetriever(
            self.graph,
            self.registry,
            default_max_depth=3,
            seed_limit=10,
            neighbor_limit=200,
            provenance_source="memory",
        )


DEAL_1 = make_node_id("Deal", ["D1"])
DEAL_2 = make_node_id("Deal", ["D2"])
ACME = make_node_id("Account", ["acme"])


async def _two_deals(registry: OntologyRegistry, agent: str = IMPORTER) -> _Crm:
    crm = _Crm(registry, frozenset({IMPORTER}))
    for deal_id, title in (("D1", "Pilot"), ("D2", "Pilot, second round")):
        payload = {"deal_id": deal_id, "title": title, "account_id": "acme", "account_name": "Acme"}
        await crm.ingest("crm.deal.created", payload, agent)
    await crm.ingest("crm.deal.replaced", {"deal_id": "D1"}, agent)
    return crm


class TestComposition:
    def test_two_domain_packs_share_the_core_interfaces(self, tmp_path: Path) -> None:
        registry = _registry(tmp_path)
        assert [p.name for p in registry.packs] == ["core", "memory", "user", "crm", "pdlc"]
        # The same registry whatever order the packs are listed in
        assert _registry(tmp_path, packs=("crm", "pdlc")).version == registry.version
        for name in ("Lifecycled", "Sourced", "Claim", "Anchored", "Versioned"):
            assert registry.interfaces[name][0] == "core"
        assert registry.interfaces["Owned"][0] == "pdlc"  # it promises OWNED_BY, a PDLC edge

    def test_every_domain_type_gets_provenance(self, tmp_path: Path) -> None:
        registry = _registry(tmp_path)
        for type_name in ("Deal", "Account", "Change", "Decision"):
            assert registry.allows(PROVENANCE_EDGE, type_name, "Event")
        assert not registry.allows(PROVENANCE_EDGE, "Entity", "Event")  # core's own types do not

    def test_a_base_pack_cannot_be_replaced(self, tmp_path: Path) -> None:
        core = (BUILTIN_PACK_DIR / "core.pack.yaml").read_text(encoding="utf-8")
        (tmp_path / "core.pack.yaml").write_text(core.replace("root cause", "fault"), "utf-8")
        with pytest.raises(OntologyError) as caught:
            load_registry(["pdlc"], [tmp_path])
        assert caught.value.problems == [
            f"base pack 'core' cannot be replaced: remove core.pack.yaml from {tmp_path}"
        ]


class TestValidation:
    def test_a_lifecycle_needs_the_lifecycled_interface(self, tmp_path: Path) -> None:
        text = CRM.replace("interfaces: [Lifecycled, Sourced]", "interfaces: [Sourced]")
        assert "crm: Deal has a lifecycle, so it must use interface Lifecycled" in _problems(
            tmp_path, text
        )

    def test_superseded_states_are_lifecycle_states(self, tmp_path: Path) -> None:
        text = CRM.replace("superseded_states: [replaced]", "superseded_states: [archived]")
        assert any(
            "superseded states ['archived'] are not among" in p for p in _problems(tmp_path, text)
        )
        text = CRM.replace("superseded_states: [replaced]", "superseded_states: [open]")
        assert any(
            "initial state 'open' cannot be a superseded state" in p
            for p in _problems(tmp_path, text)
        )

    def test_admission_rules_and_settings_are_known(self, tmp_path: Path) -> None:
        text = CRM.replace("superseded_or_reversed:", "superseded_or_reversd:")
        assert any(
            "unknown admission rule 'superseded_or_reversd'" in p for p in _problems(tmp_path, text)
        )
        text = CRM.replace("label_as: superseded}", "label_as: superseded, hide_after: 30}")
        assert (
            "crm: admission superseded_or_reversed has unknown setting 'hide_after'"
            in _problems(tmp_path, text)
        )


class TestBehaviour:
    async def test_status_trust_and_provenance_come_from_core(self, tmp_path: Path) -> None:
        crm = await _two_deals(_registry(tmp_path), agent="someone:else")
        deal = crm.node(DEAL_1)
        assert (deal["status"], deal["source_trust"]) == ("replaced", "untrusted")
        assert crm.node(DEAL_2)["status"] == "open"
        provenance = {
            source[1] for (source, kind, _target) in crm.graph.edges if kind == PROVENANCE_EDGE
        }
        assert {DEAL_1, DEAL_2, ACME} <= provenance

    async def test_a_replaced_deal_is_not_current(self, tmp_path: Path) -> None:
        crm = await _two_deals(_registry(tmp_path))
        retriever = crm.retriever()
        # No intent keeps superseded items: the replaced deal is left out
        response = await retriever.retrieve(ArtifactQuery("Acme", seed_node_ids=(ACME,)))
        assert DEAL_2 in response.nodes
        assert DEAL_1 not in response.nodes
        # crm's admission rule adds its own intent to PDLC's (status, why): kept, marked
        kept = await retriever.retrieve(
            ArtifactQuery("Acme", seed_node_ids=(ACME,), intent="pipeline")
        )
        assert kept.nodes[DEAL_1].retrieval_reason == "superseded"
        # PDLC's intents still keep it (why does not walk BELONGS_TO: ask about the deal)
        why = await retriever.retrieve(ArtifactQuery("D1", seed_node_ids=(DEAL_1,), intent="why"))
        assert why.nodes[DEAL_1].retrieval_reason == "superseded"

    async def test_without_superseded_states_a_status_is_only_a_status(
        self, tmp_path: Path
    ) -> None:
        text = CRM.replace(", superseded_states: [replaced]", "")
        crm = await _two_deals(_registry(tmp_path, text))
        response = await crm.retriever().retrieve(ArtifactQuery("Acme", seed_node_ids=(ACME,)))
        assert {DEAL_1, DEAL_2} <= set(response.nodes)


class TestKeyPatterns:
    """Review 2.2: a pack says how questions name its keys (``D-7``), not only ``PAY-341``."""

    async def test_a_key_pattern_seeds_its_node(self, tmp_path: Path) -> None:
        crm = _Crm(_registry(tmp_path), frozenset({IMPORTER}))
        payload = {
            "deal_id": "D-7",
            "title": "Renewal",
            "account_id": "acme",
            "account_name": "Acme",
        }
        await crm.ingest("crm.deal.created", payload, IMPORTER)
        response = await crm.retriever().retrieve(
            ArtifactQuery("Which account does deal D-7 belong to?")
        )
        assert response.meta.seed_nodes == [make_node_id("Deal", ["D-7"])]
        assert ACME in response.nodes

    async def test_without_one_the_question_finds_nothing(self, tmp_path: Path) -> None:
        text = CRM.replace("  key_patterns: {Deal: 'D-\\d+'}\n", "")
        crm = _Crm(_registry(tmp_path, text), frozenset({IMPORTER}))
        payload = {
            "deal_id": "D-7",
            "title": "Renewal",
            "account_id": "acme",
            "account_name": "Acme",
        }
        await crm.ingest("crm.deal.created", payload, IMPORTER)
        response = await crm.retriever().retrieve(
            ArtifactQuery("Which account does deal D-7 belong to?")
        )
        assert response.meta.seed_nodes == []

    def test_key_patterns_are_checked(self, tmp_path: Path) -> None:
        for pattern, problem in (
            ("'D-(\\d+'", "key pattern for Deal: missing )"),
            ("'D?'", "key pattern for Deal matches empty text"),
        ):
            text = CRM.replace("{Deal: 'D-\\d+'}", "{Deal: " + pattern + "}")
            assert any(problem in p for p in _problems(tmp_path, text)), pattern
        text = CRM.replace("{Deal: 'D-\\d+'}", "{Contact: 'C-\\d+'}")
        assert any("key pattern for unknown type 'Contact'" in p for p in _problems(tmp_path, text))


def _tagger(name: str, requires: str = "core>=1.1") -> str:
    """A pack that tags every tool.execute event with a node of its own."""
    tag = name.capitalize() + "Tag"
    return f"""\
pack: {{name: {name}, version: 1.0.0, requires: [{requires}]}}
types:
  nodes:
    {tag}:
      key: [tag_id]
      properties: {{tag_id: string}}
projection:
  - event: "core:tool.execute"
    upsert:
      - {{type: {tag}, key: {{tag_id: $event.event_id}}}}
"""


class TestHardening:
    """Review 1.4, 1.5, 1.6 and 2.7."""

    def _packs(self, *texts: str) -> list[Any]:
        from context_graph.ontology import load_pack_file, parse_pack

        base = [
            load_pack_file(BUILTIN_PACK_DIR / f"{n}.pack.yaml") for n in ("core", "memory", "user")
        ]
        return [*base, *(parse_pack(t) for t in texts)]

    def test_rules_run_in_one_order_whatever_the_listing(self) -> None:
        alpha, beta = _tagger("alpha"), _tagger("beta")
        forward = OntologyRegistry(self._packs(alpha, beta))
        backward = OntologyRegistry(self._packs(beta, alpha))
        order = [pack for pack, _rule in forward.projection_rules["tool.execute"]]
        assert order == ["alpha", "beta"]  # by name when neither requires the other
        assert [p for p, _r in backward.projection_rules["tool.execute"]] == order
        # A pack's rules run after those of the packs it requires
        needs_beta = _tagger("alpha", "beta>=1.0")
        required = OntologyRegistry(self._packs(needs_beta, beta))
        assert [p for p, _r in required.projection_rules["tool.execute"]] == ["beta", "alpha"]

    def test_reserved_types_and_owned_namespaces(self, tmp_path: Path) -> None:
        text = CRM.replace(
            "    Account:\n",
            "    OntologyState:\n      key: [state_id]\n"
            "      properties: {state_id: string}\n    Account:\n",
        )
        assert "crm: node type name 'OntologyState' is reserved" in _problems(tmp_path, text)
        text = CRM.replace(
            "  crm.deal.replaced: {}\n", "  crm.deal.replaced: {}\n  pdlc.deal.won: {}\n"
        )
        assert any(
            "event 'pdlc.deal.won' is in namespace 'pdlc', which pack pdlc owns" in p
            for p in _problems(tmp_path, text)
        )

    def test_unknown_plugins_are_refused(self, tmp_path: Path) -> None:
        text = CRM.replace(
            "      keywords: [pipeline]\n",
            "      keywords: [pipeline]\n      plugin: mising_links\n",
        )
        assert any(
            "intent pipeline names unknown plugin 'mising_links'" in p
            for p in _problems(tmp_path, text)
        )

    def test_settings_nothing_reads_are_listed(self, tmp_path: Path) -> None:
        notes = _registry(tmp_path).inert_settings()
        assert "pdlc: extraction.derived_proposals" in notes
        assert "pdlc: lifecycle.decay" in notes
        assert "pdlc: Change.embed_fields (no embeddings for pack types)" in notes
        assert any(n.startswith("pdlc: link_policy ") and "read_time_threshold" in n for n in notes)
        assert not any(n.startswith("crm:") for n in notes)

    def test_a_transition_to_an_unknown_state_is_reported(self, tmp_path: Path) -> None:
        text = CRM.replace(
            "transition: {type: Deal, to: replaced}", "transition: {type: Deal, to: $.state}"
        )
        registry = _registry(tmp_path, text)
        projector = PackProjector(registry, frozenset({IMPORTER}))
        event = Event(
            event_id=uuid4(),
            event_type="crm.deal.replaced",
            occurred_at=START,
            session_id="s",
            agent_id=IMPORTER,
            trace_id="t",
            payload_ref="p",
            global_position="1-0",
        )
        document = orjson.loads(event.model_dump_json()) | {
            "payload": {"deal_id": "D1", "state": "archived"}
        }
        plan = projector.plan(event, document)
        assert plan.states == []
        assert plan.rejected == [
            "Deal: state 'archived' is not in its lifecycle ['open', 'won', 'lost', 'replaced']"
        ]
