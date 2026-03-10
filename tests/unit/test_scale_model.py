"""Unit tests for the scale modeling CLI tool."""

from __future__ import annotations

import json
import math

import pytest

from context_graph.tools.scale_model import (
    BYTES_IN_GB,
    BYTES_PER_EVENT,
    CEILING_PAGECACHE_STARVED_NODES,
    CEILING_SHARDED_LIMIT_NODES,
    CEILING_SINGLE_INSTANCE_NODES,
    DeploymentProfile,
    compute_monthly_edges,
    compute_monthly_events,
    compute_monthly_nodes,
    compute_neo4j_disk_gb,
    compute_neo4j_heap_gb,
    compute_neo4j_pagecache_gb,
    compute_redis_memory_gb,
    detect_ceilings,
    determine_phase,
    format_json,
    format_text,
    main,
    project,
)

# ---------------------------------------------------------------------------
# test_growth_calculation: known inputs -> expected node/edge counts
# ---------------------------------------------------------------------------


class TestGrowthCalculation:
    """Verify projection math with known inputs."""

    def test_monthly_events_single_tenant(self) -> None:
        profile = DeploymentProfile(
            tenants=1,
            sessions_per_tenant_per_day=10,
            avg_events_per_session=25,
        )
        # 1 * 10 * 30 * 25 = 7,500
        assert compute_monthly_events(profile) == 7_500

    def test_monthly_events_multi_tenant(self) -> None:
        profile = DeploymentProfile(
            tenants=5,
            sessions_per_tenant_per_day=20,
            avg_events_per_session=30,
        )
        # 5 * 20 * 30 * 30 = 90,000
        assert compute_monthly_events(profile) == 90_000

    def test_monthly_nodes_formula(self) -> None:
        """Verify the node formula:
        monthly_events * (1 + entities/events + 1/events) * (1 - compaction_ratio)
        """
        profile = DeploymentProfile(
            tenants=1,
            sessions_per_tenant_per_day=10,
            avg_events_per_session=25,
            avg_entities_per_session=3,
            compaction_ratio=0.6,
        )
        monthly_events = compute_monthly_events(profile)  # 7500
        # entity_ratio = 3/25 = 0.12
        # summary_ratio = 1/25 = 0.04
        # raw = 7500 * (1 + 0.12 + 0.04) ~= 8700
        # compacted ~= 8700 * 0.4 ~= 3480
        nodes = compute_monthly_nodes(profile, monthly_events)
        # Allow for floating-point ceil rounding (3480 or 3481)
        assert 3480 <= nodes <= 3481

    def test_monthly_edges_formula(self) -> None:
        """Verify the edge formula:
        monthly_events * avg_edges_per_event * (1 - compaction_ratio * 0.8)
        """
        profile = DeploymentProfile(
            tenants=1,
            sessions_per_tenant_per_day=10,
            avg_events_per_session=25,
            avg_edges_per_event=2.5,
            compaction_ratio=0.6,
        )
        monthly_events = compute_monthly_events(profile)  # 7500
        # raw_edges = 7500 * 2.5 = 18750
        # edge_compaction = 0.6 * 0.8 = 0.48
        # compacted = 18750 * (1 - 0.48) = 18750 * 0.52 = 9750
        edges = compute_monthly_edges(profile, monthly_events)
        assert edges == math.ceil(18750 * 0.52)

    def test_cumulative_growth_over_months(self) -> None:
        """Verify that cumulative values grow linearly."""
        profile = DeploymentProfile(tenants=1, sessions_per_tenant_per_day=10)
        projection = project(profile, months=12)
        # Monthly events should be constant, so month 12 = 12x month 1
        assert projection.timeline[11].total_events == 12 * projection.timeline[0].total_events
        assert projection.timeline[11].total_nodes == 12 * projection.timeline[0].total_nodes
        assert projection.timeline[11].total_edges == 12 * projection.timeline[0].total_edges

    def test_redis_memory_within_retention(self) -> None:
        """When months elapsed is within retention, all events count."""
        # 100,000 events, retention=90 days, month=2 (60 days < 90)
        mem = compute_redis_memory_gb(100_000, 90, 2)
        expected = 100_000 * BYTES_PER_EVENT / BYTES_IN_GB
        assert abs(mem - expected) < 0.0001

    def test_redis_memory_beyond_retention(self) -> None:
        """When months elapsed exceeds retention, only retention-window events count."""
        # 360,000 events, retention=90 days, month=12 (360 days)
        mem = compute_redis_memory_gb(360_000, 90, 12)
        # events_in_window = 360000 * (90/360) = 90000
        expected = 90_000 * BYTES_PER_EVENT / BYTES_IN_GB
        assert abs(mem - expected) < 0.0001

    def test_neo4j_heap_minimum(self) -> None:
        """Heap should never drop below 0.5 GB."""
        assert compute_neo4j_heap_gb(0) == 0.5
        assert compute_neo4j_heap_gb(100) == 0.5
        assert compute_neo4j_heap_gb(250_000) == 0.5

    def test_neo4j_heap_scales_with_nodes(self) -> None:
        """Above 500K nodes, heap grows linearly."""
        assert compute_neo4j_heap_gb(500_000) == 1.0
        assert compute_neo4j_heap_gb(1_000_000) == 2.0
        assert compute_neo4j_heap_gb(5_000_000) == 10.0

    def test_neo4j_pagecache_formula(self) -> None:
        """Pagecache = (nodes*300 + edges*150) / BYTES_IN_GB."""
        nodes = 1_000_000
        edges = 2_000_000
        expected = (nodes * 300 + edges * 150) / BYTES_IN_GB
        result = compute_neo4j_pagecache_gb(nodes, edges)
        assert abs(result - expected) < 0.0001

    def test_neo4j_disk_overhead(self) -> None:
        """Disk = pagecache * 1.3."""
        pagecache = 2.0
        assert compute_neo4j_disk_gb(pagecache) == pytest.approx(2.6)


