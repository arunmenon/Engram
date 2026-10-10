"""Prevent resets outside the authorized DB or without the verified export."""

from datetime import UTC, datetime
from types import SimpleNamespace

import engram_composition_reuse as reuse
import pytest


@pytest.mark.parametrize("target", ["engram", "engram-g06-target", "engram-g07-target"])
def test_reuse_refuses_retained_databases(target):
    database = SimpleNamespace(name=reuse.TARGET.rsplit("/", 1)[0] + "/" + target)
    with pytest.raises(ValueError, match="exact assessment database"):
        reuse.verify_target(database)


def test_reset_refuses_changed_export_before_any_transaction(tmp_path):
    export = tmp_path / "export.json"
    export.write_text("changed data")
    database = SimpleNamespace(name=reuse.TARGET)
    with pytest.raises(ValueError, match="Export changed"):
        reuse.reset_to(database, [], {}, "wrong-digest", export, None)


def test_freeze_refuses_owner_drift_without_update(tmp_path):
    updates = []
    tx = SimpleNamespace(
        read=lambda *args: [["different-owner", 7]], update=lambda *args: updates.append(args)
    )
    database = SimpleNamespace(name=reuse.TARGET, run_in_transaction=lambda call: call(tx))
    with pytest.raises(ValueError, match="Owner drift"):
        reuse.freeze_and_export(database, ["known-owner", "active"], {}, tmp_path / "export.json")
    assert not updates


def test_export_hash_survives_json_datetime_normalization():
    when = datetime(2026, 10, 10, tzinfo=UTC)
    assert reuse.row_hash([["key", when]]) == reuse.row_hash([["key", str(when)]])
