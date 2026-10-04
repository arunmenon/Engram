"""Ledger migration and dual-run comparison (ADR-0019 §7, brief phase 3).

The source is the backend set configured today (``CG_STORAGE_*``); the
target is the same settings with every port switched to ``--to``.

Usage:
    python -m context_graph.migration copy --to spanner
        Copy the source ledger into the target until caught up. Refuses
        when the target holds events that were not imported.

    python -m context_graph.migration mirror --to spanner
        The dual run: keep importing new source events in order until
        SIGTERM. Resumes from the target's checkpoint after a restart.

    python -m context_graph.migration compare --to spanner [--graph]
        Compare ledgers (and, with --graph, the two graph projections and
        retrieval answers). Prints a JSON report; exits 1 on divergence.

The target's graph is built by running the workers against the target
(``CG_STORAGE_*=<target>``); the projection consumer replays the imported
ledger from the start.
"""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
from typing import TYPE_CHECKING, Any

import orjson
import structlog

from context_graph.adapters.registry import open_stores
from context_graph.migration.compare import (
    ComparisonReport,
    compare_graphs,
    compare_logs,
    compare_retrieval,
)
from context_graph.migration.mirror import LogMirror, MirrorRefusedError
from context_graph.settings import Settings

if TYPE_CHECKING:
    from context_graph.adapters.registry import Stores

log = structlog.get_logger(__name__)

STORAGE_PORTS = ("event_log", "subscription", "graph", "keyword_index", "vector_index")


def target_settings(settings: Settings, backend: str) -> Settings:
    """The same settings with every storage port on ``backend``."""
    storage = settings.storage.model_copy(update=dict.fromkeys(STORAGE_PORTS, backend))
    return settings.model_copy(update={"storage": storage})


async def _open_pair(settings: Settings, backend: str) -> tuple[Stores, Stores]:
    source = await open_stores(settings)
    target = await open_stores(target_settings(settings, backend))
    return source, target


async def run_copy(settings: Settings, backend: str) -> int:
    source, target = await _open_pair(settings, backend)
    try:
        mirror = LogMirror(
            source.event_log,
            target.event_log,  # type: ignore[arg-type]
            batch_size=settings.migration.batch_size,
        )
        try:
            await mirror.prepare()
        except MirrorRefusedError as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return 2
        report = await mirror.copy_once()
        print(orjson.dumps(report.__dict__).decode())
        return 0
    finally:
        await source.close()
        await target.close()


async def run_mirror(settings: Settings, backend: str) -> int:
    source, target = await _open_pair(settings, backend)
    stopping = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stopping.set)
    try:
        mirror = LogMirror(
            source.event_log,
            target.event_log,  # type: ignore[arg-type]
            batch_size=settings.migration.batch_size,
        )
        try:
            total = await mirror.run(
                poll_interval_s=settings.migration.poll_interval_ms / 1000.0,
                should_stop=stopping.is_set,
            )
        except MirrorRefusedError as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return 2
        log.info("log_mirror_stopped", imported=total)
        return 0
    finally:
        await source.close()
        await target.close()


async def run_compare(settings: Settings, backend: str, *, graph: bool) -> int:
    source, target = await _open_pair(settings, backend)
    try:
        report: ComparisonReport = await compare_logs(
            source.event_log, target.event_log, batch_size=settings.migration.batch_size
        )
        if graph:
            sample = settings.migration.sample_sessions
            report.merge(await compare_graphs(source.graph, target.graph, sample_sessions=sample))
            report.merge(
                await compare_retrieval(
                    source.graph, target.graph, sample_sessions=sample, decay=settings.decay
                )
            )
        print(orjson.dumps(report.as_dict(), option=orjson.OPT_INDENT_2).decode())
        return 0 if report.ok else 1
    finally:
        await source.close()
        await target.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Engram ledger migration and dual run")
    parser.add_argument("command", choices=("copy", "mirror", "compare"))
    parser.add_argument("--to", required=True, help="target backend, e.g. spanner")
    parser.add_argument("--graph", action="store_true", help="compare: also graph + retrieval")
    args: Any = parser.parse_args(argv)
    settings = Settings()
    if args.command == "copy":
        return asyncio.run(run_copy(settings, args.to))
    if args.command == "mirror":
        return asyncio.run(run_mirror(settings, args.to))
    return asyncio.run(run_compare(settings, args.to, graph=args.graph))


if __name__ == "__main__":
    sys.exit(main())
