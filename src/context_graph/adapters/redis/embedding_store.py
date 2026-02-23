"""Entity embedding vector store backed by Redis Stack.

Stores entity embeddings as JSON documents at ``entity_emb:{entity_id}``
keys and provides KNN search via the HNSW vector index.

Source: ADR-0011 Tier 2b
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from redis.asyncio import Redis

log = structlog.get_logger(__name__)


@dataclass
class SemanticMatch:
    """Raw result from Redis KNN vector search.

    ``distance`` is the cosine distance (0 = identical, 2 = opposite).
    ``similarity`` is the cosine similarity: ``1.0 - distance``.
    """

    entity_id: str
    name: str
    entity_type: str
    distance: float
    similarity: float


def _float_vector_to_bytes(vector: list[float]) -> bytes:
    """Pack a list of floats into a little-endian FLOAT32 byte blob for KNN queries."""
    return struct.pack(f"<{len(vector)}f", *vector)


class EntityEmbeddingStore:
    """Redis-backed vector store for entity embeddings.

    Parameters
    ----------
    redis_client:
        Async Redis client.
    prefix:
        Key prefix for entity embedding JSON docs.
    index_name:
        RediSearch index name for KNN queries.
    """

    def __init__(
        self,
        redis_client: Redis,
        prefix: str = "entity_emb:",
        index_name: str = "idx:entity_embeddings",
    ) -> None:
        self._redis = redis_client
        self._prefix = prefix
        self._index_name = index_name

    async def store_embedding(
        self,
        entity_id: str,
        name: str,
        entity_type: str,
        embedding: list[float],
    ) -> None:
        """Store a single entity embedding as a JSON document."""
        key = f"{self._prefix}{entity_id}"
        doc: dict[str, Any] = {
            "entity_id": entity_id,
            "name": name,
            "entity_type": entity_type,
            "embedding": embedding,
        }
        import orjson

        await self._redis.execute_command("JSON.SET", key, "$", orjson.dumps(doc).decode())  # type: ignore[no-untyped-call]
        log.debug("entity_embedding_stored", entity_id=entity_id, name=name)

    async def store_batch(
        self,
        entities: list[dict[str, str]],
        embeddings: list[list[float]],
    ) -> None:
        """Store multiple entity embeddings via pipeline.

        Parameters
        ----------
        entities:
            List of dicts with keys ``entity_id``, ``name``, ``entity_type``.
        embeddings:
            Corresponding embedding vectors (same length as *entities*).
        """
        import orjson

        pipe = self._redis.pipeline(transaction=False)
        for entity, embedding in zip(entities, embeddings, strict=True):
            key = f"{self._prefix}{entity['entity_id']}"
            doc: dict[str, Any] = {
                "entity_id": entity["entity_id"],
                "name": entity["name"],
                "entity_type": entity["entity_type"],
                "embedding": embedding,
            }
            pipe.execute_command("JSON.SET", key, "$", orjson.dumps(doc).decode())
        await pipe.execute()
        log.debug("entity_embeddings_stored_batch", count=len(entities))

    async def search_similar(
        self,
        query_embedding: list[float],
        k: int = 10,
        entity_type_filter: str | None = None,
    ) -> list[SemanticMatch]:
        """Search for the *k* nearest entity embeddings via KNN.

        Parameters
        ----------
        query_embedding:
            The query vector (same dimensionality as stored vectors).
        k:
            Number of nearest neighbours to return.
        entity_type_filter:
            Optional entity type filter (exact tag match).

        Returns
        -------
        List of ``SemanticMatch`` sorted by ascending distance (best first).
        """
        blob = _float_vector_to_bytes(query_embedding)

        if entity_type_filter:
            # Tag filter — escape special characters
            escaped_type = entity_type_filter.replace("-", "\\-").replace(".", "\\.")
            filter_clause = f"@entity_type:{{{escaped_type}}}"
            query_str = f"({filter_clause})=>[KNN {k} @embedding $vec AS dist]"
        else:
            query_str = f"*=>[KNN {k} @embedding $vec AS dist]"

        from redis.commands.search.query import Query

        query = (
            Query(query_str)
            .sort_by("dist")
            .return_fields("entity_id", "name", "entity_type", "dist")
            .paging(0, k)
            .dialect(2)
        )

        result = await self._redis.ft(self._index_name).search(
            query, query_params={"vec": blob}
        )

        matches: list[SemanticMatch] = []
        for doc in result.docs:
            distance = float(doc.dist)
            matches.append(
                SemanticMatch(
                    entity_id=str(doc.entity_id),
                    name=str(doc.name),
                    entity_type=str(doc.entity_type),
                    distance=distance,
                    similarity=round(1.0 - distance, 6),
                )
            )
        return matches

    async def delete_embedding(self, entity_id: str) -> bool:
        """Delete an entity's embedding document. Returns True if deleted."""
        key = f"{self._prefix}{entity_id}"
        deleted = await self._redis.delete(key)
        return bool(deleted)

    async def get_embedding(self, entity_id: str) -> list[float] | None:
        """Retrieve the stored embedding vector for an entity."""
        key = f"{self._prefix}{entity_id}"
        raw = await self._redis.execute_command("JSON.GET", key, "$.embedding")  # type: ignore[no-untyped-call]
        if raw is None:
            return None
        import orjson

        raw_str = raw.decode() if isinstance(raw, bytes) else raw
        parsed = orjson.loads(raw_str)
        if isinstance(parsed, list) and len(parsed) > 0:
            return parsed[0]  # type: ignore[no-any-return]
        return None
