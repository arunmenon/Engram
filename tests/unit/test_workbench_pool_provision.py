"""Provisioning must never adopt an existing or concurrently created database."""

import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

from context_graph.workbench.pool_config import PoolConfig


@pytest.mark.parametrize("existing,race", [(True, False), (False, True)])
def test_provisioning_refuses_existing_or_raced_target(existing, race, monkeypatch):
    from google.cloud import spanner

    from context_graph.workbench.spanner_pool import DedicatedSlot

    module = runpy.run_path(str(Path(__file__).parents[2] / "scripts/engram_workbench_pool.py"))
    create = module["create_new"]
    closed = []
    resource = "projects/test-project/instances/test-instance/databases/test-sandbox"

    def create_database():
        assert race
        raise RuntimeError("concurrent create rejected")

    database = SimpleNamespace(name=resource, exists=lambda: existing, create=create_database)
    monkeypatch.delenv("SPANNER_EMULATOR_HOST", raising=False)
    monkeypatch.setattr(
        spanner,
        "Client",
        lambda **kwargs: SimpleNamespace(
            instance=lambda name: SimpleNamespace(database=lambda *args, **kwargs: database)
        ),
    )
    monkeypatch.setitem(create.__globals__, "prepare_cleanup", lambda *args: None)
    monkeypatch.setitem(create.__globals__, "close_database", closed.append)
    monkeypatch.setattr(DedicatedSlot, "register_empty", lambda _: pytest.fail("must not adopt"))
    with pytest.raises((ValueError, RuntimeError)):
        create(PoolConfig(pool_id="pool", resources=[resource]))
    assert closed == [database]
