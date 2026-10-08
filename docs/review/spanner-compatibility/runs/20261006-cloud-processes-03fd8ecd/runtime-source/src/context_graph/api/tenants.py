"""Authenticated dispatch substrate, deliberately not a production entry point.

The private dispatcher supports recording-port conformance. The public factory
refuses service until durable ownership and epoch fences are implemented.
"""

from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING

from starlette.responses import JSONResponse

from context_graph.tenancy import TenantAuthorizationError

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import FastAPI
    from starlette.types import Receive, Scope, Send

    from context_graph.tenancy import TenantBinding, TenantCatalog


class TenantServiceNotReadyError(RuntimeError):
    """Production tenant service cannot start without durable fencing."""


def create_tenant_app(catalog: TenantCatalog):
    raise TenantServiceNotReadyError(
        "Durable tenant database ownership and epoch fences are required"
    )


class _TenantDispatcher:
    """Internal conformance substrate; child factory must use the pinned bundle."""

    def __init__(self, catalog: TenantCatalog, child_factory: Callable[[TenantBinding], FastAPI]):
        self._catalog = catalog
        self._factory = child_factory
        self._children = {}
        self._stack = None
        self._ready = False
        self._active = 0
        self._condition = asyncio.Condition()

    async def _start(self):
        if self._stack is not None:
            raise RuntimeError("Tenant dispatcher already started")
        stack = AsyncExitStack()
        try:
            children = {}
            for binding in self._catalog.bindings:
                child = self._factory(binding)
                child.state.tenant_binding = binding
                await stack.enter_async_context(child.router.lifespan_context(child))
                children[binding.tenant_id] = child
        except BaseException:
            await stack.aclose()
            raise
        self._children = children
        self._stack = stack
        self._ready = True

    async def _stop(self):
        async with self._condition:
            self._ready = False
            while self._active:
                await self._condition.wait()
        stack, self._stack = self._stack, None
        self._children = {}
        if stack is not None:
            await stack.aclose()

    async def _lifespan(self, receive, send):
        message = await receive()
        if message["type"] != "lifespan.startup":
            return
        try:
            await self._start()
        except BaseException:
            await send({"type": "lifespan.startup.failed", "message": "Tenant startup failed"})
            return
        await send({"type": "lifespan.startup.complete"})
        try:
            await receive()
        finally:
            try:
                await self._stop()
            except BaseException:
                await send(
                    {"type": "lifespan.shutdown.failed", "message": "Tenant shutdown failed"}
                )
                return
        await send({"type": "lifespan.shutdown.complete"})

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "lifespan":
            await self._lifespan(receive, send)
            return
        if scope["type"] != "http":
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
            return
        if scope["path"] == "/health":
            await JSONResponse(
                {"status": "ready" if self._ready else "unavailable"},
                status_code=200 if self._ready else 503,
            )(scope, receive, send)
            return
        # Global metrics and unbound source signatures never reach a child.
        if scope["path"].startswith(("/metrics", "/v1/webhooks")):
            await JSONResponse({"detail": "Tenant endpoint unavailable"}, status_code=503)(
                scope, receive, send
            )
            return
        authorizations = [
            value for key, value in scope.get("headers", []) if key.lower() == b"authorization"
        ]
        hints = [value for key, value in scope.get("headers", []) if key.lower() == b"x-tenant-id"]
        try:
            if len(authorizations) != 1 or len(hints) > 1:
                raise TenantAuthorizationError
            header = authorizations[0].decode("ascii")
            if not header.startswith("Bearer "):
                raise TenantAuthorizationError
            principal = self._catalog.authenticate(
                header[7:],
                tenant_hint=hints[0].decode("ascii") if hints else None,
            )
        except (TenantAuthorizationError, UnicodeError):
            await JSONResponse({"detail": "Unauthorized tenant credential"}, status_code=401)(
                scope, receive, send
            )
            return
        async with self._condition:
            child = self._children.get(principal.tenant_id)
            available = self._ready and child is not None
            if available:
                self._active += 1
        if not available:
            await JSONResponse({"detail": "Tenant runtime unavailable"}, status_code=503)(
                scope, receive, send
            )
            return
        try:
            child_scope = dict(scope)
            child_scope["engram.principal"] = principal
            await child(child_scope, receive, send)
        finally:
            async with self._condition:
                self._active -= 1
                self._condition.notify_all()
