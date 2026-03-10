"""Retrieval pipeline for subgraph queries.

Extracts the multi-channel hybrid retrieval orchestration from
Neo4jGraphStore into a focused class. Handles: HyDE query expansion,
intent classification, 3-channel parallel seed retrieval (graph, vector,
BM25), Reciprocal Rank Fusion, neighbor expansion, PPR post-processing,
and pagination.

Source: ADR-0006, ADR-0009
"""

from __future__ import annotations

import asyncio
import base64
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

from context_graph.adapters.neo4j import queries
from context_graph.domain.intent import classify_intent, get_edge_weights, select_seed_strategy
from context_graph.domain.models import (
    AtlasEdge,
    AtlasNode,
    AtlasResponse,
    NodeScores,
    Pagination,
    Provenance,
    QueryCapacity,
    QueryMeta,
)
from context_graph.domain.ppr import approximate_ppr
from context_graph.domain.query_expansion import build_hyde_prompt, expand_query
from context_graph.domain.reranking import reciprocal_rank_fusion
from context_graph.domain.scoring import score_entity_node, score_node
from context_graph.metrics import GRAPH_QUERY_DURATION
from context_graph.settings import INTENT_WEIGHTS

if TYPE_CHECKING:
    from neo4j import AsyncDriver

    from context_graph.domain.models import SubgraphQuery
    from context_graph.ports.embedding import EmbeddingService
    from context_graph.ports.event_store import EventStore
    from context_graph.ports.intent import IntentClassifier
    from context_graph.ports.llm import LLMClient
    from context_graph.settings import DecaySettings, PPRSettings

logger = structlog.get_logger(__name__)

# Map seed strategy name -> Cypher seed query
_SEED_STRATEGY_QUERIES: dict[str, str] = {
    "causal_roots": queries.GET_SEED_CAUSAL_ROOTS,
    "entity_hubs": queries.GET_SEED_ENTITY_HUBS,
    "temporal_anchors": queries.GET_SEED_TEMPORAL_ANCHORS,
    "user_profile": queries.GET_SEED_USER_PROFILE,
    "similar_cluster": queries.GET_SEED_SIMILAR_CLUSTER,
    "workflow_pattern": queries.GET_SEED_WORKFLOW_PATTERN,
    "general": queries.GET_SUBGRAPH_SEED_EVENTS,
}


@dataclass(frozen=True)
class RetrievalDeps:
    """Dependency bundle for the retrieval pipeline."""

    driver: AsyncDriver
    database: str
    embedding_service: EmbeddingService | None
    intent_classifier: IntentClassifier | None
    llm_client: LLMClient | None
    event_store: EventStore | None
    decay: DecaySettings
    ppr_settings: PPRSettings | None
    query_timeout_s: float
    neighbor_limit: int
    search_similar_entities: Any  # callable from store
    hyde_hot_path_timeout: float = 2.0


