"""Focused known-truth experiment for exogenous perturbation robustness.

The perturbation-robust candidate is chosen using only prediction adequacy and
held-out environmental-niche recovery across sampling/background/domain
perturbations. A canonical AUC selector and canonical ecological-recovery selector
are chosen from the predeclared standard sampling/background case. Only after all
three selectors have chosen candidates is the generating ecological niche opened.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from .known_truth import known_truth_niche_recovery_profile
from .known_truth_experiment import _summarize_truth, _truth_ranks
from .known_truth_perturbation import (
    DEFAULT_KNOWN_TRUTH_PERTURBATIONS,
    KnownTruthPerturbationSpec,
    _nearest_planar_distance,
    evaluate_known_truth_perturbations,
)
from .known_truth_response import (
    infer_response_predictors,
    infer_true_processes,
    known_truth_process_profile,
    known_truth_response_profile,
)
from .known_truth_scenarios import (
    simulate_known_truth_plant_niche,
    standard_known_truth_candidates,
)
from .model import fit_relative_suitability_model, score_ecological_suitability
from .niche_recovery_cv import RecoveryCandidate
from .niche_recovery_selection import select_generalization_gated_niche_recovery_protocol
from .validation import make_presence_spatial_partition


def _metric_winner(metrics: pd.DataFrame, metric: str, *, ascending: bool) -> str:
    summary = (
        metrics.groupby("candidate", as_index=False)
        .agg(selector_score=(metric, "mean"), n_predictors=("n_predictors", "mean"))
    )
    summary = summary.loc[np.isfinite(pd.to_numeric(summary["selector_score"], errors="coerce"))].copy()
    if summary.empty:
        raise ValueError(f"no finite {metric} values for canonical selector")
    summary = summary.sort_values(
        ["selector_score", "n_predictors", "candidate"],
        ascending=[ascending, True, True],
        kind="mergesort",
    )
    return str(summary.iloc[0]["candidate"])


def _canonical_model_pool(
    simulation,
    *,
    access_radius: float,
    n_spatial_blocks: int,
    random_state: int,
    outer_holdout_fraction: float,
    min_background: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    occurrence = simulation.occurrences.reset_index(drop=True)
    target = simulation.target_group.reset_index(drop=True)
    partition = make_presence_spatial_partition(
        occurrence["longitude"].to_numpy(float),
        occurrence["latitude"].to_numpy(float),
        n_blocks=n_spatial_blocks,
        holdout_fraction=outer_holdout_fraction,
        random_state=random_state,
    )
    model_mask = np.isin(partition.presence_blocks, partition.train_blocks)
    model_occurrence = occurrence.loc[model_mask].reset_index(drop=True)
    distance = _nearest_planar_distance(target, model_occurrence)
    background = target.loc[distance <= float(access_radius)].reset_index(drop=True)
    if len(background) < int(min_background):
        raise ValueError("canonical model-pool background is insufficient")
    return model_occurrence, background


def _hidden_truth_profile(
    simulation,
    candidate: RecoveryCandidate,
    model_occurrence: pd.DataFrame,
    background: pd.DataFrame,
) -> dict[str, float | int]:
    model = fit_relative_suitability_model(
        model_occurrence,
        background,
        candidate.predictors,
        model_spec=candidate.model_spec,
    )
    ecological = score_ecological_suitability(
        model,
        simulation.environment,
        candidate.predictors,
        observation_predictors=candidate.observation_predictors,
        observation_reference=background,
    )
    truth = simulation.environment[simulation.true_suitability_column].to_numpy(float)
    niche = known_truth_niche_recovery_profile(
        simulation.environment,
        ecological,
        truth,
        simulation.audit_predictors,
    )
    response = known_truth_response_profile(
        simulation.environment,
        ecological,
        truth,
        infer_response_predictors(simulation.environment),
    )
    ecological_predictors = tuple(
        predictor
        for predictor in candidate.predictors
        if predictor not in candidate.observation_predictors
    )
    process = known_truth_process_profile(
        ecological_predictors,
        infer_true_processes(simulation.environment),
    )
    return {**niche.as_dict(), **response.as_dict(), **process.as_dict()}


def run_known_truth_perturbation_experiment(
    *,
    families: Sequence[str] = ("observation_confounded", "interaction", "omitted_driver"),
    seeds: Sequence[int] = (1, 2, 3),
    candidates: Mapping[str, RecoveryCandidate] | None = None,
    perturbations: Sequence[KnownTruthPerturbationSpec] = DEFAULT_KNOWN_TRUTH_PERTURBATIONS,
    canonical_perturbation: str = "sampling_standard",
    canonical_access_radius: float = 0.35,
    n_cells: int = 3000,
    n_occurrences: int = 260,
    n_target_group: int = 950,
    n_spatial_blocks: int = 6,
    inner_folds: int = 3,
    outer_holdout_fraction: float = 0.20,
    focal_recording_bias_strength: float = 4.0,
    min_background: int = 70,
    chance_auc: float = 0.50,
    minimum_auc_margin: float = 0.01,
    auc_sem_multiplier: float = 1.0,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Compare canonical selectors with an exogenous-perturbation robust selector.

    Returns
    -------
    choices
        One row per family × seed × selector that successfully chose a candidate.
    truth
        Hidden-truth audit opened only after candidate choice.
    summary
        Selector-level hidden-truth summary with co-wins.
    perturbation_metrics
        All candidate evidence used by the perturbation selector; contains no
        generating-truth diagnostics.
    failures
        Cases where no candidate survived every predeclared prediction-adequacy
        perturbation. Such cases are retained rather than repaired by relaxing the
        gate.
    """

    candidates = dict(candidates or standard_known_truth_candidates())
    choices_rows: list[dict[str, object]] = []
    truth_rows: list[dict[str, object]] = []
    metric_frames = []
    failure_rows = []

    for family in tuple(str(x) for x in families):
        for seed in tuple(int(x) for x in seeds):
            perturbation_result = evaluate_known_truth_perturbations(
                family,
                seed,
                candidates,
                perturbations=perturbations,
                n_cells=n_cells,
                n_occurrences=n_occurrences,
                n_target_group=n_target_group,
                n_spatial_blocks=n_spatial_blocks,
                inner_folds=inner_folds,
                outer_holdout_fraction=outer_holdout_fraction,
                focal_recording_bias_strength=focal_recording_bias_strength,
                min_background=min_background,
                chance_auc=chance_auc,
                minimum_auc_margin=minimum_auc_margin,
                auc_sem_multiplier=auc_sem_multiplier,
            )
            metrics = perturbation_result.fold_metrics.assign(scenario=family, seed=seed)
            metric_frames.append(metrics)
            canonical = metrics.loc[metrics["perturbation"].astype(str).eq(str(canonical_perturbation))].copy()
            if canonical.empty:
                raise ValueError(f"canonical perturbation {canonical_perturbation!r} is absent")

            canonical_auc = _metric_winner(canonical, "presence_rank", ascending=False)
            canonical_recovery = select_generalization_gated_niche_recovery_protocol(
                canonical,
                chance_auc=chance_auc,
                minimum_auc_margin=minimum_auc_margin,
                auc_sem_multiplier=auc_sem_multiplier,
            ).candidate
            winners: dict[str, str] = {
                "canonical_auc": canonical_auc,
                "canonical_niche_recovery": canonical_recovery,
            }
            if perturbation_result.selection is None:
                failure_rows.append(
                    {
                        "scenario": family,
                        "seed": seed,
                        "selector": "perturbation_robust_niche_recovery",
                        "reason": perturbation_result.selection_error or "unknown",
                    }
                )
            else:
                winners["perturbation_robust_niche_recovery"] = perturbation_result.selection.candidate

            simulation = simulate_known_truth_plant_niche(
                family,
                seed=seed,
                n_cells=n_cells,
                n_occurrences=n_occurrences,
                n_target_group=n_target_group,
                sampling_bias_strength=1.15,
                focal_recording_bias_strength=(
                    float(focal_recording_bias_strength)
                    if family == "observation_confounded"
                    else 0.0
                ),
            )
            model_occurrence, background = _canonical_model_pool(
                simulation,
                access_radius=canonical_access_radius,
                n_spatial_blocks=n_spatial_blocks,
                random_state=seed,
                outer_holdout_fraction=outer_holdout_fraction,
                min_background=min_background,
            )
            for selector, candidate_name in winners.items():
                candidate = candidates[candidate_name]
                candidate_canonical = canonical.loc[canonical["candidate"].astype(str).eq(candidate_name)]
                choices_rows.append(
                    {
                        "scenario": family,
                        "seed": seed,
                        "selector": selector,
                        "candidate": candidate_name,
                        "mean_canonical_auc": float(candidate_canonical["presence_rank"].mean()),
                        "mean_canonical_cbi": float(candidate_canonical["continuous_boyce"].mean()),
                        "mean_canonical_or10": float(candidate_canonical["or10"].mean()),
                        "n_predictors": len(candidate.predictors),
                        "n_observation_predictors": len(candidate.observation_predictors),
                    }
                )
                truth_rows.append(
                    {
                        "scenario": family,
                        "seed": seed,
                        "selector": selector,
                        "candidate": candidate_name,
                        **_hidden_truth_profile(simulation, candidate, model_occurrence, background),
                    }
                )

    choices = pd.DataFrame(choices_rows)
    truth = pd.DataFrame(truth_rows)
    truth = _truth_ranks(truth) if len(truth) else truth
    summary = _summarize_truth(truth)
    perturbation_metrics = pd.concat(metric_frames, ignore_index=True) if metric_frames else pd.DataFrame()
    failures = pd.DataFrame(failure_rows)
    return choices, truth, summary, perturbation_metrics, failures
