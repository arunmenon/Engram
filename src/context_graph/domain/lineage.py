"""Bounded traversal utilities (ADR-0001, ADR-0009).

Provides parameter clamping for traversal bounds and Cypher query generation
for lineage and context assembly.

Pure Python — ZERO framework imports.
"""

from __future__ import annotations


def validate_traversal_bounds(
    max_depth: int,
    max_nodes: int,
    timeout_ms: int,
    max_max_depth: int = 10,
    max_max_nodes: int = 500,
    max_timeout_ms: int = 30000,
) -> tuple[int, int, int]:
    """Clamp traversal parameters to allowed ranges.

    Returns (clamped_depth, clamped_nodes, clamped_timeout).
    """
    clamped_depth = min(max(1, max_depth), max_max_depth)
    clamped_nodes = min(max(1, max_nodes), max_max_nodes)
    clamped_timeout = min(max(100, timeout_ms), max_timeout_ms)
    return (clamped_depth, clamped_nodes, clamped_timeout)


def build_lineage_cypher(
    node_id_param: str = "$node_id",
    max_depth_param: str = "$max_depth",
    max_nodes_param: str = "$max_nodes",
    edge_types: list[str] | None = None,
) -> str:
    """Generate Cypher for variable-length causal lineage traversal.

    Defaults to CAUSED_BY edges. Custom edge types can be specified for
    broader lineage queries (e.g., CAUSED_BY + FOLLOWS).
    """
    types = edge_types or ["CAUSED_BY"]
    type_str = "|".join(types)
    return (
        f"MATCH path = (start:Event {{event_id: {node_id_param}}})"
        f"-[:{type_str}*1..{max_depth_param}]->(ancestor) "
        f"RETURN start, nodes(path) AS chain_nodes, "
        f"relationships(path) AS chain_rels "
        f"LIMIT {max_nodes_param}"
    )


def build_context_cypher() -> str:
    """Cypher query for session context assembly.

    Returns events for a session ordered by recency, limited to $limit.
    """
    return (
        "MATCH (e:Event {session_id: $session_id}) "
        "RETURN e ORDER BY e.occurred_at DESC LIMIT $limit"
    )
