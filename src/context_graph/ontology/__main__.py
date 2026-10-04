"""Ontology operations (ADR-0018 phase 3).

Usage:
    python -m context_graph.ontology status
        The loaded packs, the version the configured graph records, and how
        the change between them would be applied (JSON).

    python -m context_graph.ontology evaluate [--eval-dir DIR]
        Run the evaluation sets of the active packs with intents on the
        configured graph. Exits 1 when a set fails or is missing.

    python -m context_graph.ontology rebuild --target KEY=VALUE [...] [--eval-dir DIR]
                                             [--skip-gate] [--force]
        Blue/green: project the configured ledger into the graph that the
        settings with the ``--target`` overrides select (for example
        ``CG_NEO4J_URI=bolt://green:7687`` or ``CG_SPANNER_DATABASE=engram_v2``),
        run the evaluation gate on it and record the result. Exits 0 when
        the gate passes; switch by deploying with the same overrides. Exits
        1 when the gate fails and 2 when the target holds another version.

Evaluation sets are ``<pack>.eval.yaml`` in ``--eval-dir``, then in
``CG_ONTOLOGY_PACK_DIRS``, then next to the built-in packs.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

import orjson

from context_graph.adapters.registry import open_stores
from context_graph.ontology.evaluation import run_gate
from context_graph.ontology.rebuild import RebuildRefusedError, rebuild
from context_graph.ontology.runtime import configured_projector
from context_graph.ontology.versioning import plan_change, read_state
from context_graph.retrieval.artifacts import ArtifactRetriever
from context_graph.settings import Settings

if TYPE_CHECKING:
    from collections.abc import Iterator


def _print(value: Any) -> None:
    print(orjson.dumps(value, option=orjson.OPT_INDENT_2).decode())  # noqa: T201 - CLI output


@contextmanager
def _environment(overrides: dict[str, str]) -> Iterator[None]:
    saved = {key: os.environ.get(key) for key in overrides}
    os.environ.update(overrides)
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def target_settings(overrides: list[str]) -> Settings:
    """The configured settings with ``KEY=VALUE`` environment overrides applied."""
    pairs: dict[str, str] = {}
    for item in overrides:
        key, sep, value = item.partition("=")
        if not sep or not key.startswith("CG_"):
            msg = f"--target takes CG_KEY=VALUE, got {item!r}"
            raise SystemExit(msg)
        pairs[key] = value
    with _environment(pairs):
        return Settings()


def _eval_dirs(settings: Settings, given: list[str]) -> list[Path]:
    return [Path(d) for d in [*given, *settings.ontology.pack_dirs]]


def _retriever(settings: Settings, graph: Any, registry: Any) -> ArtifactRetriever:
    ontology = settings.ontology
    return ArtifactRetriever(
        graph,
        registry,
        default_max_depth=settings.query.default_max_depth,
        seed_limit=ontology.retrieval_seed_limit,
        neighbor_limit=ontology.retrieval_neighbor_limit,
        provenance_source=settings.storage.event_log,
        seed_min_ratio=ontology.retrieval_seed_min_ratio,
        max_terms=ontology.retrieval_max_terms,
        max_graph_calls=ontology.retrieval_max_graph_calls,
        scan_limit=ontology.retrieval_scan_limit,
    )


async def run_status(settings: Settings) -> int:
    projector = configured_projector(settings.ontology)
    stores = await open_stores(settings)
    try:
        state = await read_state(stores.graph)
        plan = await plan_change(stores.graph, projector.registry)
        _print(
            {
                "loaded": projector.registry.summary(),
                "graph": None
                if state is None
                else {
                    "version": state.version,
                    "recorded_at": state.recorded_at,
                    "applied": state.properties.get("applied"),
                    "packs": state.properties.get("packs"),
                },
                "change": plan.as_dict(),
            }
        )
        return 0
    finally:
        await stores.close()


async def run_evaluate(settings: Settings, eval_dirs: list[str]) -> int:
    projector = configured_projector(settings.ontology)
    stores = await open_stores(settings)
    try:
        registry = projector.registry
        reports = await run_gate(
            registry,
            _retriever(settings, stores.graph, registry),
            _eval_dirs(settings, eval_dirs),
            max_nodes=settings.query.default_max_nodes,
        )
        _print([report.as_dict() for report in reports])
        return 0 if all(report.passed for report in reports) else 1
    finally:
        await stores.close()


async def run_rebuild(
    settings: Settings,
    target: Settings,
    eval_dirs: list[str],
    *,
    skip_gate: bool,
    force: bool,
) -> int:
    projector = configured_projector(target.ontology)
    source = await open_stores(settings)
    destination = await open_stores(target)
    try:
        try:
            report = await rebuild(
                source.event_log,
                destination.graph,
                projector,
                target,
                eval_dirs=_eval_dirs(target, eval_dirs),
                skip_gate=skip_gate,
                force=force,
            )
        except RebuildRefusedError as exc:
            print(f"refused: {exc}", file=sys.stderr)  # noqa: T201 - CLI output
            return 2
        _print(report.as_dict())
        return 0 if report.passed else 1
    finally:
        await source.close()
        await destination.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Engram ontology packs")
    parser.add_argument("command", choices=("status", "evaluate", "rebuild"))
    parser.add_argument("--eval-dir", action="append", default=[], help="evaluation set dir")
    parser.add_argument("--target", action="append", default=[], help="rebuild: CG_KEY=VALUE")
    parser.add_argument("--skip-gate", action="store_true", help="rebuild: record without eval")
    parser.add_argument("--force", action="store_true", help="rebuild: over another version")
    args: Any = parser.parse_args(argv)
    settings = Settings()
    if args.command == "status":
        return asyncio.run(run_status(settings))
    if args.command == "evaluate":
        return asyncio.run(run_evaluate(settings, args.eval_dir))
    if not args.target:
        parser.error("rebuild needs at least one --target CG_KEY=VALUE naming the new graph")
    return asyncio.run(
        run_rebuild(
            settings,
            target_settings(args.target),
            args.eval_dir,
            skip_gate=args.skip_gate,
            force=args.force,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
