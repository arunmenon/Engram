"""Strict opt-in property values, separate from legacy expression semantics.

Only literals/direct paths are supported. Wildcards keep result cells and original
positions; result tags never enter graph properties. This module does no I/O.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from context_graph.domain.ontology import EnumSpec, PropertySpec, PropertyUpdateDef
from context_graph.domain.pack_expressions import Literal as ExpressionLiteral
from context_graph.domain.pack_expressions import Path, Scope, compile_value


class PropertyUpdateError(ValueError):
    """Whole-plan refusal with safe reason and declared property name only."""

    def __init__(self, reason: str, property_name: str = "") -> None:
        self.reason = reason
        self.property_name = property_name
        super().__init__(f"Strict property refused: {reason} ({property_name})")


@dataclass(frozen=True)
class PropertyValue:
    kind: Literal["value", "missing", "null", "invalid"]
    value: Any = None
    cells: tuple[PropertyValue, ...] | None = None


def _value(value: Any) -> PropertyValue:
    return PropertyValue("null") if value is None else PropertyValue("value", value)


def _walk(value: Any, steps: tuple[str, ...]) -> PropertyValue:
    if value is None:
        return PropertyValue("null")
    if not steps:
        return _value(value)
    step, rest = steps[0], steps[1:]
    if step == "[*]":
        if not isinstance(value, list):
            return PropertyValue("invalid")
        return PropertyValue("value", cells=tuple(_walk(item, rest) for item in value))
    if not isinstance(value, dict):
        return PropertyValue("invalid")
    if step not in value:
        return PropertyValue("missing")
    return _walk(value[step], rest)


def evaluate_property(definition: PropertyUpdateDef, scope: Scope) -> PropertyValue:
    tree = compile_value(definition.value)
    if isinstance(tree, ExpressionLiteral):
        return _value(tree.value)
    if not isinstance(tree, Path):
        raise PropertyUpdateError("unsupported_expression")
    return _walk(scope.payload if tree.root == "payload" else scope.event, tree.steps)


def _plain(result: PropertyValue) -> Any:
    if result.kind != "value":
        raise PropertyUpdateError("invalid_list_member")
    if result.cells is not None:
        return [_plain(cell) for cell in result.cells]
    return result.value


def _json(value: Any, ancestors: set[int]) -> None:
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) not in (dict, list) or id(value) in ancestors:
        raise PropertyUpdateError("invalid_json")
    ancestors.add(id(value))
    try:
        if isinstance(value, dict):
            if any(type(key) is not str for key in value):
                raise PropertyUpdateError("invalid_json")
            values = value.values()
        else:
            values = value
        for item in values:
            _json(item, ancestors)
    finally:
        ancestors.remove(id(value))


def coerce_property(value: Any, spec: PropertySpec | None) -> Any:
    """Explicit supported conversions; no skipped members or object stringification."""
    if value is None or spec is None:
        raise PropertyUpdateError("invalid_value")
    if isinstance(spec, EnumSpec):
        if isinstance(value, str) and value in spec.enum:
            return value
        raise PropertyUpdateError("invalid_enum")
    if spec.startswith("list<"):
        if not isinstance(value, list):
            raise PropertyUpdateError("invalid_list")
        return [coerce_property(item, spec[5:-1]) for item in value]
    if spec == "json":
        _json(value, set())
        try:
            json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        except (ValueError, UnicodeError, RecursionError) as exc:
            raise PropertyUpdateError("invalid_json") from exc
        return value
    if spec in {"string", "text"} and isinstance(value, str):
        return value
    if spec == "bool":
        if type(value) is bool:
            return value
        if isinstance(value, str) and value.lower() in {"true", "false"}:
            return value.lower() == "true"
    if spec == "int":
        number = None
        if type(value) is int:
            number = value
        elif (type(value) is float and math.isfinite(value) and value.is_integer()) or (
            isinstance(value, str) and re.fullmatch(r"[-+]?\d{1,20}", value.strip())
        ):
            number = int(value)
        if number is not None and -(2**63) <= number <= 2**63 - 1:
            return number
    if spec == "float" and type(value) in {int, float, str}:
        try:
            number_float = float(value)
        except (ValueError, OverflowError):
            pass
        else:
            if math.isfinite(number_float):
                return number_float
    if spec == "datetime" and isinstance(value, str | datetime):
        try:
            moment = (
                value
                if isinstance(value, datetime)
                else datetime.fromisoformat(value.replace("Z", "+00:00"))
            )
            if moment.tzinfo is not None and moment.utcoffset() is not None:
                return moment.astimezone(UTC).isoformat()
        except (ValueError, OverflowError):
            pass
    raise PropertyUpdateError("invalid_value")


def property_action(
    definition: PropertyUpdateDef,
    scope: Scope,
    spec: PropertySpec | None,
    *,
    fanned: bool = False,
    index: int = 0,
    count: int = 1,
) -> tuple[Literal["set", "preserve", "clear"], Any]:
    result = evaluate_property(definition, scope)
    if definition.select == "zip":
        if not fanned:
            raise PropertyUpdateError("zip_requires_fanout")
        if result.kind == "value":
            cells = result.cells
            if cells is None and isinstance(result.value, list):
                cells = tuple(_value(item) for item in result.value)
            if cells is None or len(cells) != count or not 0 <= index < count:
                raise PropertyUpdateError("zip_shape_mismatch")
            result = cells[index]
    if result.kind == "invalid":
        raise PropertyUpdateError("invalid_path")
    if result.kind == "missing":
        if definition.on_missing == "refuse":
            raise PropertyUpdateError("missing_value")
        return "preserve", None
    if result.kind == "null":
        if definition.on_null == "refuse":
            raise PropertyUpdateError("null_value")
        return definition.on_null, None
    return "set", coerce_property(_plain(result), spec)
