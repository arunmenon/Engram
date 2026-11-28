"""How an ontology change is applied (ADR-0018 decision 8, phase 3).

``classify_change(old, new)`` compares two composed registries and says
how a graph built under ``old`` is brought to ``new``:

- ``none``: the same packs;
- ``initial``: the graph records no ontology yet;
- ``additive``: new types, edges, properties, states, events, intents,
  weights, keywords, extraction or lifecycle settings. Applied hot: new
  schema, then new events project under the new rules;
- ``mapping``: a projection rule changed or was added for an event type
  the ledger may already hold. Applied by replaying those event types into
  the live graph (writes are idempotent upserts);
- ``breaking``: a type or edge removed, a key, identity property or
  property type changed, an edge endpoint or lifecycle state removed, a
  lifecycle's initial state or effective link defaults changed, or a
  projection rule removed. Applied
  by building a fresh projection from the ledger under the new version
  (blue/green), gated on the packs' evaluation sets, then switching.

Each part of a rule (an upsert, its transition, an edge) keeps its identity
when it writes the same type by the same key or match expressions. A part
whose identity changed or that was removed is breaking (a replay would
leave the old nodes behind as duplicates); added parts, and changed
values, conditions or target states, are a mapping change. A widened
enum is additive; a narrowed one is breaking. Endpoints are compared as the
types they allow, so widening to a pack wildcard is additive.

It also checks each pack's own version against what changed in it
(``version_problems``): a pack whose content changed must have a higher
version; a breaking change needs a new major version, and a mapping or
additive change a new minor one. Before 1.0 (semver's initial development)
a breaking change needs a new minor version and anything else a patch.

``eval_required`` lists packs whose retrieval section changed: decision 10
says their weights are not trusted until their evaluation set passes.

``admission_changes`` separately reports producer compatibility. Potentially
restrictive payload or handling changes require the stronger version bump,
but do not by themselves require a graph rebuild or replay. Graph operations
remain in ``kind`` and ``pack_changes``. Proven validation relaxations are
compatible; type changes and other unproven inclusions remain conservative.

Pure Python; no framework imports.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from context_graph.domain.ontology import OPEN_PACKS

if TYPE_CHECKING:
    from context_graph.domain.ontology import OntologyRegistry, Pack
    from context_graph.domain.pack_contracts import PayloadContract, PayloadField

ChangeKind = Literal["none", "initial", "additive", "mapping", "breaking"]
AdmissionChangeKind = Literal["additive", "breaking"]
_ORDER: dict[str, int] = {"none": 0, "initial": 1, "additive": 2, "mapping": 3, "breaking": 4}


@dataclass
class ChangePlan:
    kind: ChangeKind = "none"
    reasons: list[str] = field(default_factory=list)
    # Event types whose projection changed (mapping: replay these)
    replay_event_types: set[str] = field(default_factory=set)
    # Packs whose retrieval changed (their evaluation set must pass)
    eval_required: set[str] = field(default_factory=set)
    version_problems: list[str] = field(default_factory=list)
    # Pack name -> graph-application kind (admission compatibility is separate)
    pack_changes: dict[str, ChangeKind] = field(default_factory=dict)
    # Producer compatibility is independent of the graph operation above.
    admission_changes: dict[str, AdmissionChangeKind] = field(default_factory=dict)

    def note(self, kind: ChangeKind, reason: str, pack: str | None = None) -> None:
        if _ORDER[kind] > _ORDER[self.kind]:
            self.kind = kind
        if pack is not None and _ORDER[kind] > _ORDER[self.pack_changes.get(pack, "none")]:
            self.pack_changes[pack] = kind
        self.reasons.append(reason)

    def note_admission(self, kind: AdmissionChangeKind, reason: str, event: str, pack: str) -> None:
        self.note("additive", reason, pack)
        if _ORDER[kind] > _ORDER[self.admission_changes.get(event, "none")]:
            self.admission_changes[event] = kind

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "reasons": self.reasons,
            "replay_event_types": sorted(self.replay_event_types),
            "eval_required": sorted(self.eval_required),
            "version_problems": self.version_problems,
            "pack_changes": dict(sorted(self.pack_changes.items())),
            "admission_changes": dict(sorted(self.admission_changes.items())),
        }


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def _spec(spec: Any) -> str:
    return _canonical(spec.model_dump() if hasattr(spec, "model_dump") else spec)


def _spec_change(before: Any, after: Any) -> ChangeKind:
    """``none``, ``additive`` (an enum widened) or ``breaking`` (any other type change)."""
    if _spec(before) == _spec(after):
        return "none"
    old_values, new_values = getattr(before, "enum", None), getattr(after, "enum", None)
    if old_values is not None and new_values is not None and set(old_values) <= set(new_values):
        return "additive"
    return "breaking"


def _endpoints(registry: OntologyRegistry, types: set[str], packs: set[str]) -> set[str]:
    """The node types an edge end allows: named types plus every type of a wildcard pack."""
    return types | {name for name, t in registry.node_types.items() if t.pack in packs}


def _parse_version(version: str) -> tuple[int, int, int]:
    parts = [int(p) for p in version.split(".")[:3] if p.isdigit()]
    while len(parts) < 3:
        parts.append(0)
    return parts[0], parts[1], parts[2]


def _needed_bump(kind: ChangeKind, old: tuple[int, int, int]) -> Literal["major", "minor", "patch"]:
    if old[0] < 1:
        return "minor" if kind == "breaking" else "patch"
    if kind == "breaking":
        return "major"
    if kind in ("mapping", "additive"):
        return "minor"
    return "patch"


def _bumped(old: tuple[int, int, int], new: tuple[int, int, int]) -> str | None:
    if new <= old:
        return None
    if new[0] > old[0]:
        return "major"
    if new[1] > old[1]:
        return "minor"
    return "patch"


_RANK = {"patch": 0, "minor": 1, "major": 2}


def classify_change(old: OntologyRegistry | None, new: OntologyRegistry) -> ChangePlan:
    plan = ChangePlan()
    if old is None:
        plan.note("initial", "the graph records no ontology version")
        # Decision 10 from the first deploy: no pack's weights are trusted unevaluated
        plan.eval_required = {
            p.name for p in new.packs if p.name not in OPEN_PACKS and p.retrieval.intents
        }
        return plan
    if old.version == new.version:
        return plan
    _compare_nodes(old, new, plan)
    _compare_edges(old, new, plan)
    _compare_events(old, new, plan)
    _compare_rules(old, new, plan)
    _compare_packs(old, new, plan)
    if plan.kind == "none":
        # Only descriptions, notes or mappings changed
        plan.note("additive", "documentation or vocabulary changed")
    _check_versions(old, new, plan)
    return plan


def _compare_nodes(old: OntologyRegistry, new: OntologyRegistry, plan: ChangePlan) -> None:
    for name, before in old.node_types.items():
        after = new.node_types.get(name)
        if after is None:
            plan.note("breaking", f"node type {name} removed", before.pack)
            continue
        pack = after.pack
        if before.definition.ordering != after.definition.ordering:
            plan.note(
                "breaking",
                f"node type {name}: ordering authority changed; explicit rebuild required",
                pack,
            )
        if before.key != after.key or before.key_property != after.key_property:
            plan.note("breaking", f"node type {name}: key changed", pack)
        for prop, spec in before.properties.items():
            if prop not in after.properties:
                plan.note("breaking", f"node type {name}: property {prop} removed", pack)
                continue
            change = _spec_change(spec, after.properties[prop])
            if change == "breaking":
                plan.note("breaking", f"node type {name}: property {prop} changed type", pack)
            elif change == "additive":
                plan.note("additive", f"node type {name}: property {prop} enum widened", pack)
        for prop in sorted(set(after.properties) - set(before.properties)):
            plan.note("additive", f"node type {name}: property {prop} added", pack)
        old_life, new_life = before.lifecycle, after.lifecycle
        if old_life is not None and new_life is None:
            plan.note("breaking", f"node type {name}: lifecycle removed", pack)
        elif old_life is not None and new_life is not None:
            if old_life.initial != new_life.initial:
                plan.note("breaking", f"node type {name}: initial state changed", pack)
            for state in old_life.states:
                if state not in new_life.states:
                    plan.note("breaking", f"node type {name}: state {state} removed", pack)
            for state in new_life.states:
                if state not in old_life.states:
                    plan.note("additive", f"node type {name}: state {state} added", pack)
        elif new_life is not None:
            plan.note("additive", f"node type {name}: lifecycle added", pack)
        if _canonical(before.definition.model_dump(exclude={"note"})) != _canonical(
            after.definition.model_dump(exclude={"note"})
        ):
            plan.note("additive", f"node type {name}: definition changed", pack)
    for name in sorted(set(new.node_types) - set(old.node_types)):
        plan.note("additive", f"node type {name} added", new.node_types[name].pack)


def _compare_edges(old: OntologyRegistry, new: OntologyRegistry, plan: ChangePlan) -> None:
    for name, before in old.edge_types.items():
        after = new.edge_types.get(name)
        if after is None:
            plan.note("breaking", f"edge type {name} removed", before.pack)
            continue
        pack = after.pack
        if before.link_defaults != after.link_defaults:
            # Replay merges writes and retains removed default properties.
            # Treat all default edits conservatively rather than assume
            # in-place convergence for every backend and projection rule.
            plan.note(
                "breaking",
                f"edge type {name}: effective link defaults changed; "
                "rebuild a fresh graph to reconcile existing relationships",
                pack,
            )
        old_from = _endpoints(old, before.from_types, before.from_packs)
        old_to = _endpoints(old, before.to_types, before.to_packs)
        new_from = _endpoints(new, after.from_types, after.from_packs)
        new_to = _endpoints(new, after.to_types, after.to_packs)
        dropped = sorted((old_from - new_from) | (old_to - new_to))
        if dropped:
            plan.note("breaking", f"edge type {name}: endpoints removed: {dropped}", pack)
        widened = False
        for prop, spec in before.properties.items():
            if prop not in after.properties:
                plan.note("breaking", f"edge type {name}: property {prop} removed", pack)
                continue
            change = _spec_change(spec, after.properties[prop])
            if change == "breaking":
                plan.note("breaking", f"edge type {name}: property {prop} changed type", pack)
            widened = widened or change == "additive"
        added = (new_from - old_from) | (new_to - old_to)
        if added or widened or set(after.properties) - set(before.properties):
            plan.note("additive", f"edge type {name}: endpoints or properties added", pack)
    for name in sorted(set(new.edge_types) - set(old.edge_types)):
        plan.note("additive", f"edge type {name} added", new.edge_types[name].pack)


def _compare_events(old: OntologyRegistry, new: OntologyRegistry, plan: ChangePlan) -> None:
    old_consumers, new_consumers = _processing_events(old), _processing_events(new)
    old_open_namespaces = {
        namespace
        for pack in old.packs
        if pack.name == "core"
        for namespace in pack.open_event_namespaces
    }
    for name, before in old.event_types.items():
        after = new.event_types.get(name)
        if after is None:
            plan.note("breaking", f"event type {name} removed", before.pack)
            continue
        if before.pack != after.pack:
            # Ownership changes alter core/domain admission defaults. Do not
            # prove compatibility using the new owner's policy on both sides.
            plan.note_admission(
                "breaking",
                f"event {name}: owner changed from {before.pack} to {after.pack}; "
                "review producer compatibility before adoption.",
                name,
                after.pack,
            )
            continue
        contract_changed = _spec(before.definition.payload_contract) != _spec(
            after.definition.payload_contract
        )
        if contract_changed:
            compatible = _contract_accepts(
                before.definition.payload_contract, after.definition.payload_contract
            )
            if before.definition.payload_contract is None:
                # Domain admission requires a declared contract; core events
                # without one are unrestricted by payload validation.
                compatible = after.pack != "core"
            elif after.definition.payload_contract is None:
                compatible = after.pack == "core"
            equivalent = compatible and _contract_accepts(
                after.definition.payload_contract, before.definition.payload_contract
            )
            if not equivalent:
                effect = (
                    "declared validation remains compatible with previously valid payloads. "
                    if compatible
                    else "new event submissions that passed previous validation may be rejected. "
                )
                if before.definition.payload_contract is None and after.pack != "core":
                    effect = (
                        "a contract is required for domain event admission; "
                        "review newly eligible submissions. "
                    )
                elif after.definition.payload_contract is None and after.pack != "core":
                    effect = "new domain submissions are rejected without a payload contract. "
                summary = _contract_summary(
                    before.definition.payload_contract, after.definition.payload_contract
                )
                plan.note_admission(
                    "additive" if compatible else "breaking",
                    f"event {name}: {summary}; {effect}"
                    "Review producer compatibility before adoption.",
                    name,
                    after.pack,
                )
        old_handling = _event_handling(old, name, old_consumers)
        new_handling = _event_handling(new, name, new_consumers)
        if old_handling != new_handling and (
            contract_changed or before.definition.handling != after.definition.handling
        ):
            compatible = old_handling == "unsupported" or (
                old_handling == "ledger_only" and new_handling == "processed"
            )
            plan.note_admission(
                "additive" if compatible else "breaking",
                f"event {name}: handling changed from {old_handling} to {new_handling}; "
                + (
                    "new submissions will be rejected."
                    if new_handling == "unsupported"
                    else "review how new events are recorded and processed before adoption."
                ),
                name,
                after.pack,
            )
        elif before.definition.handling != after.definition.handling:
            plan.note(
                "additive",
                f"event {name}: handling declaration changed; effective handling remains "
                f"{new_handling} under the current contract and processing declarations.",
                after.pack,
            )
    for name in sorted(set(new.event_types) - set(old.event_types)):
        plan.note("additive", f"event type {name} added", new.event_types[name].pack)
        declaration = new.event_types[name]
        if (
            declaration.pack == "core"
            and declaration.definition.payload_contract is not None
            and name.partition(".")[0] in old_open_namespaces
        ):
            plan.note_admission(
                "breaking",
                f"event {name}: payload validation added for a previously open event; "
                "new submissions previously accepted may be rejected. "
                "Review producers before adoption.",
                name,
                declaration.pack,
            )


def _processing_events(registry: OntologyRegistry) -> set[str]:
    return set(registry.projection_rules) | {
        source.rpartition(":")[2]
        for pack in registry.packs
        if pack.extraction.propose
        for source in pack.extraction.sources
    }


def _event_handling(registry: OntologyRegistry, name: str, consumers: set[str]) -> str:
    """Declared processing fallback, matching the compiled admission inventory."""
    declaration = registry.event_types[name]
    has_consumers = declaration.pack == "core" or name in consumers
    handling = declaration.definition.handling or ("processed" if has_consumers else "unsupported")
    if declaration.pack != "core" and declaration.definition.payload_contract is None:
        return "unsupported"
    return "unsupported" if handling == "processed" and not has_consumers else handling


def _contract_accepts(before: PayloadContract | None, after: PayloadContract | None) -> bool:
    """Conservatively prove the new declaration accepts every old valid payload."""
    if before is None or after is None:
        return before is after
    return _object_accepts(
        before.properties, after.properties, before.additional_fields, after.additional_fields
    )


def _contract_summary(before: PayloadContract | None, after: PayloadContract | None) -> str:
    if before is None:
        return "payload validation added"
    if after is None:
        return "payload validation removed"
    changes = []
    if before.additional_fields != after.additional_fields:
        changes.append(
            "unexpected payload fields "
            + ("now rejected" if after.additional_fields == "forbid" else "now allowed")
        )
    for name in sorted(before.properties.keys() | after.properties.keys()):
        old, new = before.properties.get(name), after.properties.get(name)
        if _spec(old) == _spec(new):
            continue
        detail = "validation changed"
        if old is None:
            detail = "validation added"
        elif new is None:
            detail = "validation removed"
        elif old.required != new.required:
            detail = "now required" if new.required else "no longer required"
            if _spec(old.model_dump(exclude={"required"})) != _spec(
                new.model_dump(exclude={"required"})
            ):
                detail += " and validation changed"
        changes.append(f"payload field {name!r}: {detail}")
    return "; ".join(changes[:5]) + (
        f"; {len(changes) - 5} more changed fields" if len(changes) > 5 else ""
    )


def _object_accepts(
    before: dict[str, PayloadField],
    after: dict[str, PayloadField],
    old_extra: str,
    new_extra: str,
) -> bool:
    if old_extra == "preserve" and new_extra == "forbid":
        return False
    if new_extra == "forbid" and before.keys() - after.keys():
        return False
    for name, new in after.items():
        old = before.get(name)
        if old is None:
            # An optional field restricts arbitrary old extras unless the old
            # object forbade that field entirely.
            if new.required or old_extra == "preserve":
                return False
        elif (new.required and not old.required) or not _field_accepts(old, new):
            return False
    return True


def _range_accepts(
    old_min: int | float | None,
    old_max: int | float | None,
    new_min: int | float | None,
    new_max: int | float | None,
) -> bool:
    return (new_min is None or (old_min is not None and new_min <= old_min)) and (
        new_max is None or (old_max is not None and new_max >= old_max)
    )


def _field_accepts(before: PayloadField, after: PayloadField) -> bool:
    if before.type != after.type or (before.nullable and not after.nullable):
        return False
    if before.type == "object":
        return _object_accepts(
            before.properties, after.properties, before.additional_fields, after.additional_fields
        )
    if before.type == "string" and before.enum is not None:
        # Enum order is not executable. Consider only old values that could
        # actually pass its length bounds.
        return all(
            (after.enum is None or value in after.enum)
            and (after.min_length is None or len(value) >= after.min_length)
            and (after.max_length is None or len(value) <= after.max_length)
            for value in before.enum
            if (before.min_length is None or len(value) >= before.min_length)
            and (before.max_length is None or len(value) <= before.max_length)
        )
    if after.enum is not None and before.enum is None:
        return False
    if before.type in {"string", "array"} and not _range_accepts(
        before.min_length or 0, before.max_length, after.min_length or 0, after.max_length
    ):
        return False
    if before.type == "array":
        assert before.items is not None and after.items is not None
        return _field_accepts(before.items, after.items)
    if before.type in {"integer", "number"}:
        return _range_accepts(before.minimum, before.maximum, after.minimum, after.maximum)
    return True


def _rules(registry: OntologyRegistry) -> dict[str, list[str]]:
    return {
        event: sorted(_canonical(rule.model_dump(by_alias=True)) for _pack, rule in rules)
        for event, rules in registry.projection_rules.items()
    }


def _parts(rule: Any) -> list[str]:
    """What a rule writes, one entry per upsert, transition and edge.

    Each part is identified by its type and key (or match) expressions, not by
    the values it sets. Parts are compared one by one, so adding an edge to a
    rule keeps the identities of the parts it had.
    """
    data = rule.model_dump(by_alias=True)
    ends = ("from", "to", "to_each", "to_latest")
    keep = ("type", "key", "node_id", "match", "match_any_prefix", *ends)

    def strip(value: Any) -> Any:
        """Keep a part's type and key expressions (and its endpoints'), drop set values."""
        if not isinstance(value, dict):
            return value
        return {k: (strip(v) if k in ends else v) for k, v in value.items() if k in keep and v}

    parts = [_canonical({"upsert": strip(u)}) for u in data.get("upsert") or []]
    transition = data.get("transition")
    if transition is not None:
        parts.append(
            _canonical(
                {"transition": {"type": transition.get("type"), "key": transition.get("key")}}
            )
        )
    parts += [_canonical({"edge": strip(e)}) for e in data.get("edges") or []]
    return parts


def _identities(registry: OntologyRegistry) -> dict[str, list[str]]:
    return {
        event: sorted(part for _pack, rule in rules for part in _parts(rule))
        for event, rules in registry.projection_rules.items()
    }


def _compare_rules(old: OntologyRegistry, new: OntologyRegistry, plan: ChangePlan) -> None:
    before, after = _rules(old), _rules(new)
    old_ids, new_ids = _identities(old), _identities(new)
    for event in sorted(set(before) | set(after)):
        old_rules, new_rules = before.get(event, []), after.get(event, [])
        if old_rules == new_rules:
            continue
        owner = new.event_types.get(event) or old.event_types.get(event)
        pack = owner.pack if owner is not None else None
        if not new_rules:
            plan.note("breaking", f"projection of {event} removed", pack)
            continue
        missing = [i for i in old_ids.get(event, []) if i not in new_ids.get(event, [])]
        if missing:
            # A replay would write nodes under new keys and leave the old ones behind
            plan.note(
                "breaking", f"projection of {event}: a part's keys changed or it was removed", pack
            )
            continue
        if set(old_rules) - set(new_rules):
            # A changed rule: what it wrote before may differ from what it writes now
            plan.note("mapping", f"projection of {event} changed", pack)
        else:
            plan.note("mapping", f"projection of {event} added", pack)
        plan.replay_event_types.add(event)


def _compare_packs(old: OntologyRegistry, new: OntologyRegistry, plan: ChangePlan) -> None:
    old_packs = {p.name: p for p in old.packs}
    new_packs = {p.name: p for p in new.packs}
    for name in sorted(set(old_packs) - set(new_packs)):
        plan.note("breaking", f"pack {name} removed", name)
    for name in sorted(set(new_packs) - set(old_packs)):
        plan.note("additive", f"pack {name} added", name)
        if new_packs[name].retrieval.intents:
            plan.eval_required.add(name)
    for name in sorted(set(old_packs) & set(new_packs)):
        before, after = old_packs[name], new_packs[name]
        if before.processing != after.processing:
            removed = set(before.processing.enabled) - set(after.processing.enabled) or set(
                before.processing.requires
            ) - set(after.processing.requires)
            plan.note(
                "breaking" if removed else "additive",
                f"pack {name}: processing changed; activation/catch-up needs explicit policy",
                name,
            )
        for section in ("extraction", "lifecycle", "retrieval", "interfaces", "mappings"):
            if _section(before, section) != _section(after, section):
                plan.note("additive", f"pack {name}: {section} changed", name)
                if section == "retrieval":
                    plan.eval_required.add(name)


def _section(pack: Pack, section: str) -> str:
    value = getattr(pack, section)
    if hasattr(value, "model_dump"):
        return _canonical(value.model_dump(by_alias=True))
    return _canonical(
        {k: v.model_dump() if hasattr(v, "model_dump") else v for k, v in value.items()}
    )


def _check_versions(old: OntologyRegistry, new: OntologyRegistry, plan: ChangePlan) -> None:
    old_packs = {p.name: p for p in old.packs}
    version_kinds = dict(plan.pack_changes)
    for event, kind in plan.admission_changes.items():
        pack_name = new.event_types[event].pack
        if _ORDER[kind] > _ORDER[version_kinds.get(pack_name, "none")]:
            version_kinds[pack_name] = kind
    for pack in new.packs:
        before = old_packs.get(pack.name)
        if before is None or before.canonical_json() == pack.canonical_json():
            continue
        old_version, new_version = _parse_version(before.version), _parse_version(pack.version)
        bumped = _bumped(old_version, new_version)
        if bumped is None:
            plan.version_problems.append(
                f"{pack.name}: content changed but version {pack.version} is not higher "
                f"than {before.version}"
            )
            continue
        change_kind: ChangeKind = version_kinds.get(pack.name, "additive")
        needed = _needed_bump(change_kind, old_version)
        if _RANK[bumped] < _RANK[needed]:
            plan.version_problems.append(
                f"{pack.name}: a {change_kind} change needs a {needed} "
                f"version, but {before.version} -> {pack.version} is a {bumped} one"
            )
