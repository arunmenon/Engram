"""Load ontology packs from YAML files and compose them (ADR-0018).

Pack files are parsed strictly:
- ``on``/``off``/``yes``/``no`` stay strings (YAML 1.1 would read them as
  booleans; only ``true``/``false`` are booleans);
- dates and times stay strings;
- duplicate keys and non-string keys are errors.

Packs are found by name as ``<name>.pack.yaml`` in the configured
directories, then in the built-in directory. Packs a pack ``requires``
are loaded with it, and ``core`` is always loaded.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from context_graph.domain.ontology import OntologyError, OntologyRegistry, Pack

BUILTIN_PACK_DIR = Path(__file__).parent / "packs"

_REQUIRED_NAME = re.compile(r"^([a-z][a-z0-9_]*)")


class _PackLoader(yaml.SafeLoader):
    """SafeLoader with YAML 1.2-style booleans, string dates and strict keys."""


# Keep only true/false as booleans, and leave timestamps as strings
_PackLoader.yaml_implicit_resolvers = {
    first: [
        (tag, regexp)
        for tag, regexp in resolvers
        if tag not in ("tag:yaml.org,2002:bool", "tag:yaml.org,2002:timestamp")
    ]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_PackLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
    list("tTfF"),
)


def _construct_mapping(loader: _PackLoader, node: yaml.MappingNode) -> dict[str, Any]:
    loader.flatten_mapping(node)
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


_PackLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def parse_pack(text: str, source: str = "<pack>") -> Pack:
    """Parse and check one pack's YAML text."""
    try:
        data = yaml.load(text, Loader=_PackLoader)  # noqa: S506 - _PackLoader is a SafeLoader
    except yaml.YAMLError as exc:
        raise OntologyError([f"{source}: {exc}"]) from exc
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


def find_pack(name: str, search_dirs: list[Path]) -> Path:
    for directory in [*search_dirs, BUILTIN_PACK_DIR]:
        candidate = directory / f"{name}.pack.yaml"
        if candidate.is_file():
            return candidate
    searched = ", ".join(str(d) for d in [*search_dirs, BUILTIN_PACK_DIR])
    raise OntologyError([f"pack {name!r} not found in {searched}"])


def load_registry(names: list[str], search_dirs: list[Path] | None = None) -> OntologyRegistry:
    """Load the named packs, the packs they require and ``core``, then compose them."""
    dirs = list(search_dirs or [])
    packs: dict[str, Pack] = {}
    pending = ["core", *names]
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
