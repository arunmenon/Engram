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
   Caller-given seeds are always kept; found seeds are cut to the seed
   limit. A key token ranks a node first only when it is the node's most
   specific key value (``PAY-341``, not the repo a change is in).
3. **Traversal**: level by level, bounded, following only the artifact
   edges the intent weights (edges between pack types; never provenance
   or session edges), in the intent's direction, to ``max_depth`` and
   ``max_nodes``. A node's relevance is the best product of normalised
   edge weights along a path from a seed; within a level, nodes are
   admitted in relevance order. Two steps drift from the question and are
   not taken: back out of a reached node through the edge type it was
   entered by, in the same role (its siblings: other changes in the same
   release), and from a reached node to a node of its own type (its
   family: a story's epic), unless from a seed or continuing such a chain.
   A query matching no intent keyword uses every artifact intent's edges in
   both directions; a tie prefers an
   intent with a plugin (a question about absence names it).
4. **Admission** (the packs' ``retrieval.admission`` rules):
   - superseded or reversed items are left out, except for the intents a
     rule lists, where they are kept and marked ``superseded``;
   - untrusted items are left out unless a trusted source linked a trusted
     item in the answer to them with a confirmed link, or the caller asks
     for untrusted items (they are then marked ``untrusted``);
   - proposed links are kept, marked with their confidence, and never
     counted as confirmed.
5. **Completeness** (intents with the ``missing_links`` plugin): a set
   difference, not a traversal. The query names a subject type and a
   related type ("requirements" ... "tests"). Each subject node in scope is
   reported as ``no_link``, ``proposed_only`` or ``confirmed`` for the
   pack edge that joins the two types (in either direction when the edge
   allows both). A link counts as confirmed only when it is confirmed, the
   node at its other end is trusted, and that node has the enum value the
   question names ("approving review": ``verdict: approved``). The scope:
   the subject nodes one artifact edge from the seeds; for seeds of the
   subject type, their descendants along subject-to-subject edges ("under
   PAY-300"), or the seeds themselves; with no seeds, every subject node
   in the lifecycle states the question names ("merged"), up to the scan
   limit. Superseded and untrusted subjects are left out as above.

Bounds: neighbour reads are paged (a call that fills the neighbour limit is
split by node and then by edge type), every request has a budget of graph
calls and of query terms, and ``truncated`` is set whenever a limit cut an
answer. The route applies the query timeout.

Provenance for each node comes from its ``DERIVED_FROM`` edge to the
newest event that observed it (an Event node is its own provenance). Uses
``PackGraph`` operations only.
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
from context_graph.domain.ontology import OPEN_PACKS, EnumSpec
from context_graph.domain.pack_intents import RegistryIntents
from context_graph.ports.pack_graph import NodeRef

if TYPE_CHECKING:
    from collections.abc import Iterable

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
        "those", "any", "all", "our", "its", "from", "into", "about", "should", "there",
        "their", "them", "they", "been", "being", "would", "could", "can", "will", "not",
        "yet", "each", "other",
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
    # The edge type this node was first reached by, and its role in it
    # (source or target); None for seeds
    via: tuple[str, str] | None = None
    # Reached by an edge between two nodes of the same type (WorkItem -> WorkItem)
    peer_step: bool = False


@dataclass
class _Result:
    nodes: dict[str, _Found] = field(default_factory=dict)
    edges: dict[tuple[str, str, str], dict[str, Any]] = field(default_factory=dict)
    truncated: bool = False
    # Graph calls made for this request (bounded by the call budget)
    calls: int = 0


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
        max_terms: int = 16,
        max_graph_calls: int = 400,
        scan_limit: int = 5000,
    ) -> None:
        self._graph = graph
        self._registry = registry
        self._intents = RegistryIntents.for_artifacts(registry)
        self._default_depth = default_max_depth
        self._seed_limit = seed_limit
        self._neighbor_limit = neighbor_limit
        self._provenance_source = provenance_source
        self._seed_min_ratio = seed_min_ratio
        self._max_terms = max_terms
        self._max_calls = max_graph_calls
        self._scan_limit = scan_limit
        self._seed_types = [
            name
            for pack in registry.packs
            if pack.name not in OPEN_PACKS
            for name in pack.retrieval.seed_types
        ]
        self._type_words = self._type_vocabulary()
        self._artifact_edges = self._edges_between_pack_types()

    @property
    def intents(self) -> list[str]:
        return list(self._intents.names)

    # -- public ------------------------------------------------------------------------

    async def retrieve(self, query: ArtifactQuery) -> AtlasResponse:
        started = time.monotonic()
        if query.intent is not None:
            intents = {query.intent: 1.0}
        else:
            intents = self._intents.classify(query.query)
        dominant = self._dominant(intents)
        intent = self._registry.intents[dominant] if dominant else None
        if intents:
            weights = self._intents.edge_weights(intents)
        else:
            # No intent named: every artifact intent's edges, both directions
            weights = self._intents.edge_weights(dict.fromkeys(self._intents.names, 1.0))
        weights = {e: w for e, w in weights.items() if w > 0 and e in self._artifact_edges}
        depth = query.max_depth or (intent.definition.max_depth if intent else None)
        depth = depth or self._default_depth
        direction = DIRECTIONS[intent.definition.direction] if intent else "both"

        result = _Result()
        seeds = await self._seeds(query, intent.definition.prefer_types if intent else [], result)
        completeness = intent is not None and intent.definition.plugin == MISSING_LINKS_PLUGIN
        if completeness:
            # Scope comes from precise references only, not from loose word matches
            seeds = [s for s in seeds if s.origin != "word"]
        for seed in seeds[: query.max_nodes]:
            result.nodes[self._node_key(seed.ref)] = seed

        reports: dict[str, int] = {}
        if completeness:
            # The completeness edge comes from that intent's own weights, not a tie's
            assert intent is not None
            own = {e: w for e, w in intent.weights.items() if w > 0 and e in self._artifact_edges}
            reports = await self._missing_links(query, own, result, depth)
        else:
            await self._traverse(result, weights, direction, depth, query.max_nodes)
            await self._admit(result, dominant, query.include_untrusted)
        await self._attach_provenance(result)
        return self._atlas(result, intents, seeds, query, depth, reports, started)

    def _dominant(self, intents: dict[str, float]) -> str | None:
        """The strongest intent; a tie prefers one with a plugin, then the first declared."""
        if not intents:
            return None
        top = max(intents.values())
        tied = [name for name in self._intents.names if intents.get(name) == top]
        tied += [name for name in intents if intents[name] == top and name not in tied]
        with_plugin = [
            name
            for name in tied
            if name in self._registry.intents and self._registry.intents[name].definition.plugin
        ]
        return (with_plugin or tied)[0]

    # -- graph reads -------------------------------------------------------------------

    def _spend(self, result: _Result) -> bool:
        """Count one graph call; False (and truncated) once the budget is spent."""
        if result.calls >= self._max_calls:
            result.truncated = True
            return False
        result.calls += 1
        return True

    async def _neighbors_all(
        self,
        refs: list[NodeRef],
        edge_types: list[str],
        direction: Direction,
        result: _Result,
        *,
        mark_truncated: bool = True,
    ) -> list[dict[str, Any]]:
        """Every edge row at ``refs``, paging past the neighbour limit.

        A call that fills the limit is split in half by node, and for one
        node by edge type (in the order given, strongest first); one node
        and one edge type that still fill it are cut, which sets truncated.
        """
        rows: list[dict[str, Any]] = []
        pending: list[tuple[list[NodeRef], list[str]]] = [(refs, edge_types)]
        while pending:
            batch, edges = pending.pop(0)
            if not batch or not edges or not self._spend(result):
                continue
            found = await self._graph.neighbors(batch, edges, direction, self._neighbor_limit)
            if len(found) < self._neighbor_limit:
                rows.extend(found)
            elif len(batch) > 1:
                middle = len(batch) // 2
                pending += [(batch[:middle], edges), (batch[middle:], edges)]
            elif len(edges) > 1:
                pending += [(batch, [edge]) for edge in edges]
            else:
                rows.extend(found)
                if mark_truncated:
                    result.truncated = True
        return rows

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
            vocabulary[name] = sorted(words, key=len, reverse=True)
        return vocabulary

    def _edges_between_pack_types(self) -> set[str]:
        """Edge types that can join two pack types (never provenance or session edges)."""
        pack_types = [n for n, t in self._registry.node_types.items() if t.pack not in OPEN_PACKS]
        return {
            name
            for name in self._registry.edge_types
            if name != PROVENANCE_EDGE
            and any(self._registry.allows(name, a, b) for a in pack_types for b in pack_types)
        }

    def mentioned_types(self, text: str) -> list[str]:
        """Pack types the text names, in order of first mention.

        A type word matches with a plural or verb ending and an ``un``
        prefix: "tests", "untested", "unreviewed".
        """
        lowered = text.lower()
        positions: dict[str, int] = {}
        for name, words in self._type_words.items():
            for word in words:
                pattern = r"\b(?:un)?" + re.escape(word) + r"(?:s|es|ed|ing)?\b"
                match = re.search(pattern, lowered)
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

    async def _seeds(
        self, query: ArtifactQuery, prefer: list[str], result: _Result
    ) -> list[_Found]:
        given: list[_Found] = []
        refs = list(dict.fromkeys(r for r in map(self._parse_node_id, query.seed_node_ids) if r))
        if refs and self._spend(result):
            for ref, props in (await self._graph.get_nodes(refs)).items():
                given.append(_Found(ref, props, 1.0, 0, origin="given"))
        given_refs = {f.ref for f in given}

        found: dict[NodeRef, _Found] = {}
        text = query.query
        key_terms = list(dict.fromkeys(t.lower() for t in _KEY_TOKEN.findall(text)))
        numbers = list(dict.fromkeys(int(n) for n in _NUMBER_REF.findall(text)))
        words = [w for w in _WORD.findall(text.lower()) if w not in _STOP and not w.isdigit()]
        mentioned = set(self.mentioned_types(text))
        words = [
            w
            for w in words
            if not any(_stem(w) in map(_stem, self._type_words[t]) for t in mentioned)
        ]
        words = list(dict.fromkeys(_stem(w) for w in words))
        if len(key_terms) > self._max_terms or len(words) > self._max_terms:
            result.truncated = True
        key_terms, words = key_terms[: self._max_terms], words[: self._max_terms]
        if len(numbers) > self._max_terms:
            result.truncated = True
            numbers = numbers[: self._max_terms]
        for terms, origin in ((key_terms, "key"), (words, "word")):
            if not terms:
                continue
            for label in self._seed_types:
                node_type = self._registry.node_types[label]
                if not self._spend(result):
                    break
                rows = await self._graph.search_nodes(
                    label, self._search_fields(node_type), terms, self._seed_limit
                )
                for props, hits in rows:
                    match_ref = self._ref(label, props)
                    if match_ref and match_ref not in found and match_ref not in given_refs:
                        score = hits / len(terms)
                        own_key = str(props.get(node_type.key[-1], "")).lower()
                        if origin == "key" and own_key in terms:
                            score += 1.0  # the token is this node's own (most specific) key
                        found[match_ref] = _Found(match_ref, props, score, 0, origin=origin)
            if key_terms and found:
                break  # precise references found; words would only add noise
        for number in numbers:
            for label in self._seed_types:
                node_type = self._registry.node_types[label]
                key_field = node_type.key[-1]
                if node_type.properties.get(key_field) != "int" or not self._spend(result):
                    continue
                for props in await self._graph.find_nodes(
                    label, {key_field: number}, self._seed_limit
                ):
                    number_ref = self._ref(label, props)
                    if number_ref is None or number_ref in given_refs:
                        continue
                    # Its own key; more so when the question also names its other key values
                    others = [str(props.get(k, "")).lower() for k in node_type.key[:-1]]
                    score = 2.0 + (0.5 if others and all(o in key_terms for o in others) else 0.0)
                    if number_ref not in found or found[number_ref].score < score:
                        found[number_ref] = _Found(number_ref, props, score, 0, origin="number")
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
        # Caller-given seeds are always kept, first
        return [*given, *ranked[: self._seed_limit]]

    # -- traversal ------------------------------------------------------------------------

    def _node_key(self, ref: NodeRef) -> str:
        return ref.key if ref.key_property == "node_id" else f"{ref.label}:{ref.key}"

    def _row_ends(self, row: dict[str, Any]) -> tuple[NodeRef, NodeRef]:
        source = NodeRef(
            row["source_label"], str(row["source_key"]), self._key_prop(row["source_label"])
        )
        target = NodeRef(
            row["target_label"], str(row["target_key"]), self._key_prop(row["target_label"])
        )
        return source, target

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
        edge_order = sorted(weights, key=lambda e: (-weights[e], e))
        frontier = list(result.nodes.values())
        for level in range(1, depth + 1):
            if not frontier:
                break
            rows = await self._neighbors_all(
                [f.ref for f in frontier], edge_order, direction, result
            )
            parents = {(f.ref.label, f.ref.key): f for f in frontier}
            reached: list[tuple[float, str, _Found, NodeRef, dict[str, Any], dict[str, Any]]] = []
            for row in rows:
                source, target = self._row_ends(row)
                near, far = (
                    (source, target) if (source.label, source.key) in parents else (target, source)
                )
                parent = parents.get((near.label, near.key))
                other = self._ref(far.label, row["node"])
                if parent is None or other is None:
                    continue
                if self._drifts(parent, row["edge_type"], near == source, far.label):
                    continue
                score = parent.score * weights.get(row["edge_type"], 0.0) / top
                reached.append((score, self._node_key(other), parent, other, row, row["node"]))
            next_frontier: list[_Found] = []
            # Most relevant first, so max_nodes keeps the best paths
            for score, key, _parent, other, row, props in sorted(
                reached, key=lambda item: (-item[0], item[1])
            ):
                existing = result.nodes.get(key)
                if existing is None:
                    if len(result.nodes) >= max_nodes:
                        result.truncated = True
                        continue
                    came_from_source = self._row_ends(row)[0] != other
                    existing = result.nodes[key] = _Found(
                        other,
                        props,
                        score,
                        level,
                        via=(row["edge_type"], "target" if came_from_source else "source"),
                        peer_step=other.label == _parent.ref.label,
                    )
                    next_frontier.append(existing)
                elif score > existing.score:
                    existing.score = score
                source, target = self._row_ends(row)
                edge_key = (self._node_key(source), self._node_key(target), row["edge_type"])
                result.edges[edge_key] = row["properties"]
            frontier = next_frontier

    @staticmethod
    def _drifts(parent: _Found, edge_type: str, parent_is_source: bool, far_label: str) -> bool:
        """Whether a step from ``parent`` leaves the question for its neighbourhood.

        - Siblings: leaving a reached node through the edge type it was
          entered by, in the same role, reaches its co-members (PR #7 ->
          release -> PR #8; sharing a release says nothing about #7's ticket).
        - Peers: a step to a node of the same type (a story's epic, a
          decision's predecessor) is taken only from a seed, or to continue
          a chain of such steps; from a node merely reached on the way, it
          widens the answer to that node's family (PR #7 -> PAY-341 -> epic).
        """
        role = "source" if parent_is_source else "target"
        if parent.via == (edge_type, role):
            return True
        return parent.depth > 0 and far_label == parent.ref.label and not parent.peer_step

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

    async def _superseded(self, result: _Result, found: Iterable[_Found]) -> set[str]:
        """Of ``found``, the nodes whose status says superseded, or that a node SUPERSEDES."""
        found = list(found)
        rows = await self._neighbors_all(
            [f.ref for f in found], [SUPERSEDES_EDGE], "in", result, mark_truncated=False
        )
        replaced = {self._node_key(self._row_ends(r)[1]) for r in rows}
        return replaced | {
            self._node_key(f.ref) for f in found if f.props.get("status") in SUPERSEDED_STATES
        }

    @staticmethod
    def _untrusted(props: dict[str, Any]) -> bool:
        return props.get("source_trust") == "untrusted"

    @staticmethod
    def _corroborates(properties: dict[str, Any]) -> bool:
        """A link a trusted source declared (edges from before edge trust count as trusted)."""
        return (
            properties.get("source_trust") != "untrusted"
            and properties.get("link_status", "confirmed") == "confirmed"
        )

    async def _admit(self, result: _Result, intent: str | None, include_untrusted: bool) -> None:
        rules = self._admission()
        superseded_rule = rules.get("superseded_or_reversed")
        if superseded_rule is not None:
            keep_for = set(superseded_rule.get("include_for_intents") or [])
            label = superseded_rule.get("label_as") or "superseded"
            superseded = await self._superseded(result, result.nodes.values())
            for key, found in list(result.nodes.items()):
                if key in superseded:
                    if intent in keep_for:
                        found.reason = label
                    else:
                        del result.nodes[key]
        if "untrusted_uncorroborated" in rules:
            trusted = {k for k, f in result.nodes.items() if not self._untrusted(f.props)}
            corroborated = {
                end
                for (source, target, _type), props in result.edges.items()
                if self._corroborates(props)
                for end, other in ((source, target), (target, source))
                if other in trusted
            }
            for key, found in list(result.nodes.items()):
                if not self._untrusted(found.props) or key in corroborated:
                    continue
                if include_untrusted:
                    found.reason = "untrusted"
                elif found.origin != "given":
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
        link = self._completeness_edge(subject, mentioned[1:], weights)
        if link is None:
            return {}
        edge_type, direction, related = link
        candidates = await self._completeness_scope(query, subject, edge_type, result, depth)

        # Admission: superseded and untrusted subjects are not reported
        superseded = await self._superseded(result, candidates)
        candidates = [
            c
            for c in candidates
            if self._node_key(c.ref) not in superseded
            and (query.include_untrusted or not self._untrusted(c.props))
        ]
        wanted = self._named_enum_values(query.query, related)
        rows = await self._neighbors_all(
            [c.ref for c in candidates], [edge_type], direction, result
        )
        status: dict[tuple[str, str], str] = {}
        candidate_keys = {(c.ref.label, c.ref.key) for c in candidates}
        for row in rows:
            source, target = self._row_ends(row)
            ends = [(source.label, source.key), (target.label, target.key)]
            for end, far in ((ends[0], ends[1]), (ends[1], ends[0])):
                if end not in candidate_keys or far == end:
                    continue
                if far[0] not in related:
                    continue
                link_status = row["properties"].get("link_status", "confirmed")
                if link_status == "rejected":
                    continue
                node = row["node"]
                if any(node.get(prop) not in values for prop, values in wanted.items()):
                    continue  # not the kind of item the question asks about
                confirmed = link_status == "confirmed" and not self._untrusted(node)
                if confirmed:
                    status[end] = "confirmed"
                else:
                    status.setdefault(end, "proposed_only")
        reports = dict.fromkeys(LINK_REPORTS, 0)
        result.nodes = {}
        result.edges = {}
        for candidate in candidates:
            report = status.get((candidate.ref.label, candidate.ref.key), "no_link")
            reports[report] += 1
            if report == "confirmed":
                continue
            if len(result.nodes) >= query.max_nodes:
                result.truncated = True
                continue
            candidate.reason = report
            result.nodes[self._node_key(candidate.ref)] = candidate
        return {f"completeness.{edge_type}.{k}": v for k, v in reports.items()}

    async def _completeness_scope(
        self, query: ArtifactQuery, subject: str, edge_type: str, result: _Result, depth: int
    ) -> list[_Found]:
        """The subject nodes the question is about."""
        seeds = list(result.nodes.values())
        of_subject = [f for f in seeds if f.ref.label == subject]
        others = [f for f in seeds if f.ref.label != subject]
        scope: dict[str, _Found] = {}
        if of_subject:
            # "under PAY-300": the seeds' descendants of the same type, else the seeds
            inner = [
                e
                for e in self._artifact_edges
                if e != edge_type and self._registry.allows(e, subject, subject)
            ]
            frontier = of_subject
            for _level in range(depth):
                rows = await self._neighbors_all([f.ref for f in frontier], inner, "out", result)
                frontier = []
                for row in rows:
                    child = self._ref(row["node_label"], row["node"])
                    key = self._node_key(child) if child else None
                    if child and child.label == subject and key not in scope:
                        scope[key] = _Found(child, row["node"], 1.0, _level + 1)  # type: ignore[index]
                        frontier.append(scope[key])  # type: ignore[index]
                if not frontier:
                    break
            if not scope:
                scope = {self._node_key(f.ref): f for f in of_subject}
        if others:
            # Subjects one artifact edge from the other seeds ("tickets shipped in #9")
            joins = [
                e
                for e in self._artifact_edges
                if e != edge_type
                and any(
                    self._registry.allows(e, f.ref.label, subject)
                    or self._registry.allows(e, subject, f.ref.label)
                    for f in others
                )
            ]
            rows = await self._neighbors_all([f.ref for f in others], joins, "both", result)
            for row in rows:
                node = self._ref(row["node_label"], row["node"])
                if node is not None and node.label == subject:
                    scope.setdefault(self._node_key(node), _Found(node, row["node"], 1.0, 1))
        if seeds:
            candidates = list(scope.values())
        else:
            candidates = await self._all_of(subject, query.query, result)
        return self._in_named_states(subject, query.query, candidates)

    async def _all_of(self, subject: str, text: str, result: _Result) -> list[_Found]:
        """Every node of the subject type (in the named states), up to the scan limit."""
        states = self._named_states(subject, text)
        filters: list[dict[str, Any]] = [{"status": s} for s in states] or [{}]
        found: list[_Found] = []
        for equals in filters:
            if not self._spend(result):
                break
            rows = await self._graph.find_nodes(subject, equals, self._scan_limit)
            if len(rows) >= self._scan_limit:
                result.truncated = True
            found += [
                _Found(ref, props, 1.0, 0) for props in rows if (ref := self._ref(subject, props))
            ]
        return found

    def _named_states(self, subject: str, text: str) -> list[str]:
        lifecycle = self._registry.node_type(subject).lifecycle
        if lifecycle is None:
            return []
        lowered = text.lower()
        return [
            state
            for state in lifecycle.states
            if re.search(r"\b" + re.escape(state.replace("_", " ")) + r"\b", lowered)
        ]

    def _in_named_states(self, subject: str, text: str, found: list[_Found]) -> list[_Found]:
        """States the question names ("merged changes") narrow the subjects."""
        states = self._named_states(subject, text)
        return [f for f in found if f.props.get("status") in states] if states else found

    def _named_enum_values(self, text: str, related: set[str]) -> dict[str, set[str]]:
        """Enum values of the related types the question names ("approving" -> approved)."""
        stems = {_stem(w) for w in _WORD.findall(text.lower())}
        wanted: dict[str, set[str]] = {}
        for type_name in related:
            for prop, spec in self._registry.node_type(type_name).properties.items():
                if not isinstance(spec, EnumSpec):
                    continue
                named = {value for value in spec.enum if _stem(value.lower()) in stems}
                if named:
                    wanted.setdefault(prop, set()).update(named)
        return wanted

    def _completeness_edge(
        self, subject: str, related: list[str], weights: dict[str, float]
    ) -> tuple[str, Direction, set[str]] | None:
        """The strongest weighted edge joining the subject type to a related type.

        Returns the edge, the direction to read it from the subject (both
        when the edge allows either), and the types at its other end.
        """
        options: list[tuple[float, int, str, Direction, set[str]]] = []
        for edge_type, weight in weights.items():
            edge = self._registry.edge_type(edge_type)
            candidates = related or sorted(edge.from_types | edge.to_types)
            for rank, other in enumerate(candidates):
                inbound = self._registry.allows(edge_type, other, subject)
                outbound = self._registry.allows(edge_type, subject, other)
                if not (inbound or outbound):
                    continue
                direction: Direction = (
                    "both" if inbound and outbound else ("in" if inbound else "out")
                )
                ends = {
                    t
                    for t in (related or self._registry.node_types)
                    if self._registry.allows(edge_type, t, subject)
                    or self._registry.allows(edge_type, subject, t)
                }
                options.append((weight, -rank if related else 0, edge_type, direction, ends))
                break
        if not options:
            return None
        _weight, _rank, edge_type, direction, ends = max(options, key=lambda o: (o[0], o[1], o[2]))
        return edge_type, direction, ends

    # -- output --------------------------------------------------------------------------------

    async def _attach_provenance(self, result: _Result) -> None:
        refs = [f.ref for f in result.nodes.values()]
        if not refs:
            return
        rows = await self._neighbors_all(
            refs, [PROVENANCE_EDGE], "out", result, mark_truncated=False
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
            if found.ref.label == "Event":
                newest.setdefault((found.ref.label, found.ref.key), found.props)
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
