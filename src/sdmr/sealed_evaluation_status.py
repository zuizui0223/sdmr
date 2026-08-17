"""Explicit status labels for outer-sealed Product-A evaluation.

NaN metrics must not be silently treated as ordinary poor performance or omitted
from summaries.  This helper distinguishes a complete sealed evaluation from
prediction-score unavailability and from ecological-recovery-only unavailability.
It does not trigger fallback, reselection, imputation, or threshold relaxation.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd


RECOVERY_COLUMNS = (
    "niche_overlap_schoener_d_pc12",
    "centroid_distance",
    "breadth_log_sd_error",
    "quantile_profile_error",
)


def complete_row_count(frame: pd.DataFrame, predictors: Sequence[str]) -> int:
    cols = tuple(str(x) for x in predictors)
    if not cols:
        return int(len(frame))
    missing = [col for col in cols if col not in frame.columns]
    if missing:
        return 0
    return int(frame[list(cols)].notna().all(axis=1).sum())


def classify_sealed_evaluation(
    payload: Mapping[str, object],
    *,
    n_complete_sealed_presence: int,
    n_complete_sealed_background: int,
    minimum_complete_rows_per_class: int = 2,
) -> str:
    """Return a non-promotional availability status for one sealed result."""

    minimum = int(minimum_complete_rows_per_class)
    if minimum < 1:
        raise ValueError("minimum_complete_rows_per_class must be >=1")
    if (
        int(n_complete_sealed_presence) < minimum
        or int(n_complete_sealed_background) < minimum
    ):
        return "abstain_prediction_evaluation_unavailable"
    rank = float(payload.get("presence_rank", float("nan")))
    if not np.isfinite(rank):
        return "abstain_prediction_metric_nonfinite"
    recovery = np.array(
        [float(payload.get(column, float("nan"))) for column in RECOVERY_COLUMNS],
        dtype=float,
    )
    if not np.isfinite(recovery).all():
        return "partial_prediction_only_ecological_recovery_unavailable"
    return "complete"
