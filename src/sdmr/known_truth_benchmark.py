"""Known-truth selector benchmark for Product-A v2.

Candidate procedures are selected using ordinary predictive criteria or the
multi-objective niche-recovery rule, then every selected procedure is evaluated
against the *known generating niche*. This separates 'won its validation metric'
from 'actually recovered the biological target'.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping

import numpy as np
import pandas as pd

from .known_truth import KnownTruthSimulation, known_truth_niche_recovery_profile
from .model import fit_relative_suitability_model, score_relative_suitability
from .niche_recovery_cv import RecoveryCandidate, cross_validated_niche_recovery
from .niche_recovery_selection import select_niche_recovery_protocol
from .validation import make_spatial_partition


@dataclass
class KnownTruthSelectorBenchmark:
    fold_metrics: pd.DataFrame
    selector_choices: pd.DataFrame
    truth_evaluation: pd.DataFrame


def _metric_winner(
    metrics: pd.DataFrame,
    metric: str,
    *,
    ascending: bool,
) -> str:
    summary = (
        metrics.groupby("candidate", as_index=False)
        .agg(selector_score=(metric, "mean"), n_predictors=("n_predictors", "mean"))
    )
    summary = summary.loc[np.isfinite(pd.to_numeric(summary["selector_score"], errors="coerce"))].copy()
    if summary.empty:
        raise ValueError(f"no finite {metric} values for selector")
    summary = summary.sort_values(
        ["selector_score", "n_predictors", "candidate"],
        ascending=[ascending, True, True],
        kind="mergesort",
    )
    return str(summary.iloc[0]["candidate"])


def benchmark_selectors_against_known_truth(
    simulation: KnownTruthSimulation,
    candidates: Mapping[str, RecoveryCandidate],
    *,
    n_spatial_blocks: int = 8,
    inner_folds: int = 4,
    random_state: int = 42,
) -> KnownTruthSelectorBenchmark:
    """Select candidates without truth, then score the winners against truth.

    The selectors are:

    - ``inner_auc``: maximum mean inner presence-background AUC-equivalent rank;
    - ``inner_cbi``: maximum mean inner continuous Boyce index;
    - ``niche_recovery``: Pareto + minimax ecological recovery profile.

    OR10 is retained in ``fold_metrics`` as an overfitting/omission diagnostic.
    AICc is intentionally not manufactured for the current class-balanced,
    penalized logistic family; a valid likelihood-backed comparator should be
    added separately.
    """

    occurrence = simulation.occurrences.reset_index(drop=True)
    background = simulation.target_group.reset_index(drop=True)
    part = make_spatial_partition(
        occurrence["longitude"].to_numpy(float),
        occurrence["latitude"].to_numpy(float),
        background["longitude"].to_numpy(float),
        background["latitude"].to_numpy(float),
        n_blocks=n_spatial_blocks,
        holdout_fraction=0.20,
        random_state=random_state,
    )

    frames = []
    for name in sorted(candidates):
        candidate = candidates[name]
        metrics = cross_validated_niche_recovery(
            occurrence,
            background,
            part.presence_blocks,
            part.background_blocks,
            candidate.predictors,
            simulation.audit_predictors,
            n_splits=inner_folds,
            model_spec=candidate.model_spec,
        )
        if metrics.empty:
            continue
        metrics["candidate"] = str(name)
        metrics["n_predictors"] = len(candidate.predictors)
        metrics["model"] = candidate.model_spec.label
        frames.append(metrics)
    if not frames:
        raise ValueError("no candidate produced known-truth CV metrics")
    fold_metrics = pd.concat(frames, ignore_index=True)

    recovery_selection = select_niche_recovery_protocol(fold_metrics)
    winners = {
        "inner_auc": _metric_winner(fold_metrics, "presence_rank", ascending=False),
        "inner_cbi": _metric_winner(fold_metrics, "continuous_boyce", ascending=False),
        "niche_recovery": recovery_selection.candidate,
    }

    choices = []
    truth_rows = []
    environment = simulation.environment
    truth = environment[simulation.true_suitability_column].to_numpy(float)
    for selector, candidate_name in winners.items():
        candidate = candidates[candidate_name]
        model = fit_relative_suitability_model(
            occurrence,
            background,
            candidate.predictors,
            model_spec=candidate.model_spec,
        )
        prediction = score_relative_suitability(model, environment, candidate.predictors)
        profile = known_truth_niche_recovery_profile(
            environment,
            prediction,
            truth,
            simulation.audit_predictors,
        )
        candidate_folds = fold_metrics.loc[fold_metrics["candidate"].astype(str) == candidate_name]
        choices.append(
            {
                "selector": selector,
                "candidate": candidate_name,
                "model": candidate.model_spec.label,
                "n_predictors": len(candidate.predictors),
                "mean_inner_auc": float(candidate_folds["presence_rank"].mean()),
                "mean_inner_cbi": float(candidate_folds["continuous_boyce"].mean()),
                "mean_inner_or10": float(candidate_folds["or10"].mean()),
            }
        )
        truth_rows.append(
            {
                "selector": selector,
                "candidate": candidate_name,
                **profile.as_dict(),
            }
        )

    return KnownTruthSelectorBenchmark(
        fold_metrics=fold_metrics,
        selector_choices=pd.DataFrame(choices),
        truth_evaluation=pd.DataFrame(truth_rows),
    )
