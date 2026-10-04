"""Backend-neutral retrieval engine (ADR-0019 C3).

Composes the storage ports: ``GraphReads`` for graph access,
``KeywordIndex`` and ``VectorIndex`` for seed search. It owns its
dependencies: embedding service, intent classifier, LLM client, and
decay, PPR and query settings. It answers the three Atlas queries:

- ``get_subgraph``: HyDE expansion, intent classification, three seed
  channels (graph, vector, keyword) fused with RRF, cross-session and
  neighbour expansion, PPR and MMR re-ranking, then pagination.
- ``get_context``: a session's working memory with keyset pagination.
- ``get_lineage``: CAUSED_BY traversal with offset pagination.

The logic moved here unchanged from ``adapters/neo4j/retrieval.py`` and
``adapters/neo4j/store.py``; only the storage calls go through ports.

Source: ADR-0006, ADR-0009, ADR-0019
"""

from __future__ import annotations

import asyncio
import base64
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

from context_graph.domain.intent import classify_intent, get_edge_weights, select_seed_strategy
from context_graph.domain.lineage import validate_traversal_bounds
from context_graph.domain.models import (
    AtlasEdge,
    AtlasNode,
    AtlasResponse,
    NodeScores,
    Pagination,
    QueryCapacity,
    QueryMeta,
)
from context_graph.domain.pagination import decode_cursor, encode_cursor
from context_graph.domain.ppr import approximate_ppr
from context_graph.domain.query_expansion import build_hyde_prompt, expand_query
from context_graph.domain.reranking import reciprocal_rank_fusion
from context_graph.domain.scoring import score_entity_node, score_node
from context_graph.metrics import GRAPH_QUERY_DURATION
from context_graph.retrieval.atlas import build_adjacency, build_atlas_node
from context_graph.settings import INTENT_WEIGHTS

if TYPE_CHECKING:
    from context_graph.domain.models import LineageQuery, SubgraphQuery
    from context_graph.ports.embedding import EmbeddingService
    from context_graph.ports.graph_reads import GraphReads
    from context_graph.ports.intent import IntentClassifier
    from context_graph.ports.llm import LLMClient
    from context_graph.ports.search import KeywordIndex, VectorIndex
    from context_graph.settings import DecaySettings, PPRSettings

logger = structlog.get_logger(__name__)

# Similarity floor for the vector seed channel
VECTOR_SEED_THRESHOLD = 0.5

# Upper bound on seeds per channel
MAX_SEEDS = 10

# Traversal timeout handed to validate_traversal_bounds for lineage
LINEAGE_BOUNDS_TIMEOUT_MS = 5000

_PROACTIVE_SIGNALS = {
    "REFERENCES": "entity_context",
    "SIMILAR_TO": "recurring_pattern",
    "CAUSED_BY": "causal_chain",
    "FOLLOWS": "temporal_sequence",
    "SUMMARIZES": "summary_context",
}


