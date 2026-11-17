"""Own the SDK database, session pool and transports opened by Engram (#26)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any


def prepare_cleanup(database: Any, client: Any, pool: Any) -> None:
    """Install cleanup before any snapshot starts the SDK maintenance thread.

    SDK 3.71 sleeps for ten minutes between polls, including during close().
    Bound that sleep on this owned manager only. Remove this compatibility
    adjustment when a released SDK uses an interruptible termination wait.
    Multiplexed sessions are server-managed; SDK delete deliberately skips
    them. Closing their local manager does not assert remote session deletion.
    """
    manager = getattr(database, "sessions_manager", None)
    if manager is not None and hasattr(manager, "_MAINTENANCE_THREAD_POLLING_INTERVAL"):
        manager._MAINTENANCE_THREAD_POLLING_INTERVAL = timedelta(seconds=1)
    closed = False

    def close() -> None:
        nonlocal closed
        if closed:
            return
        errors: list[Exception] = []
        operations = [database.close, pool.clear]
        # Only close cached transports; accessing SDK properties here would
        # instantiate new clients that this database never used.
        for owner, name in (
            (database, "_spanner_api"),
            (client, "_database_admin_api"),
            (client, "_instance_admin_api"),
        ):
            api = getattr(owner, name, None)
            if api is not None:
                operations.append(api.transport.close)
        operations.append(client.close)
        for operation in operations:
            try:
                operation()
            except Exception as exc:
                errors.append(exc)
        if errors:
            raise ExceptionGroup("Spanner resource cleanup failed", errors)
        closed = True

    database._engram_close = close


def close_database(database: Any) -> None:
    """Close an owned handle; ordinary SDK handles retain their native close."""
    closer = getattr(database, "_engram_close", None)
    if closer is None:
        database.close()
    else:
        closer()
