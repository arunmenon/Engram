"""Scale modeling CLI tool for Engram context graph.

Projects graph growth, memory requirements, and infrastructure ceiling timelines
for any deployment size. Uses the growth model constants from ADR-0018.

Usage:
    python -m context_graph.tools.scale_model --tenants 50 --sessions-per-day 500
    python -m context_graph.tools.scale_model --tenants 1 --format json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass, field

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class DeploymentProfile:
    """Input parameters for scale projection."""

    tenants: int = 1
    sessions_per_tenant_per_day: int = 10
    avg_events_per_session: int = 25
    avg_entities_per_session: int = 3
    avg_edges_per_event: float = 2.5
    retention_days: int = 90
    compaction_ratio: float = 0.6  # fraction of events compacted after summarization


@dataclass
class TimelineEntry:
    """Monthly snapshot of projected graph size and resource requirements."""

    month: int
    total_events: int
    total_nodes: int  # after compaction
    total_edges: int
    redis_memory_gb: float
    neo4j_heap_gb: float
    neo4j_pagecache_gb: float
    neo4j_disk_gb: float
    phase: str  # "single" | "sharded" | "tiered" | "distributed"


@dataclass
class CeilingEvent:
    """Records when a scaling ceiling is breached."""

    month: int
    ceiling: str  # e.g., "neo4j_single_instance"
    metric: str  # e.g., "nodes=12M"
    action: str  # e.g., "Migrate to Phase A: tenant-sharded Neo4j"


@dataclass
class ScaleProjection:
    """Complete output of a scale projection run."""

    profile: DeploymentProfile
    timeline: list[TimelineEntry] = field(default_factory=list)
    ceilings: list[CeilingEvent] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Constants (from ADR-0018)
# ---------------------------------------------------------------------------

BYTES_PER_EVENT = 1536  # 1.5 KB (JSON doc + stream entry + index overhead)
BYTES_PER_NODE_PAGECACHE = 300  # bytes per node for Neo4j pagecache sizing
BYTES_PER_EDGE_PAGECACHE = 150  # bytes per edge for Neo4j pagecache sizing
NEO4J_DISK_OVERHEAD = 1.3  # transaction logs + indexes multiplier
NEO4J_HEAP_NODES_PER_GB = 500_000  # nodes per GB of heap
NEO4J_HEAP_MIN_GB = 0.5  # minimum 512 MB heap

BYTES_IN_GB = 1024 * 1024 * 1024

# Ceiling thresholds
CEILING_PAGECACHE_STARVED_NODES = 500_000  # 500K nodes (128MB pagecache insufficient)
CEILING_SINGLE_INSTANCE_NODES = 10_000_000  # 10M nodes
CEILING_SHARDED_LIMIT_NODES = 500_000_000  # 500M nodes per shard
CEILING_REDIS_16GB = 16.0
CEILING_REDIS_64GB = 64.0
CEILING_REDIS_256GB = 256.0

# Phase thresholds (by node count)
PHASE_SINGLE_MAX = 10_000_000
PHASE_SHARDED_MAX = 500_000_000
PHASE_TIERED_MAX = 5_000_000_000


# ---------------------------------------------------------------------------
# Projection logic
# ---------------------------------------------------------------------------


def compute_monthly_events(profile: DeploymentProfile) -> int:
    """Total raw events generated per month."""
    return (
        profile.tenants * profile.sessions_per_tenant_per_day * 30 * profile.avg_events_per_session
    )


def compute_monthly_nodes(profile: DeploymentProfile, monthly_events: int) -> int:
    """Monthly node growth after compaction.

    Each event produces:
    - 1 event node
    - avg_entities_per_session / avg_events_per_session entity nodes (pro-rated)
    - 1 / avg_events_per_session summary nodes (roughly 1 summary per session)

    Then compaction removes compaction_ratio fraction of nodes.
    """
    events_per_session = max(profile.avg_events_per_session, 1)
    entity_ratio = profile.avg_entities_per_session / events_per_session
    summary_ratio = 1.0 / events_per_session

    raw_nodes = monthly_events * (1.0 + entity_ratio + summary_ratio)
    compacted_nodes = raw_nodes * (1.0 - profile.compaction_ratio)
    return max(0, math.ceil(compacted_nodes))


def compute_monthly_edges(profile: DeploymentProfile, monthly_events: int) -> int:
    """Monthly edge growth after compaction.

    Edges compact less aggressively than nodes (80% of compaction ratio).
    """
    raw_edges = monthly_events * profile.avg_edges_per_event
    edge_compaction = profile.compaction_ratio * 0.8
    compacted_edges = raw_edges * (1.0 - edge_compaction)
    return max(0, math.ceil(compacted_edges))


def compute_redis_memory_gb(total_events: int, retention_days: int, months: int) -> float:
    """Redis memory for events within the retention window.

    Only events within the retention window contribute to memory usage.
    """
    # Days elapsed so far
    days_elapsed = months * 30
    # Events within the retention window (capped by total events)
    if days_elapsed <= retention_days:
        events_in_window = total_events
    else:
        # Approximate: fraction of total events in the retention window
        events_in_window = int(total_events * (retention_days / days_elapsed))

    return events_in_window * BYTES_PER_EVENT / BYTES_IN_GB


def compute_neo4j_heap_gb(total_nodes: int) -> float:
    """Neo4j heap requirement based on node count."""
    return max(NEO4J_HEAP_MIN_GB, total_nodes / NEO4J_HEAP_NODES_PER_GB)


def compute_neo4j_pagecache_gb(total_nodes: int, total_edges: int) -> float:
    """Neo4j pagecache for full cache hit rate."""
    total_bytes = (total_nodes * BYTES_PER_NODE_PAGECACHE) + (
        total_edges * BYTES_PER_EDGE_PAGECACHE
    )
    return total_bytes / BYTES_IN_GB


def compute_neo4j_disk_gb(pagecache_gb: float) -> float:
    """Neo4j disk includes pagecache data plus overhead."""
    return pagecache_gb * NEO4J_DISK_OVERHEAD


def determine_phase(total_nodes: int) -> str:
    """Determine infrastructure phase from node count."""
    if total_nodes < PHASE_SINGLE_MAX:
        return "single"
    if total_nodes < PHASE_SHARDED_MAX:
        return "sharded"
    if total_nodes < PHASE_TIERED_MAX:
        return "tiered"
    return "distributed"


def detect_ceilings(
    month: int,
    total_nodes: int,
    total_edges: int,
    redis_memory_gb: float,
    seen_ceilings: set[str],
) -> list[CeilingEvent]:
    """Check for newly breached ceilings at a given month."""
    events: list[CeilingEvent] = []

    checks = [
        (
            "neo4j_pagecache_starved",
            total_nodes > CEILING_PAGECACHE_STARVED_NODES,
            f"nodes={_format_count(total_nodes)}",
            "Increase NEO4J_server_memory_pagecache_size to 512MB+",
        ),
        (
            "neo4j_single_instance",
            total_nodes > CEILING_SINGLE_INSTANCE_NODES,
            f"nodes={_format_count(total_nodes)}",
            "Migrate to Phase A: tenant-sharded Neo4j",
        ),
        (
            "neo4j_sharded_limit",
            total_nodes > CEILING_SHARDED_LIMIT_NODES,
            f"nodes={_format_count(total_nodes)}",
            "Migrate to Phase B: time-partitioned graph with hot/cold tiers",
        ),
        (
            "redis_memory_16gb",
            redis_memory_gb > CEILING_REDIS_16GB,
            f"redis_memory={redis_memory_gb:.1f}GB",
            "Set maxmemory, enable Auto Tiering, or reduce retention",
        ),
        (
            "redis_memory_64gb",
            redis_memory_gb > CEILING_REDIS_64GB,
            f"redis_memory={redis_memory_gb:.1f}GB",
            "Add Redis Cluster or reduce retention window significantly",
        ),
        (
            "redis_memory_256gb",
            redis_memory_gb > CEILING_REDIS_256GB,
            f"redis_memory={redis_memory_gb:.1f}GB",
            "Consider migrating event store to Kafka (Phase C)",
        ),
    ]

    for ceiling_name, triggered, metric, action in checks:
        if triggered and ceiling_name not in seen_ceilings:
            seen_ceilings.add(ceiling_name)
            events.append(
                CeilingEvent(
                    month=month,
                    ceiling=ceiling_name,
                    metric=metric,
                    action=action,
                )
            )

    return events


def project(profile: DeploymentProfile, months: int = 36) -> ScaleProjection:
    """Run a full scale projection for the given deployment profile.

    Returns a ScaleProjection with monthly timeline entries, ceiling events,
    and human-readable recommendations.
    """
    projection = ScaleProjection(profile=profile)
    seen_ceilings: set[str] = set()

    monthly_events = compute_monthly_events(profile)
    monthly_nodes = compute_monthly_nodes(profile, monthly_events)
    monthly_edges = compute_monthly_edges(profile, monthly_events)

    cumulative_events = 0
    cumulative_nodes = 0
    cumulative_edges = 0

    for month in range(1, months + 1):
        cumulative_events += monthly_events
        cumulative_nodes += monthly_nodes
        cumulative_edges += monthly_edges

        redis_mem = compute_redis_memory_gb(cumulative_events, profile.retention_days, month)
        neo4j_heap = compute_neo4j_heap_gb(cumulative_nodes)
        neo4j_pagecache = compute_neo4j_pagecache_gb(cumulative_nodes, cumulative_edges)
        neo4j_disk = compute_neo4j_disk_gb(neo4j_pagecache)
        phase = determine_phase(cumulative_nodes)

        entry = TimelineEntry(
            month=month,
            total_events=cumulative_events,
            total_nodes=cumulative_nodes,
            total_edges=cumulative_edges,
            redis_memory_gb=round(redis_mem, 3),
            neo4j_heap_gb=round(neo4j_heap, 3),
            neo4j_pagecache_gb=round(neo4j_pagecache, 3),
            neo4j_disk_gb=round(neo4j_disk, 3),
            phase=phase,
        )
        projection.timeline.append(entry)

        new_ceilings = detect_ceilings(
            month, cumulative_nodes, cumulative_edges, redis_mem, seen_ceilings
        )
        projection.ceilings.extend(new_ceilings)

    # Generate recommendations based on final state
    projection.recommendations = _generate_recommendations(projection)

    return projection


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


def _generate_recommendations(projection: ScaleProjection) -> list[str]:
    """Generate human-readable recommendations from the projection."""
    recommendations: list[str] = []

    if not projection.timeline:
        return recommendations

    final = projection.timeline[-1]
    profile = projection.profile

    # Phase-based recommendations
    if final.phase == "single":
        recommendations.append(
            "Current deployment stays within single-instance capacity for the projection period."
        )
    elif final.phase == "sharded":
        recommendations.append(
            "Deploy tenant-sharded Neo4j (Phase A) before the node count exceeds 10M."
        )
    elif final.phase == "tiered":
        recommendations.append("Deploy time-partitioned graph (Phase B) with hot/cold Neo4j tiers.")
    elif final.phase == "distributed":
        recommendations.append(
            "Evaluate distributed graph backends (Phase D): "
            "NebulaGraph, Amazon Neptune, or JanusGraph."
        )

    # Redis recommendations
    if final.redis_memory_gb > CEILING_REDIS_256GB:
        recommendations.append(
            f"Redis memory projection ({final.redis_memory_gb:.1f} GB) exceeds 256 GB. "
            "Migrate event store to Kafka (Phase C)."
        )
    elif final.redis_memory_gb > CEILING_REDIS_64GB:
        recommendations.append(
            f"Redis memory projection ({final.redis_memory_gb:.1f} GB) exceeds 64 GB. "
            "Plan Redis Cluster or reduce retention to "
            f"{profile.retention_days // 2} days."
        )
    elif final.redis_memory_gb > CEILING_REDIS_16GB:
        recommendations.append(
            f"Redis memory projection ({final.redis_memory_gb:.1f} GB) exceeds 16 GB. "
            "Consider increasing maxmemory or reducing retention."
        )

    # Compaction recommendation
    if profile.compaction_ratio < 0.3:
        recommendations.append(
            f"Compaction ratio is low ({profile.compaction_ratio:.0%}). "
            "Increasing compaction can extend single-instance runway by 2-5x."
        )

    # Neo4j pagecache
    if final.neo4j_pagecache_gb > 4.0:
        recommendations.append(
            f"Neo4j pagecache requirement reaches {final.neo4j_pagecache_gb:.1f} GB. "
            "Ensure the server has sufficient RAM (recommend 2x pagecache for OS + heap)."
        )

    return recommendations


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _format_count(n: int) -> str:
    """Format large numbers with K/M/B suffixes."""
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def _format_memory(gb: float) -> str:
    """Format memory in human-readable units."""
    if gb < 0.001:
        return f"{gb * 1024 * 1024:.0f}KB"
    if gb < 1.0:
        return f"{gb * 1024:.0f}MB"
    return f"{gb:.1f}GB"


def format_text(projection: ScaleProjection, months: int) -> str:
    """Format projection as a human-readable text table."""
    profile = projection.profile
    sessions_per_day = profile.tenants * profile.sessions_per_tenant_per_day

    lines: list[str] = []
    lines.append("")
    lines.append(
        f"Scale Projection: {profile.tenants} tenant(s), "
        f"{sessions_per_day} sessions/day, "
        f"{profile.retention_days}-day retention"
    )
    lines.append("")

    # Header
    header = (
        f"{'Month':>5} | {'Nodes':>10} | {'Edges':>10} | "
        f"{'Redis':>8} | {'Neo4j Heap':>10} | {'Neo4j Cache':>11} | {'Phase':>12}"
    )
    separator = "-" * len(header)
    lines.append(header)
    lines.append(separator)

    # Determine which months to show (show key months, not all 36)
    show_months = _select_display_months(months)

    ceiling_months = {c.month for c in projection.ceilings}

    for entry in projection.timeline:
        if entry.month not in show_months:
            continue

        warning = " !!" if entry.month in ceiling_months else ""
        line = (
            f"{entry.month:>5} | "
            f"{_format_count(entry.total_nodes):>10} | "
            f"{_format_count(entry.total_edges):>10} | "
            f"{_format_memory(entry.redis_memory_gb):>8} | "
            f"{_format_memory(entry.neo4j_heap_gb):>10} | "
            f"{_format_memory(entry.neo4j_pagecache_gb):>11} | "
            f"{entry.phase:>12}{warning}"
        )
        lines.append(line)

    # Ceilings section
    if projection.ceilings:
        lines.append("")
        lines.append("Ceilings:")
        for ceiling in projection.ceilings:
            lines.append(f"  Month {ceiling.month:>2}: {ceiling.ceiling} ({ceiling.metric})")
            lines.append(f"            -> {ceiling.action}")

    # Recommendations
    if projection.recommendations:
        lines.append("")
        lines.append("Recommendations:")
        for rec in projection.recommendations:
            lines.append(f"  - {rec}")

    lines.append("")
    return "\n".join(lines)


def _select_display_months(total_months: int) -> set[int]:
    """Select which months to display in the text table.

    Shows months 1, 3, 6, 12, 18, 24, 30, 36 (or whatever fits within total).
    """
    candidates = [1, 3, 6, 12, 18, 24, 30, 36]
    return {m for m in candidates if m <= total_months}


def format_json(projection: ScaleProjection) -> str:
    """Format projection as JSON."""
    return json.dumps(asdict(projection), indent=2)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="scale_model",
        description=(
            "Project graph growth, memory requirements, and infrastructure ceiling "
            "timelines for the Engram context graph."
        ),
    )
    parser.add_argument(
        "--tenants",
        type=int,
        default=1,
        help="Number of tenants (default: 1)",
    )
    parser.add_argument(
        "--sessions-per-day",
        type=int,
        default=10,
        dest="sessions_per_day",
        help="Sessions per tenant per day (default: 10)",
    )
    parser.add_argument(
        "--events-per-session",
        type=int,
        default=25,
        dest="events_per_session",
        help="Average events per session (default: 25)",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=90,
        dest="retention_days",
        help="Event retention window in days (default: 90)",
    )
    parser.add_argument(
        "--compaction-ratio",
        type=float,
        default=0.6,
        dest="compaction_ratio",
        help="Fraction of events compacted after summarization (default: 0.6)",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=36,
        help="Number of months to project (default: 36)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        dest="output_format",
        help="Output format (default: text)",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    profile = DeploymentProfile(
        tenants=args.tenants,
        sessions_per_tenant_per_day=args.sessions_per_day,
        avg_events_per_session=args.events_per_session,
        retention_days=args.retention_days,
        compaction_ratio=args.compaction_ratio,
    )

    projection = project(profile, months=args.months)

    if args.output_format == "json":
        output = format_json(projection)
    else:
        output = format_text(projection, args.months)

    sys.stdout.write(output)
    if args.output_format == "text":
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