# ---------------------------------------------------------------------------
# test_ceiling_detection: verify triggers at correct thresholds
# ---------------------------------------------------------------------------


class TestCeilingDetection:
    """Verify ceiling events fire at the correct thresholds."""

    def test_no_ceilings_below_thresholds(self) -> None:
        seen: set[str] = set()
        events = detect_ceilings(1, 100_000, 200_000, 1.0, seen)
        assert len(events) == 0

    def test_pagecache_starved_ceiling(self) -> None:
        seen: set[str] = set()
        events = detect_ceilings(3, CEILING_PAGECACHE_STARVED_NODES + 1, 1_000_000, 1.0, seen)
        names = [e.ceiling for e in events]
        assert "neo4j_pagecache_starved" in names

    def test_single_instance_ceiling(self) -> None:
        seen: set[str] = set()
        events = detect_ceilings(6, CEILING_SINGLE_INSTANCE_NODES + 1, 20_000_000, 5.0, seen)
        names = [e.ceiling for e in events]
        assert "neo4j_single_instance" in names
        # Should also trigger pagecache_starved since 10M > 500K
        assert "neo4j_pagecache_starved" in names

    def test_sharded_limit_ceiling(self) -> None:
        seen: set[str] = set()
        events = detect_ceilings(12, CEILING_SHARDED_LIMIT_NODES + 1, 1_000_000_000, 10.0, seen)
        names = [e.ceiling for e in events]
        assert "neo4j_sharded_limit" in names

    def test_redis_memory_ceilings(self) -> None:
        """All three Redis memory ceilings should trigger at different levels."""
        seen: set[str] = set()

        # 17 GB triggers 16GB ceiling only
        events_16 = detect_ceilings(3, 100_000, 200_000, 17.0, seen)
        assert any(e.ceiling == "redis_memory_16gb" for e in events_16)
        assert not any(e.ceiling == "redis_memory_64gb" for e in events_16)

        # 70 GB triggers 64GB ceiling (16GB already seen)
        events_64 = detect_ceilings(6, 100_000, 200_000, 70.0, seen)
        assert any(e.ceiling == "redis_memory_64gb" for e in events_64)
        assert not any(e.ceiling == "redis_memory_16gb" for e in events_64)  # already seen

        # 300 GB triggers 256GB ceiling
        events_256 = detect_ceilings(12, 100_000, 200_000, 300.0, seen)
        assert any(e.ceiling == "redis_memory_256gb" for e in events_256)

    def test_ceilings_only_fire_once(self) -> None:
        """A ceiling should not fire again once already seen."""
        seen: set[str] = set()
        events1 = detect_ceilings(1, CEILING_PAGECACHE_STARVED_NODES + 1, 1_000_000, 1.0, seen)
        events2 = detect_ceilings(
            2, CEILING_PAGECACHE_STARVED_NODES + 100_000, 2_000_000, 1.0, seen
        )
        assert len(events1) == 1
        assert len(events2) == 0

    def test_ceiling_event_has_action(self) -> None:
        seen: set[str] = set()
        events = detect_ceilings(5, CEILING_SINGLE_INSTANCE_NODES + 1, 20_000_000, 5.0, seen)
        for event in events:
            assert event.action  # non-empty action string
            assert event.metric  # non-empty metric string

    def test_phase_determination(self) -> None:
        assert determine_phase(0) == "single"
        assert determine_phase(9_999_999) == "single"
        assert determine_phase(10_000_000) == "sharded"
        assert determine_phase(499_999_999) == "sharded"
        assert determine_phase(500_000_000) == "tiered"
        assert determine_phase(4_999_999_999) == "tiered"
        assert determine_phase(5_000_000_000) == "distributed"


