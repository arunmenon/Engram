"""Ontology packs and the registry that composes them (ADR-0018).

A pack is a versioned, declarative description of part of the graph:
node and edge types, the events it owns, deterministic projection rules,
what LLM extraction may propose, retrieval intents and weights, lifecycle
rules and vocabulary mappings. ``OntologyRegistry`` composes the active
packs (always ``core``), validates them as a whole and answers lookups.

Today's schema is written as the ``core``, ``memory`` and ``user`` packs
(``context_graph/ontology/packs``); the enums in ``domain/models.py``
remain and must equal what those packs declare.

Type references inside a pack are bare (``Change``) for the pack's own
types and qualified (``core:Entity``) for another pack's; ``*`` means any
type. Event references follow the same rule (``core:observation.input``).

Pure Python: no framework, storage or file-format imports. Loading packs
from files lives in ``context_graph.ontology``.

Source: ADR-0018, docs/research/2026-10/ontology/pdlc-ontology-and-ontology-packs.md
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

WILDCARD = "*"

SCALAR_TYPES = frozenset({"string", "text", "int", "float", "bool", "datetime", "json"})

# Fields every edge listed in a pack's link policy (or an edge's ``requires``) may carry
LINK_FIELDS: dict[str, Any] = {
    "confidence": "float",
    "method": "string",
    "link_status": {"enum": ["proposed", "confirmed", "rejected"]},
}

_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
_REQUIREMENT = re.compile(r"^([a-z][a-z0-9_]*)\s*(?:(>=|<=|==|>|<)\s*(\d+(?:\.\d+){0,2}))?$")
_LIST_TYPE = re.compile(r"^list<(\w+)>$")

# Names that reach backend query text (labels, relationship types, property
# keys) are restricted to these shapes, so they can never inject anything.
NODE_TYPE_NAME = re.compile(r"^[A-Z][A-Za-z0-9]*$")
EDGE_TYPE_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
PROPERTY_NAME = re.compile(r"^[a-z_][a-z0-9_]*$")


class OntologyError(ValueError):
    """A pack, or the composition of packs, is invalid. Lists every problem found."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("Invalid ontology:\n  - " + "\n  - ".join(problems))


def _version_tuple(text: str) -> tuple[int, ...]:
    parts = [int(part) for part in text.split(".")]
    return tuple(parts + [0] * (3 - len(parts)))


# ---------------------------------------------------------------------------
# Pack format (the meta-model)
# ---------------------------------------------------------------------------


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class EnumSpec(_Strict):
    enum: list[str]


PropertySpec = str | EnumSpec


def _check_property_spec(spec: PropertySpec) -> str | None:
    if isinstance(spec, EnumSpec):
        return None if spec.enum else "empty enum"
    match = _LIST_TYPE.match(spec)
    base = match.group(1) if match else spec
    return None if base in SCALAR_TYPES else f"unknown property type {spec!r}"


class PackHeader(_Strict):
    name: str
    version: str
    requires: list[str] = Field(default_factory=list)
    owner: str | None = None
    description: str = ""

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        if not _NAME.match(value):
            msg = f"pack name {value!r} must be lowercase letters, digits and underscores"
            raise ValueError(msg)
        return value

    @field_validator("version")
    @classmethod
    def _version(cls, value: str) -> str:
        if not _SEMVER.match(value):
            msg = f"pack version {value!r} must be MAJOR.MINOR.PATCH"
            raise ValueError(msg)
        return value

    @field_validator("requires")
    @classmethod
    def _requires(cls, value: list[str]) -> list[str]:
        for requirement in value:
            if not _REQUIREMENT.match(requirement):
                msg = f"requirement {requirement!r} must look like 'core>=1.0'"
                raise ValueError(msg)
        return value


class InterfaceDef(_Strict):
    properties: dict[str, PropertySpec] = Field(default_factory=dict)
    edges: list[str] = Field(default_factory=list)
    note: str | None = None


class LifecycleDef(_Strict):
    initial: str
    states: list[str]

    @model_validator(mode="after")
    def _initial_is_a_state(self) -> LifecycleDef:
        if self.initial not in self.states:
            msg = f"initial state {self.initial!r} is not one of {self.states}"
            raise ValueError(msg)
        return self


