"""Intent classification port interface."""

from __future__ import annotations

from typing import Protocol


class IntentClassifier(Protocol):
    """Protocol for intent classification."""

    async def classify(self, query: str) -> dict[str, float]:
        """Classify a query into intent types with confidence scores."""
        ...