# ---------------------------------------------------------------------------
# test_compaction_reduces_nodes: compaction_ratio 0.6 reduces by ~40%
# ---------------------------------------------------------------------------


class TestCompaction:
    """Verify that compaction ratio affects node counts correctly."""

    def test_zero_compaction(self) -> None:
        """With 0 compaction, all raw nodes remain."""
        profile = DeploymentProfile(compaction_ratio=0.0)
        monthly_events = compute_monthly_events(profile)
        nodes_no_compact = compute_monthly_nodes(profile, monthly_events)

        profile_with = DeploymentProfile(compaction_ratio=0.6)
        nodes_with_compact = compute_monthly_nodes(profile_with, monthly_events)

        # Compacted should be ~40% of uncompacted
        ratio = nodes_with_compact / nodes_no_compact
        assert 0.38 <= ratio <= 0.42

    def test_full_compaction(self) -> None:
        """With 1.0 compaction, all nodes are removed."""
        profile = DeploymentProfile(compaction_ratio=1.0)
        monthly_events = compute_monthly_events(profile)
        nodes = compute_monthly_nodes(profile, monthly_events)
        assert nodes == 0

    def test_compaction_affects_projection(self) -> None:
        """Higher compaction ratio yields fewer total nodes at end of projection."""
        profile_low = DeploymentProfile(compaction_ratio=0.2)
        profile_high = DeploymentProfile(compaction_ratio=0.8)

        proj_low = project(profile_low, months=12)
        proj_high = project(profile_high, months=12)

        assert proj_high.timeline[-1].total_nodes < proj_low.timeline[-1].total_nodes

    def test_edges_compact_less_than_nodes(self) -> None:
        """Edges use 80% of compaction ratio, so they compact less aggressively."""
        profile = DeploymentProfile(compaction_ratio=0.6)
        monthly_events = compute_monthly_events(profile)

        nodes = compute_monthly_nodes(profile, monthly_events)
        edges = compute_monthly_edges(profile, monthly_events)

        # Calculate what the edge-to-node ratio would be at 0 compaction
        profile_zero = DeploymentProfile(compaction_ratio=0.0)
        nodes_zero = compute_monthly_nodes(profile_zero, monthly_events)
        edges_zero = compute_monthly_edges(profile_zero, monthly_events)

        # Node retention = 0.4 (1 - 0.6), Edge retention = 0.52 (1 - 0.48)
        node_retention = nodes / nodes_zero
        edge_retention = edges / edges_zero

        assert edge_retention > node_retention


# ---------------------------------------------------------------------------
# test_multi_tenant_scaling: 50 tenants grows 50x faster than 1
# ---------------------------------------------------------------------------


class TestMultiTenantScaling:
    """Verify that multi-tenant deployments scale proportionally."""

    def test_50_tenants_50x_events(self) -> None:
        single = DeploymentProfile(tenants=1, sessions_per_tenant_per_day=10)
        multi = DeploymentProfile(tenants=50, sessions_per_tenant_per_day=10)

        assert compute_monthly_events(multi) == 50 * compute_monthly_events(single)

    def test_50_tenants_50x_nodes(self) -> None:
        single = DeploymentProfile(tenants=1, sessions_per_tenant_per_day=10)
        multi = DeploymentProfile(tenants=50, sessions_per_tenant_per_day=10)

        events_single = compute_monthly_events(single)
        events_multi = compute_monthly_events(multi)

        nodes_single = compute_monthly_nodes(single, events_single)
        nodes_multi = compute_monthly_nodes(multi, events_multi)

        # Allow for floating-point ceil rounding (within 1 node difference)
        assert abs(nodes_multi - 50 * nodes_single) <= 50

    def test_multi_tenant_hits_ceilings_sooner(self) -> None:
        """A 50-tenant deployment should hit ceilings earlier than single-tenant."""
        single = DeploymentProfile(tenants=1, sessions_per_tenant_per_day=100)
        multi = DeploymentProfile(tenants=50, sessions_per_tenant_per_day=100)

        proj_single = project(single, months=36)
        proj_multi = project(multi, months=36)

        # Multi-tenant should have more (or equal) ceiling events
        assert len(proj_multi.ceilings) >= len(proj_single.ceilings)

        # If both hit pagecache_starved, multi should hit it first
        single_pagecache = [
            c for c in proj_single.ceilings if c.ceiling == "neo4j_pagecache_starved"
        ]
        multi_pagecache = [c for c in proj_multi.ceilings if c.ceiling == "neo4j_pagecache_starved"]
        if single_pagecache and multi_pagecache:
            assert multi_pagecache[0].month <= single_pagecache[0].month


