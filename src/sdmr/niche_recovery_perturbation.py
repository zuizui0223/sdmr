"""Exogenous-perturbation robustness for Product-A v2 niche recovery.

Robustness here means that one model-building procedure continues to recover the
same biological target when scientifically meaningful nuisance conditions change
(e.g. sampling effort, plausible background/M scope, or transfer domain).

The selector deliberately does *not* pool raw ecological metric values across
perturbations. Absolute overlap/centroid/breadth/tail scales can change when the
available environment changes, so candidates are ranked within each predeclared
perturbation and only those ranks are aggregated across perturbations.

Prediction adequacy and ecological robustness are also kept distinct. By default,
all perturbations are hard prediction gates for backwards compatibility. Callers
may instead declare which perturbation *types* are hard prediction gates. This is
useful when a transfer-domain perturbation is intended to test ecological
conclusion stability rather than to require successful record-discrimination
transfer. Such diagnostic perturbations remain in ecological ranking and are never
silently dropped; they simply do not determine candidate admissibility via AUC.

Stage order
-----------
1. Require independent prediction adequacy in every declared hard-gate
   perturbation.
2. Rank eligible candidates within *all* perturbations separately on each
   ecological recovery dimension.
3. For each candidate and ecological dimension retain its worst perturbation rank
   and its mean perturbation rank.
4. Pareto-filter candidates on worst perturbation ranks.
5. Apply minimax to the remaining worst-rank profile; use mean rank, then
   across-perturbation mean ranks, then parsimony only as tie-breaks.

No weighted super-score combines AUC with ecology or combines ecological axes.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

import numpy as np
import pandas as pd

from .niche_recovery_selection import RECOVERY_DIRECTIONS


@dataclass(frozen=True)
class PerturbationRobustNicheRecoverySelection:
    candidate: str
    eligible_candidates: tuple[str, ...]
    perturbations: tuple[str, ...]
    worst_rank_pareto_front: tuple[str, ...]
    adequacy_summary: pd.DataFrame
    perturbation_ranks: pd.DataFrame
    candidate_summary: pd.DataFrame


def _auc_adequacy(
    metrics: pd.DataFrame,
    *,
    candidate_col: str,
    perturbation_col: str,
    auc_col: str,
    chance_auc: float,
    minimum_auc_margin: float,
    auc_sem_multiplier: float,
) -> pd.DataFrame:
    rows: list[dict[str, float | int | str | bool]] = []
    floor = float(chance_auc + minimum_auc_margin)
    for (candidate, perturbation), group in metrics.groupby(
        [candidate_col, perturbation_col], sort=True
    ):
        values = pd.to_numeric(group[auc_col], errors="coerce")
        values = values[np.isfinite(values)]
        mean_auc = float(values.mean()) if len(values) else float("nan")
        sem = (
            float(values.std(ddof=1) / np.sqrt(len(values)))
            if len(values) >= 2
            else 0.0 if len(values) == 1 else float("nan")
        )
        lower = (
            mean_auc - float(auc_sem_multiplier) * sem
            if np.isfinite(mean_auc) and np.isfinite(sem)
            else float("nan")
        )
        passes = bool(
            np.isfinite(mean_auc)
            and np.isfinite(lower)
            and mean_auc >= floor - 1e-12
            and lower >= float(chance_auc) - 1e-12
        )
        rows.append(
            {
                candidate_col: str(candidate),
                perturbation_col: str(perturbation),
                "mean_inner_auc": mean_auc,
                "sem_inner_auc": sem,
                "auc_lower_evidence_bound": lower,
                "auc_gate_floor": floor,
                "chance_auc": float(chance_auc),
                "n_auc_folds": int(len(values)),
                "passes_prediction_adequacy": passes,
            }
        )
    return pd.DataFrame(rows)


def _dominates_min(a: pd.Series, b: pd.Series, columns: Sequence[str]) -> bool:
    strict = False
    for column in columns:
        av = float(a[column])
        bv = float(b[column])
        if not np.isfinite(av) or not np.isfinite(bv):
            return False
        if av > bv + 1e-12:
            return False
        strict |= av < bv - 1e-12
    return bool(strict)


def select_perturbation_robust_niche_recovery_protocol(
    metrics: pd.DataFrame,
    *,
    candidate_col: str = "candidate",
    perturbation_col: str = "perturbation",
    perturbation_type_col: str = "perturbation_type",
    fold_col: str = "fold",
    auc_col: str = "presence_rank",
    complexity_col: str | None = "n_predictors",
    metric_columns: Sequence[str] = tuple(RECOVERY_DIRECTIONS),
    chance_auc: float = 0.50,
    minimum_auc_margin: float = 0.01,
    auc_sem_multiplier: float = 1.0,
    prediction_adequacy_perturbation_types: Sequence[str] | None = None,
) -> PerturbationRobustNicheRecoverySelection:
    """Select a procedure robust across predeclared exogenous perturbations.

    ``prediction_adequacy_perturbation_types=None`` preserves the historical
    behavior: every perturbation is a hard AUC adequacy gate. When a non-empty
    sequence is supplied, only perturbations whose ``perturbation_type`` belongs
    to that set determine prediction eligibility. Ecological recovery ranks are
    still computed across every perturbation in ``metrics``.
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

    metric_columns = tuple(str(x) for x in metric_columns)
    unknown = [x for x in metric_columns if x not in RECOVERY_DIRECTIONS]
    if unknown:
        raise ValueError(f"unknown niche-recovery metrics: {unknown}")
    required = {candidate_col, perturbation_col, fold_col, auc_col, *metric_columns}
    if prediction_adequacy_perturbation_types is not None:
        required.add(perturbation_type_col)
    missing = required - set(metrics.columns)
    if missing:
        raise KeyError(f"perturbation-robust metrics missing columns: {sorted(missing)}")
    if metrics.empty:
        raise ValueError("no perturbation metrics supplied")

    data = metrics.copy()
    data[candidate_col] = data[candidate_col].astype(str)
    data[perturbation_col] = data[perturbation_col].astype(str)
    perturbations = tuple(sorted(data[perturbation_col].unique().tolist()))
    if len(perturbations) < 2:
        raise ValueError("at least two exogenous perturbations are required")

    if prediction_adequacy_perturbation_types is None:
        hard_gate_by_perturbation = pd.DataFrame(
            {
                perturbation_col: list(perturbations),
                "hard_prediction_gate": True,
            }
        )
    else:
        hard_types = tuple(
            dict.fromkeys(str(x) for x in prediction_adequacy_perturbation_types)
        )
        if not hard_types:
            raise ValueError(
                "prediction_adequacy_perturbation_types must be non-empty when supplied"
            )
        type_map = data[[perturbation_col, perturbation_type_col]].copy()
        type_map[perturbation_type_col] = type_map[perturbation_type_col].astype(str)
        unique_type_counts = type_map.groupby(perturbation_col)[perturbation_type_col].nunique()
        if (unique_type_counts > 1).any():
            bad = unique_type_counts.loc[unique_type_counts > 1].index.tolist()
            raise ValueError(
                "each perturbation must map to one perturbation type; "
                f"violations: {bad}"
            )
        type_map = type_map.drop_duplicates(subset=[perturbation_col])
        type_map["hard_prediction_gate"] = type_map[perturbation_type_col].isin(
            set(hard_types)
        )
        hard_gate_by_perturbation = type_map[
            [perturbation_col, "hard_prediction_gate"]
        ].copy()
        if not hard_gate_by_perturbation["hard_prediction_gate"].any():
            raise ValueError(
                "no perturbation belongs to the requested prediction-adequacy types"
            )

    hard_perturbations = tuple(
        sorted(
            hard_gate_by_perturbation.loc[
                hard_gate_by_perturbation["hard_prediction_gate"], perturbation_col
            ].astype(str)
        )
    )

    adequacy = _auc_adequacy(
        data,
        candidate_col=candidate_col,
        perturbation_col=perturbation_col,
        auc_col=auc_col,
        chance_auc=chance_auc,
        minimum_auc_margin=minimum_auc_margin,
        auc_sem_multiplier=auc_sem_multiplier,
    )
    adequacy = adequacy.merge(
        hard_gate_by_perturbation,
        on=perturbation_col,
        how="left",
        validate="many_to_one",
    )
    hard_adequacy = adequacy.loc[adequacy["hard_prediction_gate"]].copy()
    coverage = (
        hard_adequacy.groupby(candidate_col, as_index=False)
        .agg(
            n_hard_gate_perturbations=(perturbation_col, "nunique"),
            all_hard_gate_prediction_adequate=("passes_prediction_adequacy", "all"),
        )
    )
    coverage["complete_hard_gate_coverage"] = coverage[
        "n_hard_gate_perturbations"
    ].eq(len(hard_perturbations))
    coverage["eligible_hard_gate_perturbations"] = (
        coverage["complete_hard_gate_coverage"]
        & coverage["all_hard_gate_prediction_adequate"]
    )
    # Compatibility aliases for downstream diagnostics written before scoped
    # prediction gates existed. They now mean eligibility across the declared
    # hard-gate perturbations rather than necessarily across every perturbation.
    coverage["n_perturbations"] = coverage["n_hard_gate_perturbations"]
    coverage["all_prediction_adequate"] = coverage[
        "all_hard_gate_prediction_adequate"
    ]
    coverage["complete_perturbation_coverage"] = coverage[
        "complete_hard_gate_coverage"
    ]
    coverage["eligible_all_perturbations"] = coverage[
        "eligible_hard_gate_perturbations"
    ]
    eligible = tuple(
        sorted(
            coverage.loc[
                coverage["eligible_hard_gate_perturbations"], candidate_col
            ].astype(str)
        )
    )
    if not eligible:
        raise ValueError(
            "no candidate passes prediction adequacy in every hard-gate perturbation"
        )

    data = data.loc[data[candidate_col].isin(eligible)].copy()
    aggregate_spec = {metric: (metric, "mean") for metric in metric_columns}
    grouped = data.groupby([candidate_col, perturbation_col], as_index=False).agg(
        **aggregate_spec
    )
    for metric in metric_columns:
        grouped[metric] = pd.to_numeric(grouped[metric], errors="coerce")
        ascending = RECOVERY_DIRECTIONS[metric] == "min"
        grouped[f"rank__{metric}"] = grouped.groupby(perturbation_col)[metric].rank(
            method="min", ascending=ascending
        )

    rank_cols = [f"rank__{metric}" for metric in metric_columns]
    complete = grouped.groupby(candidate_col)[perturbation_col].nunique().eq(
        len(perturbations)
    )
    finite_rows = grouped[rank_cols].apply(
        lambda col: np.isfinite(pd.to_numeric(col, errors="coerce"))
    ).all(axis=1)
    finite_by_candidate = finite_rows.groupby(grouped[candidate_col]).all()
    complete_candidates = tuple(
        sorted(
            candidate
            for candidate in eligible
            if bool(complete.get(candidate, False))
            and bool(finite_by_candidate.get(candidate, False))
        )
    )
    if not complete_candidates:
        raise ValueError(
            "no candidate has complete finite ecological recovery ranks across perturbations"
        )
    grouped = grouped.loc[grouped[candidate_col].isin(complete_candidates)].copy()

    rows = []
    for candidate, group in grouped.groupby(candidate_col, sort=True):
        row: dict[str, float | str] = {candidate_col: str(candidate)}
        for metric in metric_columns:
            ranks = group[f"rank__{metric}"].to_numpy(float)
            row[f"worst_perturbation_rank__{metric}"] = float(np.max(ranks))
            row[f"mean_perturbation_rank__{metric}"] = float(np.mean(ranks))
        if complexity_col and complexity_col in data.columns:
            complexity = pd.to_numeric(
                data.loc[data[candidate_col].eq(candidate), complexity_col],
                errors="coerce",
            )
            complexity = complexity[np.isfinite(complexity)]
            row["mean_complexity"] = (
                float(complexity.mean()) if len(complexity) else float("nan")
            )
        else:
            row["mean_complexity"] = float("nan")
        rows.append(row)
    summary = pd.DataFrame(rows)

    worst_cols = [f"worst_perturbation_rank__{metric}" for metric in metric_columns]
    mean_cols = [f"mean_perturbation_rank__{metric}" for metric in metric_columns]
    indices = list(summary.index)
    frontier = []
    for idx in indices:
        dominated = any(
            other != idx
            and _dominates_min(summary.loc[other], summary.loc[idx], worst_cols)
            for other in indices
        )
        if not dominated:
            frontier.append(idx)
    summary["worst_rank_pareto_front"] = summary.index.isin(frontier)

    finalist = summary.loc[frontier].copy()
    finalist["worst_rank_minimax"] = finalist[worst_cols].max(axis=1)
    finalist["worst_rank_mean"] = finalist[worst_cols].mean(axis=1)
    finalist["mean_rank_minimax"] = finalist[mean_cols].max(axis=1)
    finalist["mean_rank_mean"] = finalist[mean_cols].mean(axis=1)
    finalist = finalist.sort_values(
        [
            "worst_rank_minimax",
            "worst_rank_mean",
            "mean_rank_minimax",
            "mean_rank_mean",
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
            "worst_rank_minimax",
            "worst_rank_mean",
            "mean_rank_minimax",
            "mean_rank_mean",
        ]
    ]
    summary = summary.merge(rank_payload, on=candidate_col, how="left")
    summary["selected"] = summary[candidate_col].eq(winner)
    summary = summary.sort_values(
        [
            "selected",
            "worst_rank_pareto_front",
            "worst_rank_minimax",
            "mean_rank_mean",
            candidate_col,
        ],
        ascending=[False, False, True, True, True],
        na_position="last",
        kind="mergesort",
    ).reset_index(drop=True)

    adequacy = adequacy.merge(coverage, on=candidate_col, how="left")
    return PerturbationRobustNicheRecoverySelection(
        candidate=winner,
        eligible_candidates=complete_candidates,
        perturbations=perturbations,
        worst_rank_pareto_front=tuple(
            sorted(
                str(x)
                for x in summary.loc[
                    summary["worst_rank_pareto_front"], candidate_col
                ]
            )
        ),
        adequacy_summary=adequacy,
        perturbation_ranks=grouped.sort_values(
            [perturbation_col, candidate_col]
        ).reset_index(drop=True),
        candidate_summary=summary,
    )
