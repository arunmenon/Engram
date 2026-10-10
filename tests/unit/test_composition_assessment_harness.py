"""Safety and false-pass guards for the live composition assessment harness."""

import re
import sys

import engram_composition_assessment as assessment
import pytest


def test_generated_targets_fit_spanner_names_and_never_overlap_retained_databases():
    for run_id in ("abcd", "12345678"):
        targets = {assessment.database_id(run_id, config) for config in assessment.CONFIGURATIONS}
        assert len(targets) == 5
        assert not targets & {
            "engram",
            "engram-compat-target",
            "engram-g06-target",
            "engram-g07-target",
        }
        assert all(re.fullmatch(r"[a-z][a-z0-9_-]{0,28}[a-z0-9]", target) for target in targets)


@pytest.mark.parametrize(
    ("state", "checks", "shutdown_errors", "expected_exit"),
    [
        ("completed", [{"status": "PASS"}], [], 0),
        ("failed", [], [], 1),
        ("completed", [], [], 1),
        ("completed", [{"status": "FAIL"}], [], 1),
        ("completed", [{"status": "BLOCKED"}], [], 1),
        ("completed", [{"status": "PASS"}], ["ShutdownError"], 1),
    ],
)
def test_failed_blocked_or_unsettled_run_never_exits_successfully(
    tmp_path, monkeypatch, state, checks, shutdown_errors, expected_exit
):
    directory = tmp_path / "docs/review/spanner-compatibility/runs/composition-test"
    directory.mkdir(parents=True)
    (directory / "manifest.json").write_text("{}")
    monkeypatch.setattr(assessment, "ROOT", tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["assessment", "--phase", "run", "--run-id", "test", "--configuration", "core"],
    )

    async def run(*args):
        return {"state": state, "checks": checks, "shutdown_errors": shutdown_errors}

    monkeypatch.setattr(assessment, "run_configuration", run)
    with pytest.raises(SystemExit) as exc:
        assessment.main()
    assert exc.value.code == expected_exit
