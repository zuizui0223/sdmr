"""Ecological response-surface stability gate for Product-A v2.

This module is deliberately separate from held-out niche recovery. A candidate
must first recover the held-out environmental niche. Only candidates on that
mean-recovery Pareto front can advance to the stability stage, where independent
spatial refits are required to imply similar ecological suitability surfaces on a
fixed common environment.

No recovery and stability quantities are added together. Stability is a separate
Pareto/minimax gate and model complexity is only a final tie-break.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

import numpy as np
import pandas as pd

from .niche_recovery_selection import (
    RECOVERY_DIRECTIONS,
    select_generalization_gated_niche_recovery_protocol,
)


STABILITY_DIRECTIONS = {
    "ecological_surface_stability_rank_mean": "max",
    "ecological_surface_stability_rank_min": "max",
    "ecological_surface_stability_nrmse_mean": "min",
    "ecological_surface_stability_nrmse_max": "min",
}


@dataclass(frozen=True)
class StableNicheRecoverySelection:
    candidate: str
    recovery_pareto_front: tuple[str, ...]
    stability_pareto_front: tuple[str, ...]
    summary: pd.DataFrame


@dataclass(frozen=True)
class GeneralizationGatedStableNicheRecoverySelection:
    candidate: str
    eligible_candidates: tuple[str, ...]
    auc_gate_floor: float
    chance_auc: float
    gate_summary: pd.DataFrame
    stable_selection: StableNicheRecoverySelection


def _aggregate(
    metrics: pd.DataFrame,
    *,
    candidate_col: str,
    fold_col: str,
    columns: Sequence[str],
    complexity_col: str | None,
) -> pd.DataFrame:
    required = {candidate_col, fold_col, *columns}
    missing = required - set(metrics.columns)
    if missing:
        raise KeyError(f"stable niche-recovery metrics missing columns: {sorted(missing)}")
    data = metrics.copy()
    for column in columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    rows = []
    for candidate, group in data.groupby(candidate_col, sort=True):
        row = {
            candidate_col: str(candidate),
            "n_folds": int(group[fold_col].nunique()),
        }
        for column in columns:
            finite = group[column][np.isfinite(group[column])]
            row[column] = float(finite.mean()) if len(finite) else float("nan")
            row[f"{column}__n"] = int(len(finite))
        if complexity_col and complexity_col in group.columns:
            finite_complexity = pd.to_numeric(group[complexity_col], errors="coerce")
            finite_complexity = finite_complexity[np.isfinite(finite_complexity)]
            row["mean_complexity"] = (
                float(finite_complexity.mean()) if len(finite_complexity) else float("nan")
            )
        else:
            row["mean_complexity"] = float("nan")
        rows.append(row)
    return pd.DataFrame(rows)


def _dominates(
    a: pd.Series,
    b: pd.Series,
    columns: Sequence[str],
    directions: dict[str, str],
) -> bool:
    strict = False
    for column in columns:
        av = float(a[column])
        bv = float(b[column])
        if not np.isfinite(av) or not np.isfinite(bv):
            return False
        if directions[column] == "max":
            if av < bv - 1e-12:
                return False
            strict |= av > bv + 1e-12
        else:
            if av > bv + 1e-12:
                return False
            strict |= av < bv - 1e-12
    return bool(strict)


def _pareto(
    frame: pd.DataFrame,
    indices: Sequence[int],
    columns: Sequence[str],
    directions: dict[str, str],
) -> list[int]:
    frontier: list[int] = []
    for idx in indices:
        if not any(
            other != idx and _dominates(frame.loc[other], frame.loc[idx], columns, directions)
            for other in indices
        ):
            frontier.append(int(idx))
    return frontier


def select_stable_niche_recovery_protocol(
    metrics: pd.DataFrame,
    *,
    candidate_col: str = "candidate",
    fold_col: str = "fold",
    complexity_col: str | None = "n_predictors",
    recovery_columns: Sequence[str] = tuple(RECOVERY_DIRECTIONS),
    stability_columns: Sequence[str] = tuple(STABILITY_DIRECTIONS),
) -> StableNicheRecoverySelection:
    """Select recovery first and ecological surface stability second.

    Stage 1
        Mean held-out niche recovery across spatial folds. Pareto-dominated
        candidates cannot be rescued merely because they are stable.
    Stage 2
        Among the recovery Pareto front, compare agreement of ecological surfaces
        inferred by independent spatial refits on one common background reference.
        Both mean and worst pairwise rank/NRMSE diagnostics are retained.
    Stage 3
        Minimax rank across stability dimensions, then mean stability rank, then
        recovery ranks and finally complexity.
    """

    recovery_columns = tuple(str(x) for x in recovery_columns)
    stability_columns = tuple(str(x) for x in stability_columns)
    unknown_recovery = [x for x in recovery_columns if x not in RECOVERY_DIRECTIONS]
    unknown_stability = [x for x in stability_columns if x not in STABILITY_DIRECTIONS]
    if unknown_recovery:
        raise ValueError(f"unknown niche-recovery metrics: {unknown_recovery}")
    if unknown_stability:
        raise ValueError(f"unknown ecological stability metrics: {unknown_stability}")

    all_columns = (*recovery_columns, *stability_columns)
    summary = _aggregate(
        metrics,
        candidate_col=candidate_col,
        fold_col=fold_col,
        columns=all_columns,
        complexity_col=complexity_col,
    )
    if summary.empty:
        raise ValueError("no candidate stable niche-recovery metrics supplied")

    finite = np.ones(len(summary), dtype=bool)
    for column in all_columns:
        finite &= np.isfinite(pd.to_numeric(summary[column], errors="coerce").to_numpy(float))
    if not np.any(finite):
        raise ValueError("no candidate has a complete recovery and surface-stability profile")
    summary["eligible_complete_profile"] = finite

    eligible_idx = list(summary.index[finite])
    recovery_front = _pareto(
        summary,
        eligible_idx,
        recovery_columns,
        {column: RECOVERY_DIRECTIONS[column] for column in recovery_columns},
    )
    summary["recovery_pareto_front"] = summary.index.isin(recovery_front)

    stability_front = _pareto(
        summary,
        recovery_front,
        stability_columns,
        {column: STABILITY_DIRECTIONS[column] for column in stability_columns},
    )
    summary["stability_pareto_front"] = summary.index.isin(stability_front)

    finalist = summary.loc[stability_front].copy()
    for column in stability_columns:
        finalist[f"stability_rank__{column}"] = finalist[column].rank(
            method="min",
            ascending=STABILITY_DIRECTIONS[column] == "min",
        )
    for column in recovery_columns:
        finalist[f"recovery_rank__{column}"] = finalist[column].rank(
            method="min",
            ascending=RECOVERY_DIRECTIONS[column] == "min",
        )
    stability_rank_cols = [f"stability_rank__{x}" for x in stability_columns]
    recovery_rank_cols = [f"recovery_rank__{x}" for x in recovery_columns]
    finalist["stability_worst_metric_rank"] = finalist[stability_rank_cols].max(axis=1)
    finalist["stability_mean_metric_rank"] = finalist[stability_rank_cols].mean(axis=1)
    finalist["recovery_worst_metric_rank"] = finalist[recovery_rank_cols].max(axis=1)
    finalist["recovery_mean_metric_rank"] = finalist[recovery_rank_cols].mean(axis=1)
    finalist = finalist.sort_values(
        [
            "stability_worst_metric_rank",
            "stability_mean_metric_rank",
            "recovery_worst_metric_rank",
            "recovery_mean_metric_rank",
            "mean_complexity",
            candidate_col,
        ],
        ascending=[True, True, True, True, True, True],
        na_position="last",
        kind="mergesort",
    )
    winner = str(finalist.iloc[0][candidate_col])

    rank_payload = finalist[
        [
            candidate_col,
            *stability_rank_cols,
            *recovery_rank_cols,
            "stability_worst_metric_rank",
            "stability_mean_metric_rank",
            "recovery_worst_metric_rank",
            "recovery_mean_metric_rank",
        ]
    ]
    summary = summary.merge(rank_payload, on=candidate_col, how="left")
    summary["selected"] = summary[candidate_col].astype(str).eq(winner)
    summary = summary.sort_values(
        [
            "selected",
            "stability_pareto_front",
            "recovery_pareto_front",
            "stability_worst_metric_rank",
            "stability_mean_metric_rank",
            candidate_col,
        ],
        ascending=[False, False, False, True, True, True],
        na_position="last",
        kind="mergesort",
    ).reset_index(drop=True)
    return StableNicheRecoverySelection(
        candidate=winner,
        recovery_pareto_front=tuple(
            sorted(str(x) for x in summary.loc[summary["recovery_pareto_front"], candidate_col])
        ),
        stability_pareto_front=tuple(
            sorted(str(x) for x in summary.loc[summary["stability_pareto_front"], candidate_col])
        ),
        summary=summary,
    )


def select_generalization_gated_stable_niche_recovery_protocol(
    metrics: pd.DataFrame,
    *,
    candidate_col: str = "candidate",
    fold_col: str = "fold",
    auc_col: str = "presence_rank",
    or10_col: str = "or10",
    chance_auc: float = 0.50,
    minimum_auc_margin: float = 0.01,
    auc_sem_multiplier: float = 1.0,
    max_mean_or10: float | None = None,
    complexity_col: str | None = "n_predictors",
    recovery_columns: Sequence[str] = tuple(RECOVERY_DIRECTIONS),
    stability_columns: Sequence[str] = tuple(STABILITY_DIRECTIONS),
) -> GeneralizationGatedStableNicheRecoverySelection:
    """Run prediction adequacy, niche recovery and surface stability in order."""

    gated = select_generalization_gated_niche_recovery_protocol(
        metrics,
        candidate_col=candidate_col,
        fold_col=fold_col,
        auc_col=auc_col,
        or10_col=or10_col,
        chance_auc=chance_auc,
        minimum_auc_margin=minimum_auc_margin,
        auc_sem_multiplier=auc_sem_multiplier,
        max_mean_or10=max_mean_or10,
        complexity_col=complexity_col,
        metric_columns=recovery_columns,
    )
    subset = metrics.loc[
        metrics[candidate_col].astype(str).isin(gated.eligible_candidates)
    ].copy()
    stable = select_stable_niche_recovery_protocol(
        subset,
        candidate_col=candidate_col,
        fold_col=fold_col,
        complexity_col=complexity_col,
        recovery_columns=recovery_columns,
        stability_columns=stability_columns,
    )
    gate_summary = gated.gate_summary.copy()
    gate_summary["selected_after_surface_stability"] = (
        gate_summary[candidate_col].astype(str).eq(stable.candidate)
    )
    gate_summary = gate_summary.sort_values(
        ["selected_after_surface_stability", "eligible_generalization", "mean_inner_auc", candidate_col],
        ascending=[False, False, False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    return GeneralizationGatedStableNicheRecoverySelection(
        candidate=stable.candidate,
        eligible_candidates=gated.eligible_candidates,
        auc_gate_floor=gated.auc_gate_floor,
        chance_auc=gated.chance_auc,
        gate_summary=gate_summary,
        stable_selection=stable,
    )
