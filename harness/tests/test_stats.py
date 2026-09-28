import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gate_eval import stats  # noqa: E402


def test_paired_power_reproduces_spec_figures():
    assert abs(stats.paired_power(0.125, 200) - 0.52) < 0.01
    assert abs(stats.paired_power(0.125, 400) - 0.82) < 0.01
    assert math.isnan(stats.paired_power(0.001, 200))


def test_cluster_bootstrap_bounds_bracket_point():
    items = [{"c": i // 3, "v": float(i % 2)} for i in range(90)]
    out = stats.cluster_bootstrap(items, "c", lambda xs: stats.mean([x["v"] for x in xs]), resamples=500, seed=1)
    assert out["G"] == 30
    assert out["lb95"] <= out["point"] <= out["ub95"]


def test_macro_f1_excludes_zero_support():
    out = stats.macro_f1(["a", "b", "a"], ["a", "a", "b"], ["a", "b", "c"])
    assert out["classes_excluded_zero_support"] == ["c"]
    assert 0.0 <= out["macro_f1"] <= 1.0
