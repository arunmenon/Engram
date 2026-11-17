"""Intent classification and weights from the ontology registry (ADR-0018 phase 2).

``RegistryIntents`` does what ``domain/intent.py`` does with its fixed
tables, from the active packs instead: keyword matching (0.4 per match,
capped at 1.0, normalised so the dominant intent is 1.0, the fallback
intent at 0.5 when nothing matches), per-edge weights scaled by intent
confidence, and the dominant intent's seed strategy. With only today's
packs (``core``, ``memory``, ``user``) the answers equal the fixed tables.

A subset of intents can be selected: event retrieval uses the intents of
today's packs; artifact retrieval uses the intents that weight a pack
edge.

Pure Python; no framework imports.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from context_graph.domain.ontology import OPEN_PACKS

if TYPE_CHECKING:
    from collections.abc import Iterable

    from context_graph.domain.ontology import OntologyRegistry

MATCH_SCORE = 0.4
FALLBACK_CONFIDENCE = 0.5
GENERAL_STRATEGY = "general"


class UnsupportedIntentError(ValueError):
    """The selected pack composition does not provide the requested intent."""


class RegistryIntents:
    """The intents of a registry (or a subset), with their keywords and weights."""

    def __init__(self, registry: OntologyRegistry, names: Iterable[str] | None = None) -> None:
        self._registry = registry
        selected = list(names) if names is not None else list(registry.intents)
        self.names = [name for name in selected if name in registry.intents]
        self._patterns = {
            name: [
                re.compile(r"\b" + re.escape(keyword.lower()) + r"\b")
                for keyword in registry.intents[name].keywords
            ]
            for name in self.names
        }
        fallback = registry.fallback_intent
        self.fallback = fallback if fallback in self.names else None

    @classmethod
    def for_events(cls, registry: OntologyRegistry) -> RegistryIntents:
        """Intents of today's packs (event retrieval)."""
        return cls(registry, [n for n, i in registry.intents.items() if i.pack in OPEN_PACKS])

    @classmethod
    def for_artifacts(cls, registry: OntologyRegistry) -> RegistryIntents:
        """Intents that weight at least one edge type a later pack declares."""
        pack_edges = {n for n, e in registry.edge_types.items() if e.pack not in OPEN_PACKS}
        return cls(
            registry,
            [n for n, i in registry.intents.items() if pack_edges & set(i.weights)],
        )

    def classify(self, query: str) -> dict[str, float]:
        text = query.lower()
        scores: dict[str, float] = {}
        for name in self.names:
            matches = sum(1 for pattern in self._patterns[name] if pattern.search(text))
            if matches:
                scores[name] = min(1.0, matches * MATCH_SCORE)
        if not scores:
            return {self.fallback: FALLBACK_CONFIDENCE} if self.fallback else {}
        top = max(scores.values())
        return {name: score / top for name, score in scores.items()}

    async def classify_async(self, query: str) -> dict[str, float]:
        """``IntentClassifier`` protocol form."""
        return self.classify(query)

    def edge_weights(self, intents: dict[str, float]) -> dict[str, float]:
        weights: dict[str, float] = {}
        for name, confidence in intents.items():
            intent = self._registry.intents.get(name)
            if intent is None:
                continue
            for edge, weight in intent.weights.items():
                weights[edge] = weights.get(edge, 0.0) + confidence * weight
        return weights

    def seed_strategy(self, intents: dict[str, float]) -> str:
        if not intents:
            return GENERAL_STRATEGY
        dominant = max(intents, key=lambda name: intents[name])
        intent = self._registry.intents.get(dominant)
        return (intent.seed_strategy if intent else None) or GENERAL_STRATEGY

    def dominant(self, intents: dict[str, float]) -> str | None:
        return max(intents, key=lambda name: intents[name]) if intents else None
