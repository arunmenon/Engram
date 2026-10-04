"""Neo4j implementation of the GraphReads port (ADR-0019 C3).

Holds the Cypher the retrieval pipeline and the store's context/lineage
methods used to run inline. Each method sends the same query text,
parameters and timeout as before and converts records to plain dicts.

Source: ADR-0009, ADR-0019
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context_graph.adapters.errors import translate_errors
from context_graph.adapters.neo4j import queries
from context_graph.adapters.neo4j.errors import translate_neo4j_error
from context_graph.ports.graph_reads import NEIGHBOR_ROW_KEYS

if TYPE_CHECKING:
    from neo4j import AsyncDriver

# Seed strategy name -> Cypher seed query
SEED_STRATEGY_QUERIES: dict[str, str] = {
    "causal_roots": queries.GET_SEED_CAUSAL_ROOTS,
    "entity_hubs": queries.GET_SEED_ENTITY_HUBS,
    "temporal_anchors": queries.GET_SEED_TEMPORAL_ANCHORS,
    "user_profile": queries.GET_SEED_USER_PROFILE,
    "similar_cluster": queries.GET_SEED_SIMILAR_CLUSTER,
    "workflow_pattern": queries.GET_SEED_WORKFLOW_PATTERN,
    "general": queries.GET_SUBGRAPH_SEED_EVENTS,
}

GET_EVENT_NODES = "MATCH (e:Event) WHERE e.event_id IN $eids RETURN e"

GET_SESSION_EVENTS_AFTER = (
    "MATCH (e:Event {session_id: $session_id}) "
    "WHERE e.occurred_at > $cursor_ts "
    "   OR (e.occurred_at = $cursor_ts AND e.event_id > $cursor_id) "
    "RETURN e ORDER BY e.occurred_at ASC LIMIT $limit"
)


@translate_errors(translate_neo4j_error)
class Neo4jGraphReads:
    """Bounded graph reads over a Neo4j driver."""

    def __init__(self, driver: AsyncDriver, database: str) -> None:
        self._driver = driver
        self._database = database

    async def _records(
        self, cypher: str, params: dict[str, Any], timeout_s: float | None
    ) -> list[Any]:
        async with self._driver.session(database=self._database) as session:
            result = await session.run(cypher, params, timeout=timeout_s)
            return [record async for record in result]

    async def seed_events(
        self,
        strategy: str,
        session_id: str | None,
        limit: int,
        *,
        timeout_s: float | None = None,
    ) -> list[dict[str, Any]]:
        cypher = SEED_STRATEGY_QUERIES.get(strategy, queries.GET_SUBGRAPH_SEED_EVENTS)
        records = await self._records(
            cypher, {"session_id": session_id, "seed_limit": limit}, timeout_s
        )
        return [dict(record["e"]) for record in records]

    async def get_event_nodes(
        self, event_ids: list[str], *, timeout_s: float | None = None
    ) -> list[dict[str, Any]]:
        records = await self._records(GET_EVENT_NODES, {"eids": event_ids}, timeout_s)
        return [dict(record["e"]) for record in records]

    async def cross_session_entity_events(
        self, session_id: str | None, limit: int, *, timeout_s: float | None = None
    ) -> list[dict[str, Any]]:
        records = await self._records(
            queries.GET_ENTITY_CROSS_SESSION_EVENTS,
            {"session_id": session_id, "limit": limit},
            timeout_s,
        )
        return [dict(record["e"]) for record in records]

    async def event_neighbors(
        self, event_ids: list[str], neighbor_limit: int, *, timeout_s: float | None = None
    ) -> list[dict[str, Any]]:
        records = await self._records(
            queries.GET_EVENT_NEIGHBORS_BATCH,
            {"event_ids": event_ids, "neighbor_limit": neighbor_limit},
            timeout_s,
        )
        return [{key: record.get(key) for key in NEIGHBOR_ROW_KEYS} for record in records]

    async def session_events_page(
        self,
        session_id: str,
        limit: int,
        *,
        after: tuple[str, str] | None = None,
        timeout_s: float | None = None,
    ) -> list[dict[str, Any]]:
        if after is not None:
            cursor_ts, cursor_id = after
            cypher = GET_SESSION_EVENTS_AFTER
            params: dict[str, Any] = {
                "session_id": session_id,
                "cursor_ts": cursor_ts,
                "cursor_id": cursor_id,
                "limit": limit,
            }
        else:
            cypher = queries.GET_SESSION_EVENTS
            params = {"session_id": session_id, "limit": limit}
        records = await self._records(cypher, params, timeout_s)
        return [dict(record["e"]) for record in records]

    async def session_edges(
        self, session_id: str, event_ids: list[str], *, timeout_s: float | None = None
    ) -> list[dict[str, Any]]:
        records = await self._records(
            queries.GET_SESSION_EDGES,
            {"session_id": session_id, "event_ids": event_ids},
            timeout_s,
        )
        return [
            {
                "source": record["source"],
                "target": record["target"],
                "edge_type": record["edge_type"],
                "props": dict(record["props"]) if record["props"] else {},
            }
            for record in records
        ]

    async def lineage_chains(
        self,
        node_id: str,
        max_depth: int,
        max_nodes: int,
        *,
        timeout_s: float | None = None,
    ) -> list[dict[str, Any]]:
        records = await self._records(
            queries.GET_LINEAGE,
            {"node_id": node_id, "max_depth": max_depth, "max_nodes": max_nodes},
            timeout_s,
        )
        chains: list[dict[str, Any]] = []
        for record in records:
            chains.append(
                {
                    "nodes": [dict(neo_node) for neo_node in record["chain_nodes"]],
                    "edges": [
                        {
                            "source": dict(rel.start_node).get("event_id", ""),
                            "target": dict(rel.end_node).get("event_id", ""),
                            "properties": dict(rel),
                        }
                        for rel in record["chain_rels"]
                    ],
                }
            )
        return chains

    async def record_access(self, event_ids: list[str], accessed_at: str) -> None:
        if not event_ids:
            return
        async with self._driver.session(database=self._database) as session:
            await session.execute_write(
                lambda tx: tx.run(
                    queries.BATCH_UPDATE_ACCESS_COUNT,
                    {"event_ids": event_ids, "now": accessed_at},
                )
            )
