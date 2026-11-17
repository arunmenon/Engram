"""Server allowlist validation and refusal to provision/adopt implicitly."""

import json
from types import SimpleNamespace

import pytest

from context_graph.workbench.pool_config import configured_execution

RESOURCE = "projects/test-project/instances/test-instance/databases/test-sandbox"


def test_config_validation_before_credentials(tmp_path, monkeypatch):
    from google.cloud import spanner

    def forbidden(**kwargs):
        pytest.fail("invalid config must not open a client")

    monkeypatch.setattr(spanner, "Client", forbidden)
    path = tmp_path / "pool.json"
    for resources in ([], [RESOURCE, RESOURCE], ["not-a-resource"], [RESOURCE] * 6):
        path.write_text(json.dumps({"pool_id": "pool", "resources": resources}))
        with pytest.raises(ValueError):
            configured_execution(path)
    path.write_text(json.dumps({"pool_id": "pool", "resources": [RESOURCE]}))
    monkeypatch.setenv("SPANNER_EMULATOR_HOST", "localhost:9010")
    with pytest.raises(ValueError, match="emulator"):
        configured_execution(path)


def test_unregistered_database_refused_and_handle_closed(tmp_path, monkeypatch):
    from google.cloud import spanner

    from context_graph.workbench.spanner_pool import DedicatedSlot, SlotOwnershipError

    opened, closed = [], []
    database = SimpleNamespace(name=RESOURCE)

    def client(**kwargs):
        opened.append(kwargs)
        return SimpleNamespace(
            instance=lambda name: SimpleNamespace(database=lambda name, **kwargs: database)
        )

    def refuse(_):
        raise SlotOwnershipError("unregistered")

    monkeypatch.delenv("SPANNER_EMULATOR_HOST", raising=False)
    monkeypatch.setattr(spanner, "Client", client)
    monkeypatch.setattr(
        "context_graph.adapters.spanner.lifecycle.prepare_cleanup", lambda *args: None
    )
    monkeypatch.setattr("context_graph.workbench.pool_config.close_database", closed.append)
    monkeypatch.setattr(DedicatedSlot, "status", refuse)
    path = tmp_path / "pool.json"
    path.write_text(json.dumps({"pool_id": "pool", "resources": [RESOURCE]}))
    with pytest.raises(SlotOwnershipError):
        configured_execution(path)
    assert opened == [{"project": "test-project"}]
    assert closed == [database]
