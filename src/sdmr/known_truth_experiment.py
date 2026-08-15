"""Repeated known-truth experiments for Product-A v2.

Two complementary suites are kept separate:

- the legacy smooth-Gaussian suite varies breadth, interaction and shared
  sampling bias;
- the structural suite varies niche family and includes asymmetric, threshold,
  omitted-driver and observation-confounded cases.

All selectors choose without access to the generating truth. Truth is opened only
for the final audit. Tied selectors are treated as co-winners rather than being
broken alphabetically.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

import numpy as np
import pandas as pd

from .known_truth import simulate_gaussian_plant_niche
from .known_truth_benchmark import benchmark_selectors_against_known_truth
from .known_truth_scenarios import (
    KNOWN_TRUTH_FAMILIES,
    simulate_known_truth_plant_niche,
    standard_known_truth_candidates,
)
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
    """Rank hidden-truth recovery and mark all exact best rows as co-winners.

    A selector name is never used as a scientific tie-break. This matters because
    two selectors can select the same candidate and therefore have identical
    hidden-truth recovery profiles.
    """

    data = frame.copy()
    directions = {
        "niche_overlap_schoener_d_pc12": False,
        "centroid_distance": True,
        "breadth_log_sd_error": True,
        "quantile_profile_error": True,
    }
    required = {"scenario", "seed", "selector", *directions}
    missing = required - set(data.columns)
    if missing:
        raise KeyError(f"known-truth rows missing columns: {sorted(missing)}")

    rank_cols = []
    for metric, ascending in directions.items():
        col = f"truth_rank__{metric}"
        data[col] = data.groupby(["scenario", "seed"])[metric].rank(method="min", ascending=ascending)
        rank_cols.append(col)
    data["truth_worst_metric_rank"] = data[rank_cols].max(axis=1)
    data["truth_mean_metric_rank"] = data[rank_cols].mean(axis=1)

    groups = ["scenario", "seed"]
    data["truth_best_worst_rank"] = data.groupby(groups)["truth_worst_metric_rank"].transform("min")
    on_best_worst = np.isclose(
        data["truth_worst_metric_rank"].to_numpy(float),
        data["truth_best_worst_rank"].to_numpy(float),
        equal_nan=False,
    )
    eligible_mean = data["truth_mean_metric_rank"].where(on_best_worst, np.inf)
    data["truth_best_mean_rank"] = eligible_mean.groupby(
        [data["scenario"], data["seed"]]
    ).transform("min")
    data["truth_selector_win"] = on_best_worst & np.isclose(
        data["truth_mean_metric_rank"].to_numpy(float),
        data["truth_best_mean_rank"].to_numpy(float),
        equal_nan=False,
    )

    co_winners = (
        data.loc[data["truth_selector_win"]]
        .groupby(groups)["selector"]
        .agg(lambda x: ",".join(sorted(dict.fromkeys(str(v) for v in x))))
        .rename("truth_best_selectors")
        .reset_index()
    )
    data = data.merge(co_winners, on=groups, how="left")
    return data


def _summarize_truth(truth: pd.DataFrame) -> pd.DataFrame:
    if truth.empty:
        return pd.DataFrame()
    return (
        truth.groupby("selector", as_index=False)
        .agg(
            n_replicates=("seed", "size"),
            truth_co_win_fraction=("truth_selector_win", "mean"),
            mean_truth_overlap=("niche_overlap_schoener_d_pc12", "mean"),
            mean_centroid_distance=("centroid_distance", "mean"),
            mean_breadth_error=("breadth_log_sd_error", "mean"),
            mean_quantile_error=("quantile_profile_error", "mean"),
            mean_truth_worst_rank=("truth_worst_metric_rank", "mean"),
            mean_truth_mean_rank=("truth_mean_metric_rank", "mean"),
        )
        .sort_values(
            ["truth_co_win_fraction", "mean_truth_worst_rank", "mean_truth_mean_rank", "selector"],
            ascending=[False, True, True, True],
            kind="mergesort",
        )
        .reset_index(drop=True)
    )


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
    """Run the legacy smooth-Gaussian selector experiment."""

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
            choice_frames.append(result.selector_choices.assign(scenario=scenario.name, seed=int(seed)))
            truth_frames.append(result.truth_evaluation.assign(scenario=scenario.name, seed=int(seed)))

    choices = pd.concat(choice_frames, ignore_index=True) if choice_frames else pd.DataFrame()
    truth = pd.concat(truth_frames, ignore_index=True) if truth_frames else pd.DataFrame()
    truth = _truth_ranks(truth) if len(truth) else truth
    return choices, truth, _summarize_truth(truth)


def run_structural_known_truth_experiment(
    *,
    families: Sequence[str] = KNOWN_TRUTH_FAMILIES,
    seeds: Sequence[int] = tuple(range(1, 11)),
    n_cells: int = 3500,
    n_occurrences: int = 280,
    n_target_group: int = 1000,
    n_spatial_blocks: int = 6,
    inner_folds: int = 3,
    observation_confounded_strength: float = 4.0,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run structural niche families with one fixed candidate library.

    Candidate definitions are identical across all families. In the
    observation-confounded family the focal observation process is stronger, but
    it is never included in the ecological audit basis or hidden truth.
    """

    families = tuple(str(x) for x in families)
    unknown = sorted(set(families) - set(KNOWN_TRUTH_FAMILIES))
    if unknown:
        raise ValueError(f"unknown structural known-truth families: {unknown}")
    candidates = standard_known_truth_candidates()
    choice_frames = []
    truth_frames = []
    for family in families:
        for seed in seeds:
            simulation = simulate_known_truth_plant_niche(
                family,
                seed=int(seed),
                n_cells=n_cells,
                n_occurrences=n_occurrences,
                n_target_group=n_target_group,
                focal_recording_bias_strength=(
                    observation_confounded_strength if family == "observation_confounded" else 0.0
                ),
            )
            result = benchmark_selectors_against_known_truth(
                simulation,
                candidates,
                n_spatial_blocks=n_spatial_blocks,
                inner_folds=inner_folds,
                random_state=int(seed),
            )
            choice_frames.append(result.selector_choices.assign(scenario=family, seed=int(seed)))
            truth_frames.append(result.truth_evaluation.assign(scenario=family, seed=int(seed)))

    choices = pd.concat(choice_frames, ignore_index=True) if choice_frames else pd.DataFrame()
    truth = pd.concat(truth_frames, ignore_index=True) if truth_frames else pd.DataFrame()
    truth = _truth_ranks(truth) if len(truth) else truth
    return choices, truth, _summarize_truth(truth)
