"""Conventional model-level evaluation/selection criteria.

This module is intentionally separate from :mod:`sdmr.niche_recovery`.
AUC/Boyce/OR10/AICc evaluate or select fitted models under statistical criteria;
they are not themselves ecological niche-recovery targets.
"""
from __future__ import annotations

import numpy as np


def omission_rate_at_training_quantile(
    training_presence_scores,
    test_presence_scores,
    *,
    training_omission_fraction: float = 0.10,
) -> float:
    """Return test omission at a threshold defined by training presences.

    ``training_omission_fraction=0.10`` is the usual OR10 convention: the
    threshold excludes the 10% lowest-scoring training presences and reports the
    fraction of independent test presences falling below that threshold.

    Lower is better for transfer, with roughly 0.10 being the nominal training
    expectation for OR10. This is a threshold-dependent model evaluator, not a
    measure of ecological niche geometry.
    """

    if not 0 <= float(training_omission_fraction) < 1:
        raise ValueError("training_omission_fraction must be in [0, 1)")
    train = np.asarray(training_presence_scores, dtype=float)
    test = np.asarray(test_presence_scores, dtype=float)
    train = train[np.isfinite(train)]
    test = test[np.isfinite(test)]
    if train.size == 0 or test.size == 0:
        return float("nan")
    threshold = float(np.quantile(train, float(training_omission_fraction)))
    return float(np.mean(test < threshold))


def or10(training_presence_scores, test_presence_scores) -> float:
    """Convenience wrapper for 10% training-presence omission rate."""

    return omission_rate_at_training_quantile(
        training_presence_scores,
        test_presence_scores,
        training_omission_fraction=0.10,
    )


def corrected_aic(
    log_likelihood: float,
    n_parameters: int,
    n_observations: int,
) -> float:
    """Akaike Information Criterion corrected for finite sample size.

    The caller must supply a *valid likelihood* and defensible effective
    parameter count for the model family being compared. SDMR deliberately does
    not manufacture AICc from arbitrary classifier probabilities or treat a
    penalized/class-weighted logistic fit as MaxEnt AICc without a justified
    likelihood mapping.

    Returns infinity when ``n_observations <= n_parameters + 1`` because the
    small-sample correction is undefined in that regime.
    """

    ll = float(log_likelihood)
    k = int(n_parameters)
    n = int(n_observations)
    if not np.isfinite(ll):
        return float("nan")
    if k < 0:
        raise ValueError("n_parameters must be >= 0")
    if n < 1:
        raise ValueError("n_observations must be >= 1")
    aic = 2.0 * k - 2.0 * ll
    denominator = n - k - 1
    if denominator <= 0:
        return float("inf")
    return float(aic + (2.0 * k * (k + 1)) / denominator)