class RetrievalPipeline:
    """Orchestrates multi-channel hybrid retrieval for subgraph queries.

    Separated from Neo4jGraphStore to keep the store focused on CRUD
    and the pipeline focused on query orchestration.
    """

    def __init__(self, deps: RetrievalDeps) -> None:
        self._deps = deps

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def get_subgraph(self, query: SubgraphQuery, tenant_id: str = "default") -> AtlasResponse:
        """Execute an intent-aware subgraph query."""
        start_ms = time.monotonic_ns()
        d = self._deps

        # HyDE query expansion (L6) — with configurable timeout
        hot_path_timeout = d.hyde_hot_path_timeout
        query_text_for_embedding = query.query
        if query.use_hyde and d.llm_client is not None:
            try:
                hyde_prompt = build_hyde_prompt(query.query)
                hyde_response = await asyncio.wait_for(
                    d.llm_client.generate_text(hyde_prompt),
                    timeout=hot_path_timeout,
                )
                if hyde_response:
                    query_text_for_embedding = expand_query(query.query, hyde_response)
            except TimeoutError:
                logger.warning("hyde_timeout", query_length=len(query.query))
            except Exception:
                logger.warning("hyde_expansion_failed", query_length=len(query.query))

        # Embed query text for relevance scoring
        query_embedding = await self._embed_query(query_text_for_embedding)

        # Classify intent from the query text — with configurable timeout
        if d.intent_classifier is not None:
            try:
                inferred_intents = await asyncio.wait_for(
                    d.intent_classifier.classify(query.query),
                    timeout=hot_path_timeout,
                )
            except TimeoutError:
                logger.warning("intent_classification_timeout", query_length=len(query.query))
                inferred_intents = classify_intent(query.query)
        else:
            inferred_intents = classify_intent(query.query)

        # If explicit intent override, use that
        if query.intent is not None:
            inferred_intents = {str(query.intent): 1.0}

        # Get edge weights based on intents
        edge_weights = get_edge_weights(inferred_intents, INTENT_WEIGHTS)

        # Select seed strategy based on dominant intent
        seed_strategy = select_seed_strategy(inferred_intents)
        seed_query = _SEED_STRATEGY_QUERIES.get(seed_strategy, queries.GET_SUBGRAPH_SEED_EVENTS)
        seed_limit = min(10, query.max_nodes)

        # Multi-channel hybrid retrieval (L4): run 3 channels in parallel
        graph_task = self._get_graph_seeds(query, seed_limit, seed_query, seed_strategy, tenant_id)
        vector_task = self._get_vector_seeds(query_embedding, seed_limit, tenant_id)
        bm25_task = self._get_bm25_seeds(query.query, query.session_id, seed_limit, tenant_id)

        channel_results = await asyncio.gather(
            graph_task, vector_task, bm25_task, return_exceptions=True
        )

        # Collect valid channel results, filtering out exceptions
        ranked_lists: list[list[tuple[str, float]]] = []
        retrieval_channels: dict[str, int] = {}
        channel_names = ["graph", "vector", "bm25"]
        for idx, ch_result in enumerate(channel_results):
            if isinstance(ch_result, BaseException):
                logger.warning(
                    "seed_channel_failed",
                    channel=channel_names[idx],
                    error=str(ch_result),
                )
                retrieval_channels[channel_names[idx]] = 0
            else:
                ranked_lists.append(ch_result)
                retrieval_channels[channel_names[idx]] = len(ch_result)

        # Fuse seed lists using Reciprocal Rank Fusion
        fused_seeds = reciprocal_rank_fusion(ranked_lists) if ranked_lists else []

        # Take top seed_limit fused seeds
        fused_seed_ids = [sid for sid, _score in fused_seeds[:seed_limit]]

        nodes: dict[str, AtlasNode] = {}
        edges: list[AtlasEdge] = []
        seen_edges: set[tuple[str, str, str]] = set()
        seed_node_ids: list[str] = []

        # Batch-fetch properties for fused seed IDs (single roundtrip)
        await self._fetch_seed_nodes(
            fused_seed_ids, nodes, seed_node_ids, query_embedding, tenant_id
        )

        # Override with user-provided seed_nodes if specified
        if query.seed_nodes:
            seed_node_ids = list(query.seed_nodes)
            user_seeds = [s for s in query.seed_nodes if s not in nodes]
            if user_seeds:
                await self._fetch_seed_nodes(
                    user_seeds, nodes, seed_node_ids, query_embedding, tenant_id
                )

        # Cross-session entity expansion for relevant intents
        await self._expand_cross_session(query, inferred_intents, nodes, query_embedding, tenant_id)

        # Batch neighbor traversal for all seeds (single roundtrip)
        await self._expand_neighbors(
            seed_node_ids, nodes, edges, seen_edges, edge_weights, query_embedding, tenant_id
        )

        # PPR post-processing (L5)
        self._apply_ppr(nodes, edges, edge_weights, seed_node_ids)

        # MMR diversity re-ranking (L4) — reorder nodes with embeddings
        self._apply_mmr(nodes, query_embedding)

        # Sort all nodes by score, take top max_nodes with offset pagination
        sorted_node_ids = sorted(
            nodes.keys(),
            key=lambda nid: nodes[nid].scores.decay_score,
            reverse=True,
        )

        # Decode cursor as offset for subgraph pagination
        sg_offset = 0
        if query.cursor:
            try:
                sg_offset = int(base64.urlsafe_b64decode(query.cursor.encode()).decode())
            except (ValueError, Exception):
                sg_offset = 0

        # Apply offset then take max_nodes
        paged_ids = sorted_node_ids[sg_offset:]
        has_more_sg = len(paged_ids) > query.max_nodes
        paged_ids = paged_ids[: query.max_nodes]

        keep_set = set(paged_ids)
        nodes = {k: v for k, v in nodes.items() if k in keep_set}

        # Bump access counts for event nodes only
        event_ids = [nid for nid in nodes if nid.startswith("evt")]
        await self._bump_access_counts(event_ids, tenant_id)

        # Build next cursor (offset-based)
        next_cursor_sg: str | None = None
        if has_more_sg:
            next_off = sg_offset + query.max_nodes
            next_cursor_sg = base64.urlsafe_b64encode(str(next_off).encode()).decode()

        elapsed_ms = int((time.monotonic_ns() - start_ms) / 1_000_000)
        GRAPH_QUERY_DURATION.labels(query_type="subgraph").observe(elapsed_ms / 1000.0)

        proactive_count = sum(1 for n in nodes.values() if n.retrieval_reason == "proactive")

        meta = QueryMeta(
            query_ms=elapsed_ms,
            nodes_returned=len(nodes),
            truncated=has_more_sg,
            inferred_intents=inferred_intents,
            intent_override=str(query.intent) if query.intent is not None else None,
            seed_nodes=seed_node_ids,
            seed_strategy=seed_strategy,
            proactive_nodes_count=proactive_count,
            retrieval_channels=retrieval_channels,
            capacity=QueryCapacity(
                max_nodes=query.max_nodes,
                used_nodes=len(nodes),
                max_depth=query.max_depth,
            ),
        )

        return AtlasResponse(
            nodes=nodes,
            edges=edges,
            pagination=Pagination(cursor=next_cursor_sg, has_more=has_more_sg),
            meta=meta,
        )

    # ------------------------------------------------------------------
    # Seed channels
    # ------------------------------------------------------------------

    async def _get_graph_seeds(
        self,
        query: SubgraphQuery,
        seed_limit: int,
        seed_query: str,
        seed_strategy: str,
        tenant_id: str = "default",
    ) -> list[tuple[str, float]]:
        """Channel 1: Graph-based seed retrieval via intent-aware strategy."""
        d = self._deps
        async with d.driver.session(database=d.database) as session:
            seed_result = await session.run(
                seed_query,
                {"session_id": query.session_id, "seed_limit": seed_limit, "tenant_id": tenant_id},
                timeout=d.query_timeout_s,
            )
            seed_records = [record async for record in seed_result]

        # Fallback to general (recency) if strategy returned nothing
        if not seed_records and seed_strategy != "general":
            async with d.driver.session(database=d.database) as session:
                seed_result = await session.run(
                    queries.GET_SUBGRAPH_SEED_EVENTS,
                    {
                        "session_id": query.session_id,
                        "seed_limit": seed_limit,
                        "tenant_id": tenant_id,
                    },
                    timeout=d.query_timeout_s,
                )
                seed_records = [record async for record in seed_result]

        seeds: list[tuple[str, float]] = []
        for rank, record in enumerate(seed_records):
            props = dict(record["e"])
            event_id = props.get("event_id", "")
            if event_id:
                seeds.append((event_id, 1.0 / (rank + 1)))
        return seeds

    async def _get_vector_seeds(
        self,
        query_embedding: list[float] | None,
        limit: int,
        tenant_id: str = "default",
    ) -> list[tuple[str, float]]:
        """Channel 2: Vector similarity seed retrieval via entity embeddings."""
        if query_embedding is None:
            return []
        try:
            results = await self._deps.search_similar_entities(
                query_embedding, top_k=limit, threshold=0.5, tenant_id=tenant_id
            )
            return [(r["entity_id"], r["score"]) for r in results]
        except Exception:
            logger.warning("vector_seed_retrieval_failed")
            return []

    async def _get_bm25_seeds(
        self,
        query_text: str,
        session_id: str | None,
        limit: int,
        tenant_id: str = "default",
    ) -> list[tuple[str, float]]:
        """Channel 3: BM25 full-text seed retrieval via Redis event store."""
        if self._deps.event_store is None:
            return []
        try:
            events = await self._deps.event_store.search_bm25(
                query_text, session_id=session_id, limit=limit, tenant_id=tenant_id
            )
            seeds: list[tuple[str, float]] = []
            for rank, event in enumerate(events):
                seeds.append((str(event.event_id), 1.0 / (rank + 1)))
            return seeds
        except Exception:
            logger.warning("bm25_seed_retrieval_failed")
            return []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _embed_query(self, query_text: str | None) -> list[float] | None:
        """Embed query text if embedding service is available."""
        if self._deps.embedding_service is None or not query_text:
            return None
        try:
            return await self._deps.embedding_service.embed_text(query_text)
        except Exception:
            logger.warning("query_embedding_failed", query_length=len(query_text))
            return None

    async def _bump_access_counts(self, event_ids: list[str], tenant_id: str = "default") -> None:
        """Increment access_count for a batch of event nodes."""
        if not event_ids:
            return
        d = self._deps
        now_iso = datetime.now(UTC).isoformat()
        async with d.driver.session(database=d.database) as session:
            await session.execute_write(
                lambda tx: tx.run(
                    queries.BATCH_UPDATE_ACCESS_COUNT,
                    {"event_ids": event_ids, "now": now_iso, "tenant_id": tenant_id},
                )
            )

    async def _fetch_seed_nodes(
        self,
        seed_ids: list[str],
        nodes: dict[str, AtlasNode],
        seed_node_ids: list[str],
        query_embedding: list[float] | None,
        tenant_id: str = "default",
    ) -> None:
        """Batch-fetch event nodes for seed IDs (single roundtrip)."""
        if not seed_ids:
            return
        d = self._deps
        new_ids = [sid for sid in seed_ids if sid not in nodes]
        if not new_ids:
            return

        async with d.driver.session(database=d.database) as session:
            result = await session.run(
                "MATCH (e:Event) WHERE e.event_id IN $eids AND e.tenant_id = $tenant_id RETURN e",
                {"eids": new_ids, "tenant_id": tenant_id},
                timeout=d.query_timeout_s,
            )
            records = [record async for record in result]

        found_ids: set[str] = set()
        for record in records:
            props = dict(record["e"])
            event_id = props.get("event_id", "")
            if event_id:
                found_ids.add(event_id)
                seed_node_ids.append(event_id)
                scores = score_node(
                    props,
                    query_embedding=query_embedding,
                    s_base=d.decay.s_base,
                    s_boost=d.decay.s_boost,
                    w_recency=d.decay.weight_recency,
                    w_importance=d.decay.weight_importance,
                    w_relevance=d.decay.weight_relevance,
                    w_user_affinity=d.decay.weight_user_affinity,
                )
                nodes[event_id] = _build_atlas_node(props, scores)

        # Seeds not found as events may be entity IDs from vector channel
        for sid in new_ids:
            if sid not in found_ids and sid not in seed_node_ids:
                seed_node_ids.append(sid)

    async def _expand_cross_session(
        self,
        query: SubgraphQuery,
        inferred_intents: dict[str, float],
        nodes: dict[str, AtlasNode],
        query_embedding: list[float] | None,
        tenant_id: str = "default",
    ) -> None:
        """Add cross-session entity events for personalization intents."""
        cross_intents = {"who_is", "personalize", "related"}
        dominant_intent = max(inferred_intents, key=lambda k: inferred_intents[k])
        if dominant_intent not in cross_intents:
            return

        d = self._deps
        cross_limit = max(1, query.max_nodes // 5)
        async with d.driver.session(database=d.database) as session:
            cross_result = await session.run(
                queries.GET_ENTITY_CROSS_SESSION_EVENTS,
                {"session_id": query.session_id, "limit": cross_limit, "tenant_id": tenant_id},
                timeout=d.query_timeout_s,
            )
            cross_records = [record async for record in cross_result]

        for record in cross_records:
            props = dict(record["e"])
            event_id = props.get("event_id", "")
            if event_id and event_id not in nodes:
                scores = score_node(
                    props,
                    query_embedding=query_embedding,
                    s_base=d.decay.s_base,
                    s_boost=d.decay.s_boost,
                    w_recency=d.decay.weight_recency,
                    w_importance=d.decay.weight_importance,
                    w_relevance=d.decay.weight_relevance,
                    w_user_affinity=d.decay.weight_user_affinity,
                )
                atlas_node = _build_atlas_node(props, scores, retrieval_reason="proactive")
                atlas_node.proactive_signal = "cross_session"
                nodes[event_id] = atlas_node

    async def _expand_neighbors(
        self,
        seed_node_ids: list[str],
        nodes: dict[str, AtlasNode],
        edges: list[AtlasEdge],
        seen_edges: set[tuple[str, str, str]],
        edge_weights: dict[str, float],
        query_embedding: list[float] | None,
        tenant_id: str = "default",
    ) -> None:
        """Batch neighbor traversal for all seeds (single roundtrip)."""
        if not seed_node_ids:
            return

        d = self._deps
        async with d.driver.session(database=d.database) as session:
            neighbor_result = await session.run(
                queries.GET_EVENT_NEIGHBORS_BATCH,
                {
                    "event_ids": seed_node_ids,
                    "neighbor_limit": d.neighbor_limit,
                    "tenant_id": tenant_id,
                },
                timeout=d.query_timeout_s,
            )
            neighbor_records = [record async for record in neighbor_result]

        for nrec in neighbor_records:
            seed_eid = nrec.get("seed_event_id")
            rel_type = nrec.get("rel_type")
            if rel_type is None or seed_eid is None:
                continue

            neighbor_eid = nrec.get("neighbor_event_id")
            neighbor_entity_id = nrec.get("neighbor_entity_id")
            neighbor_id = neighbor_eid or neighbor_entity_id or ""
            if not neighbor_id:
                continue

            weight = edge_weights.get(rel_type, 1.0)

            if neighbor_eid and neighbor_eid not in nodes:
                neighbor_props = nrec.get("neighbor_props", {}) or {}
                nscores = score_node(
                    neighbor_props,
                    query_embedding=query_embedding,
                    s_base=d.decay.s_base,
                    s_boost=d.decay.s_boost,
                    w_recency=d.decay.weight_recency,
                    w_importance=d.decay.weight_importance,
                    w_relevance=d.decay.weight_relevance,
                    w_user_affinity=d.decay.weight_user_affinity,
                )
                boosted_score = min(1.0, nscores.decay_score * (1.0 + weight * 0.1))
                boosted_scores = NodeScores(
                    decay_score=round(boosted_score, 6),
                    relevance_score=nscores.relevance_score,
                    importance_score=nscores.importance_score,
                )
                proactive_signal = {
                    "REFERENCES": "entity_context",
                    "SIMILAR_TO": "recurring_pattern",
                    "CAUSED_BY": "causal_chain",
                    "FOLLOWS": "temporal_sequence",
                    "SUMMARIZES": "summary_context",
                }.get(rel_type, "related_context")
                atlas_node = _build_atlas_node(
                    neighbor_props, boosted_scores, retrieval_reason="proactive"
                )
                atlas_node.proactive_signal = proactive_signal
                nodes[neighbor_eid] = atlas_node

            elif neighbor_entity_id and neighbor_entity_id not in nodes:
                neighbor_props = nrec.get("neighbor_props", {}) or {}
                nscores = score_entity_node(
                    neighbor_props,
                    query_embedding=query_embedding,
                    s_base=d.decay.entity_s_base,
                    s_boost=d.decay.entity_s_boost,
                    w_recency=d.decay.weight_recency,
                    w_importance=d.decay.weight_importance,
                    w_relevance=d.decay.weight_relevance,
                    w_user_affinity=d.decay.weight_user_affinity,
                )
                boosted_score = min(1.0, nscores.decay_score * (1.0 + weight * 0.1))
                boosted_scores = NodeScores(
                    decay_score=round(boosted_score, 6),
                    relevance_score=nscores.relevance_score,
                    importance_score=nscores.importance_score,
                )
                neighbor_labels = nrec.get("neighbor_labels", []) or []
                node_type = neighbor_labels[0] if neighbor_labels else "Entity"
                nodes[neighbor_entity_id] = AtlasNode(
                    node_id=neighbor_entity_id,
                    node_type=node_type,
                    attributes={k: v for k, v in neighbor_props.items() if k != "embedding"},
                    scores=boosted_scores,
                    retrieval_reason="proactive",
                    proactive_signal="entity_context",
                )

            edge_key = (seed_eid, neighbor_id, rel_type)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                rel_props = nrec.get("rel_props", {}) or {}
                edges.append(
                    AtlasEdge(
                        source=seed_eid,
                        target=neighbor_id,
                        edge_type=rel_type,
                        properties=rel_props,
                    )
                )

    def _apply_ppr(
        self,
        nodes: dict[str, AtlasNode],
        edges: list[AtlasEdge],
        edge_weights: dict[str, float],
        seed_node_ids: list[str],
    ) -> None:
        """Apply Personalized PageRank post-processing to re-rank nodes."""
        ppr = self._deps.ppr_settings
        if ppr is None or not ppr.enabled:
            return
        if len(nodes) > ppr.max_subgraph_size:
            return

        adjacency = _build_adjacency(nodes, edges, edge_weights)
        ppr_scores = approximate_ppr(
            adjacency,
            seeds=seed_node_ids,
            damping=ppr.damping,
            iterations=ppr.iterations,
        )
        blend_w = ppr.blend_weight
        node_count = len(nodes) or 1
        for node_id, node in nodes.items():
            ppr_val = ppr_scores.get(node_id, 0.0)
            ppr_clamped = max(0.0, min(1.0, ppr_val * node_count))
            blended = (1 - blend_w) * node.scores.decay_score + blend_w * ppr_clamped
            node.scores = NodeScores(
                decay_score=round(blended, 6),
                relevance_score=node.scores.relevance_score,
                importance_score=node.scores.importance_score,
                ppr_score=round(ppr_clamped, 6),
            )

    def _apply_mmr(
        self,
        nodes: dict[str, AtlasNode],
        query_embedding: list[float] | None,
    ) -> None:
        """Apply Maximal Marginal Relevance to diversify retrieval results.

        Only operates on nodes that have an embedding attribute. Updates
        relevance_score with the MMR-adjusted score.
        """
        if query_embedding is None:
            return

        from context_graph.domain.reranking import maximal_marginal_relevance

        mmr_candidates: list[tuple[str, float, list[float]]] = []
        for nid, node in nodes.items():
            embedding = node.attributes.get("embedding")
            if embedding and isinstance(embedding, list) and len(embedding) > 0:
                relevance = node.scores.relevance_score if node.scores else 0.0
                mmr_candidates.append((nid, relevance, embedding))

        if not mmr_candidates:
            return

        # Greedy iterative MMR: pick top candidate, add to selected, repeat
        selected: list[str] = []
        remaining = list(mmr_candidates)
        mmr_order: list[tuple[str, float]] = []

        while remaining:
            round_results = maximal_marginal_relevance(
                candidates=remaining,
                selected=selected,
                lambda_param=0.7,
            )
            if not round_results:
                break
            best_id, best_score = round_results[0]
            selected.append(best_id)
            mmr_order.append((best_id, best_score))
            remaining = [(cid, rel, emb) for cid, rel, emb in remaining if cid != best_id]

        # Apply diversity-adjusted rank scores (normalized to 0-1 range)
        if mmr_order:
            max_score = max(s for _, s in mmr_order) if mmr_order else 1.0
            min_score = min(s for _, s in mmr_order) if mmr_order else 0.0
            score_range = max_score - min_score if max_score != min_score else 1.0
            for nid, mmr_score in mmr_order:
                if nid in nodes and nodes[nid].scores:
                    normalized = (mmr_score - min_score) / score_range
                    nodes[nid].scores = NodeScores(
                        decay_score=nodes[nid].scores.decay_score,
                        relevance_score=round(normalized, 6),
                        importance_score=nodes[nid].scores.importance_score,
                        ppr_score=getattr(nodes[nid].scores, "ppr_score", None),
                    )


# ------------------------------------------------------------------
# Module-level helpers (no self needed)
# ------------------------------------------------------------------


def _build_atlas_node(
    record_props: dict[str, Any],
    scores: NodeScores,
    retrieval_reason: str = "direct",
) -> AtlasNode:
    """Convert Neo4j record properties to an AtlasNode with provenance."""
    event_id = record_props.get("event_id", "")
    occurred_at_raw = record_props.get("occurred_at")
    if isinstance(occurred_at_raw, str):
        occurred_at = datetime.fromisoformat(occurred_at_raw)
    else:
        occurred_at = datetime.now(UTC)

    provenance = Provenance(
        event_id=event_id,
        global_position=record_props.get("global_position", ""),
        source="redis",
        occurred_at=occurred_at,
        session_id=record_props.get("session_id", ""),
        agent_id=record_props.get("agent_id", ""),
        trace_id=record_props.get("trace_id", ""),
    )

    attributes = {
        k: v
        for k, v in record_props.items()
        if k not in {"event_id", "global_position", "session_id", "agent_id", "trace_id"}
    }

    return AtlasNode(
        node_id=event_id,
        node_type="Event",
        attributes=attributes,
        provenance=provenance,
        scores=scores,
        retrieval_reason=retrieval_reason,
    )


def _build_adjacency(
    nodes: dict[str, AtlasNode],
    edges: list[AtlasEdge],
    edge_weights: dict[str, float],
) -> dict[str, list[tuple[str, float]]]:
    """Build bidirectional adjacency list from nodes and edges for PPR."""
    adjacency: dict[str, list[tuple[str, float]]] = {}
    for node_id in nodes:
        adjacency[node_id] = []
    for edge in edges:
        weight = edge_weights.get(edge.edge_type, 1.0)
        if edge.source in adjacency:
            adjacency[edge.source].append((edge.target, weight))
        if edge.target in adjacency:
            adjacency[edge.target].append((edge.source, weight))
    return adjacency
