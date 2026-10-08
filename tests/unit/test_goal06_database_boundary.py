"""G06 cannot mistake the retained G05 database for its own reserved target."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from engram_experiment_support import runtime_settings  # noqa: E402
from engram_spanner_empty_activation import (  # noqa: E402
    ActivationRefusedError,
    validate_target,
)


def test_g06_uses_separate_database_and_refuses_unknown_targets():
    values = {"GOOGLE_CLOUD_PROJECT": "portiq-mvp", "SPANNER_INSTANCE_ID": "engram-experiment"}
    assert runtime_settings(values, database="engram-g06-target").spanner.database == (
        "engram-g06-target"
    )
    assert runtime_settings(values).spanner.database == "engram-compat-target"
    with pytest.raises(ValueError):
        runtime_settings(values, database="engram")


def test_activation_refuses_owner_from_retained_dataset():
    g05 = "projects/portiq-mvp/instances/engram-experiment/databases/engram-compat-target"
    g06 = "projects/portiq-mvp/instances/engram-experiment/databases/engram-g06-target"
    owner = ["compat-control", g05, "compat-control-binding", 43, "digest", "active"]
    with pytest.raises(ActivationRefusedError):
        validate_target(SimpleNamespace(name=g06), owner)
    owner[1] = g06
    validate_target(SimpleNamespace(name=g06), owner)
    with pytest.raises(ActivationRefusedError):
        validate_target(SimpleNamespace(name=g05), owner)
