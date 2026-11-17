"""Local packaged domain packs available to the workbench, not a remote registry."""

from pathlib import Path
from typing import Any

from context_graph.ontology.loader import BASE_PACKS, BUILTIN_PACK_DIR, load_registry

CATALOG_DIR = Path(__file__).parent / "packs"


def pack_names() -> list[str]:
    return sorted(
        {
            path.name.removesuffix(".pack.yaml")
            for directory in (BUILTIN_PACK_DIR, CATALOG_DIR)
            for path in directory.glob("*.pack.yaml")
            if path.name.removesuffix(".pack.yaml") not in BASE_PACKS
        }
    )


def entries() -> list[dict[str, Any]]:
    result = []
    for name in pack_names():
        # Only advertise packs that the real engine can load and compose.
        registry = load_registry([name], [CATALOG_DIR], builtin_packs=[])
        pack = next(pack for pack in registry.packs if pack.name == name)
        result.append(
            {
                "name": name,
                "description": pack.pack.description,
                "version": pack.pack.version,
                "requires": pack.pack.requires,
                "has_lifecycle": any(node.lifecycle for node in pack.types.nodes.values()),
            }
        )
    return result


def has_lifecycle(raw_pack: dict[str, Any] | None) -> bool:
    """Inspect only declarations; malformed proposals remain subject to validation."""
    if not raw_pack or not isinstance(raw_pack.get("types"), dict):
        return False
    nodes = raw_pack["types"].get("nodes", {})
    return isinstance(nodes, dict) and any(
        isinstance(node, dict) and bool(node.get("lifecycle")) for node in nodes.values()
    )