class NodeTypeDef(_Strict):
    key: list[str]
    # Existing types keep their own unique property (``event_id``); types
    # without one are identified by ``node_id`` = ``<type>:<key values>``
    id_property: str | None = None
    interfaces: list[str] = Field(default_factory=list)
    properties: dict[str, PropertySpec] = Field(default_factory=dict)
    lifecycle: LifecycleDef | None = None
    text_fields: list[str] = Field(default_factory=list)
    embed_fields: list[str] = Field(default_factory=list)
    indexes: list[str] = Field(default_factory=list)
    vector_property: str | None = None
    note: str | None = None


class EdgeTypeDef(_Strict):
    from_: list[str] | Literal["*"] = Field(alias="from")
    to: list[str] | Literal["*"]
    properties: dict[str, PropertySpec] = Field(default_factory=dict)
    requires: list[str] = Field(default_factory=list)
    note: str | None = None


class EdgeExtensionDef(_Strict):
    """Endpoint additions to an edge type another pack declares."""

    from_: list[str] | Literal["*"] = Field(alias="from")
    to: list[str] | Literal["*"]
    note: str | None = None


class LinkPolicyDef(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    applies_to: list[str] = Field(default_factory=list)


class TypesSection(_Strict):
    nodes: dict[str, NodeTypeDef] = Field(default_factory=dict)
    edges: dict[str, EdgeTypeDef] = Field(default_factory=dict)
    link_policy: LinkPolicyDef | None = None
    extends_core_edges: dict[str, EdgeExtensionDef] = Field(default_factory=dict)


class EventDef(_Strict):
    aliases: dict[str, str] = Field(default_factory=dict)
    note: str | None = None


# -- projection rules ---------------------------------------------------------

# A value in a rule: a constant, or an expression string ($.x, $event.x, fn(...))
RuleValue = str | int | float | bool


class NodeRef(_Strict):
    type: str | None = None
    key: dict[str, RuleValue] | None = None
    node_id: str | None = None
    match: dict[str, RuleValue] | None = None
    match_any_prefix: dict[str, RuleValue] | None = None

    @model_validator(mode="after")
    def _one_way_to_find_a_node(self) -> NodeRef:
        if self.node_id is not None:
            if self.type or self.key or self.match or self.match_any_prefix:
                msg = "a node_id reference takes nothing else"
                raise ValueError(msg)
            return self
        if self.type is None:
            msg = "a node reference needs a type or a node_id"
            raise ValueError(msg)
        return self


class UpsertDef(_Strict):
    type: str
    key: dict[str, RuleValue]
    set: dict[str, RuleValue] = Field(default_factory=dict)


class TransitionDef(_Strict):
    type: str
    to: str
    only_from: list[str] = Field(default_factory=list)


class EdgeRuleDef(_Strict):
    type: str
    from_: NodeRef = Field(alias="from")
    to: NodeRef | None = None
    to_each: NodeRef | None = None
    to_latest: NodeRef | None = None
    set: dict[str, RuleValue] = Field(default_factory=dict)
    when: str | None = None

    @model_validator(mode="after")
    def _one_target(self) -> EdgeRuleDef:
        targets = [t for t in (self.to, self.to_each, self.to_latest) if t is not None]
        if len(targets) != 1:
            msg = "an edge rule needs exactly one of to, to_each, to_latest"
            raise ValueError(msg)
        return self

    @property
    def target(self) -> NodeRef:
        target = self.to or self.to_each or self.to_latest
        assert target is not None
        return target


class ProjectionRule(_Strict):
    event: str
    upsert: list[UpsertDef] = Field(default_factory=list)
    transition: TransitionDef | None = None
    edges: list[EdgeRuleDef] = Field(default_factory=list)


# -- extraction, retrieval, lifecycle ---------------------------------------------


class ProposeDef(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    description: str
    max_confidence: float | None = None
    method: str | None = None
    link_status: str | None = None
    scoring_question: str | None = None


class ExtractionSection(_Strict):
    sources: list[str] = Field(default_factory=list)
    propose: dict[str, ProposeDef] = Field(default_factory=dict)
    never_propose: list[str] = Field(default_factory=list)
    derived_proposals: dict[str, dict[str, Any]] = Field(default_factory=dict)


class IntentDef(_Strict):
    description: str = ""
    examples: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    weights: dict[str, float] = Field(default_factory=dict)
    seed_strategy: str | None = None
    max_depth: int | None = None
    plugin: str | None = None
    prefer_types: list[str] = Field(default_factory=list)
    direction: Literal["outbound", "inbound", "both"] = "both"


class RetrievalSection(_Strict):
    seed_types: list[str] = Field(default_factory=list)
    intents: dict[str, IntentDef] = Field(default_factory=dict)
    admission: dict[str, dict[str, Any]] = Field(default_factory=dict)
    # Weights this pack adds to intents another pack declares
    core_intent_weights: dict[str, dict[str, float]] = Field(default_factory=dict)
    # Intent used when no keyword matches
    fallback_intent: str | None = None


class DecayDef(_Strict):
    class_: Literal["pinned", "slow", "medium", "fast"] = Field(alias="class")
    compressible: bool = True
    retain_days: int | None = None


class LifecycleSection(_Strict):
    decay: dict[str, DecayDef] = Field(default_factory=dict)
    terminal_states_reduce_importance: list[str] = Field(default_factory=list)


class Pack(_Strict):
    pack: PackHeader
    interfaces: dict[str, InterfaceDef] = Field(default_factory=dict)
    types: TypesSection = Field(default_factory=TypesSection)
    events: dict[str, EventDef] = Field(default_factory=dict)
    projection: list[ProjectionRule] = Field(default_factory=list)
    extraction: ExtractionSection = Field(default_factory=ExtractionSection)
    retrieval: RetrievalSection = Field(default_factory=RetrievalSection)
    lifecycle: LifecycleSection = Field(default_factory=LifecycleSection)
    mappings: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.pack.name

    @property
    def version(self) -> str:
        return self.pack.version

    def canonical_json(self) -> str:
        """Stable serialisation used for the ontology version hash."""
        return json.dumps(
            self.model_dump(mode="json", by_alias=True, exclude_none=True),
            sort_keys=True,
            separators=(",", ":"),
        )


# ---------------------------------------------------------------------------
# Composed view
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NodeType:
    name: str
    pack: str
    definition: NodeTypeDef
    # Own properties plus those of its interfaces
    properties: dict[str, PropertySpec]

    @property
    def interfaces(self) -> list[str]:
        return self.definition.interfaces

    @property
    def key(self) -> list[str]:
        return self.definition.key

    @property
    def lifecycle(self) -> LifecycleDef | None:
        return self.definition.lifecycle


@dataclass
class EdgeType:
    name: str
    pack: str
    definition: EdgeTypeDef
    from_types: set[str] = field(default_factory=set)
    to_types: set[str] = field(default_factory=set)
    from_any: bool = False
    to_any: bool = False
    # Own properties plus link fields when the edge requires them
    properties: dict[str, PropertySpec] = field(default_factory=dict)

    def allows(self, source_type: str, target_type: str) -> bool:
        return (self.from_any or source_type in self.from_types) and (
            self.to_any or target_type in self.to_types
        )


@dataclass
class Intent:
    name: str
    pack: str
    definition: IntentDef
    weights: dict[str, float] = field(default_factory=dict)

    @property
    def keywords(self) -> list[str]:
        return self.definition.keywords

    @property
    def seed_strategy(self) -> str | None:
        return self.definition.seed_strategy


@dataclass(frozen=True)
class EventTypeDecl:
    name: str
    pack: str
    definition: EventDef


class OntologyRegistry:
    """The composed, validated ontology of the active packs."""

    def __init__(self, packs: list[Pack]) -> None:
        names = [pack.name for pack in packs]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise OntologyError([f"pack {name!r} is loaded more than once" for name in duplicates])
        self._packs: dict[str, Pack] = {pack.name: pack for pack in packs}
        self.node_types: dict[str, NodeType] = {}
        self.edge_types: dict[str, EdgeType] = {}
        self.event_types: dict[str, EventTypeDecl] = {}
        self.intents: dict[str, Intent] = {}
        self.interfaces: dict[str, tuple[str, InterfaceDef]] = {}
        self.projection_rules: dict[str, list[tuple[str, ProjectionRule]]] = {}
        self.fallback_intent: str | None = None
        problems: list[str] = []
        self._compose(problems)
        # Validate even after composition problems, so every problem is reported at once
        self._validate(problems)
        if problems:
            raise OntologyError(problems)
        self.version = self._version_hash()

    # -- lookups ---------------------------------------------------------------

    @property
    def packs(self) -> list[Pack]:
        return list(self._packs.values())

    def pack(self, name: str) -> Pack:
        return self._packs[name]

    def node_type(self, name: str) -> NodeType:
        return self.node_types[name]

    def edge_type(self, name: str) -> EdgeType:
        return self.edge_types[name]

    def rules_for(self, event_type: str) -> list[tuple[str, ProjectionRule]]:
        """Projection rules triggered by an event type, with their pack names."""
        return self.projection_rules.get(event_type, [])

    def intent_weights(self) -> dict[str, dict[str, float]]:
        """Intent → edge type → weight, every pack's contributions merged."""
        return {name: dict(intent.weights) for name, intent in self.intents.items()}

    def intent_keywords(self) -> dict[str, list[str]]:
        return {name: list(i.keywords) for name, i in self.intents.items() if i.keywords}

    def seed_strategies(self) -> dict[str, str]:
        return {
            name: intent.seed_strategy
            for name, intent in self.intents.items()
            if intent.seed_strategy
        }

    def summary(self) -> dict[str, Any]:
        """Packs, versions and counts (for ``GET /v1/ontology`` and logs)."""
        return {
            "version": self.version,
            "packs": [
                {"name": p.name, "version": p.version, "owner": p.pack.owner} for p in self.packs
            ],
            "node_types": len(self.node_types),
            "edge_types": len(self.edge_types),
            "event_types": len(self.event_types),
            "intents": sorted(self.intents),
        }

    # -- composition ---------------------------------------------------------------

    def _resolve_type(self, pack: str, ref: str, problems: list[str], where: str) -> str | None:
        """A type reference as the composed (global) type name, or None if unknown."""
        owner, _, name = ref.rpartition(":")
        owner = owner or pack
        node = self.node_types.get(name)
        if node is None or node.pack != owner:
            problems.append(f"{pack}: {where} refers to unknown type {ref!r}")
            return None
        return name

    def _resolve_event(self, pack: str, ref: str) -> str | None:
        owner, _, name = ref.rpartition(":") if ":" in ref else ("", "", ref)
        declared = self.event_types.get(name)
        if declared is None or (owner and declared.pack != owner):
            return None
        return name

    def _compose(self, problems: list[str]) -> None:
        packs = self.packs
        if "core" not in self._packs:
            problems.append("the core pack must be active")
        for pack in packs:
            for requirement in pack.pack.requires:
                match = _REQUIREMENT.match(requirement)
                assert match is not None
                required, operator, version = match.groups()
                other = self._packs.get(required)
                if other is None:
                    problems.append(f"{pack.name} requires pack {required!r}, which is not active")
                    continue
                if operator and not _compare(other.version, operator, version):
                    problems.append(
                        f"{pack.name} requires {requirement}; {required} is {other.version}"
                    )

        # Declarations, checking names are globally unique
        for pack in packs:
            for name, interface in pack.interfaces.items():
                if name in self.interfaces:
                    problems.append(
                        f"interface {name!r} declared by {self.interfaces[name][0]} and {pack.name}"
                    )
                self.interfaces[name] = (pack.name, interface)
            for name, event in pack.events.items():
                if name in self.event_types:
                    problems.append(
                        f"event {name!r} declared by {self.event_types[name].pack} and {pack.name}"
                    )
                self.event_types[name] = EventTypeDecl(name, pack.name, event)
            for name, intent in pack.retrieval.intents.items():
                if name in self.intents:
                    problems.append(
                        f"intent {name!r} declared by {self.intents[name].pack} and {pack.name}"
                    )
                self.intents[name] = Intent(name, pack.name, intent, dict(intent.weights))
            for name, edge in pack.types.edges.items():
                if name in self.edge_types:
                    problems.append(
                        f"edge type {name!r} declared by {self.edge_types[name].pack} and "
                        f"{pack.name}"
                    )
                properties = dict(edge.properties)
                for required_field in edge.requires:
                    properties.setdefault(required_field, LINK_FIELDS.get(required_field, "string"))
                self.edge_types[name] = EdgeType(name, pack.name, edge, properties=properties)
            if pack.retrieval.fallback_intent:
                if self.fallback_intent:
                    problems.append(f"{pack.name}: a fallback intent is already set")
                self.fallback_intent = pack.retrieval.fallback_intent

        for pack in packs:
            for name, node in pack.types.nodes.items():
                if name in self.node_types:
                    problems.append(
                        f"node type {name!r} declared by {self.node_types[name].pack} and "
                        f"{pack.name}"
                    )
                properties = dict(node.properties)
                for interface_name in node.interfaces:
                    declared_interface = self.interfaces.get(interface_name)
                    if declared_interface is None:
                        problems.append(
                            f"{pack.name}: {name} uses unknown interface {interface_name!r}"
                        )
                        continue
                    for prop, spec in declared_interface[1].properties.items():
                        properties.setdefault(prop, spec)
                self.node_types[name] = NodeType(name, pack.name, node, properties)

        # Endpoints: declarations, then extensions
        for pack in packs:
            for name, edge in pack.types.edges.items():
                self._add_endpoints(pack.name, self.edge_types[name], edge.from_, edge.to, problems)
            for name, extension in pack.types.extends_core_edges.items():
                edge_type = self.edge_types.get(name)
                if edge_type is None:
                    problems.append(f"{pack.name}: extends unknown edge type {name!r}")
                    continue
                if edge_type.pack == pack.name:
                    problems.append(f"{pack.name}: extends its own edge type {name!r}")
                    continue
                self._add_endpoints(pack.name, edge_type, extension.from_, extension.to, problems)

        # Weights other packs add to an intent
        for pack in packs:
            for intent_name, weights in pack.retrieval.core_intent_weights.items():
                target_intent = self.intents.get(intent_name)
                if target_intent is None:
                    problems.append(f"{pack.name}: adds weights to unknown intent {intent_name!r}")
                    continue
                for edge_name, weight in weights.items():
                    if edge_name in target_intent.weights:
                        problems.append(
                            f"{pack.name}: weight for {edge_name} on intent "
                            f"{intent_name!r} is already set"
                        )
                    target_intent.weights[edge_name] = weight

        for pack in packs:
            for rule in pack.projection:
                event_name = self._resolve_event(pack.name, rule.event)
                if event_name is None:
                    problems.append(
                        f"{pack.name}: projection rule for undeclared event {rule.event!r}"
                    )
                    continue
                self.projection_rules.setdefault(event_name, []).append((pack.name, rule))

    def _add_endpoints(
        self,
        pack: str,
        edge: EdgeType,
        sources: list[str] | str,
        targets: list[str] | str,
        problems: list[str],
    ) -> None:
        where = f"edge {edge.name}"
        if sources == WILDCARD:
            edge.from_any = True
        else:
            for ref in sources:
                resolved = self._resolve_type(pack, ref, problems, where)
                if resolved:
                    edge.from_types.add(resolved)
        if targets == WILDCARD:
            edge.to_any = True
        else:
            for ref in targets:
                resolved = self._resolve_type(pack, ref, problems, where)
                if resolved:
                    edge.to_types.add(resolved)

    # -- validation ------------------------------------------------------------------

    def _validate(self, problems: list[str]) -> None:
        for pack in self.packs:
            self._validate_types(pack, problems)
            self._validate_projection(pack, problems)
            self._validate_extraction(pack, problems)
            self._validate_retrieval(pack, problems)
            self._validate_lifecycle(pack, problems)
            for type_name in pack.mappings.get("synonyms", {}):
                if type_name not in self.node_types and type_name not in self.edge_types:
                    problems.append(f"{pack.name}: synonyms for unknown type {type_name!r}")
        if self.fallback_intent and self.fallback_intent not in self.intents:
            problems.append(f"fallback intent {self.fallback_intent!r} is not declared")

    def _validate_names(self, pack: Pack, problems: list[str]) -> None:
        for name, node in pack.types.nodes.items():
            if not NODE_TYPE_NAME.match(name):
                problems.append(
                    f"{pack.name}: node type name {name!r} must be PascalCase letters and digits"
                )
            for prop in node.properties:
                if not PROPERTY_NAME.match(prop):
                    problems.append(f"{pack.name}: property name {name}.{prop} must be snake_case")
        for name, edge in pack.types.edges.items():
            if not EDGE_TYPE_NAME.match(name):
                problems.append(f"{pack.name}: edge type name {name!r} must be UPPER_SNAKE_CASE")
            for prop in edge.properties:
                if not PROPERTY_NAME.match(prop):
                    problems.append(f"{pack.name}: property name {name}.{prop} must be snake_case")
        for name, interface in pack.interfaces.items():
            for prop in interface.properties:
                if not PROPERTY_NAME.match(prop):
                    problems.append(f"{pack.name}: property name {name}.{prop} must be snake_case")

    def _validate_types(self, pack: Pack, problems: list[str]) -> None:
        self._validate_names(pack, problems)
        for name, interface in pack.interfaces.items():
            for prop, spec in interface.properties.items():
                if (error := _check_property_spec(spec)) is not None:
                    problems.append(f"{pack.name}: interface {name}.{prop}: {error}")
            for edge_name in interface.edges:
                if edge_name not in self.edge_types:
                    problems.append(
                        f"{pack.name}: interface {name} names unknown edge {edge_name!r}"
                    )
        for name, node in pack.types.nodes.items():
            properties = self.node_types[name].properties
            for prop, spec in node.properties.items():
                if (error := _check_property_spec(spec)) is not None:
                    problems.append(f"{pack.name}: {name}.{prop}: {error}")
            if not node.key:
                problems.append(f"{pack.name}: {name} has no key")
            checks = {
                "key": node.key,
                "text_fields": node.text_fields,
                "embed_fields": node.embed_fields,
                "indexes": node.indexes,
                "id_property": [node.id_property] if node.id_property else [],
                "vector_property": [node.vector_property] if node.vector_property else [],
            }
            for section, fields in checks.items():
                for field_name in fields:
                    if field_name not in properties:
                        problems.append(
                            f"{pack.name}: {name}.{section} names unknown property {field_name!r}"
                        )
        for name, edge in pack.types.edges.items():
            for prop, spec in edge.properties.items():
                if (error := _check_property_spec(spec)) is not None:
                    problems.append(f"{pack.name}: edge {name}.{prop}: {error}")
            for required_field in edge.requires:
                if required_field not in LINK_FIELDS and required_field not in edge.properties:
                    problems.append(
                        f"{pack.name}: edge {name} requires undeclared field {required_field!r}"
                    )
        if pack.types.link_policy:
            for edge_name in pack.types.link_policy.applies_to:
                if edge_name not in self.edge_types:
                    problems.append(f"{pack.name}: link policy names unknown edge {edge_name!r}")

    def _check_fields(
        self, pack: str, where: str, type_name: str, fields: dict[str, Any], problems: list[str]
    ) -> None:
        properties = self.node_types[type_name].properties
        for field_name in fields:
            if field_name not in properties and field_name not in ("node_id", "node_type"):
                problems.append(f"{pack}: {where} sets unknown property {type_name}.{field_name}")

    def _check_ref(self, pack: str, where: str, ref: NodeRef, problems: list[str]) -> str | None:
        if ref.node_id is not None:
            return None
        assert ref.type is not None
        resolved = self._resolve_type(pack, ref.type, problems, where)
        if resolved is None:
            return None
        node = self.node_types[resolved]
        if ref.key is not None and sorted(ref.key) != sorted(node.key):
            problems.append(
                f"{pack}: {where} keys {resolved} by {sorted(ref.key)}, not {sorted(node.key)}"
            )
        for fields in (ref.match, ref.match_any_prefix):
            if fields:
                self._check_fields(pack, where, resolved, fields, problems)
        if ref.key is None and ref.match is None and ref.match_any_prefix is None:
            problems.append(f"{pack}: {where} gives no key, match or node_id for {resolved}")
        return resolved

    def _validate_projection(self, pack: Pack, problems: list[str]) -> None:
        for index, rule in enumerate(pack.projection):
            where = f"projection[{index}] ({rule.event})"
            for upsert in rule.upsert:
                resolved = self._check_ref(
                    pack.name, where, NodeRef(type=upsert.type, key=upsert.key), problems
                )
                if resolved:
                    self._check_fields(pack.name, where, resolved, upsert.set, problems)
            if rule.transition is not None:
                resolved = self._resolve_type(pack.name, rule.transition.type, problems, where)
                lifecycle = self.node_types[resolved].lifecycle if resolved else None
                if resolved and lifecycle is None:
                    problems.append(
                        f"{pack.name}: {where} transitions {resolved}, which has no lifecycle"
                    )
                elif lifecycle is not None:
                    literal_states = [rule.transition.to] if _is_literal(rule.transition.to) else []
                    for state in literal_states + rule.transition.only_from:
                        if state not in lifecycle.states:
                            problems.append(
                                f"{pack.name}: {where} uses unknown {resolved} state {state!r}"
                            )
            for edge_rule in rule.edges:
                edge = self.edge_types.get(edge_rule.type)
                if edge is None:
                    problems.append(
                        f"{pack.name}: {where} creates unknown edge type {edge_rule.type!r}"
                    )
                    continue
                source = self._check_ref(pack.name, where, edge_rule.from_, problems)
                target = self._check_ref(pack.name, where, edge_rule.target, problems)
                if source and target and not edge.allows(source, target):
                    problems.append(
                        f"{pack.name}: {where} draws {edge.name} from {source} to {target}, not "
                        f"allowed"
                    )
                for prop in edge_rule.set:
                    if prop not in edge.properties:
                        problems.append(
                            f"{pack.name}: {where} sets unknown property {edge.name}.{prop}"
                        )

    def _validate_extraction(self, pack: Pack, problems: list[str]) -> None:
        extraction = pack.extraction
        for source in extraction.sources:
            if self._resolve_event(pack.name, source) is None:
                problems.append(
                    f"{pack.name}: extraction source {source!r} is not a declared event"
                )
        for name in [*extraction.propose, *extraction.never_propose, *extraction.derived_proposals]:
            if name not in self.node_types and name not in self.edge_types:
                problems.append(f"{pack.name}: extraction names unknown type {name!r}")

    def _validate_retrieval(self, pack: Pack, problems: list[str]) -> None:
        retrieval = pack.retrieval
        for type_name in retrieval.seed_types:
            if type_name not in self.node_types:
                problems.append(f"{pack.name}: unknown seed type {type_name!r}")
        weight_sets = [(f"intent {n}", i.weights) for n, i in retrieval.intents.items()]
        weight_sets += [(f"weights for {n}", w) for n, w in retrieval.core_intent_weights.items()]
        for where, weights in weight_sets:
            for edge_name in weights:
                if edge_name not in self.edge_types:
                    problems.append(f"{pack.name}: {where} weights unknown edge {edge_name!r}")
        for name, intent in retrieval.intents.items():
            for type_name in intent.prefer_types:
                if type_name not in self.node_types:
                    problems.append(
                        f"{pack.name}: intent {name} prefers unknown type {type_name!r}"
                    )
        for name, rule in retrieval.admission.items():
            for intent_name in rule.get("include_for_intents", []):
                if intent_name not in self.intents:
                    problems.append(
                        f"{pack.name}: admission {name} names unknown intent {intent_name!r}"
                    )

    def _validate_lifecycle(self, pack: Pack, problems: list[str]) -> None:
        for type_name in pack.lifecycle.decay:
            if type_name != "default" and type_name not in self.node_types:
                problems.append(f"{pack.name}: decay for unknown type {type_name!r}")
        known_states = {
            state
            for node in self.node_types.values()
            if node.lifecycle is not None
            for state in node.lifecycle.states
        }
        for state in pack.lifecycle.terminal_states_reduce_importance:
            if state not in known_states:
                problems.append(f"{pack.name}: terminal state {state!r} is in no lifecycle")

    def _version_hash(self) -> str:
        digest = hashlib.sha256()
        for name in sorted(self._packs):
            digest.update(self._packs[name].canonical_json().encode())
        return f"sha256:{digest.hexdigest()[:16]}"


def _is_literal(value: str) -> bool:
    """A rule value that is a plain word, not an expression."""
    return re.fullmatch(r"[A-Za-z_][\w-]*", value) is not None


def _compare(actual: str, operator: str, wanted: str) -> bool:
    left, right = _version_tuple(actual), _version_tuple(wanted)
    return {
        ">=": left >= right,
        "<=": left <= right,
        "==": left == right,
        ">": left > right,
        "<": left < right,
    }[operator]
