"""Backend-neutral retrieval engine (ADR-0019 C3).

Imports only ``domain/``, ``ports/``, ``settings`` and ``metrics``; never a
storage adapter or backend library.
"""

from context_graph.retrieval.engine import RetrievalEngine

__all__ = ["RetrievalEngine"]
