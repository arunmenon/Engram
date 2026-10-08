"""Compiled, observational admission contracts for an immutable active bundle.

This policy is pure. The writer must apply new-event decisions alongside duplicate
determination; route diagnostics cannot override an already accepted retry.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ValidationError

from context_graph.domain.ontology import OntologyError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from context_graph.domain.pack_bundle import ActiveBundle

Handling = Literal["processed", "ledger_only", "unsupported"]


@dataclass(frozen=True)
class PayloadProblem:
    path: tuple[str | int, ...]
    code: str


@dataclass(frozen=True)
class AdmissionDecision:
    allowed: bool
    owner: str | None
    handling: Handling
    reason: str | None = None
    problems: tuple[PayloadProblem, ...] = ()


@dataclass(frozen=True)
class EventAdmissionRule:
    event_type: str
    owner: str
    handling: Handling
    consumers: tuple[tuple[str, str], ...]
    contract_declared: bool
    unavailable_reason: str | None = None
    _validator: type[BaseModel] | None = field(default=None, repr=False, compare=False)


@dataclass(frozen=True)
class AdmissionPolicy:
    """One compiled snapshot; never inherit later caller mutations of a registry."""

    bundle_identity: str
    inventory: tuple[EventAdmissionRule, ...]
    core_open_namespaces: frozenset[str]
    _rules: Mapping[str, EventAdmissionRule] = field(repr=False, compare=False)

    def decide(self, event_type: str, payload: Any) -> AdmissionDecision:
        rule = self._rules.get(event_type)
        if rule is None:
            namespace, separator, remainder = event_type.partition(".")
            if separator and remainder and namespace in self.core_open_namespaces:
                return AdmissionDecision(True, "core", "processed")
            return AdmissionDecision(False, None, "unsupported", "event_unsupported")
        if rule.handling == "unsupported":
            return AdmissionDecision(
                False, rule.owner, rule.handling, rule.unavailable_reason or "event_unsupported"
            )
        if rule._validator is not None:
            try:
                rule._validator.model_validate(payload)
            except ValidationError as exc:
                problems = tuple(
                    PayloadProblem(
                        (*error["loc"][:-1], "<extra>")
                        if error["type"] in {"extra_forbidden", "invalid_key"}
                        else tuple(error["loc"]),
                        error["type"],
                    )
                    for error in exc.errors(
                        include_url=False, include_context=False, include_input=False
                    )
                )
                return AdmissionDecision(
                    False, rule.owner, rule.handling, "payload_invalid", problems
                )
        return AdmissionDecision(True, rule.owner, rule.handling)


def compile_admission_policy(bundle: ActiveBundle) -> AdmissionPolicy:
    """Resolve declared contracts and consumers, never infer domain mappings."""
    registry = bundle.registry
    subscribers: dict[str, set[tuple[str, str]]] = {}
    namespaces: set[str] = set()
    problems: list[str] = []
    bindings = frozenset(bundle.processing)
    for pack in registry.packs:
        if pack.open_event_namespaces:
            if pack.name != "core":
                problems.append(f"{pack.name}: only core may declare open event namespaces")
            for namespace in pack.open_event_namespaces:
                if not re.fullmatch(r"[a-z][a-z0-9_]*", namespace):
                    problems.append(f"{pack.name}: invalid open event namespace")
                elif not any(name.startswith(namespace + ".") for name in pack.events):
                    problems.append(f"{pack.name}: open namespace must contain a declared event")
                elif any(
                    declaration.pack != "core" and name.startswith(namespace + ".")
                    for name, declaration in registry.event_types.items()
                ):
                    problems.append(f"{pack.name}: open namespace overlaps another pack")
                else:
                    namespaces.add(namespace)
        if (pack.name, "pack.project.v1") in bindings:
            for rule in pack.projection:
                subscribers.setdefault(rule.event.rpartition(":")[2], set()).add(
                    (pack.name, "pack.project.v1")
                )
        if (pack.name, "pack.extract.v1") in bindings:
            for source in pack.extraction.sources:
                subscribers.setdefault(source.rpartition(":")[2], set()).add(
                    (pack.name, "pack.extract.v1")
                )
    inventory = []
    for name, declaration in sorted(registry.event_types.items()):
        definition = declaration.definition
        consumers = set(subscribers.get(name, ()))
        if declaration.pack == "core":
            consumers.add(("core", "event.project.v1"))
        reason = None
        handling: Handling = definition.handling or ("processed" if consumers else "unsupported")
        if handling in {"ledger_only", "unsupported"} and consumers:
            problems.append(f"{name}: {handling} contradicts enabled processing subscriptions")
        if handling == "processed" and not consumers:
            handling, reason = "unsupported", "processing_unavailable"
        if declaration.pack != "core" and definition.payload_contract is None:
            handling, reason = "unsupported", "payload_contract_missing"
        if handling == "unsupported" and reason is None:
            reason = "event_unsupported"
        inventory.append(
            EventAdmissionRule(
                name,
                declaration.pack,
                handling,
                tuple(sorted(consumers)),
                definition.payload_contract is not None,
                reason,
                definition.payload_contract.compile_validator()
                if definition.payload_contract
                else None,
            )
        )
    if problems:
        raise OntologyError(problems)
    rules = tuple(inventory)
    return AdmissionPolicy(
        bundle.identity,
        rules,
        frozenset(namespaces),
        MappingProxyType({rule.event_type: rule for rule in rules}),
    )
