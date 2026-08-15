"""Multi-objective selectors for ecological niche-recovery tuning.

Prediction/model-fit statistics are not the ecological objective, but independent
transfer can be used as a *gate* before ecological recovery decides among
predictively credible candidates. This keeps Product-A v2 distinct from simply
renaming AUC while avoiding ecologically attractive models that fail basic
out-of-sample generalization.
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


@dataclass(frozen=True)
class GeneralizationGatedNicheRecoverySelection:
    candidate: str
    eligible_candidates: tuple[str, ...]
    auc_gate_tolerance: float
    gate_summary: pd.DataFrame
    recovery_selection: NicheRecoverySelection


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
    """Select a balanced niche-recovery protocol without a weighted super-score."""

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
        pareto_front=tuple(sorted(str(x) for x in summary.loc[summary["pareto_front"], candidate_col])),
        summary=summary,
    )


def select_generalization_gated_niche_recovery_protocol(
    metrics: pd.DataFrame,
    *,
    candidate_col: str = "candidate",
    fold_col: str = "fold",
    auc_col: str = "presence_rank",
    or10_col: str = "or10",
    minimum_auc_tolerance: float = 0.01,
    auc_sem_multiplier: float = 1.0,
    max_mean_or10: float | None = None,
    complexity_col: str | None = "n_predictors",
    metric_columns: Sequence[str] = tuple(RECOVERY_DIRECTIONS),
) -> GeneralizationGatedNicheRecoverySelection:
    """Gate on independent transfer, then select by ecological recovery.

    The gate is deliberately not an AUC optimizer. Candidates are retained when
    their mean inner AUC-equivalent rank is within a tolerance of the best
    candidate. The tolerance is the larger of a declared minimum and a multiple
    of the best candidate's fold-level standard error, so predictively
    near-equivalent procedures can still be distinguished by ecological recovery.

    ``max_mean_or10`` is an optional severe-omission guardrail. It is configurable
    because no single OR10 cutoff is asserted as a universal biological rule.
    """

    if minimum_auc_tolerance < 0:
        raise ValueError("minimum_auc_tolerance must be >= 0")
    if auc_sem_multiplier < 0:
        raise ValueError("auc_sem_multiplier must be >= 0")
    required = {candidate_col, fold_col, auc_col, *metric_columns}
    if max_mean_or10 is not None:
        required.add(or10_col)
    missing = required - set(metrics.columns)
    if missing:
        raise KeyError(f"generalization-gated metrics missing columns: {sorted(missing)}")

    data = metrics.copy()
    data[auc_col] = pd.to_numeric(data[auc_col], errors="coerce")
    if or10_col in data.columns:
        data[or10_col] = pd.to_numeric(data[or10_col], errors="coerce")

    rows = []
    for candidate, group in data.groupby(candidate_col, sort=True):
        auc_values = group[auc_col][np.isfinite(group[auc_col])]
        mean_auc = float(auc_values.mean()) if len(auc_values) else float("nan")
        auc_sem = (
            float(auc_values.std(ddof=1) / np.sqrt(len(auc_values)))
            if len(auc_values) >= 2
            else 0.0 if len(auc_values) == 1 else float("nan")
        )
        or10_values = group[or10_col][np.isfinite(group[or10_col])] if or10_col in group else pd.Series(dtype=float)
        rows.append(
            {
                candidate_col: str(candidate),
                "mean_inner_auc": mean_auc,
                "sem_inner_auc": auc_sem,
                "mean_inner_or10": float(or10_values.mean()) if len(or10_values) else float("nan"),
                "n_auc_folds": int(len(auc_values)),
            }
        )
    gate = pd.DataFrame(rows)
    finite_auc = gate.loc[np.isfinite(gate["mean_inner_auc"])].copy()
    if finite_auc.empty:
        raise ValueError("no candidate has finite independent-transfer AUC")
    best_idx = finite_auc["mean_inner_auc"].idxmax()
    best_auc = float(gate.loc[best_idx, "mean_inner_auc"])
    best_sem = float(gate.loc[best_idx, "sem_inner_auc"])
    if not np.isfinite(best_sem):
        best_sem = 0.0
    auc_tolerance = max(float(minimum_auc_tolerance), float(auc_sem_multiplier) * best_sem)
    gate["auc_gate_threshold"] = best_auc - auc_tolerance
    gate["passes_auc_gate"] = np.isfinite(gate["mean_inner_auc"]) & (
        gate["mean_inner_auc"] >= best_auc - auc_tolerance - 1e-12
    )
    if max_mean_or10 is None:
        gate["passes_or10_gate"] = True
    else:
        cap = float(max_mean_or10)
        if not 0 <= cap <= 1:
            raise ValueError("max_mean_or10 must lie in [0, 1]")
        gate["passes_or10_gate"] = np.isfinite(gate["mean_inner_or10"]) & (gate["mean_inner_or10"] <= cap)
    gate["eligible_generalization"] = gate["passes_auc_gate"] & gate["passes_or10_gate"]

    eligible = tuple(sorted(str(x) for x in gate.loc[gate["eligible_generalization"], candidate_col]))
    if not eligible:
        raise ValueError("no candidate survives the independent-generalization gate")
    subset = data.loc[data[candidate_col].astype(str).isin(eligible)].copy()
    recovery = select_niche_recovery_protocol(
        subset,
        candidate_col=candidate_col,
        fold_col=fold_col,
        complexity_col=complexity_col,
        metric_columns=metric_columns,
    )
    gate["selected_after_recovery"] = gate[candidate_col].astype(str).eq(recovery.candidate)
    gate = gate.sort_values(
        ["selected_after_recovery", "eligible_generalization", "mean_inner_auc", candidate_col],
        ascending=[False, False, False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    return GeneralizationGatedNicheRecoverySelection(
        candidate=recovery.candidate,
        eligible_candidates=eligible,
        auc_gate_tolerance=auc_tolerance,
        gate_summary=gate,
        recovery_selection=recovery,
    )
