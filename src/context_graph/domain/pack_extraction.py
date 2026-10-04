"""Extraction profiles generated from ontology packs (ADR-0018 decision 4, phase 3).

A pack's ``extraction`` section says which events carry prose worth
reading (``sources``), which node and edge types an LLM may propose
(``propose``, with descriptions and confidence ceilings) and which it must
never create (``never_propose``). ``ExtractionProfile`` turns that into:

- ``prompt(text, known)``: instructions listing only the proposable types,
  their fields, synonyms and allowed link endpoints, the items the text may
  link to, the output schema, and the text;
- ``output_schema()``: a JSON Schema that accepts only those types;
- ``plan(raw, event, trusted)``: the LLM's answer checked against the
  registry and turned into a ``ProjectionPlan`` the projection worker's
  ``apply_plan`` writes.

What extraction may write is narrower than what projection may write:

- nodes only of proposed types, identified by their key (a ``content_hash``
  key is the SHA-256 of the type's first text field, as the pack's
  projection rules compute it, so an extracted decision and the same
  decision recorded by a tool are one node);
- a proposed node starts in its lifecycle's initial state and carries
  ``confidence`` (capped at the pack's ``max_confidence``) and ``method``
  when its type is a Claim; extraction never moves a lifecycle state;
- links only of proposed edge types, between nodes proposed from the same
  text or known items (the ids the prompt listed), and only between types
  the edge allows; ``link_status`` is the pack's (``proposed`` by default) and never
  ``confirmed``;
- ``source_trust`` comes from the event's source, never from the text;
- every proposed node gets a ``DERIVED_FROM`` edge to the source event.

Anything else in the answer is dropped and reported in ``rejected``.

Pure Python; no framework or storage imports.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from context_graph.domain.ontology import EnumSpec
from context_graph.domain.pack_projection import (
    PROVENANCE_EDGE,
    ProjectionPlan,
    coerce,
    make_node_id,
    parse_node_id,
)
from context_graph.ports.pack_graph import EdgeWrite, NodeWrite
from context_graph.ports.pack_graph import NodeRef as GraphRef

if TYPE_CHECKING:
    from context_graph.domain.models import Event
    from context_graph.domain.ontology import (
        EdgeType,
        NodeType,
        OntologyRegistry,
        Pack,
        PropertySpec,
        ProposeDef,
    )

# Properties the system sets; a proposal never supplies them
SYSTEM_PROPERTIES = frozenset(
    {
        "node_id",
        "node_type",
        "ontology_version",
        "updated_at",
        "status",
        "status_changed_at",
        "source_trust",
        "source_uri",
        "content_hash",
        "anchor_path",
        "confidence",
        "method",
        "link_status",
        "support_count",
        "version",
    }
)
CONTENT_HASH = "content_hash"
DEFAULT_NODE_METHOD = "extracted"
DEFAULT_LINK_METHOD = "inferred"
DEFAULT_LINK_STATUS = "proposed"
# Statuses extraction may give a link: never ``confirmed``
PROPOSABLE_LINK_STATUSES = frozenset({"proposed"})
LOCAL_REF = re.compile(r"^n[0-9]{1,4}$")
JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


class ExtractionAnswerError(ValueError):
    """The LLM's answer is not a JSON object."""


@dataclass(frozen=True)
class ProposableNode:
    node_type: NodeType
    proposal: ProposeDef
    # Fields the LLM fills in, with their types
    fields: dict[str, PropertySpec]
    # The field whose hash is the key, for content-addressed types
    hashed_field: str | None


@dataclass(frozen=True)
class ProposableEdge:
    edge_type: EdgeType
    proposal: ProposeDef
    fields: dict[str, PropertySpec]


@dataclass(frozen=True)
class KnownItem:
    """An existing node the text may link to, shown to the LLM by id."""

    node_id: str
    node_type: str
    label: str


@dataclass
class ExtractionResult:
    plan: ProjectionPlan = field(default_factory=ProjectionPlan)
    accepted_nodes: int = 0
    accepted_links: int = 0
    rejected: list[str] = field(default_factory=list)


