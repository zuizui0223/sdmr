"""Known-truth experiment for replicated observation-process correction.

This experiment compares conventional canonical AUC with ecological selectors
whose occurrence-target correction is admitted only when nuisance-only evidence
reproduces in every predeclared exogenous perturbation. Hidden ecological truth is
opened only after the global observation gate and ecological candidate selectors
have finished.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from .known_truth_experiment import _summarize_truth, _truth_ranks
from .known_truth_perturbation import (
    DEFAULT_KNOWN_TRUTH_PERTURBATIONS,
    KnownTruthPerturbationSpec,
)
from .known_truth_perturbation_experiment import (
    _canonical_model_pool,
    _hidden_truth_profile,
    _metric_winner,
)
from .known_truth_scenarios import (
    simulate_known_truth_plant_niche,
    standard_known_truth_candidates,
)
from .niche_recovery_cv import RecoveryCandidate
from .niche_recovery_selection import select_generalization_gated_niche_recovery_protocol
from .replicated_observation_gate import (
    evaluate_replicated_observation_gate_perturbations,
)


def run_known_truth_replicated_observation_experiment(
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
    observation_weight_truncation_quantile: float = 0.99,
    observation_signal_chance_auc: float = 0.50,
    observation_signal_minimum_auc_margin: float = 0.01,
    observation_signal_auc_sem_multiplier: float = 1.0,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run canonical and perturbation-robust selectors with replicated correction.

    Returns selector choices, hidden-truth evaluation, truth summary, effective
    candidate selection evidence and one row per family×seed describing whether
    global correction was admitted.
    """

    candidates = dict(candidates or standard_known_truth_candidates())
    choice_rows: list[dict[str, object]] = []
    truth_rows: list[dict[str, object]] = []
    metric_frames = []
    gate_rows = []

    for family in tuple(str(x) for x in families):
        for seed in tuple(int(x) for x in seeds):
            gate = evaluate_replicated_observation_gate_perturbations(
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
                observation_weight_truncation_quantile=observation_weight_truncation_quantile,
                observation_signal_chance_auc=observation_signal_chance_auc,
                observation_signal_minimum_auc_margin=observation_signal_minimum_auc_margin,
                observation_signal_auc_sem_multiplier=observation_signal_auc_sem_multiplier,
            )
            metrics = gate.result.fold_metrics.assign(scenario=family, seed=seed)
            metric_frames.append(metrics)
            signal = gate.signal_summary.copy()
            signal["scenario"] = family
            signal["seed"] = seed
            signal["global_correction_active"] = bool(gate.global_correction_active)
            signal["n_active_signal_perturbations"] = gate.n_active_signal_perturbations
            signal["n_signal_perturbations"] = gate.n_signal_perturbations
            gate_rows.append(signal)

            canonical = metrics.loc[
                metrics["perturbation"].astype(str).eq(str(canonical_perturbation))
            ].copy()
            if canonical.empty:
                raise ValueError(f"canonical perturbation {canonical_perturbation!r} is absent")
            canonical_auc = _metric_winner(canonical, "presence_rank", ascending=False)
            canonical_recovery = select_generalization_gated_niche_recovery_protocol(
                canonical,
                chance_auc=chance_auc,
                minimum_auc_margin=minimum_auc_margin,
                auc_sem_multiplier=auc_sem_multiplier,
            ).candidate
            winners = {
                "canonical_auc": canonical_auc,
                "canonical_replicated_observation_niche_recovery": canonical_recovery,
            }
            if gate.result.selection is not None:
                winners[
                    "replicated_observation_perturbation_robust_niche_recovery"
                ] = gate.result.selection.candidate

            # Final truth audit uses the canonical data-generating observation
            # world and opens hidden ecology only now, after all selectors chose.
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
                candidate_canonical = canonical.loc[
                    canonical["candidate"].astype(str).eq(candidate_name)
                ]
                choice_rows.append(
                    {
                        "scenario": family,
                        "seed": seed,
                        "selector": selector,
                        "candidate": candidate_name,
                        "global_observation_correction_active": bool(
                            gate.global_correction_active
                        ),
                        "n_active_signal_perturbations": gate.n_active_signal_perturbations,
                        "n_signal_perturbations": gate.n_signal_perturbations,
                        "mean_canonical_auc": float(
                            candidate_canonical["presence_rank"].mean()
                        ),
                        "mean_canonical_cbi": float(
                            candidate_canonical["continuous_boyce"].mean()
                        ),
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
                        "global_observation_correction_active": bool(
                            gate.global_correction_active
                        ),
                        **_hidden_truth_profile(
                            simulation,
                            candidate,
                            model_occurrence,
                            background,
                        ),
                    }
                )

    choices = pd.DataFrame(choice_rows)
    truth = pd.DataFrame(truth_rows)
    truth = _truth_ranks(truth) if len(truth) else truth
    summary = _summarize_truth(truth)
    metrics = pd.concat(metric_frames, ignore_index=True) if metric_frames else pd.DataFrame()
    signal_summary = pd.concat(gate_rows, ignore_index=True) if gate_rows else pd.DataFrame()
    return choices, truth, summary, metrics, signal_summary
