"""Consumer 2: Session Knowledge Extraction worker (ADR-0013).

Listens for ``system.session_end`` events on the Redis global stream.
When a session ends, collects all session events, runs LLM-based
knowledge extraction, and writes results (entities, preferences,
skills, interests) to Neo4j.

Source: ADR-0013 Consumer 2
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import orjson
import structlog

from context_graph.domain.entity_resolution import (
    EntityResolutionAction,
    SemanticCandidate,
    compute_transitive_closure,
    resolve_close_match,
    resolve_exact_match,
    resolve_semantic_match,
)
from context_graph.domain.models import Event
from context_graph.worker.consumer import BaseConsumer

if TYPE_CHECKING:
    from neo4j import AsyncDriver
    from redis.asyncio import Redis

    from context_graph.adapters.llm.client import LLMExtractionClient
    from context_graph.adapters.neo4j.store import Neo4jGraphStore
    from context_graph.ports.embedding import EmbeddingService
    from context_graph.ports.user_store import UserStore
    from context_graph.settings import Settings

log = structlog.get_logger(__name__)


class ExtractionConsumer(BaseConsumer):
    """Consumer 2: Session Knowledge Extraction.

    Triggers on ``system.session_end`` events. Collects all events from
    the ended session, runs LLM extraction, and writes extracted
    knowledge to the Neo4j graph.
    """

    def __init__(
        self,
        redis_client: Redis,
        neo4j_driver: AsyncDriver,
        neo4j_database: str,
        llm_client: LLMExtractionClient,
        settings: Settings,
        embedding_service: EmbeddingService | None = None,
        graph_store: Neo4jGraphStore | None = None,
        user_store: UserStore | None = None,
    ) -> None:
        consumer_settings = settings.consumer
        super().__init__(
            redis_client=redis_client,
            group_name=settings.redis.group_extraction,
            consumer_name="extraction-1",
            stream_key=settings.redis.global_stream,
            block_timeout_ms=settings.redis.block_timeout_ms,
            max_retries=consumer_settings.max_retries,
            claim_idle_ms=consumer_settings.claim_idle_ms,
            claim_batch_size=consumer_settings.claim_batch_size,
            dlq_stream_suffix=consumer_settings.dlq_stream_suffix,
        )
        self._neo4j_driver = neo4j_driver
        self._neo4j_database = neo4j_database
        self._llm_client = llm_client
        self._settings = settings
        self._event_key_prefix = settings.redis.event_key_prefix
        self._session_turn_counts: dict[str, int] = {}
        self._mid_session_interval: int = getattr(settings, "mid_session_extraction_interval", 50)
        self._embedding_service = embedding_service
        self._graph_store = graph_store
        self._user_store = user_store

    async def _fetch_event_doc(self, event_id: str) -> dict[str, Any] | None:
        """Fetch the full event JSON document from Redis."""
        json_key = f"{self._event_key_prefix}{event_id}"
        raw_json = await self._redis.execute_command("JSON.GET", json_key, "$")  # type: ignore[no-untyped-call]
        if raw_json is None:
            return None
        raw_str = raw_json.decode() if isinstance(raw_json, bytes) else raw_json
        parsed = orjson.loads(raw_str)
        doc: dict[str, Any] = parsed[0] if isinstance(parsed, list) and len(parsed) > 0 else parsed
        return doc

    async def process_message(self, entry_id: str, data: dict[str, str]) -> None:
        """Process a stream entry: check for session_end and trigger extraction.

        The stream only carries ``event_id`` — we must fetch the full JSON
        document to read ``event_type`` and ``session_id``.
        """
        event_id = data.get("event_id")
        if not event_id:
            return

        doc = await self._fetch_event_doc(event_id)
        if doc is None:
            log.warning("extraction_event_json_not_found", event_id=event_id)
            return

        event_type = doc.get("event_type", "")
        session_id = doc.get("session_id")
        agent_id = doc.get("agent_id", "unknown")

        # Track per-session turn counts for mid-session extraction
        if event_type and not event_type.startswith("system.") and session_id:
            self._session_turn_counts[session_id] = self._session_turn_counts.get(session_id, 0) + 1
            if self._session_turn_counts[session_id] % self._mid_session_interval == 0:
                log.info(
                    "mid_session_extraction_triggered",
                    session_id=session_id,
                    turn_count=self._session_turn_counts[session_id],
                )
                events, raw_docs = await self._collect_session_events(session_id)
                if events:
                    source_event_ids = [str(e.event_id) for e in events]
                    result = await self._llm_client.extract_from_session(
                        events=events,
                        session_id=session_id,
                        agent_id=agent_id,
                        event_payloads=raw_docs,
                    )
                    await self._write_extraction_results(
                        session_id, agent_id, result, source_event_ids
                    )
                return

        if event_type != "system.session_end":
            return

        if not session_id:
            log.warning(
                "session_end_missing_session_id",
                entry_id=entry_id,
            )
            return

        log.info(
            "extraction_triggered",
            entry_id=entry_id,
            session_id=session_id,
            agent_id=agent_id,
        )

        events, raw_docs = await self._collect_session_events(session_id)
        if not events:
            log.info(
                "extraction_no_events",
                session_id=session_id,
            )
            return

        source_event_ids = [str(e.event_id) for e in events]

        result = await self._llm_client.extract_from_session(
            events=events,
            session_id=session_id,
            agent_id=agent_id,
            event_payloads=raw_docs,
        )

        await self._write_extraction_results(session_id, agent_id, result, source_event_ids)

        log.info(
            "extraction_completed",
            session_id=session_id,
            entities=len(result.get("entities", [])),
            preferences=len(result.get("preferences", [])),
            skills=len(result.get("skills", [])),
            interests=len(result.get("interests", [])),
        )

    async def _collect_session_events(
        self, session_id: str
    ) -> tuple[list[Event], list[dict[str, Any]]]:
        """Collect all events for a session from Redis JSON store.

        Returns (events, raw_docs) where raw_docs contain the full JSON
        documents including payload content for LLM extraction.
        """
        events: list[Event] = []
        raw_docs: list[dict[str, Any]] = []

        # Read from the per-session stream (bounded to this session only)
        session_stream_key = f"events:session:{session_id}"
        try:
            session_entries = await self._redis.xrange(
                session_stream_key,
                min="-",
                max="+",
            )
        except Exception:
            log.warning(
                "session_stream_read_failed",
                session_id=session_id,
                stream_key=session_stream_key,
            )
            return events, raw_docs

        for _entry_id, entry_data in session_entries:
            decoded = {
                (k.decode() if isinstance(k, bytes) else k): (
                    v.decode() if isinstance(v, bytes) else v
                )
                for k, v in entry_data.items()
            }

            event_id = decoded.get("event_id")
            if not event_id:
                continue

            json_key = f"{self._event_key_prefix}{event_id}"
            raw_json = await self._redis.execute_command("JSON.GET", json_key, "$")  # type: ignore[no-untyped-call]
            if raw_json is None:
                continue

            raw_str = raw_json.decode() if isinstance(raw_json, bytes) else raw_json
            parsed = orjson.loads(raw_str)
            doc = parsed[0] if isinstance(parsed, list) and len(parsed) > 0 else parsed

            # Keep full doc for payload extraction before stripping
            raw_docs.append(dict(doc))

            doc.pop("occurred_at_epoch_ms", None)

            try:
                event = Event.model_validate(doc, strict=False)
                events.append(event)
            except Exception:
                log.warning(
                    "event_parse_failed",
                    event_id=event_id,
                    session_id=session_id,
                )

        events.sort(key=lambda e: e.occurred_at)
        # Sort raw_docs to match event order by event_id
        event_id_order = {str(e.event_id): i for i, e in enumerate(events)}
        raw_docs.sort(key=lambda d: event_id_order.get(d.get("event_id", ""), 999999))

        log.debug(
            "session_events_collected",
            session_id=session_id,
            event_count=len(events),
        )
        return events, raw_docs

    async def _fetch_existing_entities(self) -> list[dict[str, Any]]:
        """Fetch existing Entity nodes from Neo4j for deduplication."""
        query = (
            "MATCH (n:Entity) "
            "RETURN n.entity_id AS entity_id, n.name AS name, "
            "n.entity_type AS entity_type LIMIT 1000"
        )
        async with self._neo4j_driver.session(database=self._neo4j_database) as session:
            result = await session.run(query)
            records = [record async for record in result]
        return [
            {
                "entity_id": r["entity_id"],
                "name": r["name"],
                "entity_type": r["entity_type"],
            }
            for r in records
        ]

    async def _write_extraction_results(
        self,
        session_id: str,
        agent_id: str,
        result: dict[str, Any],
        source_event_ids: list[str],
    ) -> None:
        """Write extraction results to Neo4j via UserStore protocol."""
        us = self._user_store
        user_entity_id = f"user:{agent_id}"
        now = datetime.now(UTC).isoformat()

        # --- Write UserProfile from persona data ---
        persona_data = result.get("persona")
        if us is not None and isinstance(persona_data, dict) and any(persona_data.values()):
            profile_data = {
                "user_id": user_entity_id,
                "display_name": persona_data.get("name") or agent_id,
                "timezone": None,
                "language": None,
                "communication_style": persona_data.get("communication_style"),
                "technical_level": persona_data.get("tech_level"),
            }
            role = persona_data.get("role")
            if role and persona_data.get("name"):
                profile_data["display_name"] = f"{persona_data['name']} ({role})"
            await us.write_user_profile(profile_data=profile_data)
            log.info(
                "extraction_wrote_user_profile",
                session_id=session_id,
                user_entity_id=user_entity_id,
                persona_name=persona_data.get("name"),
                persona_role=persona_data.get("role"),
            )

        # --- Write extracted entities + REFERENCES edges ---
        existing_entities = await self._fetch_existing_entities()
        same_as_edges: list[tuple[str, str]] = []
        mention_counts: dict[str, int] = {
            e["entity_id"]: 1 for e in existing_entities if "entity_id" in e
        }

        for entity_data in result.get("entities", []):
            entity_name = entity_data.get("name", "")
            entity_type = entity_data.get("entity_type", "concept")
            if not entity_name:
                continue

            # Run entity resolution cascade: Tier 1 -> 2a -> 2b
            resolution = resolve_exact_match(entity_name, entity_type, existing_entities)
            if resolution is None:
                resolution = resolve_close_match(
                    entity_name, entity_type, existing_entities, threshold=0.9
                )
            if resolution is None:
                resolution, _semantic_matches = await self._resolve_semantic(
                    entity_name, entity_type
                )

            if resolution is not None and resolution.action == EntityResolutionAction.MERGE:
                entity_id = f"entity:{resolution.canonical_name}"
                mention_counts[entity_id] = mention_counts.get(entity_id, 0) + 1
                log.debug(
                    "entity_resolved_merge",
                    name=entity_name,
                    canonical=resolution.canonical_name,
                )
            elif resolution is not None and resolution.action in (
                EntityResolutionAction.SAME_AS,
                EntityResolutionAction.RELATED_TO,
            ):
                entity_id = f"entity:{entity_name}"
                embedding = await self._compute_entity_embedding(entity_name)
                await self._merge_entity_node(
                    entity_id=entity_id,
                    name=entity_name,
                    entity_type=entity_type,
                    now=now,
                    embedding=embedding,
                )
                canonical_id = f"entity:{resolution.canonical_name}"
                await self._merge_resolution_edge(
                    source_id=entity_id,
                    target_id=canonical_id,
                    action=resolution.action,
                    confidence=resolution.confidence,
                    justification=resolution.justification,
                )
                if resolution.action == EntityResolutionAction.SAME_AS:
                    same_as_edges.append((entity_id, canonical_id))
                mention_counts[entity_id] = mention_counts.get(entity_id, 0) + 1
                mention_counts[canonical_id] = mention_counts.get(canonical_id, 0) + 1
                log.debug(
                    "entity_resolved_link",
                    name=entity_name,
                    action=resolution.action,
                    canonical=resolution.canonical_name,
                )
            else:
                entity_id = f"entity:{entity_name}"
                embedding = await self._compute_entity_embedding(entity_name)
                await self._merge_entity_node(
                    entity_id=entity_id,
                    name=entity_name,
                    entity_type=entity_type,
                    now=now,
                    embedding=embedding,
                )
                existing_entities.append(
                    {"entity_id": entity_id, "name": entity_name, "entity_type": entity_type}
                )
                mention_counts[entity_id] = mention_counts.get(entity_id, 0) + 1
                log.debug("entity_created", name=entity_name, entity_id=entity_id)

            for event_id in source_event_ids:
                await self._merge_references_edge(
                    event_id=event_id,
                    entity_id=entity_id,
                )

        # --- Transitive closure: consolidate SAME_AS clusters ---
        if same_as_edges and self._graph_store is not None:
            clusters = compute_transitive_closure(same_as_edges, mention_counts)
            for canonical_id, members in clusters.items():
                if len(members) > 1:
                    await self._graph_store.consolidate_entity_cluster(
                        cluster_ids=members, canonical_id=canonical_id
                    )
            log.info(
                "transitive_closure_applied",
                session_id=session_id,
                edge_count=len(same_as_edges),
                cluster_count=len(clusters),
            )

        # --- Write preferences ---
        if us is not None:
            for pref_data in result.get("preferences", []):
                source_quote = pref_data.get("source_quote", "")
                await us.write_preference_with_edges(
                    user_entity_id=user_entity_id,
                    preference_data=pref_data,
                    source_event_ids=source_event_ids,
                    derivation_info={
                        "method": "llm_extraction",
                        "session_id": session_id,
                        "source_quote": source_quote,
                    },
                )

        # --- Write skills ---
        if us is not None:
            for skill_data in result.get("skills", []):
                source_quote = skill_data.get("source_quote", "")
                await us.write_skill_with_edges(
                    user_entity_id=user_entity_id,
                    skill_data=skill_data,
                    source_event_ids=source_event_ids,
                    derivation_info={
                        "method": "llm_extraction",
                        "session_id": session_id,
                        "source_quote": source_quote,
                    },
                )

        # --- Write interests ---
        if us is not None:
            for interest_data in result.get("interests", []):
                await us.write_interest_edge(
                    user_entity_id=user_entity_id,
                    entity_name=interest_data.get("entity_name", ""),
                    entity_type=interest_data.get("entity_type", "concept"),
                    weight=interest_data.get("weight", 0.5),
                    source=interest_data.get("source", "inferred"),
                )
                interest_entity_id = f"entity:{interest_data.get('entity_name', '')}"
                for event_id in source_event_ids:
                    await us.write_derived_from_edge(
                        source_node_id=interest_entity_id,
                        source_id_field="entity_id",
                        event_id=event_id,
                        method="llm_extraction",
                        session_id=session_id,
                    )

        log.info(
            "extraction_results_written",
            session_id=session_id,
            user_entity_id=user_entity_id,
        )

    async def _resolve_semantic(
        self,
        entity_name: str,
        entity_type: str,
    ) -> tuple[Any | None, list[dict[str, Any]]]:
        """Tier 2b: Embed entity name and search for semantic matches via Neo4j.

        Returns (resolution_result, raw_matches) where raw_matches can be
        used for logging / diagnostics.  Returns (None, []) if embedding
        service or graph store is not configured or no match exceeds the threshold.
        """
        if self._embedding_service is None or self._graph_store is None:
            return None, []

        embedding_settings = self._settings.embedding
        query_vec = await self._embedding_service.embed_text(entity_name)
        raw_matches = await self._graph_store.search_similar_entities(
            query_embedding=query_vec,
            top_k=embedding_settings.knn_k,
            threshold=embedding_settings.related_to_threshold,
        )

        if not raw_matches:
            return None, []

        candidates = [
            SemanticCandidate(
                name=m["name"],
                entity_type=m["entity_type"],
                entity_id=m["entity_id"],
                similarity=m["score"],
            )
            for m in raw_matches
        ]

        resolution = resolve_semantic_match(
            name=entity_name,
            entity_type=entity_type,
            candidates=candidates,
            same_as_threshold=embedding_settings.same_as_threshold,
            related_to_threshold=embedding_settings.related_to_threshold,
        )
        return resolution, raw_matches

    async def _compute_entity_embedding(
        self,
        entity_name: str,
    ) -> list[float]:
        """Compute embedding for an entity name. Returns empty list on failure."""
        if self._embedding_service is None:
            return []
        try:
            return await self._embedding_service.embed_text(entity_name)
        except Exception:
            log.warning("entity_embedding_failed", name=entity_name)
            return []

    async def _merge_entity_node(
        self,
        entity_id: str,
        name: str,
        entity_type: str,
        now: str,
        embedding: list[float] | None = None,
    ) -> None:
        """MERGE an Entity node in Neo4j with optional embedding."""
        from context_graph.adapters.neo4j.queries import MERGE_ENTITY_NODE

        params = {
            "entity_id": entity_id,
            "name": name,
            "entity_type": entity_type,
            "first_seen": now,
            "last_seen": now,
            "mention_count": 1,
            "embedding": embedding or [],
        }
        async with self._neo4j_driver.session(database=self._neo4j_database) as session:

            async def _write(tx: Any) -> None:
                await tx.run(MERGE_ENTITY_NODE, params)

            await session.execute_write(_write)

    async def _merge_references_edge(
        self,
        event_id: str,
        entity_id: str,
    ) -> None:
        """MERGE a REFERENCES edge from Event to Entity."""
        from context_graph.adapters.neo4j.queries import MERGE_REFERENCES

        params = {
            "source_id": event_id,
            "target_id": entity_id,
            "props": {},
        }
        async with self._neo4j_driver.session(database=self._neo4j_database) as session:

            async def _write(tx: Any) -> None:
                await tx.run(MERGE_REFERENCES, params)

            await session.execute_write(_write)

    async def _merge_resolution_edge(
        self,
        source_id: str,
        target_id: str,
        action: EntityResolutionAction,
        confidence: float,
        justification: str,
    ) -> None:
        """MERGE a SAME_AS or RELATED_TO edge between entities."""
        from context_graph.adapters.neo4j.queries import MERGE_RELATED_TO, MERGE_SAME_AS

        query = MERGE_SAME_AS if action == EntityResolutionAction.SAME_AS else MERGE_RELATED_TO
        params = {
            "source_id": source_id,
            "target_id": target_id,
            "props": {
                "confidence": confidence,
                "justification": justification,
                "resolved_at": datetime.now(UTC).isoformat(),
            },
        }
        async with self._neo4j_driver.session(database=self._neo4j_database) as session:

            async def _write(tx: Any) -> None:
                await tx.run(query, params)

            await session.execute_write(_write)
