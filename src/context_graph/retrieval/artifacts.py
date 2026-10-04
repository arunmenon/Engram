"""Artifact retrieval over ontology pack types (ADR-0018 phase 2).

Today's ``RetrievalEngine`` answers questions about agent sessions from
Event seeds. ``ArtifactRetriever`` answers questions about the artifacts
packs add (PDLC: changes, tickets, requirements, decisions, incidents):

1. **Intent**: classified from the query with the keywords of the intents
   that weight pack edges (``trace``, ``completeness``, ``status``,
   ``impact``, ``preflight``, and ``why``/``who_is``); or given.
2. **Seeds**: node ids given by the caller, plus nodes of the packs'
   seed types matched by the query. Key-like tokens are tried first
   (``PAY-341``, ``refund/retry.py``, ``#812``, ``v1.4.0``), then words:
   text fields, key fields and list fields are searched, and ``#n`` finds
   types keyed by a number.
3. **Traversal**: best-first and bounded, following only the edges the
   intent weights, in the intent's direction, to ``max_depth`` and
   ``max_nodes``. A node's relevance is the best product of normalised
   edge weights along a path from a seed.
4. **Admission** (the packs' ``retrieval.admission`` rules):
   - superseded or reversed items are left out, except for the intents a
     rule lists, where they are kept and marked ``superseded``;
   - untrusted items are left out unless a trusted item in the answer
     links to them, or the caller asks for untrusted items;
   - proposed links are kept, marked with their confidence, and never
     counted as confirmed.
5. **Completeness** (intents with the ``missing_links`` plugin): a set
   difference, not a traversal. The query names a subject type and a
   related type ("requirements" ... "tests"). Each subject node in scope is
   reported as ``no_link``, ``proposed_only`` or ``confirmed`` for the
   pack edge that joins the two types. The scope is the subject nodes
   reached from the seeds, or every subject node when there are no seeds,
   narrowed to the lifecycle states the question names ("merged").

Provenance for each node comes from its ``DERIVED_FROM`` edge to the
newest event that observed it. Uses ``PackGraph`` operations only.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from context_graph.domain.models import (
    AtlasEdge,
    AtlasNode,
    AtlasResponse,
    NodeScores,
    Provenance,
    QueryCapacity,
    QueryMeta,
)
from context_graph.domain.ontology import OPEN_PACKS
from context_graph.domain.pack_intents import RegistryIntents
from context_graph.ports.pack_graph import NodeRef

if TYPE_CHECKING:
    from context_graph.domain.ontology import NodeType, OntologyRegistry
    from context_graph.ports.pack_graph import Direction, PackGraph

MISSING_LINKS_PLUGIN = "missing_links"
PROVENANCE_EDGE = "DERIVED_FROM"
SUPERSEDES_EDGE = "SUPERSEDES"
SUPERSEDED_STATES = frozenset({"superseded", "reversed"})
LINK_REPORTS = ("no_link", "proposed_only", "confirmed")
DIRECTIONS: dict[str, Direction] = {"outbound": "out", "inbound": "in", "both": "both"}

_KEY_TOKEN = re.compile(
    r"[A-Z][A-Z0-9]+-\d+"  # tracker keys: PAY-341
    r"|[\w.\-]+/[\w.\-/]+"  # paths and repos: refund/retry.py, acme/app
    r"|\bv?\d+\.\d+(?:\.\d+)?\b"  # versions: v1.4.0
    r"|[\w\-]+\.\w{1,5}\b"  # file names: retry.py
)
_NUMBER_REF = re.compile(r"(?:#|\b(?:pr|pull request|change|mr)\s+#?)(\d+)\b", re.IGNORECASE)
_WORD = re.compile(r"[a-z0-9_]{3,}")
_STOP = frozenset(
    {
        "the", "and", "for", "with", "what", "which", "who", "why", "how", "when", "where",
        "does", "did", "have", "has", "had", "are", "was", "were", "this", "that", "these",
        "those", "any", "all", "our", "its", "from", "into", "about", "still", "should",
        "know", "before", "after", "there", "their", "them", "they", "been", "being",
        "would", "could", "can", "will", "not", "no", "yet", "each", "other", "two",
        "right", "now", "last", "next", "exist", "exists", "anything", "something",
    }
)  # fmt: skip


@dataclass(frozen=True)
class ArtifactQuery:
    query: str
    seed_node_ids: tuple[str, ...] = ()
    intent: str | None = None
    max_depth: int | None = None
    max_nodes: int = 100
    include_untrusted: bool = False


@dataclass
class _Found:
    ref: NodeRef
    props: dict[str, Any]
    score: float
    depth: int
    reason: str = "direct"
    # How a seed was found: given, key (a key-like token), number, word
    origin: str = "traversal"


@dataclass
class _Result:
    nodes: dict[str, _Found] = field(default_factory=dict)
    edges: dict[tuple[str, str, str], dict[str, Any]] = field(default_factory=dict)
    truncated: bool = False


# Suffixes stripped so "retrying", "retried" and "retries" match "retry"
_SUFFIXES = (
    ("ying", "y"),
    ("ied", "y"),
    ("ies", "y"),
    ("ing", ""),
    ("ed", ""),
    ("es", ""),
    ("s", ""),
)
_MIN_STEM = 3


def _stem(word: str) -> str:
    for suffix, replacement in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= _MIN_STEM:
            return word[: len(word) - len(suffix)] + replacement
    return word


def _split_camel(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", " ", name).lower()


class ArtifactRetriever:
    """Questions about pack artifacts, answered from the graph through ``PackGraph``."""

    def __init__(
        self,
        graph: PackGraph,
        registry: OntologyRegistry,
        *,
        default_max_depth: int,
        seed_limit: int,
        neighbor_limit: int,
        provenance_source: str,
        seed_min_ratio: float = 0.5,
    ) -> None:
        self._graph = graph
        self._registry = registry
        self._intents = RegistryIntents.for_artifacts(registry)
        self._default_depth = default_max_depth
        self._seed_limit = seed_limit
        self._neighbor_limit = neighbor_limit
        self._provenance_source = provenance_source
        self._seed_min_ratio = seed_min_ratio
        self._seed_types = [
            name
            for pack in registry.packs
            if pack.name not in OPEN_PACKS
            for name in pack.retrieval.seed_types
        ]
        self._type_words = self._type_vocabulary()

    @property
    def intents(self) -> list[str]:
        return list(self._intents.names)

    # -- public ------------------------------------------------------------------------

    async def retrieve(self, query: ArtifactQuery) -> AtlasResponse:
        started = time.monotonic()
        if query.intent is not None:
            intents = {query.intent: 1.0}
        else:
            intents = self._intents.classify(query.query) or {
                name: 1.0 for name in self._intents.names
            }
        dominant = self._intents.dominant(intents)
        intent = self._registry.intents[dominant] if dominant else None
        weights = {e: w for e, w in self._intents.edge_weights(intents).items() if w > 0}
        depth = query.max_depth or (intent.definition.max_depth if intent else None)
        depth = depth or self._default_depth
        direction = DIRECTIONS[intent.definition.direction] if intent else "both"

        seeds = await self._seeds(query, intent.definition.prefer_types if intent else [])
        completeness = intent is not None and intent.definition.plugin == MISSING_LINKS_PLUGIN
        if completeness:
            # Scope comes from precise references only, not from loose word matches
            seeds = [s for s in seeds if s.origin != "word"]
        result = _Result()
        for seed in seeds[: query.max_nodes]:
            result.nodes[self._node_key(seed.ref)] = seed

        reports: dict[str, int] = {}
        if completeness:
            reports = await self._missing_links(query, weights, result, depth)
        else:
            await self._traverse(result, weights, direction, depth, query.max_nodes)
            await self._admit(result, dominant, query.include_untrusted)
        await self._attach_provenance(result)
        return self._atlas(result, intents, seeds, query, depth, reports, started)

    # -- seeds ----------------------------------------------------------------------------

    def _type_vocabulary(self) -> dict[str, list[str]]:
        """Words that name each pack type ("requirements", "tests", "pull request")."""
        synonyms: dict[str, list[str]] = {}
        for pack in self._registry.packs:
            for name, words in pack.mappings.get("synonyms", {}).items():
                synonyms.setdefault(name, []).extend(str(w).lower() for w in words)
        vocabulary: dict[str, list[str]] = {}
        for name, node_type in self._registry.node_types.items():
            if node_type.pack in OPEN_PACKS:
                continue
            phrase = _split_camel(name)
            words = {phrase, phrase.split()[0], *synonyms.get(name, [])}
            vocabulary[name] = sorted(words | {w + "s" for w in words}, key=len, reverse=True)
        return vocabulary

    def mentioned_types(self, text: str) -> list[str]:
        """Pack types the text names, in order of first mention."""
        lowered = text.lower()
        positions: dict[str, int] = {}
        for name, words in self._type_words.items():
            for word in words:
                match = re.search(r"\b" + re.escape(word) + r"\b", lowered)
                if match and (name not in positions or match.start() < positions[name]):
                    positions[name] = match.start()
        return sorted(positions, key=lambda n: positions[n])

    def _search_fields(self, node_type: NodeType) -> list[str]:
        definition = node_type.definition
        fields = [*definition.key, *definition.text_fields]
        fields += [
            prop
            for prop, spec in node_type.properties.items()
            if isinstance(spec, str) and spec in ("list<string>", "string")
        ]
        return list(dict.fromkeys(fields))

    def _ref(self, label: str, props: dict[str, Any]) -> NodeRef | None:
        node_type = self._registry.node_types.get(label)
        if node_type is None:
            return None
        key = props.get(node_type.key_property)
        return None if key is None else NodeRef(label, str(key), node_type.key_property)

    def _parse_node_id(self, node_id: str) -> NodeRef | None:
        label, _, rest = node_id.partition(":")
        node_type = self._registry.node_types.get(label)
        if node_type is None or not rest:
            return None
        if node_type.definition.id_property:
            return NodeRef(label, rest, node_type.key_property)
        return NodeRef(label, node_id)

    async def _seeds(self, query: ArtifactQuery, prefer: list[str]) -> list[_Found]:
        found: dict[NodeRef, _Found] = {}
        given = [ref for ref in map(self._parse_node_id, query.seed_node_ids) if ref]
        for ref, props in (await self._graph.get_nodes(given)).items():
            found[ref] = _Found(ref, props, 1.0, 0, origin="given")

        text = query.query
        key_terms = [t.lower() for t in _KEY_TOKEN.findall(text)]
        numbers = [int(n) for n in _NUMBER_REF.findall(text)]
        words = [w for w in _WORD.findall(text.lower()) if w not in _STOP and not w.isdigit()]
        mentioned = set(self.mentioned_types(text))
        words = [w for w in words if not any(w in self._type_words[t] for t in mentioned)]
        words = list(dict.fromkeys(_stem(w) for w in words))
        for terms, origin in ((key_terms, "key"), (words, "word")):
            if not terms or len(found) >= self._seed_limit:
                continue
            for label in self._seed_types:
                node_type = self._registry.node_types[label]
                rows = await self._graph.search_nodes(
                    label, self._search_fields(node_type), terms, self._seed_limit
                )
                for props, hits in rows:
                    match_ref = self._ref(label, props)
                    if match_ref and match_ref not in found:
                        score = hits / len(terms)
                        if origin == "key" and any(
                            str(props.get(k, "")).lower() in terms for k in node_type.key
                        ):
                            score += 1.0  # the token is this node's own key
                        found[match_ref] = _Found(match_ref, props, score, 0, origin=origin)
            if key_terms and found:
                break  # precise references found; words would only add noise
        for number in numbers:
            for label in self._seed_types:
                node_type = self._registry.node_types[label]
                for key_field in node_type.key:
                    if node_type.properties.get(key_field) != "int":
                        continue
                    for props in await self._graph.find_nodes(
                        label, {key_field: number}, self._seed_limit
                    ):
                        number_ref = self._ref(label, props)
                        if number_ref and number_ref not in found:
                            found[number_ref] = _Found(number_ref, props, 1.0, 0, origin="number")
        # Word matches far weaker than the best one are noise
        best_word = max((f.score for f in found.values() if f.origin == "word"), default=0.0)
        kept = [
            f
            for f in found.values()
            if f.origin != "word" or f.score >= best_word * self._seed_min_ratio
        ]
        ranked = sorted(
            kept, key=lambda f: (f.ref.label not in prefer, -f.score, f.ref.label, f.ref.key)
        )
        return ranked[: self._seed_limit]

    # -- traversal ------------------------------------------------------------------------

    def _node_key(self, ref: NodeRef) -> str:
        return ref.key if ref.key_property == "node_id" else f"{ref.label}:{ref.key}"

    async def _traverse(
        self,
        result: _Result,
        weights: dict[str, float],
        direction: Direction,
        depth: int,
        max_nodes: int,
    ) -> None:
        if not weights:
            return
        top = max(weights.values())
        frontier = list(result.nodes.values())
        for level in range(1, depth + 1):
            if not frontier:
                break
            rows = await self._graph.neighbors(
                [f.ref for f in frontier], list(weights), direction, self._neighbor_limit
            )
            parents = {(f.ref.label, f.ref.key): f for f in frontier}
            next_frontier: list[_Found] = []
            for row in sorted(rows, key=lambda r: -weights.get(r["edge_type"], 0.0)):
                source = (row["source_label"], str(row["source_key"]))
                target = (row["target_label"], str(row["target_key"]))
                near, far = (source, target) if source in parents else (target, source)
                parent = parents.get(near)
                other = self._ref(far[0], row["node"])
                if parent is None or other is None:
                    continue
                score = parent.score * weights.get(row["edge_type"], 0.0) / top
                key = self._node_key(other)
                existing = result.nodes.get(key)
                if existing is None:
                    if len(result.nodes) >= max_nodes:
                        result.truncated = True
                        continue
                    existing = result.nodes[key] = _Found(other, row["node"], score, level)
                    next_frontier.append(existing)
                elif score > existing.score:
                    existing.score = score
                edge_key = (
                    self._node_key(NodeRef(source[0], source[1], self._key_prop(source[0]))),
                    self._node_key(NodeRef(target[0], target[1], self._key_prop(target[0]))),
                    row["edge_type"],
                )
                result.edges[edge_key] = row["properties"]
            frontier = next_frontier

    def _key_prop(self, label: str) -> str:
        node_type = self._registry.node_types.get(label)
        return node_type.key_property if node_type else "node_id"

    # -- admission ---------------------------------------------------------------------------

    def _admission(self) -> dict[str, dict[str, Any]]:
        rules: dict[str, dict[str, Any]] = {}
        for pack in self._registry.packs:
            for name, rule in pack.retrieval.admission.items():
                rules[name] = rule.model_dump()
        return rules

    async def _superseded(self, result: _Result) -> set[str]:
        """Nodes whose status says superseded, or that a node SUPERSEDES."""
        refs = [f.ref for f in result.nodes.values()]
        rows = await self._graph.neighbors(refs, [SUPERSEDES_EDGE], "in", self._neighbor_limit)
        replaced = {
            self._node_key(
                NodeRef(r["target_label"], str(r["target_key"]), self._key_prop(r["target_label"]))
            )
            for r in rows
        }
        return replaced | {
            key for key, f in result.nodes.items() if f.props.get("status") in SUPERSEDED_STATES
        }

    async def _admit(self, result: _Result, intent: str | None, include_untrusted: bool) -> None:
        rules = self._admission()
        superseded_rule = rules.get("superseded_or_reversed")
        if superseded_rule is not None:
            keep_for = set(superseded_rule.get("include_for_intents") or [])
            label = superseded_rule.get("label_as") or "superseded"
            superseded = await self._superseded(result)
            for key, found in list(result.nodes.items()):
                if key in superseded:
                    if intent in keep_for:
                        found.reason = label
                    else:
                        del result.nodes[key]
        if "untrusted_uncorroborated" in rules and not include_untrusted:
            trusted = {
                k for k, f in result.nodes.items() if f.props.get("source_trust") != "untrusted"
            }
            corroborated = {
                end
                for (source, target, _type) in result.edges
                for end, other in ((source, target), (target, source))
                if other in trusted
            }
            for key, found in list(result.nodes.items()):
                if found.props.get("source_trust") == "untrusted" and key not in corroborated:
                    del result.nodes[key]
        result.edges = {
            k: v for k, v in result.edges.items() if k[0] in result.nodes and k[1] in result.nodes
        }

    # -- completeness --------------------------------------------------------------------------

    async def _missing_links(
        self,
        query: ArtifactQuery,
        weights: dict[str, float],
        result: _Result,
        depth: int,
    ) -> dict[str, int]:
        mentioned = self.mentioned_types(query.query)
        if not mentioned:
            return {}
        subject = mentioned[0]
        related = mentioned[1:]
        link = self._completeness_edge(subject, related, weights)
        if link is None:
            return {}
        edge_type, subject_is_target = link
        seeds_of_subject = [f for f in result.nodes.values() if f.ref.label == subject]
        if result.nodes and not seeds_of_subject:
            # Subjects in scope: those reached from the seeds
            others = {
                e: w
                for e, w in self._intents.edge_weights(
                    {n: 1.0 for n in self._intents.names}
                ).items()
                if e != edge_type
            }
            await self._traverse(result, others, "both", depth, query.max_nodes)
            candidates = [f for f in result.nodes.values() if f.ref.label == subject]
        elif seeds_of_subject:
            candidates = seeds_of_subject
        else:
            rows = await self._graph.find_nodes(subject, {}, query.max_nodes)
            candidates = [
                _Found(ref, props, 1.0, 0)
                for props in rows
                if (ref := self._ref(subject, props)) is not None
            ]
        # States the question names ("merged changes") narrow the subjects
        lifecycle = self._registry.node_type(subject).lifecycle
        if lifecycle is not None:
            text = query.query.lower()
            named = [
                state
                for state in lifecycle.states
                if re.search(r"\b" + re.escape(state.replace("_", " ")) + r"\b", text)
            ]
            if named:
                candidates = [c for c in candidates if c.props.get("status") in named]
        direction: Direction = "in" if subject_is_target else "out"
        rows = await self._graph.neighbors(
            [c.ref for c in candidates], [edge_type], direction, self._neighbor_limit
        )
        status: dict[tuple[str, str], str] = {}
        for row in rows:
            end = (
                (row["target_label"], str(row["target_key"]))
                if subject_is_target
                else (row["source_label"], str(row["source_key"]))
            )
            link_status = row["properties"].get("link_status", "confirmed")
            if link_status == "rejected":
                continue
            current = status.get(end)
            if link_status == "confirmed" or current is None:
                status[end] = "confirmed" if link_status == "confirmed" else "proposed_only"
        reports = dict.fromkeys(LINK_REPORTS, 0)
        result.nodes = {}
        result.edges = {}
        for candidate in candidates:
            report = status.get((candidate.ref.label, candidate.ref.key), "no_link")
            reports[report] += 1
            if report != "confirmed":
                candidate.reason = report
                result.nodes[self._node_key(candidate.ref)] = candidate
        return {f"completeness.{edge_type}.{k}": v for k, v in reports.items()}

    def _completeness_edge(
        self, subject: str, related: list[str], weights: dict[str, float]
    ) -> tuple[str, bool] | None:
        """The weighted edge joining the subject type to a related type (and its direction)."""
        options: list[tuple[float, str, bool]] = []
        others: list[str | None] = [*related] if related else [None]
        for edge_type, weight in weights.items():
            for other in others:
                if self._registry.allows(edge_type, other or "", subject) or (
                    other is None and subject in self._registry.edge_type(edge_type).to_types
                ):
                    options.append((weight, edge_type, True))
                if other is not None and self._registry.allows(edge_type, subject, other):
                    options.append((weight, edge_type, False))
        if not options:
            return None
        _weight, edge_type, subject_is_target = max(options)
        return edge_type, subject_is_target

    # -- output --------------------------------------------------------------------------------

    async def _attach_provenance(self, result: _Result) -> None:
        refs = [f.ref for f in result.nodes.values()]
        if not refs:
            return
        rows = await self._graph.neighbors(
            refs, [PROVENANCE_EDGE], "out", self._neighbor_limit * 10
        )
        newest: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            source = (row["source_label"], str(row["source_key"]))
            event = row["node"]
            if row["node_label"] != "Event":
                continue
            if source not in newest or str(event.get("occurred_at", "")) > str(
                newest[source].get("occurred_at", "")
            ):
                newest[source] = event
        for found in result.nodes.values():
            event = newest.get((found.ref.label, found.ref.key))
            if event is not None:
                found.props = {**found.props, "_provenance": event}

    def _provenance(self, event: dict[str, Any]) -> Provenance | None:
        try:
            occurred = event.get("occurred_at")
            return Provenance(
                event_id=str(event["event_id"]),
                global_position=str(event.get("global_position", "")),
                source=self._provenance_source,
                occurred_at=occurred
                if isinstance(occurred, datetime)
                else datetime.fromisoformat(str(occurred).replace("Z", "+00:00")),
                session_id=str(event.get("session_id", "")),
                agent_id=str(event.get("agent_id", "")),
                trace_id=str(event.get("trace_id", "")),
            )
        except (KeyError, ValueError):
            return None

    def _atlas(
        self,
        result: _Result,
        intents: dict[str, float],
        seeds: list[_Found],
        query: ArtifactQuery,
        depth: int,
        reports: dict[str, int],
        started: float,
    ) -> AtlasResponse:
        nodes: dict[str, AtlasNode] = {}
        for key, found in sorted(result.nodes.items(), key=lambda item: -item[1].score):
            attributes = {
                k: v for k, v in found.props.items() if k not in ("embedding", "_provenance")
            }
            event = found.props.get("_provenance")
            nodes[key] = AtlasNode(
                node_id=key,
                node_type=found.ref.label,
                attributes=attributes,
                provenance=self._provenance(event) if isinstance(event, dict) else None,
                scores=NodeScores(relevance_score=round(found.score, 4)),
                retrieval_reason=found.reason,
            )
        edges = [
            AtlasEdge(source=source, target=target, edge_type=edge_type, properties=props)
            for (source, target, edge_type), props in sorted(result.edges.items())
        ]
        return AtlasResponse(
            nodes=nodes,
            edges=edges,
            meta=QueryMeta(
                query_ms=int((time.monotonic() - started) * 1000),
                nodes_returned=len(nodes),
                truncated=result.truncated,
                inferred_intents=intents,
                intent_override=query.intent,
                seed_nodes=[self._node_key(s.ref) for s in seeds],
                seed_strategy="artifact_seeds",
                retrieval_channels=reports,
                capacity=QueryCapacity(
                    max_nodes=query.max_nodes, used_nodes=len(nodes), max_depth=depth
                ),
            ),
        )
