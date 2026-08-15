"""Multi-objective selector for ecological niche-recovery tuning.

The selector deliberately avoids inventing a weighted super-score. Candidate
protocols are first filtered to the Pareto frontier of ecological recovery
metrics, then a minimax rank rule chooses the most balanced frontier member.
Prediction/model-fit statistics (AUC, CBI, OR10, AICc) can be reported as
comparators or guardrails but are not part of this ecological recovery target.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd


RECOVERY_DIRECTIONS = {
    "niche_overlap_schoener_d_pc12": "max",
    "centroid_distance": "min",
    "breadth_log_sd_error": "min",
    "quantile_profile_error": "min",
}


@dataclass(frozen=True)
class NicheRecoverySelection:
    candidate: str
    pareto_front: tuple[str, ...]
    summary: pd.DataFrame


def _aggregate_candidate_metrics(
    metrics: pd.DataFrame,
    *,
    candidate_col: str,
    fold_col: str,
    metric_columns: Sequence[str],
) -> pd.DataFrame:
    required = {candidate_col, fold_col, *metric_columns}
    missing = required - set(metrics.columns)
    if missing:
        raise KeyError(f"niche-recovery metrics missing columns: {sorted(missing)}")
    data = metrics.copy()
    for metric in metric_columns:
        data[metric] = pd.to_numeric(data[metric], errors="coerce")
    rows = []
    for candidate, group in data.groupby(candidate_col, sort=True):
        row = {candidate_col: str(candidate), "n_folds": int(group[fold_col].nunique())}
        for metric in metric_columns:
            finite = group[metric][np.isfinite(group[metric])]
            row[metric] = float(finite.mean()) if len(finite) else float("nan")
            row[f"{metric}__n"] = int(len(finite))
        rows.append(row)
    return pd.DataFrame(rows)


def _dominates(a: pd.Series, b: pd.Series, metric_columns: Sequence[str]) -> bool:
    at_least_one_strict = False
    for metric in metric_columns:
        av = float(a[metric])
        bv = float(b[metric])
        if not np.isfinite(av) or not np.isfinite(bv):
            return False
        direction = RECOVERY_DIRECTIONS[metric]
        if direction == "max":
            if av < bv - 1e-12:
                return False
            at_least_one_strict |= av > bv + 1e-12
        else:
            if av > bv + 1e-12:
                return False
            at_least_one_strict |= av < bv - 1e-12
    return bool(at_least_one_strict)


def select_niche_recovery_protocol(
    metrics: pd.DataFrame,
    *,
    candidate_col: str = "candidate",
    fold_col: str = "fold",
    complexity_col: str | None = "n_predictors",
    metric_columns: Sequence[str] = tuple(RECOVERY_DIRECTIONS),
) -> NicheRecoverySelection:
    """Select a balanced niche-recovery protocol without a weighted super-score.

    Steps
    -----
    1. Average each ecological recovery dimension across inner held-out folds.
    2. Remove candidates Pareto-dominated across all recovery dimensions.
    3. Rank the remaining candidates separately on each dimension.
    4. Choose the candidate minimizing its worst dimension rank (minimax).
    5. Break ties by mean dimension rank, then model complexity, then name.

    This is a *tuning procedure*, not a new model-evaluation statistic.
    """

    metric_columns = tuple(str(x) for x in metric_columns)
    unknown = [x for x in metric_columns if x not in RECOVERY_DIRECTIONS]
    if unknown:
        raise ValueError(f"unknown niche-recovery metrics: {unknown}")
    summary = _aggregate_candidate_metrics(
        metrics,
        candidate_col=candidate_col,
        fold_col=fold_col,
        metric_columns=metric_columns,
    )
    if summary.empty:
        raise ValueError("no candidate niche-recovery metrics supplied")

    if complexity_col and complexity_col in metrics.columns:
        complexity = (
            metrics.groupby(candidate_col, as_index=False)[complexity_col]
            .mean()
            .rename(columns={complexity_col: "mean_complexity"})
        )
        complexity[candidate_col] = complexity[candidate_col].astype(str)
        summary = summary.merge(complexity, on=candidate_col, how="left")
    else:
        summary["mean_complexity"] = np.nan

    finite = np.ones(len(summary), dtype=bool)
    for metric in metric_columns:
        finite &= np.isfinite(pd.to_numeric(summary[metric], errors="coerce").to_numpy(float))
    if not np.any(finite):
        raise ValueError("no candidate has a complete niche-recovery profile")
    summary["eligible_complete_profile"] = finite

    frontier = []
    eligible_idx = list(summary.index[finite])
    for idx in eligible_idx:
        dominated = any(
            other != idx and _dominates(summary.loc[other], summary.loc[idx], metric_columns)
            for other in eligible_idx
        )
        if not dominated:
            frontier.append(idx)
    summary["pareto_front"] = summary.index.isin(frontier)

    frontier_frame = summary.loc[frontier].copy()
    for metric in metric_columns:
        ascending = RECOVERY_DIRECTIONS[metric] == "min"
        frontier_frame[f"rank__{metric}"] = frontier_frame[metric].rank(
            method="min", ascending=ascending
        )
    rank_cols = [f"rank__{metric}" for metric in metric_columns]
    frontier_frame["worst_metric_rank"] = frontier_frame[rank_cols].max(axis=1)
    frontier_frame["mean_metric_rank"] = frontier_frame[rank_cols].mean(axis=1)
    frontier_frame = frontier_frame.sort_values(
        ["worst_metric_rank", "mean_metric_rank", "mean_complexity", candidate_col],
        ascending=[True, True, True, True],
        na_position="last",
        kind="mergesort",
    )
    winner = str(frontier_frame.iloc[0][candidate_col])

    rank_payload = frontier_frame[[candidate_col, *rank_cols, "worst_metric_rank", "mean_metric_rank"]]
    summary = summary.merge(rank_payload, on=candidate_col, how="left")
    summary["selected"] = summary[candidate_col].astype(str).eq(winner)
    summary = summary.sort_values(
        ["selected", "pareto_front", "worst_metric_rank", "mean_metric_rank", candidate_col],
        ascending=[False, False, True, True, True],
        na_position="last",
        kind="mergesort",
    ).reset_index(drop=True)

    return NicheRecoverySelection(
        candidate=winner,
        pareto_front=tuple(sorted(str(summary.loc[i, candidate_col]) for i in summary.index[summary["pareto_front"]])),
        summary=summary,
    )
