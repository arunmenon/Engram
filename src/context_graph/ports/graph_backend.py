"""The combined graph-side surface a graph backend provides (ADR-0019).

A graph backend serves graph writes and queries (``GraphStore``),
maintenance (``GraphMaintenance``), user data (``UserStore``), the generic
operations ontology packs use (``PackGraph``, ADR-0018) and the retrieval
engine's bounded reads (via ``reads``). The registry types its
``Stores.graph`` with this protocol, so callers never see an adapter class.

Source: ADR-0019
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from context_graph.ports.graph_store import GraphStore
from context_graph.ports.maintenance import GraphMaintenance
from context_graph.ports.pack_graph import PackGraph
from context_graph.ports.user_store import UserStore

if TYPE_CHECKING:
    from context_graph.ports.graph_reads import GraphReads


class GraphBackend(GraphStore, GraphMaintenance, UserStore, PackGraph, Protocol):
    """GraphStore + GraphMaintenance + UserStore + PackGraph, plus the retrieval reads."""

    @property
    def reads(self) -> GraphReads:
        """Bounded reads for the retrieval engine."""
        ...
