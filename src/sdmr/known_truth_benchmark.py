"""Known-truth selector benchmark for Product-A v2.

Candidate procedures are selected using ordinary predictive criteria or ecological
recovery rules, then every selected procedure is evaluated against the *known
generating niche*. Hidden truth never participates in candidate selection.

Explicit observation-process predictors remain available to the fitted record
model, but ecological recovery and hidden ecological truth are evaluated from a
separate observation-marginalized suitability surface.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping

import numpy as np
import pandas as pd

from .known_truth import KnownTruthSimulation, known_truth_niche_recovery_profile
from .known_truth_response import (
    infer_response_predictors,
    infer_true_processes,
    known_truth_process_profile,
    known_truth_response_profile,
)
from .model import (
    fit_relative_suitability_model,
    score_ecological_suitability,
)
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


def _metric_winner(metrics: pd.DataFrame, metric: str, *, ascending: bool) -> str:
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
    gated_chance_auc: float = 0.50,
    gated_minimum_auc_margin: float = 0.01,
    gated_auc_sem_multiplier: float = 1.0,
    gated_max_mean_or10: float | None = None,
) -> KnownTruthSelectorBenchmark:
    """Select without truth, then score ecological products against truth.

    Conventional selectors use full observation-aware record predictions. The
    ecological selectors use observation-marginalized suitability for their niche
    recovery profile. After a selector chooses a candidate, its final ecological
    product is also marginalized before hidden-truth scoring.
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
            observation_predictors=candidate.observation_predictors,
            n_splits=inner_folds,
            model_spec=candidate.model_spec,
        )
        if metrics.empty:
            continue
        metrics["candidate"] = str(name)
        metrics["n_predictors"] = len(candidate.predictors)
        metrics["n_ecological_predictors"] = len(
            [p for p in candidate.predictors if p not in candidate.observation_predictors]
        )
        metrics["n_observation_predictors_declared"] = len(candidate.observation_predictors)
        metrics["model"] = candidate.model_spec.label
        frames.append(metrics)
    if not frames:
        raise ValueError("no candidate produced known-truth CV metrics")
    fold_metrics = pd.concat(frames, ignore_index=True)

    recovery_selection = select_niche_recovery_protocol(fold_metrics)
    gated_selection = select_generalization_gated_niche_recovery_protocol(
        fold_metrics,
        chance_auc=gated_chance_auc,
        minimum_auc_margin=gated_minimum_auc_margin,
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
    response_predictors = infer_response_predictors(environment)
    true_processes = infer_true_processes(environment)
    for selector, candidate_name in winners.items():
        candidate = candidates[candidate_name]
        model = fit_relative_suitability_model(
            occurrence,
            background,
            candidate.predictors,
            model_spec=candidate.model_spec,
        )
        ecological_prediction = score_ecological_suitability(
            model,
            environment,
            candidate.predictors,
            observation_predictors=candidate.observation_predictors,
            observation_reference=background,
        )
        niche_profile = known_truth_niche_recovery_profile(
            environment,
            ecological_prediction,
            truth,
            simulation.audit_predictors,
        )
        response_profile = known_truth_response_profile(
            environment,
            ecological_prediction,
            truth,
            response_predictors,
        )
        ecological_predictors = tuple(
            p for p in candidate.predictors if p not in candidate.observation_predictors
        )
        process_profile = known_truth_process_profile(ecological_predictors, true_processes)
        candidate_folds = fold_metrics.loc[fold_metrics["candidate"].astype(str) == candidate_name]
        choices.append(
            {
                "selector": selector,
                "candidate": candidate_name,
                "model": candidate.model_spec.label,
                "n_predictors": len(candidate.predictors),
                "n_ecological_predictors": len(ecological_predictors),
                "n_observation_predictors": len(candidate.observation_predictors),
                "observation_predictors": ",".join(candidate.observation_predictors),
                "mean_inner_auc": float(candidate_folds["presence_rank"].mean()),
                "mean_inner_cbi": float(candidate_folds["continuous_boyce"].mean()),
                "mean_inner_or10": float(candidate_folds["or10"].mean()),
                "gated_auc_floor": (
                    gated_selection.auc_gate_floor if selector == "gated_niche_recovery" else float("nan")
                ),
                "gated_chance_auc": (
                    gated_selection.chance_auc if selector == "gated_niche_recovery" else float("nan")
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
                **niche_profile.as_dict(),
                **response_profile.as_dict(),
                **process_profile.as_dict(),
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
    """Audit selector disagreement and hidden-truth consequences after selection."""

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
        "truth_surface_rank",
        "truth_surface_nrmse",
        "response_curve_error",
        "optimum_error",
        "lower_limit_error",
        "upper_limit_error",
        "driver_process_f1",
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

        gains = {
            "truth_overlap_gain": float(ref["niche_overlap_schoener_d_pc12"] - other["niche_overlap_schoener_d_pc12"]),
            "truth_centroid_error_reduction": float(other["centroid_distance"] - ref["centroid_distance"]),
            "truth_breadth_error_reduction": float(other["breadth_log_sd_error"] - ref["breadth_log_sd_error"]),
            "truth_quantile_error_reduction": float(other["quantile_profile_error"] - ref["quantile_profile_error"]),
            "truth_surface_rank_gain": float(ref["truth_surface_rank"] - other["truth_surface_rank"]),
            "truth_surface_nrmse_reduction": float(other["truth_surface_nrmse"] - ref["truth_surface_nrmse"]),
            "truth_response_curve_error_reduction": float(other["response_curve_error"] - ref["response_curve_error"]),
            "truth_optimum_error_reduction": float(other["optimum_error"] - ref["optimum_error"]),
            "truth_lower_limit_error_reduction": float(other["lower_limit_error"] - ref["lower_limit_error"]),
            "truth_upper_limit_error_reduction": float(other["upper_limit_error"] - ref["upper_limit_error"]),
            "truth_process_f1_gain": float(ref["driver_process_f1"] - other["driver_process_f1"]),
        }
        gain_values = np.asarray(list(gains.values()), dtype=float)
        pareto_better = bool(
            np.isfinite(gain_values).all()
            and np.all(gain_values >= -1e-12)
            and np.any(gain_values > 1e-12)
        )
        rows.append(
            {
                "selector": selector,
                "selector_candidate": candidate,
                "reference_selector": reference_selector,
                "reference_candidate": reference_candidate,
                "candidate_disagrees": candidate != reference_candidate,
                **gains,
                "reference_truth_pareto_better": pareto_better,
            }
        )
    return pd.DataFrame(rows)
