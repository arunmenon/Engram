import logging
import os

import httpx
from typing import Any

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_RETRY_BACKOFF = 0.5  # seconds


class ContextGraphClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or os.environ.get(
            "CG_API_URL", "http://localhost:8000"
        )
        transport = httpx.AsyncHTTPTransport(retries=_MAX_RETRIES)
        self.client = httpx.AsyncClient(
            base_url=self.base_url, timeout=30.0, transport=transport
        )

    async def ingest_event(self, event: dict[str, Any]) -> dict:
        resp = await self.client.post("/v1/events", json=event)
        resp.raise_for_status()
        return resp.json()

    async def get_session_context(
        self, session_id: str, query: str = "", max_nodes: int = 50
    ) -> dict:
        params = {"query": query, "max_nodes": max_nodes}
        resp = await self.client.get(f"/v1/context/{session_id}", params=params)
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        await self.client.aclose()
