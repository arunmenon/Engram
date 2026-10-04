"""Ontology packs on disk: loading, and the registry for the configured packs (ADR-0018).

The pack format and the registry live in ``domain/ontology.py``; this
package reads pack files (``packs/*.pack.yaml`` ships today's schema as
``core``, ``memory`` and ``user``, plus ``pdlc``).
"""

from context_graph.ontology.loader import (
    BUILTIN_PACK_DIR,
    find_pack,
    load_pack_file,
    load_registry,
    parse_pack,
)

__all__ = ["BUILTIN_PACK_DIR", "find_pack", "load_pack_file", "load_registry", "parse_pack"]
