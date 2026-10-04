"""Source adapters: tool webhooks to ontology events (ADR-0018).

Each adapter translates one tool's webhook payload into the events of an
ontology pack (``pdlc.*``, CDEvents-shaped). Adapters know nothing about
the graph; the pack's projection rules do the rest.
"""

from context_graph.sources.events import SourceEvent

__all__ = ["SourceEvent"]
