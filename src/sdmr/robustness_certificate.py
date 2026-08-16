"""Structured certificates for Product-A v2 perturbation robustness.

A robust ecological selector is allowed to abstain. In particular, a candidate
library can contain models that are each adequate in most perturbations while no
single model satisfies the absolute prediction-adequacy contract in *every*
predeclared perturbation. Relaxing thresholds to manufacture a winner would turn
an informative cross-perturbation incompatibility into hidden tuning.

This module converts the existing perturbation evidence into an auditable
certificate. It does not change selection thresholds or choose a fallback model.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .niche_recovery_perturbation import (
    PerturbationRobustNicheRecoverySelection,
    _auc_adequacy,
)


@dataclass(frozen=True)
class PerturbationRobustnessCertificate:
    """Outcome and diagnostics for one perturbation-robust selection attempt."""

    status: str
    selected_candidate: str | None
    selection_error: str | None
    n_perturbations: int
    max_passed_perturbations: int
    fully_adequate_candidates: tuple[str, ...]
    near_complete_candidates: tuple[str, ...]
    critical_perturbations: tuple[str, ...]
    candidate_adequacy: pd.DataFrame
    perturbation_adequacy: pd.DataFrame


def build_perturbation_robustness_certificate(
    metrics: pd.DataFrame,
    *,
    selection: PerturbationRobustNicheRecoverySelection | None = None,
    selection_error: str | None = None,
    candidate_col: str = "candidate",
    perturbation_col: str = "perturbation",
    auc_col: str = "presence_rank",
    chance_auc: float = 0.50,
    minimum_auc_margin: float = 0.01,
    auc_sem_multiplier: float = 1.0,
) -> PerturbationRobustnessCertificate:
    """Describe selection or principled abstention without changing the gate.

    ``critical_perturbations`` is the union of failed perturbations among the
    candidate(s) that pass the largest number of perturbations. This identifies
    the smallest currently relevant conflict set without pretending that one
    perturbation must be solely responsible for an empty global intersection.
    """

    required = {candidate_col, perturbation_col, auc_col}
    missing = required - set(metrics.columns)
    if missing:
        raise KeyError(f"robustness-certificate metrics missing columns: {sorted(missing)}")
    if metrics.empty:
        raise ValueError("no perturbation metrics supplied")

    data = metrics.copy()
    data[candidate_col] = data[candidate_col].astype(str)
    data[perturbation_col] = data[perturbation_col].astype(str)
    perturbations = tuple(sorted(data[perturbation_col].unique()))
    adequacy = _auc_adequacy(
        data,
        candidate_col=candidate_col,
        perturbation_col=perturbation_col,
        auc_col=auc_col,
        chance_auc=float(chance_auc),
        minimum_auc_margin=float(minimum_auc_margin),
        auc_sem_multiplier=float(auc_sem_multiplier),
    )

    candidate_summary = (
        adequacy.groupby(candidate_col, as_index=False)
        .agg(
            n_perturbations=(perturbation_col, "nunique"),
            n_passed_perturbations=("passes_prediction_adequacy", "sum"),
            minimum_mean_auc=("mean_inner_auc", "min"),
            minimum_auc_lower_bound=("auc_lower_evidence_bound", "min"),
        )
        .sort_values(
            ["n_passed_perturbations", "minimum_auc_lower_bound", candidate_col],
            ascending=[False, False, True],
            kind="mergesort",
        )
        .reset_index(drop=True)
    )
    candidate_summary["complete_coverage"] = candidate_summary["n_perturbations"].eq(
        len(perturbations)
    )
    candidate_summary["fully_prediction_adequate"] = (
        candidate_summary["complete_coverage"]
        & candidate_summary["n_passed_perturbations"].eq(len(perturbations))
    )

    perturbation_summary = (
        adequacy.groupby(perturbation_col, as_index=False)
        .agg(
            n_candidates=(candidate_col, "nunique"),
            n_passing_candidates=("passes_prediction_adequacy", "sum"),
            best_mean_auc=("mean_inner_auc", "max"),
            best_auc_lower_bound=("auc_lower_evidence_bound", "max"),
        )
        .sort_values(perturbation_col, kind="mergesort")
        .reset_index(drop=True)
    )

    fully = tuple(
        sorted(
            candidate_summary.loc[
                candidate_summary["fully_prediction_adequate"], candidate_col
            ].astype(str)
        )
    )
    max_passed = int(candidate_summary["n_passed_perturbations"].max())
    near = tuple(
        sorted(
            candidate_summary.loc[
                candidate_summary["n_passed_perturbations"].eq(max_passed), candidate_col
            ].astype(str)
        )
    )
    near_failures = adequacy.loc[
        adequacy[candidate_col].isin(near)
        & ~adequacy["passes_prediction_adequacy"].astype(bool)
    ]
    critical = tuple(sorted(near_failures[perturbation_col].astype(str).unique()))

    if selection is not None:
        status = "selected"
        selected = str(selection.candidate)
    elif not fully:
        status = "abstain_cross_perturbation_prediction_incompatibility"
        selected = None
    else:
        # Prediction adequacy permits at least one common candidate, so an
        # ecological-rank/selection failure should remain distinct from an AUC
        # incompatibility rather than being mislabeled.
        status = "abstain_ecological_selection_unavailable"
        selected = None

    candidate_summary["near_complete"] = candidate_summary[candidate_col].isin(near)
    candidate_summary["selected"] = candidate_summary[candidate_col].eq(selected)
    perturbation_summary["critical_for_near_complete_candidates"] = (
        perturbation_summary[perturbation_col].isin(critical)
    )

    return PerturbationRobustnessCertificate(
        status=status,
        selected_candidate=selected,
        selection_error=selection_error,
        n_perturbations=len(perturbations),
        max_passed_perturbations=max_passed,
        fully_adequate_candidates=fully,
        near_complete_candidates=near,
        critical_perturbations=critical,
        candidate_adequacy=candidate_summary,
        perturbation_adequacy=perturbation_summary,
    )
