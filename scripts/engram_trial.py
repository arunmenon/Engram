"""Real-instance Spanner trial for Engram (maturity review F7, test plan rows 1-4).

Runs a bounded set of measurements against ONE Spanner database and prints
a JSON report. It is meant for the trial instance only:

- it refuses any instance other than ``engram-experiment`` (``--instance``
  exists only to say so explicitly) unless ``--emulator`` is given;
- it never creates or drops an instance or a database, and never changes
  the schema. The database must already hold Engram's schema; the
  start-up check (``schema_differences``) is phase 0;
- it stops starting new phases at ``--minutes`` (at most 60);
- it deletes nothing: the rows it writes stay in the trial database
  (tagged ``trial-``) until the database is dropped by its owner.

Credentials and target come from the environment, in the names the
trial's token script prints:

    GOOGLE_CLOUD_PROJECT, SPANNER_INSTANCE_ID, SPANNER_DATABASE_ID,
    GOOGLE_OAUTH_ACCESS_TOKEN   (or Application Default Credentials)

Phases:

1. schema    the database matches the schema the code expects
2. ledger    concurrent producers and two consumer groups: every event
             delivered to every group, per-session order kept, latencies
3. import    large appends (10 KiB payloads) through the commit budget,
             with Spanner's commit statistics against our estimates
4. graph     node and edge writes at flush size, a label scan
             (find_nodes_matching), GQL lineage and vector search timings

Usage (``pip install -e ".[spanner]"`` first; ``.claude/settings.json``
allows exactly ``python scripts/engram_trial.py ...``):

    python scripts/engram_trial.py --minutes 50 > trial.json
    python scripts/engram_trial.py --emulator 127.0.0.1:9010 --database <db>   # dry run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import random
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

TRIAL_INSTANCE = "engram-experiment"
MAX_MINUTES = 60


class Clock:
    def __init__(self, minutes: float) -> None:
        self.deadline = time.monotonic() + minutes * 60

    def left_s(self) -> float:
        return self.deadline - time.monotonic()


class Latencies:
    def __init__(self) -> None:
        self.samples: dict[str, list[float]] = {}

    def add(self, name: str, started: float) -> None:
        self.samples.setdefault(name, []).append((time.monotonic() - started) * 1000)

    def report(self) -> dict[str, Any]:
        out = {}
        for name, values in sorted(self.samples.items()):
            ordered = sorted(values)

            def pct(p: float, ordered: list[float] = ordered) -> float:
                return round(ordered[min(len(ordered) - 1, int(p * len(ordered)))], 1)

            out[name] = {
                "n": len(ordered),
                "p50_ms": pct(0.50),
                "p95_ms": pct(0.95),
                "p99_ms": pct(0.99),
                "max_ms": round(ordered[-1], 1),
            }
        return out


class CommitStats(logging.Handler):
    """Collects the CommitStats the client logs when ``log_commit_stats`` is on."""

    def __init__(self) -> None:
        super().__init__(logging.INFO)
        self.mutation_counts: list[int] = []

    def emit(self, record: logging.LogRecord) -> None:
        stats = getattr(record, "commit_stats", None)
        if stats is not None:
            self.mutation_counts.append(int(stats.mutation_count))


def open_trial_database(args: argparse.Namespace) -> Any:
    from google.cloud import spanner

    if args.emulator:
        os.environ["SPANNER_EMULATOR_HOST"] = args.emulator
        client = spanner.Client(project=args.project or "engram-local")
    else:
        os.environ.pop("SPANNER_EMULATOR_HOST", None)
        if args.instance != TRIAL_INSTANCE:
            sys.exit(f"refusing instance {args.instance!r}: this script runs on {TRIAL_INSTANCE}")
        token = os.environ.get("GOOGLE_OAUTH_ACCESS_TOKEN")
        credentials = None
        if token:
            from google.oauth2.credentials import Credentials

            credentials = Credentials(token=token)
        client = spanner.Client(project=args.project, credentials=credentials)
    database = client.instance(args.instance).database(args.database)
    if not database.exists():
        sys.exit(f"database {args.database} does not exist; this script never creates one")
    return database


def make_event(session_id: str, payload_bytes: int = 0) -> tuple[Any, dict[str, Any] | None]:
    from context_graph.domain.models import Event

    event = Event(
        event_id=uuid.uuid4(),
        event_type="tool.execute",
        occurred_at=datetime.now(UTC),
        session_id=session_id,
        agent_id="trial-agent",
        trace_id=f"trial-{session_id}",
        payload_ref="payload:trial",
        tool_name="trial",
    )
    payload = {"blob": "x" * payload_bytes} if payload_bytes else None
    return event, payload


async def phase_schema(database: Any) -> dict[str, Any]:
    from context_graph.adapters.spanner.schema import schema_differences

    started = time.monotonic()
    differences = await asyncio.to_thread(schema_differences, database, 384)
    return {
        "differences": differences,
        "ok": not differences,
        "ms": round((time.monotonic() - started) * 1000),
    }


async def phase_ledger(database: Any, args: argparse.Namespace, lat: Latencies) -> dict[str, Any]:
    """Producers append while two groups of two consumers read; check delivery and order."""
    from context_graph.adapters.spanner.log import SpannerEventLog
    from context_graph.adapters.spanner.subscription import SpannerSubscription

    log = SpannerEventLog(database, shards=16)
    run = uuid.uuid4().hex[:8]
    sessions = [f"trial-{run}-s{i}" for i in range(args.sessions)]
    written: dict[str, tuple[str, str]] = {}  # event_id -> (session, position)
    errors: list[str] = []
    stop_at = time.monotonic() + args.ledger_seconds

    async def producer(number: int) -> None:
        rng = random.Random(number)
        while time.monotonic() < stop_at and len(written) < args.events:
            batch = [make_event(rng.choice(sessions)) for _ in range(args.batch)]
            started = time.monotonic()
            try:
                outcomes = await log.append_batch_outcomes(
                    [e for e, _p in batch], [p for _e, p in batch]
                )
            except Exception as exc:  # noqa: BLE001 - counted and reported
                errors.append(f"append: {type(exc).__name__}: {exc}"[:200])
                continue
            lat.add("append_batch", started)
            for (event, _p), outcome in zip(batch, outcomes, strict=True):
                if outcome.status == "created":
                    written[str(event.event_id)] = (event.session_id, outcome.position or "")
                else:
                    errors.append(f"append outcome {outcome.status}: {outcome.error}")

    groups = [f"trial-{run}-g{i}" for i in range(2)]
    delivered: dict[str, list[tuple[str, str]]] = {g: [] for g in groups}  # (event_id, position)
    producers_done = asyncio.Event()

    async def consumer(group: str, name: str) -> None:
        subscription = SpannerSubscription(database, group, name, shards=16, poll_interval_ms=50)
        await subscription.ensure_group()
        idle_since: float | None = None
        while True:
            started = time.monotonic()
            try:
                batch = await subscription.read_new(args.read_count, 200)
            except Exception as exc:  # noqa: BLE001 - counted and reported
                errors.append(f"read_new: {type(exc).__name__}: {exc}"[:200])
                continue
            lat.add("read_new" if batch else "read_new_empty", started)
            if batch:
                idle_since = None
                delivered[group].extend((d.fields["event_id"], d.position) for d in batch)
                started = time.monotonic()
                await subscription.ack(*[d.position for d in batch])
                lat.add("ack", started)
                continue
            if producers_done.is_set():
                idle_since = idle_since or time.monotonic()
                if time.monotonic() - idle_since > 5:
                    return

    started = time.monotonic()
    consumers = [
        asyncio.create_task(consumer(group, f"c{i}")) for group in groups for i in range(2)
    ]
    await asyncio.gather(*[producer(i) for i in range(args.producers)])
    produced_s = time.monotonic() - started
    producers_done.set()
    await asyncio.gather(*consumers)

    result: dict[str, Any] = {
        "events_written": len(written),
        "produce_seconds": round(produced_s, 1),
        "events_per_second": round(len(written) / produced_s, 1) if produced_s else None,
        "errors": errors[:20],
        "error_count": len(errors),
        "groups": {},
    }
    for group, items in delivered.items():
        ids = [event_id for event_id, _pos in items]
        ours = [i for i in ids if i in written]
        missing = set(written) - set(ours)
        duplicates = len(ours) - len(set(ours))
        # Per-session order: within a session, delivery order follows position order
        out_of_order = 0
        last: dict[str, str] = {}
        for event_id, position in items:
            if event_id not in written:
                continue
            session = written[event_id][0]
            if session in last and position < last[session]:
                out_of_order += 1
            last[session] = position
        result["groups"][group] = {
            "delivered": len(ours),
            "missing": len(missing),
            "duplicates": duplicates,
            "session_order_violations": out_of_order,
        }
    return result


async def phase_import(database: Any, args: argparse.Namespace, lat: Latencies) -> dict[str, Any]:
    """Large appends through the commit budget; real mutation counts against estimates."""
    from context_graph.adapters.spanner.commits import EVENT_ROW_MUTATIONS
    from context_graph.adapters.spanner.log import SpannerEventLog

    stats = CommitStats()
    database.log_commit_stats = True
    database._logger = logging.getLogger("engram-trial-commit-stats")
    database._logger.setLevel(logging.INFO)
    database._logger.propagate = False
    database._logger.addHandler(stats)
    try:
        log = SpannerEventLog(database, shards=16)
        session = f"trial-import-{uuid.uuid4().hex[:8]}"
        rows = []
        for size in (1_024, 10_240):
            batch = [make_event(session, size) for _ in range(args.import_events)]
            before = len(stats.mutation_counts)
            started = time.monotonic()
            outcomes = await log.append_batch_outcomes(
                [e for e, _p in batch], [p for _e, p in batch]
            )
            lat.add(f"import_{args.import_events}x{size // 1024}KiB", started)
            counts = stats.mutation_counts[before:]
            rows.append(
                {
                    "payload_bytes": size,
                    "events": len(batch),
                    "created": sum(o.status == "created" for o in outcomes),
                    "transactions": len(counts),
                    "spanner_mutations": counts,
                    "estimated_mutations_per_event": EVENT_ROW_MUTATIONS,
                    "spanner_mutations_per_event": round(sum(counts) / len(batch), 1)
                    if counts
                    else None,
                    "seconds": round(time.monotonic() - started, 2),
                }
            )
        return {"runs": rows}
    finally:
        database.log_commit_stats = False


async def phase_graph(database: Any, args: argparse.Namespace, lat: Latencies) -> dict[str, Any]:
    """Graph writes at flush size, then the reads the review flagged (S3) at this size."""
    from context_graph.adapters.spanner.graph import SpannerGraphStore

    graph = SpannerGraphStore(database)
    run = uuid.uuid4().hex[:8]
    rng = random.Random(7)
    nodes = [
        (("Event", f"trial-{run}-e{i}"), {"session_id": f"trial-{run}"}) for i in range(args.nodes)
    ]
    entities = [
        (("Entity", f"trial-{run}-n{i}"), {"name": f"n{i}", "kind": rng.choice("abc")})
        for i in range(args.nodes // 4)
    ]
    for start in range(0, len(nodes), args.flush):
        started = time.monotonic()
        await graph._upsert_nodes(nodes[start : start + args.flush])
        lat.add("upsert_nodes_flush", started)
    for start in range(0, len(entities), args.flush):
        await graph._upsert_nodes(entities[start : start + args.flush])
    edges = [
        ((nodes[i][0], "CAUSED_BY", nodes[i - 1][0]), {"w": 1.0}) for i in range(1, len(nodes))
    ]
    for start in range(0, len(edges), args.flush):
        started = time.monotonic()
        await graph._upsert_edges(edges[start : start + args.flush])
        lat.add("upsert_edges_flush", started)

    timings: dict[str, Any] = {}
    started = time.monotonic()
    matched = await graph.find_nodes_matching("Entity", [{"kind": "a"}, {"kind": "b"}], 10)
    timings["find_nodes_matching_label_scan_ms"] = round((time.monotonic() - started) * 1000)
    timings["label_rows"] = len(entities)
    timings["matched"] = [len(m) for m in matched]
    started = time.monotonic()
    chains = await graph.reads.lineage_chains(nodes[-1][0][1], 10, 100)
    timings["lineage_10_hops_ms"] = round((time.monotonic() - started) * 1000)
    timings["lineage_chains"] = len(chains)

    dims = 384
    vectors = [[rng.uniform(-1, 1) for _ in range(dims)] for _ in range(50)]
    await graph._upsert_nodes(
        [
            (("Entity", f"trial-{run}-v{i}"), {"name": f"v{i}", "embedding": vector})
            for i, vector in enumerate(vectors)
        ]
    )
    started = time.monotonic()
    similar = await graph.search_similar_entities(vectors[0], top_k=5, threshold=0.0)
    timings["vector_search_ms"] = round((time.monotonic() - started) * 1000)
    timings["vector_top_hit_is_self"] = (
        bool(similar) and similar[0].get("entity_id") == f"trial-{run}-v0"
    )
    return {"nodes": len(nodes) + len(entities) + len(vectors), "edges": len(edges), **timings}


async def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--project", default=os.environ.get("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--instance", default=os.environ.get("SPANNER_INSTANCE_ID", TRIAL_INSTANCE))
    parser.add_argument("--database", default=os.environ.get("SPANNER_DATABASE_ID", "engram"))
    parser.add_argument("--emulator", help="host:port of a Spanner emulator (dry run)")
    parser.add_argument("--minutes", type=float, default=50)
    parser.add_argument("--phases", default="schema,ledger,import,graph")
    parser.add_argument("--producers", type=int, default=8)
    parser.add_argument("--sessions", type=int, default=40)
    parser.add_argument("--batch", type=int, default=10)
    parser.add_argument("--events", type=int, default=3_000)
    parser.add_argument("--ledger-seconds", type=float, default=180)
    parser.add_argument("--read-count", type=int, default=10)
    parser.add_argument("--import-events", type=int, default=500)
    parser.add_argument("--nodes", type=int, default=2_000)
    parser.add_argument("--flush", type=int, default=200)
    args = parser.parse_args()
    if args.minutes > MAX_MINUTES:
        sys.exit(f"--minutes is capped at {MAX_MINUTES}")
    if not args.emulator and not args.project:
        sys.exit("set GOOGLE_CLOUD_PROJECT or --project")

    clock = Clock(args.minutes)
    database = await asyncio.to_thread(open_trial_database, args)
    lat = Latencies()
    report: dict[str, Any] = {
        "started_at": datetime.now(UTC).isoformat(),
        "target": {"instance": args.instance, "database": args.database, "emulator": args.emulator},
        "phases": {},
    }
    runners = {
        "schema": lambda: phase_schema(database),
        "ledger": lambda: phase_ledger(database, args, lat),
        "import": lambda: phase_import(database, args, lat),
        "graph": lambda: phase_graph(database, args, lat),
    }
    for name in args.phases.split(","):
        if clock.left_s() < 120:
            report["phases"][name] = {"skipped": "time limit"}
            continue
        print(f"[trial] {name} ({clock.left_s() / 60:.0f} min left)", file=sys.stderr)
        started = time.monotonic()
        try:
            report["phases"][name] = await asyncio.wait_for(runners[name](), clock.left_s() - 60)
        except Exception as exc:  # noqa: BLE001 - the report records it
            report["phases"][name] = {"failed": f"{type(exc).__name__}: {exc}"[:500]}
        report["phases"][name]["phase_seconds"] = round(time.monotonic() - started, 1)
        if name == "schema" and not report["phases"][name].get("ok"):
            break
    report["latencies"] = lat.report()
    report["finished_at"] = datetime.now(UTC).isoformat()
    report["elapsed_minutes"] = round(
        (
            datetime.fromisoformat(report["finished_at"])
            - datetime.fromisoformat(report["started_at"])
        )
        / timedelta(minutes=1),
        1,
    )
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
