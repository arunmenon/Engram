"""Bound intake bodies before JSON parsing, without relying on Content-Length."""

from __future__ import annotations

import asyncio
from typing import Any

from starlette.responses import JSONResponse


class IntakeLimits:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT"}:
            await self.app(scope, receive, send)
            return
        chunks = []
        size = 0
        try:
            async with asyncio.timeout(15):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    chunk = message.get("body", b"")
                    size += len(chunk)
                    if size > 1_200_000:
                        await JSONResponse({"detail": "Intake request exceeds 1.2 MB"}, 413)(
                            scope, receive, send
                        )
                        return
                    chunks.append(chunk)
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            await JSONResponse({"detail": "Intake request timed out"}, 408)(scope, receive, send)
            return
        pending = True

        async def bounded_receive() -> Any:
            nonlocal pending
            if pending:
                pending = False
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        await self.app(scope, bounded_receive, send)
