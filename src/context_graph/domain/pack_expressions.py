"""The value language of pack projection rules (ADR-0018).

A rule value is either a constant (``jira``, ``1.0``, ``true``) or an
expression over the triggering event:

- ``$.a.b`` reads the event payload; ``$.items[*].id`` reads a field of
  every list element (the result is a list);
- ``$event.x`` reads the event envelope (``occurred_at``,
  ``global_position``, ``event_id``, ``session_id``, ...);
- ``a + b`` concatenates text (a missing operand counts as empty);
- functions (patterns use the ``regex`` engine, each match bounded in
  time by ``MATCH_TIMEOUT_SECONDS``): ``regex(text, 'pattern')`` (first capture group, or the
  whole match), ``regex_all(text, 'pattern')`` (every capture; a capture
  holding a comma-separated list gives one item per entry),
  ``match(text, 'pattern')`` (true or false), ``sha256(text)``,
  ``map(value, {'From': to, ...})`` and ``each(list)``;
- ``'quoted'`` strings, with ``''`` for a quote, and bare words inside
  function arguments and map values.

A value that is missing evaluates to None. Expressions are parsed once
when a pack is loaded, so an invalid one fails validation, not projection.

Pure Python; no framework imports.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

import regex

FUNCTIONS = {
    "regex": 2,
    "regex_all": 2,
    "match": 2,
    "sha256": 1,
    "map": 2,
    "each": 1,
}

# Text a pattern is matched against, at most (bounds regex work per value)
MAX_TEXT_LENGTH = 100_000
# Time one pattern may take on one value. Capping the text does not bound a
# pattern that backtracks catastrophically (``(a+)+$``): this does.
MATCH_TIMEOUT_SECONDS = 0.25


class ExpressionError(ValueError):
    """An expression does not parse."""


class PatternTimeoutError(ValueError):
    """A pattern took longer than ``MATCH_TIMEOUT_SECONDS`` on a value.

    The same pattern on the same value always does, so the event's rules
    fail like any other bad value: the projection worker dead-letters the
    event instead of stalling on it.
    """


# ---------------------------------------------------------------------------
# Syntax tree
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Literal:
    value: Any


@dataclass(frozen=True)
class Path:
    root: str  # "payload" or "event"
    steps: tuple[str, ...]  # field names; "[*]" maps over a list


@dataclass(frozen=True)
class Call:
    name: str
    args: tuple[Node, ...]


@dataclass(frozen=True)
class Concat:
    parts: tuple[Node, ...]


@dataclass(frozen=True)
class MapLiteral:
    entries: tuple[tuple[str, str], ...]


Node = Literal | Path | Call | Concat | MapLiteral


def is_expression(value: object) -> bool:
    """Whether a rule value is an expression rather than a constant."""
    return isinstance(value, str) and (
        value.startswith("$") or re.match(r"^[a-z_][a-z0-9_]*\(", value) is not None
    )


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class _Parser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    def error(self, message: str) -> ExpressionError:
        return ExpressionError(f"{message} at position {self.pos} in {self.text!r}")

    def skip_spaces(self) -> None:
        while self.pos < len(self.text) and self.text[self.pos].isspace():
            self.pos += 1

    def peek(self) -> str:
        self.skip_spaces()
        return self.text[self.pos] if self.pos < len(self.text) else ""

    def expect(self, char: str) -> None:
        if self.peek() != char:
            raise self.error(f"expected {char!r}")
        self.pos += 1

    def parse(self) -> Node:
        node = self.concat()
        if self.peek():
            raise self.error("unexpected text")
        return node

    def concat(self) -> Node:
        parts = [self.term()]
        while self.peek() == "+":
            self.pos += 1
            parts.append(self.term())
        return parts[0] if len(parts) == 1 else Concat(tuple(parts))

    def term(self) -> Node:
        char = self.peek()
        if char == "$":
            return self.path()
        if char == "'":
            return Literal(self.quoted())
        if char == "{":
            return self.map_literal()
        word = self.word()
        if self.peek() == "(":
            return self.call(word)
        return Literal(_constant(word))

    def word(self) -> str:
        self.skip_spaces()
        match = re.compile(r"[A-Za-z0-9_.\-]+").match(self.text, self.pos)
        if not match:
            raise self.error("expected a value")
        self.pos = match.end()
        return match.group(0)

    def quoted(self) -> str:
        self.expect("'")
        chars: list[str] = []
        while True:
            if self.pos >= len(self.text):
                raise self.error("unterminated string")
            char = self.text[self.pos]
            self.pos += 1
            if char == "'":
                if self.pos < len(self.text) and self.text[self.pos] == "'":
                    chars.append("'")
                    self.pos += 1
                    continue
                return "".join(chars)
            chars.append(char)

    def path(self) -> Path:
        self.expect("$")
        root = "payload"
        if self.text.startswith("event", self.pos):
            root = "event"
            self.pos += len("event")
        steps: list[str] = []
        while self.pos < len(self.text):
            if self.text.startswith("[*]", self.pos):
                steps.append("[*]")
                self.pos += 3
                continue
            if self.text[self.pos] != ".":
                break
            self.pos += 1
            match = re.compile(r"[A-Za-z_][A-Za-z0-9_]*").match(self.text, self.pos)
            if not match:
                raise self.error("expected a field name")
            steps.append(match.group(0))
            self.pos = match.end()
        if not steps or steps[0] == "[*]":
            raise self.error("a path needs a field")
        return Path(root, tuple(steps))

    def call(self, name: str) -> Call:
        if name not in FUNCTIONS:
            raise self.error(f"unknown function {name!r}")
        self.expect("(")
        args = [self.concat()]
        while self.peek() == ",":
            self.pos += 1
            args.append(self.concat())
        self.expect(")")
        if len(args) != FUNCTIONS[name]:
            raise self.error(f"{name} takes {FUNCTIONS[name]} argument(s)")
        if name in ("regex", "regex_all", "match"):
            pattern = args[1]
            if not isinstance(pattern, Literal) or not isinstance(pattern.value, str):
                raise self.error(f"{name} needs a quoted pattern")
            try:
                regex.compile(pattern.value)
            except regex.error as exc:
                raise self.error(f"invalid pattern: {exc}") from exc
        if name == "map" and not isinstance(args[1], MapLiteral):
            raise self.error("map needs a {...} table")
        return Call(name, tuple(args))

    def map_literal(self) -> MapLiteral:
        self.expect("{")
        entries: list[tuple[str, str]] = []
        while self.peek() != "}":
            key = self.quoted() if self.peek() == "'" else self.word()
            self.expect(":")
            value = self.quoted() if self.peek() == "'" else self.word()
            entries.append((key, value))
            if self.peek() == ",":
                self.pos += 1
        self.expect("}")
        return MapLiteral(tuple(entries))


def _constant(word: str) -> Any:
    if word in ("true", "false"):
        return word == "true"
    if re.fullmatch(r"-?\d+", word):
        return int(word)
    if re.fullmatch(r"-?\d+\.\d+", word):
        return float(word)
    return word


def parse_expression(text: str) -> Node:
    """Parse a rule value; constants that are not expressions become literals."""
    if not is_expression(text):
        return Literal(text)
    return _Parser(text).parse()


def compile_value(value: Any) -> Node:
    """A rule value (constant or expression) as a syntax tree."""
    if isinstance(value, str):
        return parse_expression(value)
    return Literal(value)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Scope:
    """What an expression can read: the payload and the event envelope."""

    payload: dict[str, Any]
    event: dict[str, Any]


def _walk(value: Any, steps: tuple[str, ...]) -> Any:
    for index, step in enumerate(steps):
        if step == "[*]":
            if not isinstance(value, list):
                return None
            rest = steps[index + 1 :]
            return [_walk(item, rest) for item in value]
        if not isinstance(value, dict):
            return None
        value = value.get(step)
    return value


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        return " ".join(str(v) for v in value if v is not None)[:MAX_TEXT_LENGTH]
    return str(value)[:MAX_TEXT_LENGTH]


def evaluate(node: Node, scope: Scope) -> Any:
    if isinstance(node, Literal):
        return node.value
    if isinstance(node, Path):
        return _walk(scope.payload if node.root == "payload" else scope.event, node.steps)
    if isinstance(node, Concat):
        parts = [_text(evaluate(part, scope)) for part in node.parts]
        if all(part is None for part in parts):
            return None
        return "".join(part or "" for part in parts)
    if isinstance(node, MapLiteral):
        return dict(node.entries)
    return _call(node, scope)


def _call(node: Call, scope: Scope) -> Any:
    name = node.name
    first = evaluate(node.args[0], scope)
    if name == "each":
        if first is None:
            return []
        return first if isinstance(first, list) else [first]
    if name == "sha256":
        text = _text(first)
        return None if text is None else hashlib.sha256(text.encode()).hexdigest()
    if name == "map":
        table = evaluate(node.args[1], scope)
        return None if first is None else table.get(str(first))
    pattern = node.args[1]
    assert isinstance(pattern, Literal)
    text = _text(first)
    if text is None:
        return [] if name == "regex_all" else (False if name == "match" else None)
    try:
        if name == "match":
            return regex.search(pattern.value, text, timeout=MATCH_TIMEOUT_SECONDS) is not None
        if name == "regex":
            found = regex.search(pattern.value, text, timeout=MATCH_TIMEOUT_SECONDS)
            if found is None:
                return None
            return found.group(1) if found.groups() else found.group(0)
        # regex_all: every capture (the first group, or the whole match), in order
        results: list[str] = []
        for found in regex.finditer(pattern.value, text, timeout=MATCH_TIMEOUT_SECONDS):
            captured = found.group(1) if found.groups() else found.group(0)
            if captured is not None:
                results.extend(part.strip() for part in captured.split(",") if part.strip())
        return results
    except TimeoutError as exc:
        msg = (
            f"{name}() pattern {pattern.value!r} took over {MATCH_TIMEOUT_SECONDS}s "
            f"on a {len(text)}-character value"
        )
        raise PatternTimeoutError(msg) from exc
