"""Private tenant-child response authorization; production enablement is separate."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import parse_qs

from starlette.responses import JSONResponse

from context_graph.ports.errors import RuntimeFencedError
from context_graph.tenancy import Principal

if TYPE_CHECKING:
    from fastapi import FastAPI
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

    from context_graph.tenancy import TenantBinding


class _ResponseRefusedError(Exception):
    pass


class TenantResponseGuard:
    """Fresh active checks bracket execution, including cached/empty responses.

    Only bounded nonstreaming responses are released. The final strong check is
    the authorization linearization point; network send can overlap a later
    activation. Epochs must never be reused after freeze/reactivation.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        child: FastAPI,
        binding: TenantBinding,
        max_body_bytes: int = 8 * 1024 * 1024,
    ) -> None:
        self.app = app
        self.child = child
        self.binding = binding
        if max_body_bytes < 1:
            raise ValueError("Response bound must be positive")
        self.max_body_bytes = max_body_bytes

    async def _check(self) -> None:
        stores = getattr(self.child.state, "stores", None)
        check = getattr(stores, "tenant_read_check", None)
        if check is None:
            raise RuntimeFencedError("Tenant authorization check unavailable")
        try:
            await check()
        except RuntimeFencedError:
            raise
        except Exception as exc:
            raise RuntimeFencedError("Tenant authorization check unavailable") from exc

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        principal = scope.get("engram.principal")
        if not isinstance(principal, Principal):
            await JSONResponse({"detail": "Tenant authentication required"}, 401)(
                scope, receive, send
            )
            return
        if principal.tenant_id != self.binding.tenant_id:
            await JSONResponse({"detail": "Tenant is not authorized"}, 403)(scope, receive, send)
            return
        # Until tenant-bound cursors and bounded import outcomes are implemented,
        # reject these private entry paths before handlers can commit effects.
        path = scope.get("path", "").rstrip("/")
        if path == "/v1/events/import":
            await JSONResponse({"detail": "Tenant streaming import unavailable"}, 503)(
                scope, receive, send
            )
            return
        if "cursor" in parse_qs(
            scope.get("query_string", b"").decode("latin1"), keep_blank_values=True
        ):
            await JSONResponse({"detail": "Tenant cursor unavailable"}, 400)(scope, receive, send)
            return
        start: Message | None = None
        body_size = 0
        body = bytearray()
        completed = False
        released = False

        async def guarded_send(message: Message) -> None:
            nonlocal start, body_size, completed, released
            if message["type"] == "http.response.start":
                if start is not None:
                    raise _ResponseRefusedError("Duplicate response start")
                start = message
                return
            if message["type"] != "http.response.body" or start is None or completed:
                raise _ResponseRefusedError("Unsupported tenant response")
            body_size += len(message.get("body", b""))
            if body_size > self.max_body_bytes:
                raise _ResponseRefusedError("Tenant response exceeds bound")
            body.extend(message.get("body", b""))
            if message.get("more_body", False):
                return
            completed = True
            await self._check()
            released = True
            await send(start)
            await send({"type": "http.response.body", "body": bytes(body)})

        try:
            await self._check()
            await self.app(scope, receive, guarded_send)
            if not completed:
                raise _ResponseRefusedError("Incomplete tenant response")
        except (RuntimeFencedError, _ResponseRefusedError):
            if released:
                raise  # A network/background failure cannot retract a released response.
            await JSONResponse({"detail": "Tenant runtime unavailable"}, 503)(scope, receive, send)
