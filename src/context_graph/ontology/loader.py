"""Load ontology packs from YAML files and compose them (ADR-0018).

Pack files are parsed strictly:
- ``on``/``off``/``yes``/``no`` stay strings (YAML 1.1 would read them as
  booleans; only ``true``/``false`` are booleans);
- dates and times stay strings;
- duplicate keys and non-string keys are errors.

Packs are found by name as ``<name>.pack.yaml`` in the configured
directories, then in the built-in directory. Packs a pack ``requires``
are loaded with it, and the base packs (``core``, ``memory``, ``user``)
are always loaded.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from context_graph.domain.ontology import OntologyError, OntologyRegistry, Pack

BUILTIN_PACK_DIR = Path(__file__).parent / "packs"

# Today's schema, which the code writes; always active
BASE_PACKS = ("core", "memory", "user")

_REQUIRED_NAME = re.compile(r"^([a-z][a-z0-9_]*)")


_TAG = "tag:yaml.org,2002:"

# Only these tags may appear, implicitly or explicitly
_ALLOWED_TAGS = frozenset(_TAG + t for t in ("str", "int", "float", "bool", "null", "seq", "map"))


class _PackLoader(yaml.SafeLoader):
    """SafeLoader narrowed for pack files.

    - booleans are only ``true``/``false``; ``on``, ``yes``, ``no`` are text;
    - integers are decimal (no octal ``010`` or sexagesimal ``1:30``);
    - floats are decimal (no ``.nan``/``.inf``);
    - dates stay text; other tags (``!!set``, ``!!binary``, ...) are errors;
    - aliases and merge keys (``<<``) are errors, so a small file cannot
      expand into a huge document;
    - duplicate and non-string keys are errors.
    """

    def compose_node(self, parent: Any, index: Any) -> Any:
        if self.check_event(yaml.events.AliasEvent):
            event = self.peek_event()  # type: ignore[no-untyped-call]
            raise yaml.composer.ComposerError(
                None, None, "aliases are not allowed in pack files", event.start_mark
            )
        node = super().compose_node(parent, index)
        if node is not None and node.tag not in _ALLOWED_TAGS:
            raise yaml.constructor.ConstructorError(
                None, None, f"tag {node.tag!r} is not allowed in pack files", node.start_mark
            )
        return node


_REPLACED = {_TAG + t for t in ("bool", "int", "float", "timestamp", "merge")}
_PackLoader.yaml_implicit_resolvers = {
    first: [(tag, regexp) for tag, regexp in resolvers if tag not in _REPLACED]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_PackLoader.add_implicit_resolver(
    _TAG + "bool", re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"), list("tTfF")
)
_PackLoader.add_implicit_resolver(
    _TAG + "int", re.compile(r"^[-+]?(?:0|[1-9][0-9]*)$"), list("-+0123456789")
)
_PackLoader.add_implicit_resolver(
    _TAG + "float",
    re.compile(r"^[-+]?(?:[0-9]+\.[0-9]*|\.[0-9]+)(?:[eE][-+]?[0-9]+)?$"),
    list("-+0123456789."),
)


def _construct_bool(loader: _PackLoader, node: yaml.ScalarNode) -> bool:
    value = loader.construct_scalar(node)
    if value.lower() not in ("true", "false"):
        raise yaml.constructor.ConstructorError(
            None, None, f"{value!r} is not a boolean (use true or false)", node.start_mark
        )
    return value.lower() == "true"


def _construct_int(loader: _PackLoader, node: yaml.ScalarNode) -> int:
    value = loader.construct_scalar(node)
    if not re.fullmatch(r"[-+]?(?:0|[1-9][0-9]*)", value):
        raise yaml.constructor.ConstructorError(
            None, None, f"{value!r} is not a decimal integer", node.start_mark
        )
    return int(value)


def _construct_float(loader: _PackLoader, node: yaml.ScalarNode) -> float:
    value = loader.construct_scalar(node)
    try:
        number = float(value)
    except ValueError:
        number = float("nan")
    if number != number or number in (float("inf"), float("-inf")):
        raise yaml.constructor.ConstructorError(
            None, None, f"{value!r} is not a finite decimal number", node.start_mark
        )
    return number


def _construct_mapping(loader: _PackLoader, node: yaml.MappingNode) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if not isinstance(key, str):
            msg = f"non-string key {key!r} at line {key_node.start_mark.line + 1}"
            raise yaml.constructor.ConstructorError(None, None, msg, key_node.start_mark)
        if key in mapping:
            msg = f"duplicate key {key!r} at line {key_node.start_mark.line + 1}"
            raise yaml.constructor.ConstructorError(None, None, msg, key_node.start_mark)
        mapping[key] = loader.construct_object(value_node, deep=True)
    return mapping


_PackLoader.add_constructor(_TAG + "bool", _construct_bool)
_PackLoader.add_constructor(_TAG + "int", _construct_int)
_PackLoader.add_constructor(_TAG + "float", _construct_float)
_PackLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def load_yaml(text: str, source: str) -> Any:
    """YAML read with the pack loader's strict rules (no aliases, tags or YAML 1.1 booleans)."""
    try:
        return yaml.load(text, Loader=_PackLoader)  # noqa: S506 - _PackLoader is a SafeLoader
    except yaml.YAMLError as exc:
        raise OntologyError([f"{source}: {exc}"]) from exc


def parse_pack(text: str, source: str = "<pack>") -> Pack:
    """Parse and check one pack's YAML text."""
    data = load_yaml(text, source)
    if not isinstance(data, dict):
        raise OntologyError([f"{source}: a pack must be a mapping"])
    try:
        return Pack.model_validate(data)
    except ValidationError as exc:
        problems = [
            f"{source}: {'.'.join(str(p) for p in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ]
        raise OntologyError(problems) from exc


def load_pack_file(path: Path) -> Pack:
    return parse_pack(path.read_text(encoding="utf-8"), source=str(path))


def find_eval_set(name: str, search_dirs: list[Path]) -> Path | None:
    """A pack's evaluation set, ``<name>.eval.yaml``, in the search dirs or built in."""
    for directory in [*search_dirs, BUILTIN_PACK_DIR]:
        candidate = directory / f"{name}.eval.yaml"
        if candidate.is_file():
            return candidate
    return None


def find_pack(name: str, search_dirs: list[Path]) -> Path:
    for directory in [*search_dirs, BUILTIN_PACK_DIR]:
        candidate = directory / f"{name}.pack.yaml"
        if candidate.is_file():
            return candidate
    searched = ", ".join(str(d) for d in [*search_dirs, BUILTIN_PACK_DIR])
    raise OntologyError([f"pack {name!r} not found in {searched}"])


def load_registry(names: list[str], search_dirs: list[Path] | None = None) -> OntologyRegistry:
    """Load the base packs, the named packs and the packs they require, then compose them."""
    dirs = list(search_dirs or [])
    packs: dict[str, Pack] = {}
    pending = [*BASE_PACKS, *names]
    while pending:
        name = pending.pop(0)
        if name in packs:
            continue
        pack = load_pack_file(find_pack(name, dirs))
        if pack.name != name:
            raise OntologyError([f"file for pack {name!r} declares pack {pack.name!r}"])
        packs[name] = pack
        for requirement in pack.pack.requires:
            match = _REQUIRED_NAME.match(requirement)
            if match:
                pending.append(match.group(1))
    return OntologyRegistry(list(packs.values()))
