"""Presence-only evaluation metrics.

The key rule in this project is that GBIF occurrences are positive evidence of
occupancy, not observations of a calibrated 100% occurrence probability.
Scores are therefore evaluated relative to a background/reference sample.

These functions are model-evaluation diagnostics. They are deliberately
separate from Product-A v2 ecological niche-recovery tuning targets.
"""

from __future__ import annotations

import numpy as np


def _finite(values: np.ndarray | list[float]) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    return arr[np.isfinite(arr)]


def _average_ranks(x: np.ndarray) -> np.ndarray:
    order = np.argsort(x, kind="mergesort")
    sorted_x = x[order]
    ranks = np.empty(len(x), dtype=float)
    start = 0
    while start < len(x):
        end = start + 1
        while end < len(x) and sorted_x[end] == sorted_x[start]:
            end += 1
        rank = 0.5 * (start + end - 1) + 1.0
        ranks[order[start:end]] = rank
        start = end
    return ranks


def _spearman(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2 or len(y) != len(x):
        return float("nan")
    xr = _average_ranks(np.asarray(x, dtype=float))
    yr = _average_ranks(np.asarray(y, dtype=float))
    xr -= xr.mean()
    yr -= yr.mean()
    denom = np.sqrt(np.sum(xr * xr) * np.sum(yr * yr))
    if denom == 0:
        return float("nan")
    return float(np.sum(xr * yr) / denom)


def presence_rank_score(
    presence_scores: np.ndarray | list[float],
    background_scores: np.ndarray | list[float],
) -> float:
    """Return mean rank of held-out presences against held-out background.

    The score is in [0, 1]. 0.5 is random ranking; 1.0 means every held-out
    presence receives a higher suitability score than every background point.
    With ties handled at half credit this is numerically equivalent to the
    presence-background ROC AUC, but the name avoids implying verified absences.
    """

    p = _finite(presence_scores)
    b = _finite(background_scores)
    if p.size == 0 or b.size == 0:
        return float("nan")

    b_sorted = np.sort(b)
    lower = np.searchsorted(b_sorted, p, side="left")
    upper = np.searchsorted(b_sorted, p, side="right")
    ranks = (lower + 0.5 * (upper - lower)) / b.size
    return float(np.mean(ranks))


def omission_rate_at_training_quantile(
    training_presence_scores: np.ndarray | list[float],
    test_presence_scores: np.ndarray | list[float],
    *,
    quantile: float = 0.10,
) -> float:
    """Return independent-test omission at a training-presence quantile threshold.

    With the default ``quantile=0.10`` this is an OR10-style diagnostic: the
    threshold is the 10th percentile of training-presence suitability and the
    returned value is the fraction of independent test presences below it.

    This remains a conventional model diagnostic. It is not a niche-recovery
    objective and does not alter frozen Product-A v1 selection semantics.
    """

    if not 0.0 <= quantile <= 1.0:
        raise ValueError("quantile must lie in [0, 1].")
    train = _finite(training_presence_scores)
    test = _finite(test_presence_scores)
    if train.size == 0 or test.size == 0:
        return float("nan")
    threshold = float(np.quantile(train, quantile))
    return float(np.mean(test < threshold))


def boyce_index(
    presence_scores: np.ndarray | list[float],
    background_scores: np.ndarray | list[float],
    *,
    n_bins: int = 10,
) -> float:
    """Compute a binned Boyce-style presence/background calibration index.

    Suitability is divided into equal-width bins across the combined score
    range. For each usable bin we calculate the observed-to-expected presence
    ratio and correlate that ratio with increasing suitability. The result is
    in [-1, 1]; positive values indicate that presences become more frequent
    relative to background as predicted suitability increases.

    This implementation deliberately reports NaN when fewer than three bins
    carry information rather than manufacturing a stable-looking number. It is
    retained for backwards compatibility and is distinct from the continuous
    moving-window Boyce index implemented below.
    """

    p = _finite(presence_scores)
    b = _finite(background_scores)
    if p.size == 0 or b.size == 0 or n_bins < 3:
        return float("nan")

    lo = min(float(p.min()), float(b.min()))
    hi = max(float(p.max()), float(b.max()))
    if not hi > lo:
        return float("nan")

    edges = np.linspace(lo, hi, n_bins + 1)
    p_count, _ = np.histogram(p, bins=edges)
    b_count, _ = np.histogram(b, bins=edges)
    expected = b_count / b.size
    observed = p_count / p.size

    usable = expected > 0
    if np.sum(usable) < 3:
        return float("nan")

    ratio = observed[usable] / expected[usable]
    mids = ((edges[:-1] + edges[1:]) / 2)[usable]
    if np.unique(ratio).size < 2:
        return float("nan")
    return _spearman(mids, ratio)


def continuous_boyce_index(
    presence_scores: np.ndarray | list[float],
    background_scores: np.ndarray | list[float],
    *,
    window_width: float | None = None,
    resolution: int = 100,
    remove_successive_duplicates: bool = True,
) -> float:
    """Compute the moving-window continuous Boyce index (CBI).

    This follows the Hirzel et al. (2006) / current ``ecospat.boyce`` moving-
    window convention for presence-only evaluation: the validation-presence
    score distribution is compared with the available/background score
    distribution through predicted-to-expected (P/E) ratios along the
    suitability gradient. The index is the Spearman correlation between the
    moving-window position and its finite P/E ratio.

    By default the moving-window width is one tenth of the *background/fit*
    suitability range and 100 focal steps are used. Successive duplicated P/E
    ratios are removed by default to match the current ecospat convention.
    This metric is provided as a secondary sensitivity; it does not redefine
    SDMR's Product-A selector or retroactively change frozen promotion criteria.
    """

    obs = _finite(presence_scores)
    fit = _finite(background_scores)
    if obs.size == 0 or fit.size == 0 or resolution < 1:
        return float("nan")

    fit_range = float(fit.max() - fit.min())
    if not fit_range > 0:
        return float("nan")
    width = fit_range / 10.0 if window_width is None else float(window_width)
    if not width > 0:
        return float("nan")

    lo = min(float(fit.min()), float(obs.min()))
    hi = max(float(fit.max()), float(obs.max()))
    span = hi - lo - width
    if not span > 0:
        return float("nan")

    # ecospat's nclass=0 implementation uses res+1 overlapping intervals.
    left = np.linspace(lo, hi - width, int(resolution) + 1)
    ratios = np.full(left.size, np.nan, dtype=float)
    for i, lower in enumerate(left):
        upper = lower + width
        observed = np.count_nonzero((obs >= lower) & (obs <= upper)) / obs.size
        expected = np.count_nonzero((fit >= lower) & (fit <= upper)) / fit.size
        if expected > 0:
            # ecospat rounds its P/E values before the correlation/duplicate test.
            ratios[i] = np.round(observed / expected, 10)

    keep = np.isfinite(ratios)
    if np.count_nonzero(keep) < 2:
        return float("nan")
    x = left[keep]
    y = ratios[keep]

    if remove_successive_duplicates and y.size > 1:
        distinct = np.ones(y.size, dtype=bool)
        distinct[1:] = y[1:] != y[:-1]
        x = x[distinct]
        y = y[distinct]
    if y.size < 2 or np.unique(y).size < 2:
        return float("nan")
    return _spearman(x, y)
