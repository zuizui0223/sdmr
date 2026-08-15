"""Repeated known-truth experiment for Product-A v2.

The experiment varies response complexity, niche breadth and occurrence-sampling
bias. AUC/CBI and ecological niche-recovery selectors choose among the same
candidate models without access to the generating truth. Their chosen models are
then scored against that truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

import numpy as np
import pandas as pd

from .known_truth import simulate_gaussian_plant_niche
from .known_truth_benchmark import benchmark_selectors_against_known_truth
from .model import ModelSpec
from .niche_recovery_cv import RecoveryCandidate


@dataclass(frozen=True)
class KnownTruthScenario:
    name: str
    niche_width: tuple[float, float]
    interaction_strength: float
    sampling_bias_strength: float


DEFAULT_KNOWN_TRUTH_SCENARIOS = (
    KnownTruthScenario("simple_low_bias", (0.70, 0.75), 0.0, 0.25),
    KnownTruthScenario("simple_high_bias", (0.70, 0.75), 0.0, 2.0),
    KnownTruthScenario("narrow_high_bias", (0.38, 0.45), 0.15, 2.0),
    KnownTruthScenario("interactive_low_bias", (0.60, 0.65), 0.55, 0.25),
    KnownTruthScenario("interactive_high_bias", (0.60, 0.65), 0.55, 2.0),
)


def default_known_truth_candidates() -> dict[str, RecoveryCandidate]:
    """Return deliberately plausible, misspecified and noisy candidate models."""

    return {
        "true_linear": RecoveryCandidate(
            "true_linear", ("temperature", "water"), ModelSpec(C=1.0, degree=1, penalty="l2")
        ),
        "true_quadratic": RecoveryCandidate(
            "true_quadratic", ("temperature", "water"), ModelSpec(C=1.0, degree=2, penalty="l2")
        ),
        "proxy_quadratic": RecoveryCandidate(
            "proxy_quadratic", ("temp_proxy", "water"), ModelSpec(C=1.0, degree=2, penalty="l2")
        ),
        "all_linear": RecoveryCandidate(
            "all_linear",
            ("temperature", "water", "temp_proxy", "seasonality", "noise"),
            ModelSpec(C=1.0, degree=1, penalty="l2"),
        ),
        "all_quadratic_regularized": RecoveryCandidate(
            "all_quadratic_regularized",
            ("temperature", "water", "temp_proxy", "seasonality", "noise"),
            ModelSpec(C=0.1, degree=2, penalty="l2"),
        ),
        "noise_linear": RecoveryCandidate(
            "noise_linear", ("noise", "seasonality"), ModelSpec(C=1.0, degree=1, penalty="l2")
        ),
    }


def _truth_ranks(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    directions = {
        "niche_overlap_schoener_d_pc12": False,
        "centroid_distance": True,
        "breadth_log_sd_error": True,
        "quantile_profile_error": True,
    }
    rank_cols = []
    for metric, ascending in directions.items():
        col = f"truth_rank__{metric}"
        data[col] = data.groupby(["scenario", "seed"])[metric].rank(method="min", ascending=ascending)
        rank_cols.append(col)
    data["truth_worst_metric_rank"] = data[rank_cols].max(axis=1)
    data["truth_mean_metric_rank"] = data[rank_cols].mean(axis=1)
    best = (
        data.sort_values(
            ["scenario", "seed", "truth_worst_metric_rank", "truth_mean_metric_rank", "selector"],
            kind="mergesort",
        )
        .groupby(["scenario", "seed"], as_index=False)
        .head(1)[["scenario", "seed", "selector"]]
        .rename(columns={"selector": "truth_best_selector"})
    )
    data = data.merge(best, on=["scenario", "seed"], how="left")
    data["truth_selector_win"] = data["selector"].astype(str).eq(data["truth_best_selector"].astype(str))
    return data


def run_known_truth_experiment(
    *,
    scenarios: Sequence[KnownTruthScenario] = DEFAULT_KNOWN_TRUTH_SCENARIOS,
    seeds: Sequence[int] = tuple(range(1, 11)),
    n_cells: int = 3500,
    n_occurrences: int = 280,
    n_target_group: int = 1000,
    n_spatial_blocks: int = 6,
    inner_folds: int = 3,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run the repeated selector experiment and return choices, truth rows and summary."""

    candidates = default_known_truth_candidates()
    choice_frames = []
    truth_frames = []
    for scenario in scenarios:
        for seed in seeds:
            simulation = simulate_gaussian_plant_niche(
                seed=int(seed),
                n_cells=n_cells,
                n_occurrences=n_occurrences,
                n_target_group=n_target_group,
                niche_width=scenario.niche_width,
                interaction_strength=scenario.interaction_strength,
                sampling_bias_strength=scenario.sampling_bias_strength,
            )
            result = benchmark_selectors_against_known_truth(
                simulation,
                candidates,
                n_spatial_blocks=n_spatial_blocks,
                inner_folds=inner_folds,
                random_state=int(seed),
            )
            choice_frames.append(
                result.selector_choices.assign(scenario=scenario.name, seed=int(seed))
            )
            truth_frames.append(
                result.truth_evaluation.assign(scenario=scenario.name, seed=int(seed))
            )

    choices = pd.concat(choice_frames, ignore_index=True) if choice_frames else pd.DataFrame()
    truth = pd.concat(truth_frames, ignore_index=True) if truth_frames else pd.DataFrame()
    truth = _truth_ranks(truth) if len(truth) else truth
    if len(truth):
        summary = (
            truth.groupby("selector", as_index=False)
            .agg(
                n_replicates=("seed", "size"),
                truth_win_fraction=("truth_selector_win", "mean"),
                mean_truth_overlap=("niche_overlap_schoener_d_pc12", "mean"),
                mean_centroid_distance=("centroid_distance", "mean"),
                mean_breadth_error=("breadth_log_sd_error", "mean"),
                mean_quantile_error=("quantile_profile_error", "mean"),
                mean_truth_worst_rank=("truth_worst_metric_rank", "mean"),
                mean_truth_mean_rank=("truth_mean_metric_rank", "mean"),
            )
            .sort_values(
                ["truth_win_fraction", "mean_truth_worst_rank", "mean_truth_mean_rank", "selector"],
                ascending=[False, True, True, True],
                kind="mergesort",
            )
            .reset_index(drop=True)
        )
    else:
        summary = pd.DataFrame()
    return choices, truth, summary