def _spec_text(spec: PropertySpec) -> str:
    if isinstance(spec, EnumSpec):
        return "one of " + ", ".join(spec.enum)
    return spec


def _json_type(spec: PropertySpec) -> dict[str, Any]:
    if isinstance(spec, EnumSpec):
        return {"type": "string", "enum": list(spec.enum)}
    if spec.startswith("list<"):
        return {"type": "array", "items": _json_type(spec[5:-1])}
    return {
        "int": {"type": "integer"},
        "float": {"type": "number"},
        "bool": {"type": "boolean"},
        "datetime": {"type": "string", "format": "date-time"},
        "json": {},
    }.get(spec, {"type": "string"})


def content_hash(text: str) -> str:
    """The key of a content-addressed node, as ``sha256(...)`` in a projection rule."""
    return hashlib.sha256(text.encode()).hexdigest()


def parse_answer(text: str) -> Any:
    """The JSON object in an LLM answer (bare, or inside a fenced block)."""
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except ValueError:
        pass
    match = JSON_BLOCK.search(stripped)
    if match is None:
        raise ExtractionAnswerError("no JSON object in the answer")
    try:
        return json.loads(match.group(0))
    except ValueError as exc:
        raise ExtractionAnswerError(f"invalid JSON in the answer: {exc}") from exc


