"""Ontology packs and the registry that composes them (ADR-0018).

A pack is a versioned, declarative description of part of the graph:
node and edge types, the events it owns, deterministic projection rules,
what LLM extraction may propose, retrieval intents and weights, lifecycle
rules and vocabulary mappings. ``OntologyRegistry`` composes the active
packs (always ``core``), validates them as a whole and answers lookups.

Today's schema is written as the ``core``, ``memory`` and ``user`` packs
(``context_graph/ontology/packs``); the enums in ``domain/models.py``
remain and must equal what those packs declare.

References:
- edge endpoints, projection rules, extensions and extraction sources:
  bare names (``Change``, ``pdlc.change.merged``) mean the pack's own
  types and events; another pack's are qualified (``core:Entity``,
  ``core:observation.input``). ``*`` means every type of the pack that
  wrote it;
- retrieval, lifecycle, extraction and mapping lists name types by their
  global name (type names are unique across packs, ignoring case).

Pure Python: no framework, storage or file-format imports. Loading packs
from files lives in ``context_graph.ontology``.

Source: ADR-0018, docs/research/2026-10/ontology/pdlc-ontology-and-ontology-packs.md
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Literal

import regex
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer,
    model_validator,
)

from context_graph.domain.pack_contracts import (
    PayloadContract,  # noqa: TC001 - Pydantic runtime type
)
from context_graph.domain.pack_expressions import (
    Call,
    Concat,
    ExpressionError,
    MapLiteral,
    Node,
    Path,
    compile_value,
    is_expression,
)
from context_graph.domain.pack_expressions import (
    Literal as ExpressionLiteral,
)

WILDCARD = "*"

SCALAR_TYPES = frozenset({"string", "text", "int", "float", "bool", "datetime", "json"})


# Event envelope fields an expression may read as ``$event.<field>``
ENVELOPE_FIELDS = frozenset(
    {
        "event_id",
        "event_type",
        "occurred_at",
        "session_id",
        "agent_id",
        "trace_id",
        "payload_ref",
        "global_position",
        "tool_name",
        "parent_event_id",
        "ended_at",
        "status",
        "schema_version",
        "importance_hint",
    }
)

# Properties the projector writes on every pack node, besides declared ones
SYSTEM_PROPERTIES = frozenset(
    {"node_id", "node_type", "ontology_version", "updated_at", "status_changed_at"}
)

_PACK_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
_REQUIREMENT = re.compile(r"^([a-z][a-z0-9_]*)\s*(?:(>=|<=|==|>|<)\s*(\d+(?:\.\d+){0,2}))?$")
_LIST_TYPE = re.compile(r"^list<(\w+)>$")

# Names that reach backend query text (labels, relationship types, property
# keys) are restricted to these shapes, so they can never inject anything.
NODE_TYPE_NAME = re.compile(r"^[A-Z][A-Za-z0-9]*$")
EDGE_TYPE_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
PROPERTY_NAME = re.compile(r"^[a-z_][a-z0-9_]*$")
# Same shape as the event envelope's event_type (domain/models.py)
EVENT_TYPE_NAME = re.compile(r"^[a-z][a-z0-9]*(\.[a-z][a-z0-9_]*)+$")
LOWER_NAME = re.compile(r"^[a-z][a-z0-9_]*$")

# Packs restating today's schema; their event namespaces stay open at ingest
OPEN_PACKS = frozenset({"core", "memory", "user"})

# Edge every domain pack type gets to the Event that observed it (provenance)
PROVENANCE_EDGE = "DERIVED_FROM"
# Interface a domain type with a lifecycle must use (core declares it)
LIFECYCLED_INTERFACE = "Lifecycled"
# Query plugins an intent may name (served by retrieval/artifacts.py)
INTENT_PLUGINS = frozenset({"missing_links"})
# Node types the system writes itself; packs may not declare them
RESERVED_NODE_TYPES = frozenset({"OntologyState"})
# Link policy settings the engine reads; others are recorded but inert
LINK_POLICY_SETTINGS = frozenset({"applies_to", "link_status"})
# Admission rules retrieval understands, with the settings each one takes
ADMISSION_RULES: dict[str, frozenset[str]] = {
    "superseded_or_reversed": frozenset({"default", "include_for_intents", "label_as"}),
    "untrusted_uncorroborated": frozenset({"default", "available_via"}),
    "proposed_links": frozenset({"default", "never_counted_as"}),
}

# Index names a node type may not use (they would clash with its key constraint)
RESERVED_INDEX_FIELDS = frozenset({"pk", "node_id"})


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
    # strict: a YAML string is never coerced to a number or a boolean
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, strict=True)


class _Open(BaseModel):
    """Sections whose extra keys are kept as free-form notes."""

    model_config = ConfigDict(extra="allow", frozen=True, strict=True)


class EnumSpec(_Strict):
    enum: list[str]


PropertySpec = str | EnumSpec

# Fields an edge in a pack's link policy (or an edge's ``requires``) carries.
# A projection rule that does not set them gets the declared-link defaults.
LINK_FIELDS: dict[str, PropertySpec] = {
    "confidence": "float",
    "method": "string",
    "link_status": EnumSpec(enum=["proposed", "confirmed", "rejected"]),
}
DECLARED_LINK = {"confidence": 1.0, "method": "declared", "link_status": "confirmed"}


def _check_property_spec(spec: PropertySpec) -> str | None:
    if isinstance(spec, EnumSpec):
        if not spec.enum:
            return "empty enum"
        return None if len(set(spec.enum)) == len(spec.enum) else "repeated enum value"
    match = _LIST_TYPE.match(spec)
    base = match.group(1) if match else spec
    return None if base in SCALAR_TYPES else f"unknown property type {spec!r}"


def _finite_weights(weights: dict[str, float]) -> dict[str, float]:
    for edge, weight in weights.items():
        if not math.isfinite(weight) or weight < 0:
            msg = f"weight for {edge} must be a finite number >= 0, not {weight}"
            raise ValueError(msg)
    return weights


class PackHeader(_Strict):
    name: str
    version: str
    requires: list[str] = Field(default_factory=list)
    owner: str | None = None
    description: str = ""

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        if not _PACK_NAME.match(value):
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
    # States meaning "no longer current" (retrieval's superseded_or_reversed rule)
    superseded_states: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _states(self) -> LifecycleDef:
        if self.initial not in self.states:
            msg = f"initial state {self.initial!r} is not one of {self.states}"
            raise ValueError(msg)
        unknown = [s for s in self.superseded_states if s not in self.states]
        if unknown:
            msg = f"superseded states {unknown} are not among {self.states}"
            raise ValueError(msg)
        if self.initial in self.superseded_states:
            msg = f"initial state {self.initial!r} cannot be a superseded state"
            raise ValueError(msg)
        if len(set(self.states)) != len(self.states):
            msg = f"repeated state in {self.states}"
            raise ValueError(msg)
        for state in self.states:
            if not LOWER_NAME.match(state):
                msg = f"state {state!r} must be lowercase letters, digits and underscores"
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


class LinkPolicyDef(_Open):
    applies_to: list[str] = Field(default_factory=list)

    def declared_link_status(self) -> str:
        """The status a declared (tool-stated) link starts with."""
        status = getattr(self, "link_status", None)
        if isinstance(status, dict):
            value = status.get("declared_links_start_as")
            if isinstance(value, str):
                return value
        return "confirmed"


class TypesSection(_Strict):
    nodes: dict[str, NodeTypeDef] = Field(default_factory=dict)
    edges: dict[str, EdgeTypeDef] = Field(default_factory=dict)
    link_policy: LinkPolicyDef | None = None
    extends_core_edges: dict[str, EdgeExtensionDef] = Field(default_factory=dict)


class EventDef(_Strict):
    payload_contract: PayloadContract | None = None
    handling: Literal["processed", "ledger_only", "unsupported"] | None = None
    aliases: dict[str, str] = Field(default_factory=dict)
    note: str | None = None


# -- projection rules ---------------------------------------------------------

# A value in a rule: a constant, or an expression string ($.x, $event.x, fn(...))
RuleValue = str | int | float | bool


class PropertyUpdateDef(_Strict):
    """Opt-in property contract; the first engine supports literals/direct paths."""

    value: RuleValue | None
    on_missing: Literal["preserve", "refuse"] = "preserve"
    on_null: Literal["preserve", "clear", "refuse"] = "preserve"
    select: Literal["value", "zip"] = "value"

    @model_validator(mode="after")
    def _supported_expression(self) -> PropertyUpdateDef:
        if not isinstance(compile_value(self.value), (ExpressionLiteral, Path)):
            raise ValueError("Strict properties support only literals and direct paths")
        return self

    @model_serializer(mode="wrap")
    def _required_value(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data: dict[str, Any] = handler(self)
        # Explicit null is a required instruction, not an absent optional field.
        data["value"] = self.value
        return data


PropertyRuleValue = RuleValue | PropertyUpdateDef


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
    set: dict[str, PropertyRuleValue] = Field(default_factory=dict)


class TransitionDef(_Strict):
    """Move a node to a lifecycle state.

    The node is the one the rule upserts with this type, or, when the rule
    does not upsert it, the first edge endpoint of this type with a key
    (``pdlc.change.reviewed`` moves the Change its Review points at);
    ``key`` names it explicitly.
    """

    type: str
    to: str
    only_from: list[str] = Field(default_factory=list)
    key: dict[str, RuleValue] | None = None


class EdgeRuleDef(_Strict):
    type: str
    from_: NodeRef = Field(alias="from")
    to: NodeRef | None = None
    to_each: NodeRef | None = None
    to_latest: NodeRef | None = None
    set: dict[str, PropertyRuleValue] = Field(default_factory=dict)
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


def transition_key(rule: ProjectionRule, type_name: str) -> dict[str, RuleValue] | None:
    """The key of the node a rule's transition moves, or None if the rule names none."""
    transition = rule.transition
    if transition is None:
        return None
    if transition.key is not None:
        return transition.key
    for upsert in rule.upsert:
        if upsert.type.rpartition(":")[2] == type_name:
            return upsert.key
    for edge in rule.edges:
        for ref in (edge.from_, edge.target):
            if ref.type and ref.type.rpartition(":")[2] == type_name and ref.key is not None:
                return ref.key
    return None


