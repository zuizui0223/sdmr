"""Pre-outcome power planning for the fresh empirical SDMR programme."""
from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist


@dataclass(frozen=True)
class PairedGainPowerResult:
    n_taxa: int
    standard_error: float
    critical_mean: float
    power: float


def paired_gain_power(
    *,
    n_taxa: int,
    true_mean_gain: float,
    taxon_sd: float,
    minimum_mean_gain: float,
    minimum_lower_bound: float,
    alpha: float = 0.05,
) -> PairedGainPowerResult:
    """Approximate power for the joint EMP-A / EMP-B paired-gain gate.

    The planning model treats taxon-level paired reconstruction gains as iid
    Gaussian draws only for pre-outcome sample-size planning. The empirical
    execution may use the separately frozen resampling interval, but no fresh
    answer-check data are used here.
    """
    if isinstance(n_taxa, bool) or not isinstance(n_taxa, int) or n_taxa < 2:
        raise ValueError("n_taxa must be an integer >= 2")
    for name, value in (
        ("true_mean_gain", true_mean_gain),
        ("taxon_sd", taxon_sd),
        ("minimum_mean_gain", minimum_mean_gain),
        ("minimum_lower_bound", minimum_lower_bound),
        ("alpha", alpha),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError(f"{name} must be finite numeric")
    if taxon_sd <= 0:
        raise ValueError("taxon_sd must be > 0")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1)")

    se = float(taxon_sd) / math.sqrt(n_taxa)
    z = NormalDist().inv_cdf(1.0 - float(alpha) / 2.0)
    ci_required_mean = float(minimum_lower_bound) + z * se
    critical_mean = max(float(minimum_mean_gain), ci_required_mean)
    standardized = (critical_mean - float(true_mean_gain)) / se
    power = 1.0 - NormalDist().cdf(standardized)
    return PairedGainPowerResult(
        n_taxa=n_taxa,
        standard_error=se,
        critical_mean=critical_mean,
        power=power,
    )


def select_minimum_denominator(
    *,
    planning_min: int,
    planning_max: int,
    target_power: float,
    true_mean_gain: float,
    taxon_sd: float,
    minimum_mean_gain: float,
    minimum_lower_bound: float,
    alpha: float = 0.05,
) -> PairedGainPowerResult:
    """Return the smallest predeclared denominator meeting target power."""
    if (
        isinstance(planning_min, bool)
        or isinstance(planning_max, bool)
        or not isinstance(planning_min, int)
        or not isinstance(planning_max, int)
        or planning_min < 2
        or planning_max < planning_min
    ):
        raise ValueError("invalid planning range")
    if isinstance(target_power, bool) or not isinstance(target_power, (int, float)):
        raise ValueError("target_power must be numeric")
    if not 0 < float(target_power) <= 1:
        raise ValueError("target_power must be in (0, 1]")

    for n_taxa in range(planning_min, planning_max + 1):
        result = paired_gain_power(
            n_taxa=n_taxa,
            true_mean_gain=true_mean_gain,
            taxon_sd=taxon_sd,
            minimum_mean_gain=minimum_mean_gain,
            minimum_lower_bound=minimum_lower_bound,
            alpha=alpha,
        )
        if result.power >= float(target_power):
            return result
    raise ValueError("no denominator in the planning range reaches target power")


def stable_fraction_power(
    *,
    n_taxa: int,
    true_stable_fraction: float,
    minimum_stable_fraction: float,
) -> float:
    """Exact binomial power for the EMP-D stable-process fraction gate."""
    if isinstance(n_taxa, bool) or not isinstance(n_taxa, int) or n_taxa < 1:
        raise ValueError("n_taxa must be a positive integer")
    for name, value in (
        ("true_stable_fraction", true_stable_fraction),
        ("minimum_stable_fraction", minimum_stable_fraction),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be numeric")
        if not 0 <= float(value) <= 1:
            raise ValueError(f"{name} must be in [0, 1]")

    threshold = math.ceil(float(minimum_stable_fraction) * n_taxa - 1e-12)
    p = float(true_stable_fraction)
    return sum(
        math.comb(n_taxa, k) * p**k * (1.0 - p) ** (n_taxa - k)
        for k in range(threshold, n_taxa + 1)
    )