# ---------------------------------------------------------------------------
# test_json_output_format: valid JSON with required fields
# ---------------------------------------------------------------------------


class TestJsonOutput:
    """Verify JSON output format."""

    def test_json_is_valid(self) -> None:
        profile = DeploymentProfile()
        projection = project(profile, months=6)
        output = format_json(projection)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_json_has_required_fields(self) -> None:
        profile = DeploymentProfile()
        projection = project(profile, months=6)
        output = format_json(projection)
        parsed = json.loads(output)

        assert "profile" in parsed
        assert "timeline" in parsed
        assert "ceilings" in parsed
        assert "recommendations" in parsed

    def test_json_profile_fields(self) -> None:
        profile = DeploymentProfile(tenants=5, sessions_per_tenant_per_day=20)
        projection = project(profile, months=3)
        parsed = json.loads(format_json(projection))

        assert parsed["profile"]["tenants"] == 5
        assert parsed["profile"]["sessions_per_tenant_per_day"] == 20

    def test_json_timeline_entry_fields(self) -> None:
        profile = DeploymentProfile()
        projection = project(profile, months=3)
        parsed = json.loads(format_json(projection))

        entry = parsed["timeline"][0]
        required_keys = {
            "month",
            "total_events",
            "total_nodes",
            "total_edges",
            "redis_memory_gb",
            "neo4j_heap_gb",
            "neo4j_pagecache_gb",
            "neo4j_disk_gb",
            "phase",
        }
        assert required_keys.issubset(entry.keys())

    def test_json_ceiling_entry_fields(self) -> None:
        """Generate a scenario that triggers a ceiling to test fields."""
        profile = DeploymentProfile(
            tenants=100,
            sessions_per_tenant_per_day=100,
            avg_events_per_session=50,
        )
        projection = project(profile, months=12)
        parsed = json.loads(format_json(projection))

        assert len(parsed["ceilings"]) > 0
        ceiling = parsed["ceilings"][0]
        assert "month" in ceiling
        assert "ceiling" in ceiling
        assert "metric" in ceiling
        assert "action" in ceiling

    def test_json_roundtrip_consistency(self) -> None:
        """JSON output should be consistent across multiple calls."""
        profile = DeploymentProfile(tenants=3)
        proj1 = project(profile, months=6)
        proj2 = project(profile, months=6)
        assert format_json(proj1) == format_json(proj2)