# -- extraction, retrieval, lifecycle ---------------------------------------------


class ProposeDef(_Open):
    description: str
    max_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
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
    max_depth: int | None = Field(default=None, ge=1)
    plugin: str | None = None
    prefer_types: list[str] = Field(default_factory=list)
    direction: Literal["outbound", "inbound", "both"] = "both"

    _weights = field_validator("weights")(_finite_weights)


class AdmissionRuleDef(_Open):
    default: str | None = None
    include_for_intents: list[str] = Field(default_factory=list)


class RetrievalSection(_Strict):
    seed_types: list[str] = Field(default_factory=list)
    # How a question names a node of a type by its key: a pattern per type
    # (``Deal: 'D-\\d+'``); a match (its first group, if any) is looked up
    # as the type's most specific key value
    key_patterns: dict[str, str] = Field(default_factory=dict)
    intents: dict[str, IntentDef] = Field(default_factory=dict)
    admission: dict[str, AdmissionRuleDef] = Field(default_factory=dict)
    # Weights this pack adds to intents another pack declares
    core_intent_weights: dict[str, dict[str, float]] = Field(default_factory=dict)
    # Intent used when no keyword matches
    fallback_intent: str | None = None

    @field_validator("core_intent_weights")
    @classmethod
    def _weights(cls, value: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
        for weights in value.values():
            _finite_weights(weights)
        return value


class DecayDef(_Strict):
    class_: Literal["pinned", "slow", "medium", "fast"] = Field(alias="class")
    compressible: bool = True
    retain_days: int | None = Field(default=None, ge=1)


class LifecycleSection(_Strict):
    decay: dict[str, DecayDef] = Field(default_factory=dict)
    terminal_states_reduce_importance: list[str] = Field(default_factory=list)


class ProcessingSection(_Strict):
    """Exact versioned engine handlers; requirements do not enable processing."""

    requires: list[str] = Field(default_factory=list, max_length=64)
    enabled: list[str] = Field(default_factory=list, max_length=64)

    @field_validator("requires", "enabled")
    @classmethod
    def _handler_ids(cls, values: list[str]) -> list[str]:
        for value in values:
            if not re.fullmatch(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*\.v[1-9][0-9]*", value):
                raise ValueError(f"processing handler {value!r} must be an exact versioned ID")
        return sorted(set(values))


class Pack(_Strict):
    pack: PackHeader
    processing: ProcessingSection = Field(default_factory=ProcessingSection)
    interfaces: dict[str, InterfaceDef] = Field(default_factory=dict)
    types: TypesSection = Field(default_factory=TypesSection)
    events: dict[str, EventDef] = Field(default_factory=dict)
    open_event_namespaces: list[str] = Field(default_factory=list)
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
        data = self.model_dump(mode="json", by_alias=True, exclude_none=True)
        # Adding an absent-equivalent optional section must not invalidate
        # recorded legacy snapshots merely because the parser gained a field.
        if not self.processing.requires and not self.processing.enabled:
            data.pop("processing", None)
        if not self.open_event_namespaces:
            data.pop("open_event_namespaces", None)
        return json.dumps(
            data,
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

    @property
    def key_property(self) -> str:
        """The property that identifies a node of this type."""
        return self.definition.id_property or "node_id"


@dataclass
class EdgeType:
    name: str
    pack: str
    definition: EdgeTypeDef
    from_types: set[str] = field(default_factory=set)
    to_types: set[str] = field(default_factory=set)
    # Packs whose every type is an allowed endpoint (``*`` in that pack)
    from_packs: set[str] = field(default_factory=set)
    to_packs: set[str] = field(default_factory=set)
    # Own properties plus link fields when the edge requires them
    properties: dict[str, PropertySpec] = field(default_factory=dict)
    # Values a projection rule gets for required link fields it does not set
    link_defaults: dict[str, Any] = field(default_factory=dict)


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


# The base packs come first, in this order
_BASE_ORDER = {"core": 0, "memory": 1, "user": 2}


def _canonical_order(packs: list[Pack]) -> list[Pack]:
    """The base packs, then each pack after the active packs it requires; ties by name.

    Requirements on packs that are not active, and cycles (reported by
    validation), do not hold a pack back.
    """
    by_name = {pack.name: pack for pack in packs}
    needs = {
        pack.name: {
            match.group(1)
            for requirement in pack.pack.requires
            if (match := _REQUIREMENT.match(requirement)) and match.group(1) in by_name
        }
        - {pack.name}
        for pack in packs
    }
    ordered: list[Pack] = []
    placed: set[str] = set()
    while len(ordered) < len(packs):
        ready = [n for n in by_name if n not in placed and needs[n] <= placed]
        if not ready:  # a cycle: place the rest by name
            ready = [n for n in by_name if n not in placed]
        name = min(ready, key=lambda n: (_BASE_ORDER.get(n, len(_BASE_ORDER)), n))
        ordered.append(by_name[name])
        placed.add(name)
    return ordered


class OntologyRegistry:
    """The composed, validated ontology of the active packs."""

    def __init__(self, packs: list[Pack]) -> None:
        names = [pack.name for pack in packs]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise OntologyError([f"pack {name!r} is loaded more than once" for name in duplicates])
        # Canonical order: a pack after the packs it requires, ties by name; so
        # rule order and merges never depend on the order packs were listed
        self._packs: dict[str, Pack] = {pack.name: pack for pack in _canonical_order(packs)}
        self.node_types: dict[str, NodeType] = {}
        self.edge_types: dict[str, EdgeType] = {}
        self.event_types: dict[str, EventTypeDecl] = {}
        self.intents: dict[str, Intent] = {}
        self.interfaces: dict[str, tuple[str, InterfaceDef]] = {}
        self.projection_rules: dict[str, list[tuple[str, ProjectionRule]]] = {}
        self.fallback_intent: str | None = None
        self._closed_namespaces: frozenset[str] | None = None
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

    def allows(self, edge_type: str, source_type: str, target_type: str) -> bool:
        """Whether an edge type may connect these node types."""
        edge = self.edge_types.get(edge_type)
        source = self.node_types.get(source_type)
        target = self.node_types.get(target_type)
        if edge is None or source is None or target is None:
            return False
        return (source_type in edge.from_types or source.pack in edge.from_packs) and (
            target_type in edge.to_types or target.pack in edge.to_packs
        )

    def closed_namespaces(self) -> frozenset[str]:
        """Event namespaces owned by packs other than today's schema.

        Today's agent events are open (any ``tool.*`` type is accepted);
        a namespace a later pack owns (``pdlc``) accepts only declared types.
        """
        if self._closed_namespaces is None:
            open_namespaces = {
                name.split(".")[0] for name, e in self.event_types.items() if e.pack in OPEN_PACKS
            }
            self._closed_namespaces = (
                frozenset(
                    name.split(".")[0]
                    for name, e in self.event_types.items()
                    if e.pack not in OPEN_PACKS
                )
                - open_namespaces
            )
        return self._closed_namespaces

    def accepts_event_type(self, event_type: str) -> bool:
        """Whether ingest may accept an event type (declared, or in an open namespace)."""
        if event_type in self.event_types:
            return True
        return event_type.split(".")[0] not in self.closed_namespaces()

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

    def inert_settings(self) -> list[str]:
        """Settings domain packs declare that nothing reads yet (review 2.7).

        They load and validate, so packs can state intent, but an author
        should not rely on them: the loader logs each one as a warning.
        """
        notes: list[str] = []
        for pack in self.packs:
            if pack.name in OPEN_PACKS:
                continue
            for name, node in pack.types.nodes.items():
                if node.embed_fields:
                    notes.append(f"{pack.name}: {name}.embed_fields (no embeddings for pack types)")
            policy = pack.types.link_policy
            declared = set(policy.model_dump(exclude_defaults=True)) if policy else set()
            extra = sorted(declared - LINK_POLICY_SETTINGS)
            if extra:
                notes.append(f"{pack.name}: link_policy {', '.join(extra)}")
            if pack.extraction.derived_proposals:
                notes.append(f"{pack.name}: extraction.derived_proposals")
            if pack.lifecycle.decay:
                notes.append(f"{pack.name}: lifecycle.decay")
            if pack.lifecycle.terminal_states_reduce_importance:
                notes.append(f"{pack.name}: lifecycle.terminal_states_reduce_importance")
            if pack.mappings:
                notes.append(f"{pack.name}: mappings (vocabulary only)")
        return notes

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
        """An event reference (own pack's when bare) as its name, or None if undeclared."""
        owner, _, name = ref.rpartition(":")
        declared = self.event_types.get(name)
        if declared is None or declared.pack != (owner or pack):
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
            self._declare(pack, problems)

        lowered: dict[str, str] = {}
        for pack in packs:
            for name, node in pack.types.nodes.items():
                if name in self.node_types:
                    problems.append(
                        f"node type {name!r} declared by {self.node_types[name].pack} and "
                        f"{pack.name}"
                    )
                elif name.lower() in lowered:
                    problems.append(
                        f"node types {lowered[name.lower()]!r} and {name!r} differ only by case"
                    )
                lowered.setdefault(name.lower(), name)
                self.node_types[name] = NodeType(
                    name, pack.name, node, self._node_properties(pack.name, name, node, problems)
                )

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

        # Provenance: every domain pack type may link to the Event that observed it
        provenance = self.edge_types.get(PROVENANCE_EDGE)
        if provenance is not None and "Event" in provenance.to_types:
            for pack in packs:
                if pack.name not in OPEN_PACKS and pack.types.nodes:
                    provenance.from_packs.add(pack.name)

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

    def _declare(self, pack: Pack, problems: list[str]) -> None:
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
        policy = pack.types.link_policy
        policy_edges = set(policy.applies_to) if policy else set()
        for name, edge in pack.types.edges.items():
            if name in self.edge_types:
                problems.append(
                    f"edge type {name!r} declared by {self.edge_types[name].pack} and {pack.name}"
                )
            properties = dict(edge.properties)
            link_fields = set(edge.requires) & set(LINK_FIELDS)
            if name in policy_edges:
                link_fields |= set(LINK_FIELDS)
            for link_field in sorted(link_fields):
                properties.setdefault(link_field, LINK_FIELDS[link_field])
            defaults = {k: DECLARED_LINK[k] for k in link_fields}
            if "link_status" in defaults and policy is not None:
                defaults["link_status"] = policy.declared_link_status()
            self.edge_types[name] = EdgeType(
                name, pack.name, edge, properties=properties, link_defaults=defaults
            )
        if pack.retrieval.fallback_intent:
            if self.fallback_intent:
                problems.append(f"{pack.name}: a fallback intent is already set")
            self.fallback_intent = pack.retrieval.fallback_intent

    def _node_properties(
        self, pack: str, name: str, node: NodeTypeDef, problems: list[str]
    ) -> dict[str, PropertySpec]:
        properties = dict(node.properties)
        for interface_name in node.interfaces:
            declared = self.interfaces.get(interface_name)
            if declared is None:
                problems.append(f"{pack}: {name} uses unknown interface {interface_name!r}")
                continue
            for prop, spec in declared[1].properties.items():
                if prop in properties and properties[prop] != spec:
                    problems.append(
                        f"{pack}: {name}.{prop} conflicts with interface {interface_name}"
                    )
                    continue
                properties[prop] = spec
        return properties

    def _add_endpoints(
        self,
        pack: str,
        edge: EdgeType,
        sources: list[str] | str,
        targets: list[str] | str,
        problems: list[str],
    ) -> None:
        where = f"edge {edge.name}"
        for refs, types, packs in (
            (sources, edge.from_types, edge.from_packs),
            (targets, edge.to_types, edge.to_packs),
        ):
            if refs == WILDCARD:
                packs.add(pack)
                continue
            for ref in refs:
                resolved = self._resolve_type(pack, ref, problems, where)
                if resolved:
                    types.add(resolved)

    # -- validation ------------------------------------------------------------------

    def _validate(self, problems: list[str]) -> None:
        for pack in self.packs:
            self._validate_names(pack, problems)
            self._validate_types(pack, problems)
            self._validate_projection(pack, problems)
            self._validate_extraction(pack, problems)
            self._validate_retrieval(pack, problems)
            self._validate_lifecycle(pack, problems)
            self._validate_mappings(pack, problems)
        if self.fallback_intent and self.fallback_intent not in self.intents:
            problems.append(f"fallback intent {self.fallback_intent!r} is not declared")

    def _validate_names(self, pack: Pack, problems: list[str]) -> None:
        def check(pattern: re.Pattern[str], name: str, what: str, shape: str) -> None:
            if not pattern.match(name):
                problems.append(f"{pack.name}: {what} {name!r} must be {shape}")

        for name, node in pack.types.nodes.items():
            check(NODE_TYPE_NAME, name, "node type name", "PascalCase letters and digits")
            for prop in node.properties:
                check(PROPERTY_NAME, prop, f"property name {name}.", "snake_case")
        for name, edge in pack.types.edges.items():
            check(EDGE_TYPE_NAME, name, "edge type name", "UPPER_SNAKE_CASE")
            for prop in edge.properties:
                check(PROPERTY_NAME, prop, f"property name {name}.", "snake_case")
        for name, interface in pack.interfaces.items():
            check(NODE_TYPE_NAME, name, "interface name", "PascalCase letters and digits")
            for prop in interface.properties:
                check(PROPERTY_NAME, prop, f"property name {name}.", "snake_case")
        for name in pack.events:
            check(EVENT_TYPE_NAME, name, "event type", "dot-namespaced lowercase")
            namespace = name.split(".")[0]
            owners = {
                e.pack for e in self.event_types.values() if e.name.split(".")[0] == namespace
            }
            if owners - {pack.name}:
                problems.append(
                    f"{pack.name}: event {name!r} is in namespace {namespace!r}, "
                    f"which pack {sorted(owners - {pack.name})[0]} owns"
                )
        for name in pack.types.nodes:
            if name in RESERVED_NODE_TYPES:
                problems.append(f"{pack.name}: node type name {name!r} is reserved")
        for name in pack.retrieval.intents:
            check(LOWER_NAME, name, "intent name", "lowercase letters, digits and underscores")

    def _validate_types(self, pack: Pack, problems: list[str]) -> None:
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
            self._validate_node(pack.name, name, node, problems)
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

    def _validate_node(self, pack: str, name: str, node: NodeTypeDef, problems: list[str]) -> None:
        properties = self.node_types[name].properties
        for prop, spec in node.properties.items():
            if (error := _check_property_spec(spec)) is not None:
                problems.append(f"{pack}: {name}.{prop}: {error}")
        if not node.key:
            problems.append(f"{pack}: {name} has no key")
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
                        f"{pack}: {name}.{section} names unknown property {field_name!r}"
                    )
        for field_name in node.indexes:
            if field_name in RESERVED_INDEX_FIELDS or field_name == node.id_property:
                problems.append(f"{pack}: {name} cannot index its key field {field_name!r}")
        # The projector writes status for a lifecycle: the type must declare it
        if (
            node.lifecycle is not None
            and pack not in OPEN_PACKS
            and LIFECYCLED_INTERFACE not in node.interfaces
        ):
            problems.append(
                f"{pack}: {name} has a lifecycle, so it must use interface {LIFECYCLED_INTERFACE}"
            )
        # Every edge an interface promises must accept this type as its source
        for interface_name in node.interfaces:
            declared = self.interfaces.get(interface_name)
            for edge_name in declared[1].edges if declared else []:
                edge = self.edge_types.get(edge_name)
                if edge and name not in edge.from_types and pack not in edge.from_packs:
                    problems.append(
                        f"{pack}: {name} uses interface {interface_name}, but {edge_name} "
                        f"does not start from {name}"
                    )

    def _check_fields(
        self, pack: str, where: str, type_name: str, fields: dict[str, Any], problems: list[str]
    ) -> None:
        properties = self.node_types[type_name].properties
        for field_name in fields:
            if field_name not in properties and field_name not in SYSTEM_PROPERTIES:
                problems.append(f"{pack}: {where} sets unknown property {type_name}.{field_name}")

    def _check_values(
        self, pack: str, where: str, values: dict[str, Any] | None, problems: list[str]
    ) -> None:
        for value in (values or {}).values():
            self._check_expression(
                pack,
                where,
                value.value if isinstance(value, PropertyUpdateDef) else value,
                problems,
            )

    def _check_expression(self, pack: str, where: str, value: Any, problems: list[str]) -> None:
        try:
            tree = compile_value(value)
        except ExpressionError as exc:
            problems.append(f"{pack}: {where}: {exc}")
            return
        for path in _paths(tree):
            if path.root == "event" and path.steps[0] not in ENVELOPE_FIELDS:
                problems.append(f"{pack}: {where} reads unknown envelope field {path.steps[0]!r}")

    def _check_ref(self, pack: str, where: str, ref: NodeRef, problems: list[str]) -> str | None:
        for values in (ref.key, ref.match, ref.match_any_prefix):
            self._check_values(pack, where, values, problems)
        if ref.node_id is not None:
            self._check_expression(pack, where, ref.node_id, problems)
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
            event_name = self._resolve_event(pack.name, rule.event)
            contract = (
                self.event_types[event_name].definition.payload_contract if event_name else None
            )
            if contract is not None:
                pending = list(rule.model_dump().values())
                while pending:
                    value = pending.pop()
                    if isinstance(value, dict):
                        pending.extend(value.values())
                    elif isinstance(value, list):
                        pending.extend(value)
                    elif is_expression(value):
                        try:
                            paths = _paths(compile_value(value))
                        except ExpressionError:
                            continue  # The existing expression check reports malformed syntax.
                        for path in paths:
                            if path.root == "payload" and not contract.declares_path(path.steps):
                                problems.append(
                                    f"{pack.name}: {where} reads undeclared payload path "
                                    f"{'.'.join(path.steps)!r}"
                                )
            for upsert in rule.upsert:
                resolved = self._check_ref(
                    pack.name, where, NodeRef(type=upsert.type, key=upsert.key), problems
                )
                self._check_values(pack.name, where, upsert.set, problems)
                if resolved:
                    self._check_fields(pack.name, where, resolved, upsert.set, problems)
                    node = self.node_types[resolved]
                    self._check_strict_properties(
                        pack.name,
                        where,
                        upsert.set,
                        node.pack,
                        set(node.key) | {node.key_property, "status"},
                        set(),
                        problems,
                    )
            if rule.transition is not None:
                self._validate_transition(pack.name, where, rule, problems)
            for edge_rule in rule.edges:
                self._validate_edge_rule(pack.name, where, edge_rule, problems)

    def _validate_transition(
        self, pack: str, where: str, rule: ProjectionRule, problems: list[str]
    ) -> None:
        transition = rule.transition
        assert transition is not None
        self._check_expression(pack, where, transition.to, problems)
        self._check_values(pack, where, transition.key, problems)
        resolved = self._resolve_type(pack, transition.type, problems, where)
        if resolved is None:
            return
        node = self.node_types[resolved]
        lifecycle = node.lifecycle
        if lifecycle is None:
            problems.append(f"{pack}: {where} transitions {resolved}, which has no lifecycle")
            return
        key = transition_key(rule, resolved)
        if key is None:
            problems.append(f"{pack}: {where} does not say which {resolved} to transition")
        elif sorted(key) != sorted(node.key):
            problems.append(f"{pack}: {where} transition keys {resolved} by {sorted(key)}")
        for state in [*_target_states(transition.to), *transition.only_from]:
            if state not in lifecycle.states:
                problems.append(f"{pack}: {where} uses unknown {resolved} state {state!r}")

    def _validate_edge_rule(
        self, pack: str, where: str, edge_rule: EdgeRuleDef, problems: list[str]
    ) -> None:
        self._check_values(pack, where, edge_rule.set, problems)
        if edge_rule.when is not None:
            self._check_expression(pack, where, edge_rule.when, problems)
        edge = self.edge_types.get(edge_rule.type)
        source = self._check_ref(pack, where, edge_rule.from_, problems)
        target = self._check_ref(pack, where, edge_rule.target, problems)
        origin = edge_rule.from_
        if origin.match_any_prefix is not None:
            problems.append(f"{pack}: {where} cannot find an edge's source by match_any_prefix")
        if origin.match is not None and (
            edge_rule.to_latest is not None
            or edge_rule.target.match is not None
            or edge_rule.target.match_any_prefix is not None
        ):
            problems.append(
                f"{pack}: {where} finds the source by match, so the target needs a key or node_id"
            )
        if edge is None:
            problems.append(f"{pack}: {where} creates unknown edge type {edge_rule.type!r}")
            return
        if source and target and not self.allows(edge.name, source, target):
            problems.append(f"{pack}: {where} draws {edge.name} from {source} to {target}")
        self._check_strict_properties(
            pack,
            where,
            edge_rule.set,
            edge.pack,
            set(),
            set(edge.definition.requires),
            problems,
        )
        for prop in edge_rule.set:
            if prop not in edge.properties:
                problems.append(f"{pack}: {where} sets unknown property {edge.name}.{prop}")
        for required_field in edge.definition.requires:
            if required_field not in edge_rule.set and required_field not in edge.link_defaults:
                problems.append(f"{pack}: {where} must set {edge.name}.{required_field}")

    def _check_strict_properties(
        self,
        pack: str,
        where: str,
        values: dict[str, PropertyRuleValue],
        target_owner: str,
        protected: set[str],
        required: set[str],
        problems: list[str],
    ) -> None:
        for name, value in values.items():
            if not isinstance(value, PropertyUpdateDef):
                continue
            if "pack.properties.v1" not in self._packs[pack].processing.requires:
                problems.append(f"{pack}: {where} requires pack.properties.v1")
            if target_owner != pack:
                problems.append(f"{pack}: {where} strict foreign property writes are unsupported")
            if name in protected | SYSTEM_PROPERTIES | {"source_trust", "status_changed_at"}:
                problems.append(f"{pack}: {where} strict write to protected property {name}")
            if name in required and value.on_null == "clear":
                problems.append(f"{pack}: {where} cannot clear required property {name}")

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
        for name in sorted(set(extraction.propose) & set(extraction.never_propose)):
            problems.append(f"{pack.name}: {name} is both proposed and never proposed")

    def _validate_retrieval(self, pack: Pack, problems: list[str]) -> None:
        retrieval = pack.retrieval
        for type_name in retrieval.seed_types:
            if type_name not in self.node_types:
                problems.append(f"{pack.name}: unknown seed type {type_name!r}")
        for type_name, pattern in retrieval.key_patterns.items():
            if type_name not in self.node_types:
                problems.append(f"{pack.name}: key pattern for unknown type {type_name!r}")
            elif type_name not in retrieval.seed_types:
                problems.append(f"{pack.name}: key pattern for {type_name}, not a seed type")
            try:
                if regex.compile(pattern).search(""):
                    problems.append(f"{pack.name}: key pattern for {type_name} matches empty text")
            except regex.error as exc:
                problems.append(f"{pack.name}: key pattern for {type_name}: {exc}")
        weight_sets = [(f"intent {n}", i.weights) for n, i in retrieval.intents.items()]
        weight_sets += [(f"weights for {n}", w) for n, w in retrieval.core_intent_weights.items()]
        for where, weights in weight_sets:
            for edge_name in weights:
                if edge_name not in self.edge_types:
                    problems.append(f"{pack.name}: {where} weights unknown edge {edge_name!r}")
        for name, intent in retrieval.intents.items():
            if intent.plugin is not None and intent.plugin not in INTENT_PLUGINS:
                problems.append(
                    f"{pack.name}: intent {name} names unknown plugin {intent.plugin!r} "
                    f"(known: {', '.join(sorted(INTENT_PLUGINS))})"
                )
            for type_name in intent.prefer_types:
                if type_name not in self.node_types:
                    problems.append(
                        f"{pack.name}: intent {name} prefers unknown type {type_name!r}"
                    )
        for name, rule in retrieval.admission.items():
            settings = ADMISSION_RULES.get(name)
            if settings is None:
                problems.append(
                    f"{pack.name}: unknown admission rule {name!r} "
                    f"(known: {', '.join(sorted(ADMISSION_RULES))})"
                )
                continue
            for setting in sorted(set(rule.model_dump(exclude_defaults=True)) - settings):
                problems.append(f"{pack.name}: admission {name} has unknown setting {setting!r}")
            for intent_name in rule.include_for_intents:
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

    def _validate_mappings(self, pack: Pack, problems: list[str]) -> None:
        for vocabulary, terms in pack.mappings.items():
            for term in terms:
                if term not in self.node_types and term not in self.edge_types:
                    problems.append(f"{pack.name}: mappings.{vocabulary} names unknown {term!r}")

    def _version_hash(self) -> str:
        digest = hashlib.sha256()
        for name in sorted(self._packs):
            digest.update(self._packs[name].canonical_json().encode())
        return f"sha256:{digest.hexdigest()[:16]}"


def _paths(tree: Node) -> list[Path]:
    if isinstance(tree, Path):
        return [tree]
    if isinstance(tree, Call):
        return [p for arg in tree.args for p in _paths(arg)]
    if isinstance(tree, Concat):
        return [p for part in tree.parts for p in _paths(part)]
    return []


def _target_states(value: str) -> list[str]:
    """The states a transition can move to: the literal, or a map's values."""
    if not is_expression(value):
        return [value]
    try:
        tree = compile_value(value)
    except ExpressionError:
        return []
    if isinstance(tree, Call) and tree.name == "map" and isinstance(tree.args[1], MapLiteral):
        return [state for _key, state in tree.args[1].entries]
    return []


def _compare(actual: str, operator: str, wanted: str) -> bool:
    left, right = _version_tuple(actual), _version_tuple(wanted)
    return {
        ">=": left >= right,
        "<=": left <= right,
        "==": left == right,
        ">": left > right,
        "<": left < right,
    }[operator]
