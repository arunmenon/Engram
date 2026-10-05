"""Ontology operations (ADR-0018 phase 3).

Usage:
    python -m context_graph.ontology status
        The loaded packs, the version the configured graph records, and how
        the change between them would be applied (JSON).

    python -m context_graph.ontology evaluate [--eval-dir DIR] [--record]
        Run the evaluation sets of the active packs with intents on the
        configured graph. Exits 1 when a set fails or is missing. With
        --record, the graph's state records the result (clearing
        ``eval_pending`` when every set passes; decision 10).

    python -m context_graph.ontology rebuild --target KEY=VALUE [...] [--eval-dir DIR]
                                             [--skip-gate] [--force]
        Blue/green: project the configured ledger into the graph that the
        settings with the ``--target`` overrides select (for example
        ``CG_NEO4J_URI=bolt://green:7687`` or ``CG_SPANNER_DATABASE=engram_v2``),
        run the evaluation gate on it and record the result. Exits 0 when
        the gate passes, 1 when it fails, and 2 when the rebuild is refused
        (the target is the live graph, holds another version or other data,
        an override names no setting, or an evaluation set is missing).

        Switch by deploying with the same overrides plus new consumer group
        names (``CG_CONSUMER_GROUP_*``): new groups read the ledger from the
        start, so the projection group replays onto the rebuilt graph
        (idempotently) and then follows live events with no gap, and the
        enrichment, extraction and consolidation groups build their part of
        the new graph.

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
from pydantic_settings import BaseSettings

from context_graph.adapters.registry import open_stores
from context_graph.ontology.evaluation import run_gate
from context_graph.ontology.rebuild import RebuildRefusedError, rebuild
from context_graph.ontology.runtime import configured_projector
from context_graph.ontology.versioning import plan_for_state, read_state, record_state
from context_graph.retrieval.artifacts import ArtifactRetriever
from context_graph.settings import Settings

if TYPE_CHECKING:
    from collections.abc import Iterator

    from context_graph.domain.ontology import OntologyRegistry
    from context_graph.ontology.evaluation import EvalReport
    from context_graph.ports.graph_backend import GraphBackend


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


def known_settings_keys() -> set[str]:
    """Every ``CG_*`` environment name a setting reads."""
    keys = set()
    for name, field in Settings.model_fields.items():
        model = field.annotation
        if isinstance(model, type) and issubclass(model, BaseSettings):
            prefix = str(model.model_config.get("env_prefix", ""))
            keys |= {f"{prefix}{inner}".upper() for inner in model.model_fields}
        else:
            keys.add(f"CG_{name}".upper())
    return keys


def target_settings(overrides: list[str]) -> Settings:
    """The configured settings with ``KEY=VALUE`` environment overrides applied."""
    pairs: dict[str, str] = {}
    known = known_settings_keys()
    for item in overrides:
        key, sep, value = item.partition("=")
        if not sep or not key.startswith("CG_"):
            msg = f"--target takes CG_KEY=VALUE, got {item!r}"
            raise SystemExit(msg)
        if key.upper() not in known:
            msg = f"--target {key} is not a setting (a misspelling would rebuild the live graph)"
            raise SystemExit(msg)
        pairs[key] = value
    with _environment(pairs):
        return Settings()


def same_graph(source: Settings, target: Settings) -> bool:
    """Whether two configurations select the same graph (a rebuild would overwrite it)."""
    backend = source.storage.graph
    if backend != target.storage.graph or backend == "memory":
        return False
    section = {"neo4j": "neo4j", "spanner": "spanner"}.get(backend)
    if section is None:
        return False
    return bool(getattr(source, section).model_dump() == getattr(target, section).model_dump())


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
        word_scan_limit=ontology.retrieval_word_scan_limit,
    )


async def run_status(settings: Settings) -> int:
    projector = configured_projector(settings.ontology)
    stores = await open_stores(settings)
    try:
        state = await read_state(stores.graph)
        plan = plan_for_state(state, projector.registry)
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
                    "eval_pending": state.properties.get("eval_pending", []),
                    "gate_passed": state.properties.get("gate_passed"),
                },
                "change": plan.as_dict(),
            }
        )
        return 0
    finally:
        await stores.close()


async def evaluate_graph(
    settings: Settings,
    graph: GraphBackend,
    registry: OntologyRegistry,
    eval_dirs: list[Path],
    *,
    record: bool,
) -> list[EvalReport]:
    """Run the active packs' evaluation sets on ``graph``; with ``record``, record the result.

    Recording clears ``eval_pending`` when every set passes (decision 10:
    the packs' weights are trusted from then on); otherwise it lists every
    pack that has a set. Nothing is recorded on a graph that records no
    ontology, or another version.
    """
    reports = await run_gate(
        registry,
        _retriever(settings, graph, registry),
        eval_dirs,
        max_nodes=settings.query.default_max_nodes,
    )
    passed = all(report.passed for report in reports)
    state = await read_state(graph)
    if record and state is not None and state.version == registry.version:
        await record_state(
            graph,
            registry,
            applied=str(state.properties.get("applied", "")),
            extra={
                "eval_pending": [] if passed else sorted(r.pack for r in reports),
                "gate": [f"{r.pack}:{r.mean_f1:.3f}" for r in reports],
            },
        )
    return reports


async def run_evaluate(settings: Settings, eval_dirs: list[str], *, record: bool) -> int:
    projector = configured_projector(settings.ontology)
    stores = await open_stores(settings)
    try:
        reports = await evaluate_graph(
            settings,
            stores.graph,
            projector.registry,
            _eval_dirs(settings, eval_dirs),
            record=record,
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
    if same_graph(settings, target):
        print("refused: --target selects the configured (live) graph", file=sys.stderr)  # noqa: T201
        return 2
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
    parser.add_argument("--record", action="store_true", help="evaluate: record the result")
    args: Any = parser.parse_args(argv)
    settings = Settings()
    if args.command == "status":
        return asyncio.run(run_status(settings))
    if args.command == "evaluate":
        return asyncio.run(run_evaluate(settings, args.eval_dir, record=args.record))
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
