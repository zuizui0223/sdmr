"""Presence-only evaluation metrics.

The key rule in this project is that GBIF occurrences are positive evidence of
occupancy, not observations of a calibrated 100% occurrence probability.
Scores are therefore evaluated relative to a background/reference sample.
"""

from __future__ import annotations

import numpy as np


def _finite(values: np.ndarray | list[float]) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    return arr[np.isfinite(arr)]


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
    carry information rather than manufacturing a stable-looking number.
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
    mids = (edges[:-1] + edges[1:]) / 2
    mids = mids[usable]
    if np.unique(ratio).size < 2:
        return float("nan")

    def average_ranks(x: np.ndarray) -> np.ndarray:
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

    x = average_ranks(mids)
    y = average_ranks(ratio)
    x -= x.mean()
    y -= y.mean()
    denom = np.sqrt(np.sum(x * x) * np.sum(y * y))
    if denom == 0:
        return float("nan")
    return float(np.sum(x * y) / denom)
