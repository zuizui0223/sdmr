"""Replicated observation-process activation across exogenous perturbations.

A single nuisance-only CV result can exceed the random-ranking adequacy threshold
by chance. Observation-target correction is a species/procedure-level audit
operation, so it should not switch on independently in whichever M/domain happens
to cross the threshold.

This development gate therefore asks a stricter structural question without
changing the existing AUC thresholds: **does the nuisance-only signal reproduce in
every predeclared perturbation?**

The function runs both evidence paths on identical data:

- uncorrected held-out occurrence target (identity weights);
- per-perturbation observation correction with training-only nuisance evidence.

Only if every perturbation independently activates the existing nuisance gate is
the corrected evidence admitted. Otherwise all ecological selection metrics are
reverted to the uncorrected/identity-weight evidence. Per-perturbation nuisance
AUC/SEM/lower-bound diagnostics are retained so a global inactive decision is
fully auditable.

No ecological truth, candidate-model score, or relaxed threshold participates in
the global activation decision.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping, Sequence

import pandas as pd

from .known_truth_perturbation import (
    KnownTruthPerturbationResult,
    KnownTruthPerturbationSpec,
    DEFAULT_KNOWN_TRUTH_PERTURBATIONS,
    evaluate_known_truth_perturbations,
)
from .niche_recovery_cv import RecoveryCandidate


SIGNAL_COLUMNS = (
    "observation_signal_correction_active",
    "observation_signal_mean_auc",
    "observation_signal_sem_auc",
    "observation_signal_lower_bound",
    "observation_signal_auc_floor",
    "observation_signal_chance_auc",
    "observation_signal_n_folds",
)


@dataclass(frozen=True)
class ReplicatedObservationGateResult:
    result: KnownTruthPerturbationResult
    global_correction_active: bool
    n_signal_perturbations: int
    n_active_signal_perturbations: int
    signal_summary: pd.DataFrame
    per_perturbation_corrected_result: KnownTruthPerturbationResult
    uncorrected_result: KnownTruthPerturbationResult


def _signal_summary(metrics: pd.DataFrame) -> pd.DataFrame:
    required = {"perturbation", *SIGNAL_COLUMNS}
    missing = required - set(metrics.columns)
    if missing:
        raise KeyError(f"corrected perturbation metrics missing signal columns: {sorted(missing)}")
    columns = ["perturbation", *SIGNAL_COLUMNS]
    summary = metrics[columns].drop_duplicates().copy()
    duplicated = summary.groupby("perturbation").size()
    if (duplicated > 1).any():
        bad = duplicated.loc[duplicated > 1].index.tolist()
        raise ValueError(
            "observation signal evidence must be candidate/fold independent within perturbation; "
            f"violations: {bad}"
        )
    return summary.sort_values("perturbation").reset_index(drop=True)


def _identity_metrics_with_signal_diagnostics(
    uncorrected: pd.DataFrame,
    signal_summary: pd.DataFrame,
) -> pd.DataFrame:
    data = uncorrected.copy()
    # The corrected audit was requested, but the replicated species-level gate is
    # inactive. Selection must therefore use exact identity-weight evidence.
    data["observation_correction"] = True
    data["observation_correction_active"] = False
    data["observation_signal_global_active"] = False
    data = data.drop(columns=list(SIGNAL_COLUMNS), errors="ignore")
    data = data.merge(signal_summary, on="perturbation", how="left", validate="many_to_one")
    # Weight diagnostics explicitly describe identity weighting rather than
    # retaining values from the rejected per-perturbation correction.
    if "n_heldout_presence" in data.columns:
        data["observation_weight_ess"] = pd.to_numeric(
            data["n_heldout_presence"], errors="coerce"
        )
    else:
        data["observation_weight_ess"] = float("nan")
    data["observation_weight_max"] = 1.0
    data["observation_weight_truncation_cap"] = 1.0
    return data


def evaluate_replicated_observation_gate_perturbations(
    family: str,
    seed: int,
    candidates: Mapping[str, RecoveryCandidate],
    *,
    perturbations: Sequence[KnownTruthPerturbationSpec] = DEFAULT_KNOWN_TRUTH_PERTURBATIONS,
    n_cells: int = 3500,
    n_occurrences: int = 280,
    n_target_group: int = 1000,
    n_spatial_blocks: int = 6,
    inner_folds: int = 3,
    outer_holdout_fraction: float = 0.20,
    focal_recording_bias_strength: float = 4.0,
    min_background: int = 80,
    chance_auc: float = 0.50,
    minimum_auc_margin: float = 0.01,
    auc_sem_multiplier: float = 1.0,
    observation_weight_truncation_quantile: float = 0.99,
    observation_signal_chance_auc: float = 0.50,
    observation_signal_minimum_auc_margin: float = 0.01,
    observation_signal_auc_sem_multiplier: float = 1.0,
) -> ReplicatedObservationGateResult:
    """Admit correction only when nuisance evidence reproduces everywhere.

    The existing per-perturbation correction path is deliberately kept as an
    ablation. If even one predeclared perturbation fails its training-only nuisance
    evidence gate, the returned selection/result comes from the uncorrected path.
    This changes no numeric AUC threshold; it changes only the required scope of
    replication for a global observation correction.
    """

    common = dict(
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
    uncorrected = evaluate_known_truth_perturbations(
        family,
        seed,
        candidates,
        observation_correction=False,
        **common,
    )
    corrected = evaluate_known_truth_perturbations(
        family,
        seed,
        candidates,
        observation_correction=True,
        **common,
    )
    signals = _signal_summary(corrected.fold_metrics)
    expected = tuple(sorted(str(spec.name) for spec in perturbations))
    observed = tuple(sorted(signals["perturbation"].astype(str).tolist()))
    if observed != expected:
        raise ValueError(
            "observation signal evidence must cover every predeclared perturbation; "
            f"expected={expected}, observed={observed}"
        )
    active = signals["observation_signal_correction_active"].astype(bool)
    global_active = bool(len(signals) and active.all())

    if global_active:
        effective_metrics = corrected.fold_metrics.copy()
        effective_metrics["observation_signal_global_active"] = True
        effective = KnownTruthPerturbationResult(
            fold_metrics=effective_metrics,
            selection=corrected.selection,
            selection_error=corrected.selection_error,
        )
    else:
        effective_metrics = _identity_metrics_with_signal_diagnostics(
            uncorrected.fold_metrics,
            signals,
        )
        effective = KnownTruthPerturbationResult(
            fold_metrics=effective_metrics,
            selection=uncorrected.selection,
            selection_error=uncorrected.selection_error,
        )

    return ReplicatedObservationGateResult(
        result=effective,
        global_correction_active=global_active,
        n_signal_perturbations=len(signals),
        n_active_signal_perturbations=int(active.sum()),
        signal_summary=signals,
        per_perturbation_corrected_result=corrected,
        uncorrected_result=uncorrected,
    )