class RetrievalEngine:
    """Answers context, lineage and subgraph queries over the storage ports."""

    def __init__(
        self,
        graph: GraphReads,
        *,
        decay: DecaySettings,
        keyword_index: KeywordIndex | None = None,
        vector_index: VectorIndex | None = None,
        embedding_service: EmbeddingService | None = None,
        intent_classifier: IntentClassifier | None = None,
        llm_client: LLMClient | None = None,
        ppr_settings: PPRSettings | None = None,
        query_timeout_s: float = 5.0,
        neighbor_limit: int = 50,
        hyde_hot_path_timeout: float = 2.0,
        provenance_source: str = "redis",
    ) -> None:
        self._graph = graph
        self._keyword_index = keyword_index
        self._vector_index = vector_index
        self._embedding_service = embedding_service
        self._intent_classifier = intent_classifier
        self._llm_client = llm_client
        self._decay = decay
        self._ppr_settings = ppr_settings
        self._query_timeout_s = query_timeout_s
        self._neighbor_limit = neighbor_limit
        self._hyde_hot_path_timeout = hyde_hot_path_timeout
        self._provenance_source = provenance_source

    # ------------------------------------------------------------------
    # Subgraph
    # ------------------------------------------------------------------

    async def get_subgraph(self, query: SubgraphQuery) -> AtlasResponse:
        """Execute an intent-aware subgraph query."""
        start_ms = time.monotonic_ns()

        # HyDE query expansion (L6) — with configurable timeout
        hot_path_timeout = self._hyde_hot_path_timeout
        query_text_for_embedding = query.query
        if query.use_hyde and self._llm_client is not None:
            try:
                hyde_prompt = build_hyde_prompt(query.query)
                hyde_response = await asyncio.wait_for(
                    self._llm_client.generate_text(hyde_prompt),
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
        if self._intent_classifier is not None:
            try:
                inferred_intents = await asyncio.wait_for(
                    self._intent_classifier.classify(query.query),
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
        seed_limit = min(MAX_SEEDS, query.max_nodes)

        # Multi-channel hybrid retrieval (L4): run 3 channels in parallel
        graph_task = self._get_graph_seeds(query, seed_limit, seed_strategy=seed_strategy)
        vector_task = self._get_vector_seeds(query_embedding, seed_limit)
        bm25_task = self._get_bm25_seeds(query.query, query.session_id, seed_limit)

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
        await self._fetch_seed_nodes(fused_seed_ids, nodes, seed_node_ids, query_embedding)

        # Override with user-provided seed_nodes if specified
        if query.seed_nodes:
            seed_node_ids = list(query.seed_nodes)
            user_seeds = [s for s in query.seed_nodes if s not in nodes]
            if user_seeds:
                await self._fetch_seed_nodes(user_seeds, nodes, seed_node_ids, query_embedding)

        # Cross-session entity expansion for relevant intents
        await self._expand_cross_session(query, inferred_intents, nodes, query_embedding)

        # Batch neighbor traversal for all seeds (single roundtrip)
        await self._expand_neighbors(
            seed_node_ids, nodes, edges, seen_edges, edge_weights, query_embedding
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
        await self._bump_access_counts(event_ids)

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
    # Context
    # ------------------------------------------------------------------

    async def get_context(
        self,
        session_id: str,
        max_nodes: int = 100,
        query: str | None = None,
        max_depth: int = 3,
        cursor: str | None = None,
    ) -> AtlasResponse:
        """Assemble working memory context for a session."""
        start_ms = time.monotonic_ns()

        # Embed query text for relevance scoring
        query_embedding = await self._embed_query(query)

        # Decode cursor for keyset pagination
        after: tuple[str, str] | None = None
        if cursor:
            cursor_ts, cursor_id = decode_cursor(cursor)
            if cursor_ts:
                after = (cursor_ts, cursor_id)

        fetch_limit = max_nodes + 1  # fetch one extra to detect has_more
        records = await self._graph.session_events_page(
            session_id, fetch_limit, after=after, timeout_s=self._query_timeout_s
        )

        has_more = len(records) > max_nodes
        if has_more:
            records = records[:max_nodes]

        nodes: dict[str, AtlasNode] = {}
        scored_entries: list[tuple[str, dict[str, Any], NodeScores]] = []

        for props in records:
            event_id = props.get("event_id", "")
            scores = self._score_event(props, query_embedding)
            scored_entries.append((event_id, props, scores))

        # Sort by composite decay_score descending, take top max_nodes
        scored_entries.sort(key=lambda x: x[2].decay_score, reverse=True)
        scored_entries = scored_entries[:max_nodes]

        for event_id, props, scores in scored_entries:
            nodes[event_id] = self._atlas_node(props, scores)

        # Bump access counts
        event_ids = [eid for eid, _, _ in scored_entries]
        await self._bump_access_counts(event_ids)

        # Fetch edges between session events
        edges: list[AtlasEdge] = []
        if event_ids:
            edge_rows = await self._graph.session_edges(
                session_id, event_ids, timeout_s=self._query_timeout_s
            )
            for row in edge_rows:
                edges.append(
                    AtlasEdge(
                        source=row["source"],
                        target=row["target"],
                        edge_type=row["edge_type"],
                        properties=row["props"],
                    )
                )

        # Build pagination cursor from last record
        next_cursor: str | None = None
        if has_more and records:
            last_props = records[-1]
            last_ts = last_props.get("occurred_at", "")
            last_eid = last_props.get("event_id", "")
            if last_ts and last_eid:
                next_cursor = encode_cursor(str(last_ts), str(last_eid))

        elapsed_ms = int((time.monotonic_ns() - start_ms) / 1_000_000)
        GRAPH_QUERY_DURATION.labels(query_type="context").observe(elapsed_ms / 1000.0)

        meta = QueryMeta(
            query_ms=elapsed_ms,
            nodes_returned=len(nodes),
            truncated=has_more,
            capacity=QueryCapacity(
                max_nodes=max_nodes,
                used_nodes=len(nodes),
                max_depth=max_depth,
            ),
        )

        return AtlasResponse(
            nodes=nodes,
            edges=edges,
            pagination=Pagination(cursor=next_cursor, has_more=has_more),
            meta=meta,
        )

    # ------------------------------------------------------------------
    # Lineage
    # ------------------------------------------------------------------

    async def get_lineage(
        self, query: LineageQuery, query_text: str | None = None
    ) -> AtlasResponse:
        """Traverse lineage (CAUSED_BY chains) from a node."""
        start_ms = time.monotonic_ns()

        # Embed query text for relevance scoring
        query_embedding = await self._embed_query(query_text)

        clamped_depth, clamped_nodes, _timeout = validate_traversal_bounds(
            max_depth=query.max_depth,
            max_nodes=query.max_nodes,
            timeout_ms=LINEAGE_BOUNDS_TIMEOUT_MS,
        )

        # Decode cursor as offset for lineage pagination
        offset = 0
        if query.cursor:
            try:
                offset = int(base64.urlsafe_b64decode(query.cursor.encode()).decode())
            except (ValueError, Exception):
                offset = 0

        fetch_limit = clamped_nodes + 1

        chains = await self._graph.lineage_chains(
            query.node_id, clamped_depth, fetch_limit, timeout_s=self._query_timeout_s
        )

        # Apply offset for pagination
        if offset > 0:
            chains = chains[offset:]

        has_more = len(chains) > clamped_nodes
        if has_more:
            chains = chains[:clamped_nodes]

        nodes: dict[str, AtlasNode] = {}
        edges: list[AtlasEdge] = []
        seen_edges: set[tuple[str, str]] = set()

        for chain in chains:
            for props in chain["nodes"]:
                event_id = props.get("event_id", "")
                if event_id and event_id not in nodes:
                    scores = self._score_event(props, query_embedding)
                    nodes[event_id] = self._atlas_node(props, scores)

            for chain_edge in chain["edges"]:
                edge_key = (chain_edge["source"], chain_edge["target"])
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append(
                        AtlasEdge(
                            source=chain_edge["source"],
                            target=chain_edge["target"],
                            edge_type="CAUSED_BY",
                            properties=chain_edge["properties"],
                        )
                    )

        await self._bump_access_counts(list(nodes.keys()))

        # Build next cursor (offset-based)
        next_cursor: str | None = None
        if has_more:
            next_offset = offset + clamped_nodes
            next_cursor = base64.urlsafe_b64encode(str(next_offset).encode()).decode()

        elapsed_ms = int((time.monotonic_ns() - start_ms) / 1_000_000)
        GRAPH_QUERY_DURATION.labels(query_type="lineage").observe(elapsed_ms / 1000.0)

        meta = QueryMeta(
            query_ms=elapsed_ms,
            nodes_returned=len(nodes),
            truncated=has_more,
            capacity=QueryCapacity(
                max_nodes=clamped_nodes,
                used_nodes=len(nodes),
                max_depth=clamped_depth,
            ),
        )

        return AtlasResponse(
            nodes=nodes,
            edges=edges,
            pagination=Pagination(cursor=next_cursor, has_more=has_more),
            meta=meta,
        )

    # ------------------------------------------------------------------
    # Seed channels
    # ------------------------------------------------------------------

    async def _get_graph_seeds(
        self,
        query: SubgraphQuery,
        seed_limit: int,
        *,
        seed_strategy: str,
    ) -> list[tuple[str, float]]:
        """Channel 1: Graph-based seed retrieval via intent-aware strategy."""
        seed_records = await self._graph.seed_events(
            seed_strategy, query.session_id, seed_limit, timeout_s=self._query_timeout_s
        )

        # Fallback to general (recency) if strategy returned nothing
        if not seed_records and seed_strategy != "general":
            seed_records = await self._graph.seed_events(
                "general", query.session_id, seed_limit, timeout_s=self._query_timeout_s
            )

        seeds: list[tuple[str, float]] = []
        for rank, props in enumerate(seed_records):
            event_id = props.get("event_id", "")
            if event_id:
                seeds.append((event_id, 1.0 / (rank + 1)))
        return seeds

    async def _get_vector_seeds(
        self,
        query_embedding: list[float] | None,
        limit: int,
    ) -> list[tuple[str, float]]:
        """Channel 2: Vector similarity seed retrieval via entity embeddings."""
        if query_embedding is None or self._vector_index is None:
            return []
        try:
            hits = await self._vector_index.nearest(
                query_embedding, top_k=limit, threshold=VECTOR_SEED_THRESHOLD
            )
            return [(hit.id, hit.score) for hit in hits]
        except Exception:
            logger.warning("vector_seed_retrieval_failed")
            return []

    async def _get_bm25_seeds(
        self,
        query_text: str,
        session_id: str | None,
        limit: int,
    ) -> list[tuple[str, float]]:
        """Channel 3: keyword (BM25) seed retrieval via the keyword index."""
        if self._keyword_index is None:
            return []
        try:
            hits = await self._keyword_index.search(query_text, session_id=session_id, limit=limit)
            return [(hit.id, hit.score) for hit in hits]
        except Exception:
            logger.warning("bm25_seed_retrieval_failed")
            return []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _score_event(
        self, props: dict[str, Any], query_embedding: list[float] | None
    ) -> NodeScores:
        decay = self._decay
        return score_node(
            props,
            query_embedding=query_embedding,
            s_base=decay.s_base,
            s_boost=decay.s_boost,
            w_recency=decay.weight_recency,
            w_importance=decay.weight_importance,
            w_relevance=decay.weight_relevance,
            w_user_affinity=decay.weight_user_affinity,
        )

    def _atlas_node(
        self,
        props: dict[str, Any],
        scores: NodeScores,
        retrieval_reason: str = "direct",
    ) -> AtlasNode:
        return build_atlas_node(
            props,
            scores,
            retrieval_reason=retrieval_reason,
            provenance_source=self._provenance_source,
        )

    async def _embed_query(self, query_text: str | None) -> list[float] | None:
        """Embed query text if embedding service is available."""
        if self._embedding_service is None or not query_text:
            return None
        try:
            return await self._embedding_service.embed_text(query_text)
        except Exception:
            logger.warning("query_embedding_failed", query_length=len(query_text))
            return None

    async def _bump_access_counts(self, event_ids: list[str]) -> None:
        """Increment access_count for a batch of event nodes."""
        if not event_ids:
            return
        await self._graph.record_access(event_ids, datetime.now(UTC).isoformat())

    async def _fetch_seed_nodes(
        self,
        seed_ids: list[str],
        nodes: dict[str, AtlasNode],
        seed_node_ids: list[str],
        query_embedding: list[float] | None,
    ) -> None:
        """Batch-fetch event nodes for seed IDs (single roundtrip)."""
        if not seed_ids:
            return
        new_ids = [sid for sid in seed_ids if sid not in nodes]
        if not new_ids:
            return

        records = await self._graph.get_event_nodes(new_ids, timeout_s=self._query_timeout_s)

        found_ids: set[str] = set()
        for props in records:
            event_id = props.get("event_id", "")
            if event_id:
                found_ids.add(event_id)
                seed_node_ids.append(event_id)
                scores = self._score_event(props, query_embedding)
                nodes[event_id] = self._atlas_node(props, scores)

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
    ) -> None:
        """Add cross-session entity events for personalization intents."""
        cross_intents = {"who_is", "personalize", "related"}
        dominant_intent = max(inferred_intents, key=lambda k: inferred_intents[k])
        if dominant_intent not in cross_intents:
            return

        cross_limit = max(1, query.max_nodes // 5)
        cross_records = await self._graph.cross_session_entity_events(
            query.session_id, cross_limit, timeout_s=self._query_timeout_s
        )

        for props in cross_records:
            event_id = props.get("event_id", "")
            if event_id and event_id not in nodes:
                scores = self._score_event(props, query_embedding)
                atlas_node = self._atlas_node(props, scores, retrieval_reason="proactive")
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
    ) -> None:
        """Batch neighbor traversal for all seeds (single roundtrip)."""
        if not seed_node_ids:
            return

        decay = self._decay
        neighbor_rows = await self._graph.event_neighbors(
            seed_node_ids, self._neighbor_limit, timeout_s=self._query_timeout_s
        )

        for nrec in neighbor_rows:
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
                nscores = self._score_event(neighbor_props, query_embedding)
                boosted_score = min(1.0, nscores.decay_score * (1.0 + weight * 0.1))
                boosted_scores = NodeScores(
                    decay_score=round(boosted_score, 6),
                    relevance_score=nscores.relevance_score,
                    importance_score=nscores.importance_score,
                )
                proactive_signal = _PROACTIVE_SIGNALS.get(rel_type, "related_context")
                atlas_node = self._atlas_node(
                    neighbor_props, boosted_scores, retrieval_reason="proactive"
                )
                atlas_node.proactive_signal = proactive_signal
                nodes[neighbor_eid] = atlas_node

            elif neighbor_entity_id and neighbor_entity_id not in nodes:
                neighbor_props = nrec.get("neighbor_props", {}) or {}
                nscores = score_entity_node(
                    neighbor_props,
                    query_embedding=query_embedding,
                    s_base=decay.entity_s_base,
                    s_boost=decay.entity_s_boost,
                    w_recency=decay.weight_recency,
                    w_importance=decay.weight_importance,
                    w_relevance=decay.weight_relevance,
                    w_user_affinity=decay.weight_user_affinity,
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
        ppr = self._ppr_settings
        if ppr is None or not ppr.enabled:
            return
        if len(nodes) > ppr.max_subgraph_size:
            return

        adjacency = build_adjacency(nodes, edges, edge_weights)
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
