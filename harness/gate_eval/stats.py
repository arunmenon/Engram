"""Statistics for the scorers: cluster bootstrap, F1, ECE, normal CDF, DEFF.

Pure Python. 10,000 resamples over a few hundred items runs in seconds.
"""
from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Callable, Sequence


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def variance(values: Sequence[float]) -> float:
    if len(values) < 2:
        return float("nan")
    m = mean(values)
    return sum((v - m) ** 2 for v in values) / (len(values) - 1)


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def percentile(sorted_values: Sequence[float], q: float) -> float:
    """Nearest-rank percentile on an already sorted list, q in [0, 1]."""
    if not sorted_values:
        return float("nan")
    k = max(0, min(len(sorted_values) - 1, int(math.ceil(q * len(sorted_values))) - 1))
    return sorted_values[k]


def cluster_bootstrap(
    items: Sequence[dict],
    cluster_key: str,
    statistic: Callable[[Sequence[dict]], float],
    resamples: int = 10_000,
    seed: int = 20260928,
) -> dict:
    """Percentile cluster bootstrap of `statistic` over `items`.

    Clusters (for example source documents or decision threads) are resampled
    with replacement, each carrying all of its items. Returns the point estimate,
    one-sided and two-sided bounds, the cluster count G and the realised design
    effect DEFF = bootstrap variance / (i.i.d. variance of the per-item values / n),
    where the per-item values are the statistic evaluated on single items when
    that is meaningful (binary indicators); callers pass `iid_values` via the
    returned dict if they want a different DEFF base.
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        groups[str(item[cluster_key])].append(item)
    cluster_ids = sorted(groups)
    G = len(cluster_ids)
    point = statistic(items)
    rng = random.Random(seed)
    draws: list[float] = []
    for _ in range(resamples):
        sample: list[dict] = []
        for _ in range(G):
            sample.extend(groups[cluster_ids[rng.randrange(G)]])
        value = statistic(sample)
        if not math.isnan(value):
            draws.append(value)
    draws.sort()
    boot_var = variance(draws) if len(draws) > 1 else float("nan")
    return {
        "point": point,
        "n_items": len(items),
        "G": G,
        "resamples": resamples,
        "resamples_valid": len(draws),
        "seed": seed,
        "lb95": percentile(draws, 0.05),
        "ub95": percentile(draws, 0.95),
        "lb975": percentile(draws, 0.025),
        "ub975": percentile(draws, 0.975),
        "ci95_two_sided": [percentile(draws, 0.025), percentile(draws, 0.975)],
        "bootstrap_var": boot_var,
    }


def design_effect(bootstrap_var: float, per_item_values: Sequence[float]) -> float:
    """DEFF = bootstrap variance of the mean / (i.i.d. variance / n)."""
    n = len(per_item_values)
    iid = variance(per_item_values)
    if n == 0 or math.isnan(iid) or iid == 0.0 or math.isnan(bootstrap_var):
        return float("nan")
    return bootstrap_var / (iid / n)


def binary_f1(pred: Sequence[str], gold: Sequence[str], positive: str) -> float:
    tp = sum(1 for p, g in zip(pred, gold) if p == positive and g == positive)
    fp = sum(1 for p, g in zip(pred, gold) if p == positive and g != positive)
    fn = sum(1 for p, g in zip(pred, gold) if p != positive and g == positive)
    if tp == 0:
        return 0.0 if (fp or fn) else float("nan")
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    return 2 * precision * recall / (precision + recall)


def macro_f1(pred: Sequence[str], gold: Sequence[str], classes: Sequence[str]) -> dict:
    """Macro-F1 over classes with gold support; zero-support classes are listed."""
    per_class: dict[str, float] = {}
    excluded: list[str] = []
    for cls in classes:
        support = sum(1 for g in gold if g == cls)
        if support == 0:
            excluded.append(cls)
            continue
        per_class[cls] = binary_f1(pred, gold, cls)
    value = mean(list(per_class.values())) if per_class else float("nan")
    return {"macro_f1": value, "per_class": per_class, "classes_excluded_zero_support": excluded}


def expected_calibration_error(probabilities: Sequence[float], correct: Sequence[bool], bins: int = 10) -> float:
    """ECE with equal-width bins over [0, 1]."""
    n = len(probabilities)
    if n == 0:
        return float("nan")
    totals = [0] * bins
    conf_sum = [0.0] * bins
    acc_sum = [0.0] * bins
    for p, c in zip(probabilities, correct):
        idx = min(bins - 1, int(p * bins))
        totals[idx] += 1
        conf_sum[idx] += p
        acc_sum[idx] += 1.0 if c else 0.0
    ece = 0.0
    for b in range(bins):
        if totals[b]:
            ece += (totals[b] / n) * abs(acc_sum[b] / totals[b] - conf_sum[b] / totals[b])
    return ece


def paired_power(pi_hat: float, n_eff: float, d: float = 0.05, alpha_two_sided: float = 0.05) -> float:
    """Two-sided power for a paired binary difference d at discordance pi_hat.

    Var(D) = pi - d^2 (E-20260928-07-r2 power note). Undefined when the
    variance is not positive; the caller reports NaN rather than a number.
    """
    var = pi_hat - d * d
    if n_eff <= 0 or var <= 0:
        return float("nan")
    se = math.sqrt(var / n_eff)
    z = 1.959963984540054 if alpha_two_sided == 0.05 else -_norm_ppf(alpha_two_sided / 2)
    return normal_cdf(d / se - z)


def _norm_ppf(p: float) -> float:
    """Acklam's approximation of the normal quantile; good to ~1e-9."""
    a = [-3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02,
         1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00]
    b = [-5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02,
         6.680131188771972e01, -1.328068155288572e01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e00,
         -2.549732539343734e00, 4.374664141464968e00, 2.938163982698783e00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00,
         3.754408661907416e00]
    plow = 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p <= 1 - plow:
        q = p - 0.5
        r = q * q
        return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
               (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    q = math.sqrt(-2 * math.log(1 - p))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
           ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
