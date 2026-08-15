"""Known-truth selector benchmark for Product-A v2.

Candidate procedures are selected using ordinary predictive criteria or ecological
recovery rules, then every selected procedure is evaluated against the *known
generating niche*. Hidden truth never participates in candidate selection.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping

import numpy as np
import pandas as pd

from .known_truth import KnownTruthSimulation, known_truth_niche_recovery_profile
from .model import fit_relative_suitability_model, score_relative_suitability
from .niche_recovery_cv import RecoveryCandidate, cross_validated_niche_recovery
from .niche_recovery_selection import (
    select_generalization_gated_niche_recovery_protocol,
    select_niche_recovery_protocol,
)
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
    gated_auc_minimum_tolerance: float = 0.01,
    gated_auc_sem_multiplier: float = 1.0,
    gated_max_mean_or10: float | None = None,
) -> KnownTruthSelectorBenchmark:
    """Select candidates without truth, then score the winners against truth.

    Selectors:

    - ``inner_auc``: maximum mean inner presence-background AUC-equivalent rank;
    - ``inner_cbi``: maximum mean inner continuous Boyce index;
    - ``inner_or10``: minimum mean independent-test OR10;
    - ``niche_recovery``: ecological Pareto + minimax without a prediction gate;
    - ``gated_niche_recovery``: retain predictively credible candidates first,
      then use the same ecological Pareto + minimax rule.

    AICc is intentionally not manufactured for the current class-balanced,
    penalized logistic family; a valid likelihood-backed comparator belongs in a
    separate model family/criterion implementation.
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
    gated_selection = select_generalization_gated_niche_recovery_protocol(
        fold_metrics,
        minimum_auc_tolerance=gated_auc_minimum_tolerance,
        auc_sem_multiplier=gated_auc_sem_multiplier,
        max_mean_or10=gated_max_mean_or10,
    )
    winners = {
        "inner_auc": _metric_winner(fold_metrics, "presence_rank", ascending=False),
        "inner_cbi": _metric_winner(fold_metrics, "continuous_boyce", ascending=False),
        "inner_or10": _metric_winner(fold_metrics, "or10", ascending=True),
        "niche_recovery": recovery_selection.candidate,
        "gated_niche_recovery": gated_selection.candidate,
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
                "gated_auc_tolerance": (
                    gated_selection.auc_gate_tolerance if selector == "gated_niche_recovery" else float("nan")
                ),
                "gated_eligible_candidates": (
                    ",".join(gated_selection.eligible_candidates) if selector == "gated_niche_recovery" else ""
                ),
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


def summarize_selector_disagreement(
    result: KnownTruthSelectorBenchmark,
    *,
    reference_selector: str = "gated_niche_recovery",
) -> pd.DataFrame:
    """Audit selector disagreement and hidden-truth consequences after selection.

    No truth metric is used to choose a candidate. The returned truth gains are
    post-selection diagnostics only, and they remain separate by ecological axis
    instead of being collapsed into a weighted score.
    """

    choices = result.selector_choices.copy()
    truth = result.truth_evaluation.copy()
    required_choices = {"selector", "candidate"}
    required_truth = {
        "selector",
        "candidate",
        "niche_overlap_schoener_d_pc12",
        "centroid_distance",
        "breadth_log_sd_error",
        "quantile_profile_error",
    }
    if not required_choices <= set(choices.columns):
        raise KeyError(f"selector_choices missing columns: {sorted(required_choices - set(choices.columns))}")
    if not required_truth <= set(truth.columns):
        raise KeyError(f"truth_evaluation missing columns: {sorted(required_truth - set(truth.columns))}")

    reference_choice = choices.loc[choices["selector"].astype(str).eq(reference_selector)]
    reference_truth = truth.loc[truth["selector"].astype(str).eq(reference_selector)]
    if len(reference_choice) != 1 or len(reference_truth) != 1:
        raise ValueError(f"benchmark must contain exactly one {reference_selector} selector result")
    reference_candidate = str(reference_choice.iloc[0]["candidate"])
    ref = reference_truth.iloc[0]

    rows = []
    for _, choice in choices.iterrows():
        selector = str(choice["selector"])
        if selector == reference_selector:
            continue
        candidate = str(choice["candidate"])
        other_truth = truth.loc[truth["selector"].astype(str).eq(selector)]
        if len(other_truth) != 1:
            raise ValueError(f"truth_evaluation must contain exactly one row for {selector}")
        other = other_truth.iloc[0]

        overlap_gain = float(ref["niche_overlap_schoener_d_pc12"] - other["niche_overlap_schoener_d_pc12"])
        centroid_gain = float(other["centroid_distance"] - ref["centroid_distance"])
        breadth_gain = float(other["breadth_log_sd_error"] - ref["breadth_log_sd_error"])
        quantile_gain = float(other["quantile_profile_error"] - ref["quantile_profile_error"])
        gains = np.array([overlap_gain, centroid_gain, breadth_gain, quantile_gain], dtype=float)
        finite = np.isfinite(gains)
        pareto_better = bool(
            finite.all()
            and np.all(gains >= -1e-12)
            and np.any(gains > 1e-12)
        )
        rows.append(
            {
                "selector": selector,
                "selector_candidate": candidate,
                "reference_selector": reference_selector,
                "reference_candidate": reference_candidate,
                "candidate_disagrees": candidate != reference_candidate,
                "truth_overlap_gain": overlap_gain,
                "truth_centroid_error_reduction": centroid_gain,
                "truth_breadth_error_reduction": breadth_gain,
                "truth_quantile_error_reduction": quantile_gain,
                "reference_truth_pareto_better": pareto_better,
            }
        )
    return pd.DataFrame(rows)
