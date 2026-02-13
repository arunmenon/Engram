"""Base consumer class for Redis Stream consumer workers.

Provides the XREADGROUP lifecycle loop that all consumers share:
create group, read messages, process, acknowledge. Subclasses
override ``process_message`` with their specific logic.

Source: ADR-0005, ADR-0013
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from redis.asyncio import Redis

log = structlog.get_logger(__name__)


class BaseConsumer:
    """Base class for Redis Stream consumer workers.

    Manages the XREADGROUP loop: read pending/new messages, dispatch to
    ``process_message``, and XACK on success. On failure the message
    stays in the Pending Entries List (PEL) for automatic retry on
    next read cycle.
    """

    def __init__(
        self,
        redis_client: Redis,
        group_name: str,
        consumer_name: str,
        stream_key: str,
        batch_size: int = 10,
        block_timeout_ms: int = 5000,
    ) -> None:
        self._redis = redis_client
        self._group_name = group_name
        self._consumer_name = consumer_name
        self._stream_key = stream_key
        self._batch_size = batch_size
        self._block_timeout_ms = block_timeout_ms
        self._stopped = False

    async def ensure_group(self) -> None:
        """Create the consumer group if it does not already exist.

        Uses ``XGROUP CREATE ... MKSTREAM`` so the stream is created
        automatically if it doesn't exist. The ``$`` ID means only new
        messages are delivered (pending messages from before group
        creation are ignored).
        """
        try:
            await self._redis.xgroup_create(
                name=self._stream_key,
                groupname=self._group_name,
                id="0",
                mkstream=True,
            )
            log.info(
                "consumer_group_created",
                group=self._group_name,
                stream=self._stream_key,
            )
        except Exception as exc:  # noqa: BLE001
            # BUSYGROUP means group already exists — that's fine
            error_msg = str(exc)
            if "BUSYGROUP" in error_msg:
                log.debug(
                    "consumer_group_exists",
                    group=self._group_name,
                    stream=self._stream_key,
                )
            else:
                raise

    async def run(self) -> None:
        """Main consumer loop.

        Reads messages via XREADGROUP, dispatches each to
        ``process_message``, and ACKs on success. Loops until
        ``stop()`` is called.
        """
        await self.ensure_group()
        log.info(
            "consumer_started",
            group=self._group_name,
            consumer=self._consumer_name,
            stream=self._stream_key,
        )

        # Drain pending messages (PEL recovery) before reading new ones
        while not self._stopped:
            pending = await self._redis.xreadgroup(
                groupname=self._group_name,
                consumername=self._consumer_name,
                streams={self._stream_key: "0"},
                count=self._batch_size,
                block=0,
            )
            if not pending or not any(entries for _, entries in pending):
                break
            for _stream_name, entries in pending:
                for entry_id_raw, data in entries:
                    entry_id = (
                        entry_id_raw.decode()
                        if isinstance(entry_id_raw, bytes)
                        else str(entry_id_raw)
                    )
                    decoded_data = {
                        (k.decode() if isinstance(k, bytes) else k): (
                            v.decode() if isinstance(v, bytes) else v
                        )
                        for k, v in data.items()
                    }
                    try:
                        await self.process_message(entry_id, decoded_data)
                        await self._redis.xack(
                            self._stream_key,
                            self._group_name,
                            entry_id,
                        )
                    except Exception:
                        log.exception(
                            "pending_message_processing_failed",
                            entry_id=entry_id,
                            group=self._group_name,
                        )

        log.info("pending_drain_completed", group=self._group_name)

        while not self._stopped:
            messages = await self._redis.xreadgroup(
                groupname=self._group_name,
                consumername=self._consumer_name,
                streams={self._stream_key: ">"},
                count=self._batch_size,
                block=self._block_timeout_ms,
            )

            if not messages:
                continue

            for _stream_name, entries in messages:
                for entry_id_raw, data in entries:
                    entry_id = (
                        entry_id_raw.decode()
                        if isinstance(entry_id_raw, bytes)
                        else str(entry_id_raw)
                    )
                    # Decode bytes keys/values in the data dict
                    decoded_data = {
                        (k.decode() if isinstance(k, bytes) else k): (
                            v.decode() if isinstance(v, bytes) else v
                        )
                        for k, v in data.items()
                    }

                    try:
                        await self.process_message(entry_id, decoded_data)
                        await self._redis.xack(
                            self._stream_key,
                            self._group_name,
                            entry_id,
                        )
                    except Exception:
                        # Message stays in PEL for retry on next read cycle
                        log.exception(
                            "message_processing_failed",
                            entry_id=entry_id,
                            group=self._group_name,
                            consumer=self._consumer_name,
                        )

        log.info(
            "consumer_stopped",
            group=self._group_name,
            consumer=self._consumer_name,
        )

    async def process_message(self, entry_id: str, data: dict[str, str]) -> None:
        """Process a single stream message. Override in subclasses."""
        raise NotImplementedError

    def stop(self) -> None:
        """Signal the consumer loop to stop gracefully."""
        self._stopped = True
