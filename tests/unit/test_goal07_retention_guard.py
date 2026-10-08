"""G07 driver verifies both retained datasets before allowing execution."""

import json
import sys
from types import SimpleNamespace

import engram_goal07_event_demo as driver
import engram_goal07_retention as retention
import pytest


def setup_guard(monkeypatch, tmp_path, *, changed=False):
    monkeypatch.setattr(retention, "ROOT", tmp_path)
    for run in ("20261008-cloud-g05-all-01", "20261008-cloud-g06-all-03"):
        path = tmp_path / "docs/review/spanner-compatibility/runs" / run / "retained-dataset.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(dict(fingerprints={"Events": run}, owner=[run])))
    calls, databases = [], {}

    def database(name, **kwargs):
        databases[name] = SimpleNamespace(name=name)
        return databases[name]

    monkeypatch.setattr(
        retention.spanner,
        "Client",
        lambda **kwargs: SimpleNamespace(instance=lambda _: SimpleNamespace(database=database)),
    )
    monkeypatch.setattr(retention, "prepare_cleanup", lambda *args: None)
    counts = {}

    def fingerprint(db):
        calls.append(db.name)
        counts[db.name] = counts.get(db.name, 0) + 1
        run = (
            "20261008-cloud-g05-all-01"
            if db.name == "engram-compat-target"
            else "20261008-cloud-g06-all-03"
        )
        return {"Events": "changed" if changed and counts[db.name] > 1 else run}

    monkeypatch.setattr(retention, "fingerprint", fingerprint)
    monkeypatch.setattr(
        retention,
        "read_owner",
        lambda db: [
            [
                "20261008-cloud-g05-all-01"
                if db.name == "engram-compat-target"
                else "20261008-cloud-g06-all-03"
            ]
        ],
    )
    closed = []
    monkeypatch.setattr(retention, "close_database", lambda db: closed.append(db.name))
    return calls, closed


@pytest.mark.parametrize("changed", [False, True])
def test_both_receipts_checked_before_after_and_failure_preserved(monkeypatch, tmp_path, changed):
    calls, closed = setup_guard(monkeypatch, tmp_path, changed=changed)
    directory = tmp_path / "new-run"
    values = dict(
        GOOGLE_CLOUD_PROJECT="portiq-mvp",
        SPANNER_INSTANCE_ID="engram-experiment",
        GOOGLE_OAUTH_ACCESS_TOKEN="not-printed",
    )
    with (
        pytest.raises(AssertionError if changed else SystemExit) as failure,
        retention.retain_previous_datasets(values, directory),
    ):
        assert calls == ["engram-compat-target", "engram-g06-target"]
        raise SystemExit(7)
    if not changed:
        assert failure.value.code == 7
    assert sorted(closed) == ["engram-compat-target", "engram-g06-target"]
    evidence = json.loads((directory / "g05-g06-protection.json").read_text())
    assert evidence["passed"] is not changed
    assert set(evidence["datasets"]) == {"G05", "G06"}


@pytest.mark.parametrize("run_id", ["../escape", "previous"])
def test_g07_driver_refuses_invalid_or_existing_run_before_credentials(
    monkeypatch, tmp_path, run_id
):
    monkeypatch.setattr(driver, "ROOT", tmp_path)
    previous = tmp_path / "docs/review/spanner-compatibility/runs/previous"
    previous.mkdir(parents=True)
    receipt = previous / "observations.json"
    receipt.write_text("original")
    monkeypatch.setattr(sys, "argv", ["demo", "--credentials", "missing", "--run-id", run_id])
    monkeypatch.setattr(
        driver, "load_credentials", lambda _: pytest.fail("must reject before credentials")
    )
    with pytest.raises(SystemExit) as failure:
        driver.main()
    assert failure.value.code == 2
    assert receipt.read_text() == "original"
