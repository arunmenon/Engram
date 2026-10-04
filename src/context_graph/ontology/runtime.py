"""The configured ontology at runtime: registry and projector (ADR-0018).

Composition roots (``api/app.py``, ``worker/__main__.py``) call these
once at start-up; an invalid pack fails start-up with every problem listed.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from context_graph.domain.pack_projection import PackProjector
from context_graph.ontology.loader import load_registry

if TYPE_CHECKING:
    from context_graph.domain.ontology import OntologyRegistry
    from context_graph.settings import OntologySettings


@lru_cache(maxsize=8)
def _registry(packs: tuple[str, ...], pack_dirs: tuple[str, ...]) -> OntologyRegistry:
    return load_registry(list(packs), [Path(d) for d in pack_dirs])


def configured_registry(settings: OntologySettings) -> OntologyRegistry:
    """The registry for ``CG_ONTOLOGY_*`` (loaded once per configuration)."""
    return _registry(tuple(settings.packs), tuple(settings.pack_dirs))


def configured_projector(settings: OntologySettings) -> PackProjector:
    return PackProjector(configured_registry(settings), frozenset(settings.trusted_sources))