class ExtractionProfile:
    """What one pack lets an LLM extract, as a prompt, a schema and a validator."""

    def __init__(
        self,
        registry: OntologyRegistry,
        pack: Pack,
        *,
        max_nodes: int,
        max_links: int,
        max_text_chars: int,
    ) -> None:
        self._registry = registry
        self._pack = pack
        self.max_nodes = max_nodes
        self.max_links = max_links
        self.max_text_chars = max_text_chars
        extraction = pack.extraction
        self.sources = frozenset(source.rpartition(":")[2] for source in extraction.sources)
        self.never_propose = frozenset(extraction.never_propose)
        self.nodes: dict[str, ProposableNode] = {}
        self.edges: dict[str, ProposableEdge] = {}
        for name, proposal in extraction.propose.items():
            if name in registry.node_types:
                self.nodes[name] = self._proposable_node(registry.node_types[name], proposal)
            elif name in registry.edge_types:
                edge = registry.edge_types[name]
                fields = {n: s for n, s in edge.properties.items() if n not in SYSTEM_PROPERTIES}
                self.edges[name] = ProposableEdge(edge, proposal, fields)
        synonyms = pack.mappings.get("synonyms", {})
        self._synonyms: dict[str, list[str]] = {
            str(name): [str(s) for s in values]
            for name, values in synonyms.items()
            if isinstance(values, list)
        }

    @staticmethod
    def _proposable_node(node_type: NodeType, proposal: ProposeDef) -> ProposableNode:
        fields = {
            name: spec
            for name, spec in node_type.properties.items()
            if name not in SYSTEM_PROPERTIES
        }
        hashed = None
        if node_type.key == [CONTENT_HASH]:
            text_fields = [f for f in node_type.definition.text_fields if f in fields]
            hashed = text_fields[0] if text_fields else None
        return ProposableNode(node_type, proposal, fields, hashed)

    @property
    def pack_name(self) -> str:
        return self._pack.name

    def handles(self, event_type: str) -> bool:
        return event_type in self.sources and bool(self.nodes or self.edges)

    def required_fields(self, node: ProposableNode) -> list[str]:
        """Fields a proposal must fill: the hashed field, or the key fields."""
        if node.hashed_field is not None:
            return [node.hashed_field]
        return [name for name in node.node_type.key if name in node.fields]

    def link_targets(self) -> dict[str, set[str]]:
        """Proposable edge type → the node types it may end at."""
        return {
            name: {
                t
                for t in self._registry.node_types
                if any(self._registry.allows(name, s, t) for s in self._registry.node_types)
            }
            for name in self.edges
        }

    # -- prompt and schema -----------------------------------------------------------

    def output_schema(self) -> dict[str, Any]:
        """JSON Schema of the answer: only the proposable types and their fields."""
        node_variants = []
        for name, node in sorted(self.nodes.items()):
            properties: dict[str, Any] = {
                "ref": {"type": "string", "pattern": LOCAL_REF.pattern},
                "type": {"const": name},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "evidence": {"type": "string"},
            }
            properties.update({f: _json_type(s) for f, s in sorted(node.fields.items())})
            node_variants.append(
                {
                    "type": "object",
                    "properties": properties,
                    "required": ["ref", "type", "confidence", *self.required_fields(node)],
                    "additionalProperties": False,
                }
            )
        link_variants = []
        for name, edge in sorted(self.edges.items()):
            properties = {
                "type": {"const": name},
                "from": {"type": "string"},
                "to": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "evidence": {"type": "string"},
            }
            properties.update({f: _json_type(s) for f, s in sorted(edge.fields.items())})
            link_variants.append(
                {
                    "type": "object",
                    "properties": properties,
                    "required": ["type", "from", "to", "confidence"],
                    "additionalProperties": False,
                }
            )
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": f"{self._pack.name} extraction",
            "type": "object",
            "properties": {
                "nodes": {
                    "type": "array",
                    "maxItems": self.max_nodes,
                    "items": {"oneOf": node_variants} if node_variants else False,
                },
                "links": {
                    "type": "array",
                    "maxItems": self.max_links,
                    "items": {"oneOf": link_variants} if link_variants else False,
                },
            },
            "required": ["nodes", "links"],
            "additionalProperties": False,
        }

    def prompt(self, text: str, known: list[KnownItem]) -> str:
        lines = [
            f"You extract {self._pack.name} knowledge from the text at the end.",
            "Propose only what the text states or clearly implies. Do not invent items.",
            "",
            "Node types you may propose:",
        ]
        for name, node in sorted(self.nodes.items()):
            fields = ", ".join(
                f"{f} ({_spec_text(s)}{', required' if f in self.required_fields(node) else ''})"
                for f, s in sorted(node.fields.items())
            )
            lines.append(f"- {name}: {node.proposal.description}")
            lines.append(f"  fields: {fields}")
            if self._synonyms.get(name):
                lines.append(f"  also called: {', '.join(self._synonyms[name])}")
            if node.proposal.max_confidence is not None:
                lines.append(f"  confidence at most {node.proposal.max_confidence}")
        if self.edges:
            lines += ["", "Links you may propose:"]
            for name, edge in sorted(self.edges.items()):
                sources = sorted(edge.edge_type.from_types)
                targets = sorted(edge.edge_type.to_types)
                lines.append(f"- {name}: {edge.proposal.description}")
                lines.append(f"  from {' or '.join(sources)} to {' or '.join(targets)}")
                if edge.fields:
                    fields = ", ".join(
                        f"{f} ({_spec_text(s)})" for f, s in sorted(edge.fields.items())
                    )
                    lines.append(f"  fields: {fields}")
                if edge.proposal.scoring_question:
                    lines.append(f"  ask yourself: {edge.proposal.scoring_question}")
        if self.never_propose:
            lines += [
                "",
                "Never create items of these types (link to them only by a known id): "
                + ", ".join(sorted(self.never_propose)),
            ]
        lines += [
            "",
            "Give each node you propose a ref n1, n2, ... A link's from and to are refs of "
            "nodes you propose or ids of the known items below, exactly as written.",
            "Confidence is between 0 and 1. Evidence is a short quote from the text.",
            "",
            "Known items:",
        ]
        if known:
            lines += [f"- {item.node_id} ({item.node_type}): {item.label}" for item in known]
        else:
            lines.append("- none")
        lines += [
            "",
            "Answer with one JSON object matching this schema, and nothing else:",
            json.dumps(self.output_schema(), sort_keys=True),
            "",
            "Text:",
            "<<<",
            text[: self.max_text_chars],
            ">>>",
        ]
        return "\n".join(lines)

    # -- validation ------------------------------------------------------------------

    def plan(
        self, raw: Any, event: Event, *, trusted: bool, known: list[KnownItem]
    ) -> ExtractionResult:
        """Check an answer against the profile; plan the writes that pass."""
        result = ExtractionResult()
        if not isinstance(raw, dict):
            result.rejected.append("answer is not a JSON object")
            return result
        event_ref = GraphRef("Event", str(event.event_id), "event_id")
        changed_at = str(event.occurred_at.isoformat()) if event.occurred_at else ""
        trust = "trusted" if trusted else "untrusted"
        local: dict[str, tuple[str, GraphRef]] = {}

        nodes = raw.get("nodes", [])
        if not isinstance(nodes, list):
            result.rejected.append("nodes is not a list")
            nodes = []
        for index, item in enumerate(nodes):
            if result.accepted_nodes >= self.max_nodes:
                result.rejected.append(f"nodes[{index}]: over the limit of {self.max_nodes}")
                continue
            planned = self._plan_node(item, index, event_ref, changed_at, trust, result)
            if planned is not None:
                ref_name, type_name, graph_ref = planned
                local[ref_name] = (type_name, graph_ref)

        known_ids = {item.node_id: item.node_type for item in known}
        links = raw.get("links", [])
        if not isinstance(links, list):
            result.rejected.append("links is not a list")
            links = []
        for index, item in enumerate(links):
            if result.accepted_links >= self.max_links:
                result.rejected.append(f"links[{index}]: over the limit of {self.max_links}")
                continue
            self._plan_link(item, index, local, known_ids, trust, result)
        return result

    def _plan_node(
        self,
        item: Any,
        index: int,
        event_ref: GraphRef,
        changed_at: str,
        trust: str,
        result: ExtractionResult,
    ) -> tuple[str, str, GraphRef] | None:
        where = f"nodes[{index}]"
        if not isinstance(item, dict):
            result.rejected.append(f"{where}: not an object")
            return None
        type_name = item.get("type")
        node = self.nodes.get(type_name) if isinstance(type_name, str) else None
        if node is None:
            result.rejected.append(f"{where}: type {type_name!r} may not be proposed")
            return None
        ref_name = item.get("ref")
        if not isinstance(ref_name, str) or not LOCAL_REF.match(ref_name):
            result.rejected.append(f"{where}: ref must look like n1")
            return None
        confidence = self._confidence(item.get("confidence"), node.proposal)
        if confidence is None:
            result.rejected.append(f"{where}: confidence must be a number from 0 to 1")
            return None
        values: dict[str, Any] = {}
        for name, spec in node.fields.items():
            value = coerce(item.get(name), spec)
            if value is not None and value != "":
                values[name] = value
        missing = [f for f in self.required_fields(node) if f not in values]
        if missing:
            result.rejected.append(f"{where}: missing {', '.join(missing)}")
            return None
        node_type = node.node_type
        if node.hashed_field is not None:
            key_props = {CONTENT_HASH: content_hash(str(values[node.hashed_field]))}
        else:
            key_props = {name: values[name] for name in node_type.key}
        graph_ref = GraphRef(node_type.name, make_node_id(node_type.name, list(key_props.values())))
        # Everything but identity is a create-time default: a proposal never
        # overwrites a node that exists (one a tool recorded, or an earlier proposal)
        defaults: dict[str, Any] = {
            **values,
            "ontology_version": self._registry.version,
            "updated_at": changed_at,
        }
        if "confidence" in node_type.properties:
            defaults["confidence"] = confidence
        if "method" in node_type.properties:
            defaults["method"] = node.proposal.method or DEFAULT_NODE_METHOD
        if "source_trust" in node_type.properties:
            defaults["source_trust"] = trust
        if node_type.lifecycle is not None:
            defaults["status"] = node_type.lifecycle.initial
            defaults["status_changed_at"] = changed_at
        props = {**key_props, "node_type": node_type.name}
        result.plan.nodes.append(NodeWrite(graph_ref, props, defaults))
        if self._registry.allows(PROVENANCE_EDGE, node_type.name, "Event"):
            result.plan.edges.append(EdgeWrite(PROVENANCE_EDGE, graph_ref, event_ref))
        result.accepted_nodes += 1
        return ref_name, node_type.name, graph_ref

    def _plan_link(
        self,
        item: Any,
        index: int,
        local: dict[str, tuple[str, GraphRef]],
        known_ids: dict[str, str],
        trust: str,
        result: ExtractionResult,
    ) -> None:
        where = f"links[{index}]"
        if not isinstance(item, dict):
            result.rejected.append(f"{where}: not an object")
            return
        type_name = item.get("type")
        edge = self.edges.get(type_name) if isinstance(type_name, str) else None
        if edge is None:
            result.rejected.append(f"{where}: link type {type_name!r} may not be proposed")
            return
        ends = []
        for side in ("from", "to"):
            end = self._endpoint(item.get(side), local, known_ids)
            if end is None:
                result.rejected.append(
                    f"{where}: {side} {item.get(side)!r} is not a proposed ref or known id"
                )
                return
            ends.append(end)
        (source_type, source), (target_type, target) = ends
        if not self._registry.allows(edge.edge_type.name, source_type, target_type):
            result.rejected.append(
                f"{where}: {edge.edge_type.name} may not link {source_type} to {target_type}"
            )
            return
        confidence = self._confidence(item.get("confidence"), edge.proposal)
        if confidence is None:
            result.rejected.append(f"{where}: confidence must be a number from 0 to 1")
            return
        props: dict[str, Any] = {}
        for name, spec in edge.fields.items():
            value = coerce(item.get(name), spec)
            if value is not None and value != "":
                props[name] = value
        if "confidence" in edge.edge_type.properties:
            props["confidence"] = confidence
        if "method" in edge.edge_type.properties:
            props["method"] = edge.proposal.method or DEFAULT_LINK_METHOD
        if "link_status" in edge.edge_type.properties:
            status = edge.proposal.link_status or DEFAULT_LINK_STATUS
            props["link_status"] = (
                status if status in PROPOSABLE_LINK_STATUSES else DEFAULT_LINK_STATUS
            )
        props["source_trust"] = trust
        result.plan.edges.append(EdgeWrite(edge.edge_type.name, source, target, props))
        result.accepted_links += 1

    def _endpoint(
        self,
        value: Any,
        local: dict[str, tuple[str, GraphRef]],
        known_ids: dict[str, str],
    ) -> tuple[str, GraphRef] | None:
        if not isinstance(value, str):
            return None
        if value in local:
            return local[value]
        if value not in known_ids:
            return None
        return parse_node_id(self._registry, value)

    @staticmethod
    def _confidence(value: Any, proposal: ProposeDef) -> float | None:
        if isinstance(value, bool) or not isinstance(value, int | float):
            return None
        if not 0.0 <= float(value) <= 1.0:
            return None
        ceiling = proposal.max_confidence if proposal.max_confidence is not None else 1.0
        return min(float(value), ceiling)


def extraction_profiles(
    registry: OntologyRegistry, *, max_nodes: int, max_links: int, max_text_chars: int
) -> list[ExtractionProfile]:
    """One profile per active pack that declares something to extract."""
    return [
        ExtractionProfile(
            registry,
            pack,
            max_nodes=max_nodes,
            max_links=max_links,
            max_text_chars=max_text_chars,
        )
        for pack in registry.packs
        if pack.extraction.sources and pack.extraction.propose
    ]


def event_text(document: dict[str, Any], max_chars: int) -> str:
    """The prose of an event's payload: its text values, labelled by field, in order."""
    payload = document.get("payload")
    if not isinstance(payload, dict):
        return ""
    parts: list[str] = []
    total = 0
    for name, value in payload.items():
        if not isinstance(value, str) or not value.strip():
            continue
        part = f"{name}: {value.strip()}"
        parts.append(part)
        total += len(part)
        if total >= max_chars:
            break
    return "\n".join(parts)[:max_chars]
