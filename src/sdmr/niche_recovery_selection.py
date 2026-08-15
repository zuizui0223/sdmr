"""Multi-objective selectors for ecological niche-recovery tuning.

Prediction/model-fit statistics are not the ecological objective. Independent
transfer is used only as an adequacy gate before ecological recovery decides
among candidates that generalize above chance. This prevents the gate itself
from becoming a disguised best-AUC selector.
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
    auc_gate_floor: float
    chance_auc: float
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
    chance_auc: float = 0.50,
    minimum_auc_margin: float = 0.01,
    auc_sem_multiplier: float = 1.0,
    max_mean_or10: float | None = None,
    complexity_col: str | None = "n_predictors",
    metric_columns: Sequence[str] = tuple(RECOVERY_DIRECTIONS),
) -> GeneralizationGatedNicheRecoverySelection:
    """Require minimally credible independent transfer, then optimize ecology.

    AUC is used only as an adequacy test, not as a relative-to-best optimizer.
    A candidate passes when:

    1. its mean inner AUC is at least ``chance_auc + minimum_auc_margin``; and
    2. its lower evidence bound ``mean - auc_sem_multiplier * SEM`` is at least
       ``chance_auc``.

    For presence-background rank, 0.5 has a direct random-ranking meaning. The
    default +0.01 margin is an operational development guardrail and should be
    sensitivity-tested rather than interpreted as a biological effect size.

    ``max_mean_or10`` remains an optional severe-omission guardrail. No universal
    biological OR10 cutoff is assumed.
    """

    chance_auc = float(chance_auc)
    minimum_auc_margin = float(minimum_auc_margin)
    auc_sem_multiplier = float(auc_sem_multiplier)
    if not 0 <= chance_auc < 1:
        raise ValueError("chance_auc must lie in [0, 1)")
    if minimum_auc_margin < 0 or chance_auc + minimum_auc_margin > 1:
        raise ValueError("minimum_auc_margin must keep the AUC floor in [0, 1]")
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
    if not np.isfinite(gate["mean_inner_auc"]).any():
        raise ValueError("no candidate has finite independent-transfer AUC")

    auc_floor = chance_auc + minimum_auc_margin
    gate["auc_gate_floor"] = auc_floor
    gate["auc_lower_evidence_bound"] = gate["mean_inner_auc"] - auc_sem_multiplier * gate["sem_inner_auc"]
    gate["passes_auc_mean_floor"] = np.isfinite(gate["mean_inner_auc"]) & (
        gate["mean_inner_auc"] >= auc_floor - 1e-12
    )
    gate["passes_auc_chance_bound"] = np.isfinite(gate["auc_lower_evidence_bound"]) & (
        gate["auc_lower_evidence_bound"] >= chance_auc - 1e-12
    )
    gate["passes_auc_gate"] = gate["passes_auc_mean_floor"] & gate["passes_auc_chance_bound"]

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
        raise ValueError("no candidate survives the independent-generalization adequacy gate")
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
        auc_gate_floor=auc_floor,
        chance_auc=chance_auc,
        gate_summary=gate,
        recovery_selection=recovery,
    )
