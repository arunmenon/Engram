"""G07 is confined to its own database; retained G05/G06 cannot be selected."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from engram_experiment_support import runtime_settings  # noqa: E402
from engram_goal03_implementation_demo import main  # noqa: E402
from engram_spanner_empty_activation import ActivationRefusedError, validate_target  # noqa: E402


def test_g07_settings_select_its_reserved_database():
    values = {"GOOGLE_CLOUD_PROJECT": "portiq-mvp", "SPANNER_INSTANCE_ID": "engram-experiment"}
    assert (
        runtime_settings(values, database="engram-g07-target").spanner.database
        == "engram-g07-target"
    )


@pytest.mark.parametrize("database", ["engram-compat-target", "engram-g06-target", "engram"])
def test_g07_driver_refuses_other_database_before_credentials(database):
    with pytest.raises(ValueError, match="separate reserved database"):
        main(goal="G07", target_database=database)


@pytest.mark.parametrize("database", ["engram-compat-target", "engram-g06-target"])
def test_g07_activation_rejects_retained_owner(database):
    prefix = "projects/portiq-mvp/instances/engram-experiment/databases/"
    target = prefix + "engram-g07-target"
    owner = ["compat-control", prefix + database, "compat-control-binding", 6, "digest", "active"]
    with pytest.raises(ActivationRefusedError):
        validate_target(SimpleNamespace(name=target), owner)
    owner[1] = target
    validate_target(SimpleNamespace(name=target), owner)


@pytest.mark.parametrize(
    "goal,database", [("G07", "engram-g06-target"), ("G06", "engram-g07-target")]
)
def test_preparation_refuses_mismatched_goal_target_before_credentials(goal, database):
    from engram_goal06_prepare import main as prepare

    with pytest.raises(ValueError, match="separate reserved database"):
        prepare(goal=goal, target_database=database)
