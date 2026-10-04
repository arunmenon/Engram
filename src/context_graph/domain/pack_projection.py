"""Deterministic projection of events through ontology pack rules (ADR-0018).

``PackProjector.plan`` turns one event into a ``ProjectionPlan``: the node
upserts, lifecycle transitions and edges its pack rules declare, plus
lookups for targets found by matching (``to_latest``,
``match_any_prefix``). The projection worker applies the plan through the
``PackGraph`` port; this module does no I/O.

Conventions:
- a pack node is identified by ``node_id`` = ``<Type>:<key values>``, the
  key values in the type's key order, canonicalised by property type
  (datetimes in UTC ISO form, numbers without a fraction as integers),
  with ``%`` and ``|`` percent-encoded and ``|`` between values;
- every node a rule upserts gets ``node_type``, ``ontology_version`` and
  ``updated_at`` (the event's time), its lifecycle's initial state when it
  is created, ``source_trust`` when its type declares it (``trusted`` only
  for events from a configured source), and a ``DERIVED_FROM`` edge to
  the event;
- an edge endpoint named by type and key is created as a stub if missing,
  so a link can arrive before the artifact it points at;
- values missing from the event are not written; a key with a missing
  value produces no node;
- a list-valued expression fans out: one node or edge per element, zipped
  with other lists of the same length and broadcasting scalars;
- required link fields a rule does not set get the declared-link defaults.

Pure Python; no framework or storage imports.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from context_graph.domain.ontology import EnumSpec, NodeRef, transition_key
from context_graph.domain.pack_expressions import Scope, compile_value, evaluate, is_expression
from context_graph.ports.pack_graph import EdgeWrite, NodeWrite, StateChange
from context_graph.ports.pack_graph import NodeRef as GraphRef

if TYPE_CHECKING:
    from context_graph.domain.models import Event
    from context_graph.domain.ontology import (
        EdgeRuleDef,
        NodeType,
        OntologyRegistry,
        ProjectionRule,
        PropertySpec,
        RuleValue,
    )

PROVENANCE_EDGE = "DERIVED_FROM"


@dataclass(frozen=True)
class EdgeLookup:
    """An edge whose target is found by matching nodes, not by key."""

    edge_type: str
    source: GraphRef
    label: str
    key_property: str
    equals: dict[str, Any]
    # match_any_prefix: a node matches when one of its ``prefix_field``
    # values is a prefix of one of ``prefixes``
    prefix_field: str | None = None
    prefixes: tuple[str, ...] = ()
    # to_latest: only the most recent match
    latest: bool = False
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProjectionPlan:
    nodes: list[NodeWrite] = field(default_factory=list)
    states: list[StateChange] = field(default_factory=list)
    edges: list[EdgeWrite] = field(default_factory=list)
    lookups: list[EdgeLookup] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not (self.nodes or self.states or self.edges or self.lookups)


# ---------------------------------------------------------------------------
# Values
# ---------------------------------------------------------------------------


def _datetime(value: Any) -> str | None:
    if isinstance(value, datetime):
        moment = value
    else:
        try:
            moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).isoformat()


def coerce(value: Any, spec: PropertySpec | None) -> Any:
    """A value as the declared property type, or None if it does not fit."""
    if value is None:
        return None
    if spec is None:
        return value
    if isinstance(spec, dict):
        spec = EnumSpec.model_validate(spec)
    if isinstance(spec, EnumSpec):
        text = str(value)
        return text if text in spec.enum else None
    if spec.startswith("list<"):
        inner = spec[5:-1]
        items = value if isinstance(value, list) else [value]
        coerced = [coerce(item, inner) for item in items]
        return [item for item in coerced if item is not None]
    if isinstance(value, list):
        return None
    try:
        if spec == "int":
            if isinstance(value, bool):
                return None
            number = float(value)
            return int(number) if math.isfinite(number) and number == int(number) else None
        if spec == "float":
            if isinstance(value, bool):
                return None
            number = float(value)
            return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None
    if spec == "bool":
        if isinstance(value, bool):
            return value
        return {"true": True, "false": False}.get(str(value).lower())
    if spec == "datetime":
        return _datetime(value)
    if spec == "json":
        return value
    return str(value)


def _escape(text: str) -> str:
    return text.replace("%", "%25").replace("|", "%7C")


def make_node_id(type_name: str, key_values: list[Any]) -> str:
    """``<Type>:<v1>|<v2>...`` from already-coerced key values."""
    parts = []
    for value in key_values:
        if isinstance(value, bool):
            parts.append("true" if value else "false")
        else:
            parts.append(_escape(str(value)))
    return f"{type_name}:" + "|".join(parts)


def _truthy(value: Any) -> bool:
    if isinstance(value, list):
        return any(_truthy(item) for item in value)
    return value not in (None, "", False, 0)


def _fan_out(values: dict[str, Any]) -> list[dict[str, Any]]:
    """Expand list values into rows, zipping lists and broadcasting scalars."""
    lengths = {len(v) for v in values.values() if isinstance(v, list)}
    if not lengths:
        return [values]
    count = min(lengths)
    return [
        {k: (v[i] if isinstance(v, list) else v) for k, v in values.items()} for i in range(count)
    ]


# ---------------------------------------------------------------------------
# Projector
# ---------------------------------------------------------------------------


class PackProjector:
    """Plans graph writes for events from the projection rules of the active packs."""

    def __init__(self, registry: OntologyRegistry, trusted_sources: frozenset[str]) -> None:
        self._registry = registry
        self._trusted = trusted_sources
        # Rule values parsed once (validated when the registry was built)
        self._compiled: dict[str, Any] = {}

    @property
    def registry(self) -> OntologyRegistry:
        return self._registry

    def handles(self, event_type: str) -> bool:
        return bool(self._registry.rules_for(event_type))

    def _eval(self, value: RuleValue, scope: Scope) -> Any:
        if not isinstance(value, str) or not is_expression(value):
            return value
        tree = self._compiled.get(value)
        if tree is None:
            tree = self._compiled[value] = compile_value(value)
        return evaluate(tree, scope)

    def plan(self, event: Event, document: dict[str, Any]) -> ProjectionPlan:
        plan = ProjectionPlan()
        rules = self._registry.rules_for(event.event_type)
        if not rules:
            return plan
        payload = document.get("payload")
        envelope = event.model_dump(mode="json")
        envelope["global_position"] = event.global_position or document.get("global_position")
        context = _Context(
            scope=Scope(payload if isinstance(payload, dict) else {}, envelope),
            event_ref=GraphRef("Event", str(event.event_id), "event_id"),
            occurred_at=_datetime(event.occurred_at) or "",
            trust="trusted" if event.agent_id in self._trusted else "untrusted",
        )
        for _pack, rule in rules:
            self._plan_rule(rule, context, plan)
        return plan

    # -- rule parts --------------------------------------------------------------------

    def _node_type(self, ref_type: str) -> NodeType:
        return self._registry.node_type(ref_type.rpartition(":")[2])

    def _keyed_refs(
        self, node_type: NodeType, key: dict[str, RuleValue], scope: Scope
    ) -> list[tuple[GraphRef, dict[str, Any]]]:
        """The nodes a key names (several when a key value is a list)."""
        values = {name: self._eval(expr, scope) for name, expr in key.items()}
        refs = []
        for row in _fan_out(values):
            coerced = {
                name: coerce(row[name], node_type.properties.get(name)) for name in node_type.key
            }
            if any(v is None or v == "" for v in coerced.values()):
                continue
            if node_type.definition.id_property:
                ref = GraphRef(
                    node_type.name, str(coerced[node_type.key[0]]), node_type.key_property
                )
            else:
                ref = GraphRef(node_type.name, make_node_id(node_type.name, list(coerced.values())))
            refs.append((ref, coerced))
        return refs

    def _properties(
        self, node_type: NodeType, values: dict[str, RuleValue], scope: Scope, fan: int, index: int
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, expr in values.items():
            value = self._eval(expr, scope)
            if isinstance(value, list) and fan > 1 and len(value) == fan:
                value = value[index]
            result[name] = coerce(value, node_type.properties.get(name))
        return result

    def _system(self, node_type: NodeType, context: _Context) -> dict[str, Any]:
        props: dict[str, Any] = {
            "node_type": node_type.name,
            "ontology_version": self._registry.version,
        }
        if "source_trust" in node_type.properties:
            props["source_trust"] = context.trust
        return props

    def _defaults(self, node_type: NodeType, context: _Context) -> dict[str, Any]:
        lifecycle = node_type.lifecycle
        if lifecycle is None:
            return {}
        return {"status": lifecycle.initial, "status_changed_at": context.occurred_at}

    def _stub(
        self, node_type: NodeType, ref: GraphRef, key_props: dict[str, Any], context: _Context
    ) -> NodeWrite | None:
        if node_type.definition.id_property:
            return None  # today's types are never created by a reference
        return NodeWrite(
            ref,
            {**key_props, "node_type": node_type.name, "ontology_version": self._registry.version},
            self._defaults(node_type, context),
        )

    def _plan_rule(self, rule: ProjectionRule, context: _Context, plan: ProjectionPlan) -> None:
        scope = context.scope
        for upsert in rule.upsert:
            node_type = self._node_type(upsert.type)
            refs = self._keyed_refs(node_type, upsert.key, scope)
            for index, (ref, key_props) in enumerate(refs):
                props = self._properties(node_type, upsert.set, scope, len(refs), index)
                plan.nodes.append(
                    NodeWrite(
                        ref,
                        {
                            **key_props,
                            **props,
                            **self._system(node_type, context),
                            "updated_at": context.occurred_at,
                        },
                        self._defaults(node_type, context),
                    )
                )
                if self._registry.allows(PROVENANCE_EDGE, node_type.name, "Event"):
                    plan.edges.append(EdgeWrite(PROVENANCE_EDGE, ref, context.event_ref))
        if rule.transition is not None:
            self._plan_transition(rule, context, plan)
        for edge_rule in rule.edges:
            self._plan_edge(edge_rule, context, plan)

    def _plan_transition(
        self, rule: ProjectionRule, context: _Context, plan: ProjectionPlan
    ) -> None:
        transition = rule.transition
        assert transition is not None
        node_type = self._node_type(transition.type)
        lifecycle = node_type.lifecycle
        key = transition_key(rule, node_type.name)
        state = self._eval(transition.to, context.scope)
        if lifecycle is None or key is None or state not in lifecycle.states:
            return
        for ref, _key_props in self._keyed_refs(node_type, key, context.scope):
            plan.states.append(
                StateChange(ref, str(state), context.occurred_at, tuple(transition.only_from))
            )

    def _endpoint_refs(
        self, ref: NodeRef, context: _Context, plan: ProjectionPlan
    ) -> list[tuple[str, GraphRef]]:
        """(type name, graph ref) for an endpoint given by key or node_id; stubs keyed ones."""
        if ref.node_id is not None:
            value = self._eval(ref.node_id, context.scope)
            found = []
            for node_id in value if isinstance(value, list) else [value]:
                parsed = self._parse_node_id(node_id)
                if parsed is not None:
                    found.append(parsed)
            return found
        assert ref.type is not None and ref.key is not None
        node_type = self._node_type(ref.type)
        refs = []
        for graph_ref, key_props in self._keyed_refs(node_type, ref.key, context.scope):
            stub = self._stub(node_type, graph_ref, key_props, context)
            if stub is not None:
                plan.nodes.append(stub)
            refs.append((node_type.name, graph_ref))
        return refs

    def _parse_node_id(self, node_id: Any) -> tuple[str, GraphRef] | None:
        if not isinstance(node_id, str) or ":" not in node_id:
            return None
        type_name, _, rest = node_id.partition(":")
        node_type = self._registry.node_types.get(type_name)
        if node_type is None or not rest:
            return None
        if node_type.definition.id_property:
            return type_name, GraphRef(type_name, rest, node_type.key_property)
        return type_name, GraphRef(type_name, node_id)

    def _edge_properties(
        self, edge_rule: EdgeRuleDef, scope: Scope, fan: int, index: int
    ) -> dict[str, Any]:
        edge = self._registry.edge_type(edge_rule.type)
        props: dict[str, Any] = dict(edge.link_defaults)
        for name, expr in edge_rule.set.items():
            value = self._eval(expr, scope)
            if isinstance(value, list) and fan > 1 and len(value) == fan:
                value = value[index]
            value = coerce(value, edge.properties.get(name))
            if value is not None:
                props[name] = value
        return props

    def _plan_edge(self, edge_rule: EdgeRuleDef, context: _Context, plan: ProjectionPlan) -> None:
        scope = context.scope
        if edge_rule.when is not None and not _truthy(self._eval(edge_rule.when, scope)):
            return
        sources = self._endpoint_refs(edge_rule.from_, context, plan)
        target = edge_rule.target
        if target.match is not None or target.match_any_prefix is not None:
            self._plan_lookup(edge_rule, sources, context, plan)
            return
        targets = self._endpoint_refs(target, context, plan)
        for source_type, source in sources:
            for index, (target_type, target_ref) in enumerate(targets):
                if not self._registry.allows(edge_rule.type, source_type, target_type):
                    continue
                props = self._edge_properties(edge_rule, scope, len(targets), index)
                plan.edges.append(EdgeWrite(edge_rule.type, source, target_ref, props))

    def _plan_lookup(
        self,
        edge_rule: EdgeRuleDef,
        sources: list[tuple[str, GraphRef]],
        context: _Context,
        plan: ProjectionPlan,
    ) -> None:
        target = edge_rule.target
        assert target.type is not None
        node_type = self._node_type(target.type)
        equals: dict[str, Any] = {}
        prefix_field: str | None = None
        prefixes: tuple[str, ...] = ()
        for name, expr in (target.match or target.match_any_prefix or {}).items():
            value = self._eval(expr, context.scope)
            if target.match_any_prefix is not None and isinstance(value, list):
                prefix_field, prefixes = name, tuple(str(v) for v in value if v is not None)
                continue
            value = coerce(value, node_type.properties.get(name))
            if value is None:
                return  # a match on a missing value finds nothing
            equals[name] = value
        props = self._edge_properties(edge_rule, context.scope, 1, 0)
        for source_type, source in sources:
            if not self._registry.allows(edge_rule.type, source_type, node_type.name):
                continue
            plan.lookups.append(
                EdgeLookup(
                    edge_type=edge_rule.type,
                    source=source,
                    label=node_type.name,
                    key_property=node_type.key_property,
                    equals=equals,
                    prefix_field=prefix_field,
                    prefixes=prefixes,
                    latest=edge_rule.to_latest is not None,
                    properties=props,
                )
            )


@dataclass(frozen=True)
class _Context:
    scope: Scope
    event_ref: GraphRef
    occurred_at: str
    trust: str
