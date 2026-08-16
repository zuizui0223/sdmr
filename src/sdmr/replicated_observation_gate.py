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

When the replicated gate is active, ecological inference has one additional
*specification* requirement: a candidate record model must explicitly declare the
validated nuisance predictors as ``observation_predictors``. Correcting the
held-out occurrence target cannot undo ecological-coefficient confounding that
already entered a model which omitted the observation process. Conventional AUC
comparison remains outside this admissibility gate.

No ecological truth, candidate-model score, or relaxed threshold participates in
the global activation or admissibility decisions.
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
from .niche_recovery_perturbation import select_perturbation_robust_niche_recovery_protocol
from .observation_admissibility import (
    ObservationAdmissibility,
    observation_model_admissibility,
)


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
    observation_admissibility: ObservationAdmissibility
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


def _annotate_admissibility(
    metrics: pd.DataFrame,
    admissibility: ObservationAdmissibility,
) -> pd.DataFrame:
    data = metrics.copy()
    allowed = set(admissibility.admissible_candidates)
    data["observation_model_admissible"] = data["candidate"].astype(str).isin(allowed)
    data["required_observation_predictors"] = ",".join(
        admissibility.required_observation_predictors
    )
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
    required_observation_predictors: Sequence[str] = ("recording_bias",),
) -> ReplicatedObservationGateResult:
    """Admit correction and ecological model specifications only after replication.

    The existing per-perturbation correction path is deliberately kept as an
    ablation. If even one predeclared perturbation fails its training-only nuisance
    evidence gate, the returned ecological selection/result comes from the
    uncorrected path and every predeclared candidate remains admissible.

    When every perturbation passes, corrected occurrence-target evidence is used
    and ecological selection is recomputed using only record-model specifications
    that explicitly declare all ``required_observation_predictors`` as nuisance.
    This changes no numeric AUC threshold and does not constrain conventional AUC
    comparison outside this function.
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

    admissibility = observation_model_admissibility(
        candidates,
        required_observation_predictors,
        correction_active=global_active,
    )
    signals = signals.copy()
    signals["admissible_candidates"] = ",".join(admissibility.admissible_candidates)
    signals["inadmissible_candidates"] = ",".join(admissibility.inadmissible_candidates)
    signals["required_observation_predictors"] = ",".join(
        admissibility.required_observation_predictors
    )

    if global_active:
        effective_metrics = corrected.fold_metrics.copy()
        effective_metrics["observation_signal_global_active"] = True
        effective_metrics = _annotate_admissibility(effective_metrics, admissibility)
        selection_metrics = effective_metrics.loc[
            effective_metrics["observation_model_admissible"]
        ].copy()
        try:
            selection = select_perturbation_robust_niche_recovery_protocol(
                selection_metrics,
                chance_auc=chance_auc,
                minimum_auc_margin=minimum_auc_margin,
                auc_sem_multiplier=auc_sem_multiplier,
            )
            selection_error = None
        except ValueError as exc:
            selection = None
            selection_error = str(exc)
        effective = KnownTruthPerturbationResult(
            fold_metrics=effective_metrics,
            selection=selection,
            selection_error=selection_error,
        )
    else:
        effective_metrics = _identity_metrics_with_signal_diagnostics(
            uncorrected.fold_metrics,
            signals,
        )
        effective_metrics = _annotate_admissibility(effective_metrics, admissibility)
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
        observation_admissibility=admissibility,
        per_perturbation_corrected_result=corrected,
        uncorrected_result=uncorrected,
    )
