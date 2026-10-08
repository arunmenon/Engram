"""Shared experiment plumbing, separate from goal fixtures and assertions.

No scenario runner or framework. Helpers preserve authenticated bound requests,
exact observations and shutdown ordering before goal-owned cleanup.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shlex
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from google.cloud.spanner_v1 import KeySet
from starlette.responses import JSONResponse

from context_graph.api.tenant_responses import TenantResponseGuard
from context_graph.settings import Settings
from context_graph.tenancy import (
    CredentialGrant,
    Principal,
    TenantAuthorizationError,
    TenantCatalog,
)

CONTROL_COLUMNS = [
    "tenant_id",
    "database_resource",
    "binding_id",
    "epoch",
    "bundle_digest",
    "serving_state",
]


def load_credentials(path: Path) -> dict[str, str]:
    keys = (
        "GOOGLE_CLOUD_PROJECT",
        "SPANNER_INSTANCE_ID",
        "SPANNER_DATABASE_ID",
        "GOOGLE_OAUTH_ACCESS_TOKEN",
    )
    result = {}
    for line in path.read_text().splitlines():
        if any(
            line.startswith(prefix) for key in keys for prefix in (key + "=", "export " + key + "=")
        ):
            key, _, value = shlex.split(line)[-1].partition("=")
            result[key] = value
    if set(result) != set(keys):
        raise ValueError("four expected credential assignments required")
    return result


def durable_json(path, value):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w") as output:
        json.dump(value, output, indent=2)
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def fingerprint(database):
    """Application rows and existing DDL; control table is separately observed."""
    names = (
        "Events",
        "GraphNodes",
        "GraphEdges",
        "ConsumerGroups",
        "ConsumerCursors",
        "ConsumerDeliveries",
        "ConsumerDeadLetters",
    )
    evidence = {}
    with database.snapshot(multi_use=True) as snapshot:
        for table in names:
            rows = list(snapshot.execute_sql(f"SELECT * FROM {table}"))
            canonical = sorted(json.dumps(row, sort_keys=True, default=str) for row in rows)
            evidence[table] = {
                "count": len(rows),
                "sha256": hashlib.sha256(json.dumps(canonical).encode()).hexdigest(),
            }
    return evidence


def runtime_settings(values):
    settings = Settings()
    for port in ("event_log", "subscription", "graph", "keyword_index", "vector_index"):
        setattr(settings.storage, port, "spanner")
    settings.spanner.project = values["GOOGLE_CLOUD_PROJECT"]
    settings.spanner.instance = values["SPANNER_INSTANCE_ID"]
    settings.spanner.database = "engram-compat-target"
    settings.spanner.emulator_host = None
    settings.spanner.check_schema = True
    settings.spanner.create_if_missing = False
    settings.spanner.allow_create_on_instance = False
    settings.archive.enabled = False
    settings.ontology.packs = []
    settings.ontology.builtin_packs = []
    return settings


async def await_settled(awaitable):
    """Cancellation cannot let SDK threads outlive fixture cleanup."""
    task = asyncio.ensure_future(awaitable)
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
            except BaseException:
                break
        with suppress(BaseException):
            task.result()
        raise


def read_owner(database):
    with database.snapshot() as snapshot:
        return [
            list(row)
            for row in snapshot.read("TenantControl", CONTROL_COLUMNS, KeySet(keys=[["active"]]))
        ]


class DemoAuthentication:
    """Single-bound test entrypoint using actual catalog credential verification.

    HMAC routes authenticate in Engram's handler. Other requests authenticate
    against the actual immutable catalog before Engram's tenant role/response
    guards. This is not the disabled public multi-tenant dispatcher.
    """

    def __init__(self, app, binding, *, token):
        self.app = app
        principal = Principal("demo.query", binding.tenant_id, frozenset({"api"}), "demo.query")
        self.catalog = TenantCatalog((binding,), (CredentialGrant.from_token(principal, token),))
        self.guarded = TenantResponseGuard(app, child=app, binding=binding)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"].startswith("/v1/webhooks/"):
            await self.app(scope, receive, send)
            return
        headers = [v for k, v in scope.get("headers", []) if k.lower() == b"authorization"]
        try:
            if len(headers) != 1 or not headers[0].startswith(b"Bearer "):
                raise TenantAuthorizationError
            principal = self.catalog.authenticate(headers[0][7:].decode("ascii"))
        except (TenantAuthorizationError, UnicodeError):
            await JSONResponse({"detail": "Unauthorized"}, 401)(scope, receive, send)
            return
        scope = dict(scope)
        scope["engram.principal"] = principal
        await self.guarded(scope, receive, send)


def snapshot(database):
    with database.snapshot(multi_use=True) as snap:
        return {
            "events": [
                list(r)
                for r in snap.execute_sql("SELECT event_id, document, acceptance FROM Events")
            ],
            "nodes": [
                list(r) for r in snap.execute_sql("SELECT label, node_id, props FROM GraphNodes")
            ],
            "edges": [
                list(r)
                for r in snap.execute_sql(
                    "SELECT src_label, src_id, edge_type, dst_label, dst_id, props FROM GraphEdges"
                )
            ],
            "pending": [
                list(r)
                for r in snap.execute_sql("SELECT group_name, event_id FROM ConsumerDeliveries")
            ],
            "dead_letters": [
                list(r)
                for r in snap.execute_sql("SELECT group_name, event_id FROM ConsumerDeadLetters")
            ],
        }


async def stop_demo(consumers, tasks, stores, server, server_task):
    """Settle workers and close stores/server before any fixture deletion.

    Never cancel a worker's to_thread await: its SDK transaction may still commit.
    Return shutdown errors so each goal retains its existing failure assertion.
    """
    for consumer in consumers:
        consumer.stop()
    task_results = await asyncio.gather(*tasks, return_exceptions=True)
    errors = [type(r).__name__ for r in task_results if isinstance(r, BaseException)]
    for store in stores:
        try:
            await store.close()
        except Exception as exc:
            errors.append(type(exc).__name__)
    if server is not None:
        server.should_exit = True
    if server_task is not None:
        try:
            await asyncio.wait_for(server_task, 15)
        except Exception as exc:
            errors.append(type(exc).__name__)
    return errors