# ---------------------------------------------------------------------------
# test_edge_cases: 0 sessions, very large numbers
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Verify behavior at boundary conditions."""

    def test_zero_sessions(self) -> None:
        """0 sessions per day should produce no growth."""
        profile = DeploymentProfile(
            tenants=1,
            sessions_per_tenant_per_day=0,
        )
        projection = project(profile, months=12)
        for entry in projection.timeline:
            assert entry.total_events == 0
            assert entry.total_nodes == 0
            assert entry.total_edges == 0
            assert entry.redis_memory_gb == 0.0

    def test_zero_tenants(self) -> None:
        """0 tenants should produce no growth."""
        profile = DeploymentProfile(tenants=0)
        projection = project(profile, months=12)
        for entry in projection.timeline:
            assert entry.total_events == 0
            assert entry.total_nodes == 0

    def test_very_large_deployment(self) -> None:
        """Platform-scale deployment should not overflow."""
        profile = DeploymentProfile(
            tenants=1000,
            sessions_per_tenant_per_day=500,
            avg_events_per_session=50,
            retention_days=365,
        )
        projection = project(profile, months=36)
        # Should complete without error
        assert len(projection.timeline) == 36
        # Final month should have very large numbers
        final = projection.timeline[-1]
        assert final.total_events > 0
        assert final.total_nodes > 0
        assert final.total_edges > 0
        assert final.phase in ("sharded", "tiered", "distributed")

    def test_one_month_projection(self) -> None:
        """Single month projection should work."""
        profile = DeploymentProfile()
        projection = project(profile, months=1)
        assert len(projection.timeline) == 1

    def test_very_short_retention(self) -> None:
        """1-day retention should cap Redis memory heavily."""
        profile = DeploymentProfile(retention_days=1)
        projection = project(profile, months=12)
        # Redis memory should be much lower than with 90-day retention
        profile_long = DeploymentProfile(retention_days=90)
        proj_long = project(profile_long, months=12)
        assert projection.timeline[-1].redis_memory_gb < proj_long.timeline[-1].redis_memory_gb

    def test_full_compaction_ratio(self) -> None:
        """compaction_ratio=1.0 means all nodes/edges compacted away."""
        profile = DeploymentProfile(compaction_ratio=1.0)
        projection = project(profile, months=6)
        for entry in projection.timeline:
            assert entry.total_nodes == 0
            # Edges use 0.8 of compaction, so 1.0 * 0.8 = 0.8 -> still 20% remain
            # Wait: (1 - 1.0 * 0.8) = 0.2, so edges are NOT zero
            # This is intentional: edges compact less aggressively

    def test_zero_compaction_ratio(self) -> None:
        """compaction_ratio=0.0 means no compaction."""
        profile = DeploymentProfile(compaction_ratio=0.0)
        monthly_events = compute_monthly_events(profile)
        events_per_session = profile.avg_events_per_session
        entity_ratio = profile.avg_entities_per_session / events_per_session
        summary_ratio = 1.0 / events_per_session

        expected_raw_nodes = monthly_events * (1.0 + entity_ratio + summary_ratio)
        nodes = compute_monthly_nodes(profile, monthly_events)
        assert nodes == math.ceil(expected_raw_nodes)


# ---------------------------------------------------------------------------
# test_text_output: verify text formatting
# ---------------------------------------------------------------------------


class TestTextOutput:
    """Verify text output formatting."""

    def test_text_contains_header(self) -> None:
        profile = DeploymentProfile(tenants=5)
        projection = project(profile, months=6)
        text = format_text(projection, 6)
        assert "Scale Projection" in text
        assert "5 tenant(s)" in text

    def test_text_contains_table_columns(self) -> None:
        profile = DeploymentProfile()
        projection = project(profile, months=12)
        text = format_text(projection, 12)
        assert "Month" in text
        assert "Nodes" in text
        assert "Edges" in text
        assert "Redis" in text
        assert "Phase" in text

    def test_text_shows_ceilings(self) -> None:
        """A large deployment should show ceiling warnings."""
        profile = DeploymentProfile(
            tenants=50,
            sessions_per_tenant_per_day=100,
            avg_events_per_session=50,
        )
        projection = project(profile, months=12)
        text = format_text(projection, 12)
        if projection.ceilings:
            assert "Ceilings:" in text

    def test_text_shows_recommendations(self) -> None:
        profile = DeploymentProfile()
        projection = project(profile, months=12)
        text = format_text(projection, 12)
        assert "Recommendations:" in text


# ---------------------------------------------------------------------------
# test_cli_main: verify CLI entry point
# ---------------------------------------------------------------------------


class TestCLI:
    """Verify the CLI argument parsing and execution."""

    def test_main_default_args(self, capsys: pytest.CaptureFixture[str]) -> None:
        main(["--months", "3"])
        captured = capsys.readouterr()
        assert "Scale Projection" in captured.out

    def test_main_json_format(self, capsys: pytest.CaptureFixture[str]) -> None:
        main(["--months", "3", "--format", "json"])
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert "timeline" in parsed
        assert len(parsed["timeline"]) == 3

    def test_main_custom_tenants(self, capsys: pytest.CaptureFixture[str]) -> None:
        main(["--tenants", "10", "--months", "1", "--format", "json"])
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["profile"]["tenants"] == 10

    def test_main_all_args(self, capsys: pytest.CaptureFixture[str]) -> None:
        main(
            [
                "--tenants",
                "5",
                "--sessions-per-day",
                "20",
                "--events-per-session",
                "30",
                "--retention-days",
                "60",
                "--compaction-ratio",
                "0.5",
                "--months",
                "6",
                "--format",
                "json",
            ]
        )
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["profile"]["tenants"] == 5
        assert parsed["profile"]["sessions_per_tenant_per_day"] == 20
        assert parsed["profile"]["avg_events_per_session"] == 30
        assert parsed["profile"]["retention_days"] == 60
        assert parsed["profile"]["compaction_ratio"] == 0.5
        assert len(parsed["timeline"]) == 6
