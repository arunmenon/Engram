"""Unit tests for maintenance.delete_orphan_nodes() — ADR-0014 Amendment Gap 8."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from context_graph.adapters.neo4j.maintenance import delete_orphan_nodes


class _MockSessionCtx:
    """Mimics the neo4j driver.session() return — a sync object with async context."""

    def __init__(self, session: AsyncMock) -> None:
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *args):
        pass


def _make_driver(execute_results: list) -> MagicMock:
    """Build a mock AsyncDriver with sequential execute_read/execute_write results.

    ``execute_results`` is a flat list of return values. Each call to
    execute_read or execute_write pops from the front.

    The Entity path alternates: read (get IDs) -> write (delete) -> read -> ...
    Non-Entity paths call only: write (delete) -> write -> ... until 0.

    Callers must carefully sequence values matching actual execution order.
    """
    results = list(execute_results)  # shallow copy

    async def _pop_result(fn):
        return results.pop(0) if results else 0

    session = AsyncMock()
    session.execute_read = AsyncMock(side_effect=_pop_result)
    session.execute_write = AsyncMock(side_effect=_pop_result)

    session_ctx = _MockSessionCtx(session)

    driver = MagicMock()
    driver.session.return_value = session_ctx

    return driver


# ── Test Cases ─────────────────────────────────────────────────────────


class TestDeleteOrphanEntities:
    """Entity orphan cleanup returns entity IDs for embedding cleanup."""

    @pytest.mark.asyncio()
    async def test_single_batch_entities_deleted(self):
        """Orphaned entities are deleted and their IDs returned."""
        # Entity: read=["ent-1","ent-2"], write=2, breaks (2<500)
        # Preference/Skill/Workflow/BehavioralPattern: write=0 each
        driver = _make_driver(
            [
                ["ent-1", "ent-2"],  # entity read
                2,  # entity write
                # batch_deleted(2) < batch_size(500) -> break
                0,  # Preference write
                0,  # Skill write
                0,  # Workflow write
                0,  # BehavioralPattern write
            ]
        )

        counts, entity_ids = await delete_orphan_nodes(driver, "neo4j", batch_size=500)

        assert counts["Entity"] == 2
        assert entity_ids == ["ent-1", "ent-2"]

    @pytest.mark.asyncio()
    async def test_no_orphan_entities(self):
        """When no orphan entities exist, count is 0 and no IDs returned."""
        # Entity: read=[] -> break immediately
        # Preference/Skill/Workflow/BehavioralPattern: write=0 each
        driver = _make_driver(
            [
                [],  # entity read: empty -> break
                0,  # Preference write
                0,  # Skill write
                0,  # Workflow write
                0,  # BehavioralPattern write
            ]
        )

        counts, entity_ids = await delete_orphan_nodes(driver, "neo4j")

        assert counts["Entity"] == 0
        assert entity_ids == []


class TestDeleteOrphanPreferences:
    """Preference orphan cleanup."""

    @pytest.mark.asyncio()
    async def test_orphan_preferences_deleted(self):
        # Entity: read=[] -> break
        # Preference: write=3, write=0 (loop terminates)
        # Skill/Workflow/BehavioralPattern: write=0 each
        driver = _make_driver(
            [
                [],  # entity read
                3,  # Preference write batch 1
                0,  # Preference write batch 2 -> terminates
                0,  # Skill write
                0,  # Workflow write
                0,  # BehavioralPattern write
            ]
        )

        counts, _ = await delete_orphan_nodes(driver, "neo4j")

        assert counts["Preference"] == 3


class TestDeleteOrphanSkills:
    """Skill orphan cleanup."""

    @pytest.mark.asyncio()
    async def test_orphan_skills_deleted(self):
        driver = _make_driver(
            [
                [],  # entity read
                0,  # Preference write
                5,  # Skill write batch 1
                0,  # Skill write batch 2 -> terminates
                0,  # Workflow write
                0,  # BehavioralPattern write
            ]
        )

        counts, _ = await delete_orphan_nodes(driver, "neo4j")

        assert counts["Skill"] == 5


class TestDeleteOrphanWorkflows:
    """Workflow orphan cleanup."""

    @pytest.mark.asyncio()
    async def test_orphan_workflows_deleted(self):
        driver = _make_driver(
            [
                [],  # entity read
                0,  # Preference write
                0,  # Skill write
                2,  # Workflow write batch 1
                0,  # Workflow write batch 2 -> terminates
                0,  # BehavioralPattern write
            ]
        )

        counts, _ = await delete_orphan_nodes(driver, "neo4j")

        assert counts["Workflow"] == 2


class TestDeleteOrphanPatterns:
    """BehavioralPattern orphan cleanup."""

    @pytest.mark.asyncio()
    async def test_orphan_patterns_deleted(self):
        driver = _make_driver(
            [
                [],  # entity read
                0,  # Preference write
                0,  # Skill write
                0,  # Workflow write
                4,  # BehavioralPattern write batch 1
                0,  # BehavioralPattern write batch 2 -> terminates
            ]
        )

        counts, _ = await delete_orphan_nodes(driver, "neo4j")

        assert counts["BehavioralPattern"] == 4


class TestNoOrphansReturnsZero:
    """All labels return zero when no orphans exist."""

    @pytest.mark.asyncio()
    async def test_all_zero(self):
        driver = _make_driver(
            [
                [],  # entity read -> break
                0,  # Preference write -> 0 -> break
                0,  # Skill write
                0,  # Workflow write
                0,  # BehavioralPattern write
            ]
        )

        counts, entity_ids = await delete_orphan_nodes(driver, "neo4j")

        assert all(v == 0 for v in counts.values())
        assert entity_ids == []
        assert len(counts) == 5  # All 5 labels present


class TestBatchLoopContinuesUntilZero:
    """Verifies the batch loop runs multiple times for >batch_size orphans."""

    @pytest.mark.asyncio()
    async def test_multi_batch_entity_cleanup(self):
        """Entity cleanup loops when batch_deleted == batch_size."""
        # batch_size=3: read=3 IDs, write=3 (==batch_size -> continue)
        #               read=2 IDs, write=2 (<batch_size -> break)
        driver = _make_driver(
            [
                ["e1", "e2", "e3"],  # entity read batch 1
                3,  # entity write batch 1 (3 == batch_size -> continue)
                ["e4", "e5"],  # entity read batch 2
                2,  # entity write batch 2 (2 < 3 -> break)
                0,  # Preference write
                0,  # Skill write
                0,  # Workflow write
                0,  # BehavioralPattern write
            ]
        )

        counts, entity_ids = await delete_orphan_nodes(driver, "neo4j", batch_size=3)

        assert counts["Entity"] == 5
        assert entity_ids == ["e1", "e2", "e3", "e4", "e5"]

    @pytest.mark.asyncio()
    async def test_multi_batch_non_entity_cleanup(self):
        """Non-entity labels loop until deleted_count is 0."""
        # batch_size=10
        # Preference: write=10 (continue), write=10 (continue), write=0 (break)
        driver = _make_driver(
            [
                [],  # entity read
                10,  # Preference write batch 1
                10,  # Preference write batch 2
                0,  # Preference write batch 3 -> terminates
                0,  # Skill write
                0,  # Workflow write
                0,  # BehavioralPattern write
            ]
        )

        counts, _ = await delete_orphan_nodes(driver, "neo4j", batch_size=10)

        assert counts["Preference"] == 20
