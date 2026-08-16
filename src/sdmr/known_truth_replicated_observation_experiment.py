"""Known-truth experiment for replicated observation-process correction.

This experiment compares conventional canonical AUC with ecological selectors
whose occurrence-target correction is admitted only when nuisance-only evidence
reproduces in every predeclared exogenous perturbation. When that replicated
observation process is active, ecological selectors additionally require a record
model that explicitly declares the validated nuisance term so fitted ecological
responses are not already confounded by an omitted observation process.

Conventional AUC remains an unrestricted record-prediction comparator. Hidden
ecological truth is opened only after the global observation gate, model
admissibility gate and ecological candidate selectors have finished.
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
    required_observation_predictors: Sequence[str] = ("recording_bias",),
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run canonical and perturbation-robust selectors with replicated correction.

    Returns selector choices, hidden-truth evaluation, truth summary, effective
    candidate selection evidence and one row per family×seed×perturbation
    describing the observation signal and resulting model admissibility.
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
                required_observation_predictors=required_observation_predictors,
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

            # Conventional AUC stays outside observation-model admissibility. Use
            # the unrestricted uncorrected candidate table; its record-prediction
            # scores are invariant to ecological target correction.
            unrestricted = gate.uncorrected_result.fold_metrics
            canonical_all = unrestricted.loc[
                unrestricted["perturbation"].astype(str).eq(str(canonical_perturbation))
            ].copy()
            if canonical_all.empty:
                raise ValueError(f"canonical perturbation {canonical_perturbation!r} is absent")
            canonical_auc = _metric_winner(canonical_all, "presence_rank", ascending=False)

            # Ecological selectors use only model specifications admitted by the
            # independently validated observation process. When the global gate is
            # inactive every candidate is annotated admissible and this is exactly
            # the historical candidate library.
            canonical = metrics.loc[
                metrics["perturbation"].astype(str).eq(str(canonical_perturbation))
                & metrics["observation_model_admissible"].astype(bool)
            ].copy()
            if canonical.empty:
                raise ValueError(
                    f"no observation-admissible candidate in canonical perturbation "
                    f"{canonical_perturbation!r}"
                )
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
            admissible_names = set(gate.observation_admissibility.admissible_candidates)
            required_text = ",".join(
                gate.observation_admissibility.required_observation_predictors
            )
            for selector, candidate_name in winners.items():
                candidate = candidates[candidate_name]
                is_admissible = candidate_name in admissible_names
                candidate_canonical_source = (
                    canonical_all if selector == "canonical_auc" else canonical
                )
                candidate_canonical = candidate_canonical_source.loc[
                    candidate_canonical_source["candidate"].astype(str).eq(candidate_name)
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
                        "observation_model_admissible": bool(is_admissible),
                        "required_observation_predictors": required_text,
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
                        "observation_model_admissible": bool(is_admissible),
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
