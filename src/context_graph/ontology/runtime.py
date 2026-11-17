"""The configured ontology at runtime: registry and projector (ADR-0018).

Composition roots (``api/app.py``, ``worker/__main__.py``) call these
once at start-up; an invalid pack fails start-up with every problem listed.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from context_graph.domain.pack_bundle import ActiveBundle, resolve_bundle
from context_graph.domain.pack_projection import PackProjector
from context_graph.ontology.loader import load_registry

if TYPE_CHECKING:
    from context_graph.domain.ontology import OntologyRegistry
    from context_graph.settings import OntologySettings


@lru_cache(maxsize=8)
def _bundle(
    packs: tuple[str, ...], pack_dirs: tuple[str, ...], builtin_packs: tuple[str, ...]
) -> ActiveBundle:
    registry = load_registry(
        list(packs), [Path(d) for d in pack_dirs], builtin_packs=list(builtin_packs)
    )
    return resolve_bundle(registry)


def configured_bundle(settings: OntologySettings) -> ActiveBundle:
    """Immutable composition snapshot; not a tenant routing or service-readiness proof."""
    return _bundle(
        tuple(sorted(set(settings.packs))),
        tuple(settings.pack_dirs),
        tuple(sorted(set(settings.builtin_packs))),
    )


def configured_registry(settings: OntologySettings) -> OntologyRegistry:
    """The registry for ``CG_ONTOLOGY_*`` (loaded once per configuration)."""
    return configured_bundle(settings).registry


def configured_projector(settings: OntologySettings) -> PackProjector:
    return PackProjector(configured_registry(settings), frozenset(settings.trusted_sources))
