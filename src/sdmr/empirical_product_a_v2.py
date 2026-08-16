"""Empirical Product-A v2 orchestration without hidden ecological truth.

This module is the bridge from the known-truth development program to real plant
occurrence data.  It composes the already-falsified Product-A v2 pieces without
introducing another score:

1. candidate-independent observation-process evidence across predeclared
   perturbations;
2. one global correction/admissibility decision per taxon;
3. conventional record-prediction diagnostics for every candidate;
4. canonical ecological niche-recovery selection;
5. exogenous-perturbation ecological robustness selection;
6. consensus-first ecological inference certificate;
7. selector-range response interpretation on the canonical audit environment.

There is deliberately no hidden-truth input here.  For empirical plants the claim
remains realized environmental niche recovery/sensitivity, not recovery of a
fundamental physiological niche.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .ecological_inference_certificate import EcologicalInferenceCertificate, build_ecological_inference_certificate
from .ecological_interpretation import EcologicalInterpretationBundle, build_ecological_interpretation_bundle
from .model import fit_relative_suitability_model, score_ecological_suitability
from .niche_recovery_cv import RecoveryCandidate
from .niche_recovery_perturbation import (
    PerturbationRobustNicheRecoverySelection,
    select_perturbation_robust_niche_recovery_protocol,
)
from .niche_recovery_selection import (
    GeneralizationGatedNicheRecoverySelection,
    select_generalization_gated_niche_recovery_protocol,
)
from .observation_admissibility import ObservationAdmissibility, observation_model_admissibility
from .observation_corrected_recovery import cross_validated_observation_corrected_niche_recovery
from .observation_process import ObservationSignalEvidence, observation_process_signal_evidence


@dataclass(frozen=True)
class EmpiricalNichePerturbation:
    name: str
    perturbation_type: str
    presence: pd.DataFrame
    background: pd.DataFrame
    presence_groups: np.ndarray
    background_groups: np.ndarray

    def __post_init__(self) -> None:
        if not str(self.name).strip():
            raise ValueError("perturbation name must be non-empty")
        if not str(self.perturbation_type).strip():
            raise ValueError("perturbation_type must be non-empty")
        p_groups = np.asarray(self.presence_groups)
        b_groups = np.asarray(self.background_groups)
        if len(p_groups) != len(self.presence):
            raise ValueError("presence_groups must align with presence rows")
        if len(b_groups) != len(self.background):
            raise ValueError("background_groups must align with background rows")


@dataclass(frozen=True)
class EmpiricalProductAV2Result:
    canonical_auc_candidate: str
    canonical_ecological_candidate: str
    robust_ecological_candidate: str | None
    robustness_error: str | None
    observation_correction_active: bool
    observation_signal_by_perturbation: pd.DataFrame
    observation_admissibility: ObservationAdmissibility
    candidate_fold_metrics: pd.DataFrame
    canonical_selection: GeneralizationGatedNicheRecoverySelection
    robust_selection: PerturbationRobustNicheRecoverySelection | None
    certificate: EcologicalInferenceCertificate
    interpretation: EcologicalInterpretationBundle | None


def _validate_perturbations(
    perturbations: Sequence[EmpiricalNichePerturbation],
    canonical_perturbation: str,
) -> tuple[EmpiricalNichePerturbation, ...]:
    items = tuple(perturbations)
    if len(items) < 2:
        raise ValueError("at least two predeclared perturbations are required")
    names = [str(item.name) for item in items]
    if len(set(names)) != len(names):
        raise ValueError("perturbation names must be unique")
    if str(canonical_perturbation) not in set(names):
        raise KeyError(f"canonical perturbation is absent: {canonical_perturbation!r}")
    return items


def _observation_signal_table(
    perturbations: Sequence[EmpiricalNichePerturbation],
    observation_predictors: Sequence[str],
    *,
    n_splits: int,
    chance_auc: float,
    minimum_auc_margin: float,
    auc_sem_multiplier: float,
) -> tuple[pd.DataFrame, bool]:
    rows = []
    for perturbation in perturbations:
        evidence = observation_process_signal_evidence(
            perturbation.presence,
            perturbation.background,
            perturbation.presence_groups,
            perturbation.background_groups,
            observation_predictors,
            n_splits=n_splits,
            chance_auc=chance_auc,
            minimum_auc_margin=minimum_auc_margin,
            auc_sem_multiplier=auc_sem_multiplier,
        )
        rows.append(
            {
                "perturbation": str(perturbation.name),
                "perturbation_type": str(perturbation.perturbation_type),
                "correction_active": bool(evidence.correction_active),
                "mean_auc": float(evidence.mean_auc),
                "sem_auc": float(evidence.sem_auc),
                "lower_evidence_bound": float(evidence.lower_evidence_bound),
                "auc_gate_floor": float(evidence.auc_gate_floor),
                "chance_auc": float(evidence.chance_auc),
                "n_folds": int(evidence.n_folds),
            }
        )
    table = pd.DataFrame(rows).sort_values("perturbation").reset_index(drop=True)
    global_active = bool(len(table) and table["correction_active"].all())
    return table, global_active


def _candidate_metrics(
    perturbations: Sequence[EmpiricalNichePerturbation],
    candidates: Mapping[str, RecoveryCandidate],
    audit_predictors: Sequence[str],
    observation_predictors: Sequence[str],
    *,
    observation_correction_active: bool,
    admissibility: ObservationAdmissibility,
    n_splits: int,
    observation_weight_truncation_quantile: float,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    allowed = set(admissibility.admissible_candidates)
    for perturbation in perturbations:
        for candidate_name in sorted(candidates):
            candidate = candidates[candidate_name]
            frame = cross_validated_observation_corrected_niche_recovery(
                perturbation.presence,
                perturbation.background,
                perturbation.presence_groups,
                perturbation.background_groups,
                candidate.predictors,
                audit_predictors,
                candidate_observation_predictors=candidate.observation_predictors,
                audit_observation_predictors=observation_predictors,
                observation_correction_active=observation_correction_active,
                n_splits=n_splits,
                model_spec=candidate.model_spec,
                observation_weight_truncation_quantile=observation_weight_truncation_quantile,
            )
            if frame.empty:
                continue
            frame = frame.copy()
            frame["candidate"] = str(candidate_name)
            frame["n_predictors"] = len(candidate.predictors)
            frame["model"] = candidate.model_spec.label
            frame["perturbation"] = str(perturbation.name)
            frame["perturbation_type"] = str(perturbation.perturbation_type)
            frame["observation_model_admissible"] = candidate_name in allowed
            frames.append(frame)
    if not frames:
        raise ValueError("no empirical Product-A v2 candidate could be evaluated")
    return pd.concat(frames, ignore_index=True)


def _mean_auc_winner(metrics: pd.DataFrame) -> str:
    summary = (
        metrics.groupby("candidate", as_index=False)["presence_rank"]
        .mean()
        .sort_values(["presence_rank", "candidate"], ascending=[False, True], kind="mergesort")
    )
    if summary.empty or not np.isfinite(float(summary.iloc[0]["presence_rank"])):
        raise ValueError("canonical AUC comparator has no finite candidate")
    return str(summary.iloc[0]["candidate"])


def _fit_interpretation(
    canonical: EmpiricalNichePerturbation,
    canonical_candidate: str,
    robust_candidate: str,
    candidates: Mapping[str, RecoveryCandidate],
    *,
    process_groups: Mapping[str, str] | None,
) -> EcologicalInterpretationBundle:
    canonical_spec = candidates[canonical_candidate]
    robust_spec = candidates[robust_candidate]
    canonical_model = fit_relative_suitability_model(
        canonical.presence,
        canonical.background,
        canonical_spec.predictors,
        model_spec=canonical_spec.model_spec,
    )
    robust_model = fit_relative_suitability_model(
        canonical.presence,
        canonical.background,
        robust_spec.predictors,
        model_spec=robust_spec.model_spec,
    )
    canonical_surface = score_ecological_suitability(
        canonical_model,
        canonical.background,
        canonical_spec.predictors,
        observation_predictors=canonical_spec.observation_predictors,
        observation_reference=canonical.background,
    )
    robust_surface = score_ecological_suitability(
        robust_model,
        canonical.background,
        robust_spec.predictors,
        observation_predictors=robust_spec.observation_predictors,
        observation_reference=canonical.background,
    )
    return build_ecological_interpretation_bundle(
        canonical_candidate,
        robust_candidate,
        candidates,
        canonical.background,
        canonical_surface,
        robust_surface,
        process_groups=process_groups,
    )


def benchmark_empirical_product_a_v2(
    perturbations: Sequence[EmpiricalNichePerturbation],
    candidates: Mapping[str, RecoveryCandidate],
    audit_predictors: Sequence[str],
    *,
    canonical_perturbation: str,
    observation_predictors: Sequence[str] = (),
    process_groups: Mapping[str, str] | None = None,
    n_splits: int = 4,
    chance_auc: float = 0.50,
    minimum_auc_margin: float = 0.01,
    auc_sem_multiplier: float = 1.0,
    max_mean_or10: float | None = None,
    prediction_adequacy_perturbation_types: Sequence[str] = ("sampling_or_background",),
    observation_weight_truncation_quantile: float = 0.99,
) -> EmpiricalProductAV2Result:
    """Run the empirical Product-A v2 selection and interpretation contract.

    Observation correction is a global per-taxon decision: the same predeclared
    nuisance variables must pass their training-only evidence gate in *every*
    perturbation.  If not, identity occurrence weights are used everywhere.

    Conventional canonical AUC remains unrestricted by ecological model
    admissibility.  Canonical and robust ecological selectors are restricted to
    admissible candidates and use prediction only as an absolute adequacy gate.
    """

    items = _validate_perturbations(perturbations, canonical_perturbation)
    candidates = dict(candidates)
    if not candidates:
        raise ValueError("at least one Product-A v2 candidate is required")
    audit_predictors = tuple(dict.fromkeys(str(x) for x in audit_predictors))
    observation_predictors = tuple(dict.fromkeys(str(x) for x in observation_predictors))
    overlap = sorted(set(audit_predictors) & set(observation_predictors))
    if overlap:
        raise ValueError(
            "ecological audit predictors must exclude observation-process variables: "
            f"{overlap}"
        )

    signal_table, global_correction = _observation_signal_table(
        items,
        observation_predictors,
        n_splits=n_splits,
        chance_auc=chance_auc,
        minimum_auc_margin=minimum_auc_margin,
        auc_sem_multiplier=auc_sem_multiplier,
    )
    admissibility = observation_model_admissibility(
        candidates,
        observation_predictors,
        correction_active=global_correction,
    )
    metrics = _candidate_metrics(
        items,
        candidates,
        audit_predictors,
        observation_predictors,
        observation_correction_active=global_correction,
        admissibility=admissibility,
        n_splits=n_splits,
        observation_weight_truncation_quantile=observation_weight_truncation_quantile,
    )

    canonical_metrics = metrics.loc[
        metrics["perturbation"].eq(str(canonical_perturbation))
    ].copy()
    canonical_auc = _mean_auc_winner(canonical_metrics)
    ecological_canonical_metrics = canonical_metrics.loc[
        canonical_metrics["observation_model_admissible"]
    ].copy()
    canonical_selection = select_generalization_gated_niche_recovery_protocol(
        ecological_canonical_metrics,
        chance_auc=chance_auc,
        minimum_auc_margin=minimum_auc_margin,
        auc_sem_multiplier=auc_sem_multiplier,
        max_mean_or10=max_mean_or10,
    )

    ecological_metrics = metrics.loc[metrics["observation_model_admissible"]].copy()
    robust_selection: PerturbationRobustNicheRecoverySelection | None
    robustness_error: str | None
    try:
        robust_selection = select_perturbation_robust_niche_recovery_protocol(
            ecological_metrics,
            chance_auc=chance_auc,
            minimum_auc_margin=minimum_auc_margin,
            auc_sem_multiplier=auc_sem_multiplier,
            prediction_adequacy_perturbation_types=prediction_adequacy_perturbation_types,
        )
        robust_candidate = robust_selection.candidate
        robustness_error = None
    except ValueError as exc:
        robust_selection = None
        robust_candidate = None
        robustness_error = str(exc)

    certificate = build_ecological_inference_certificate(
        canonical_selection.candidate,
        robust_candidate,
        candidates,
        process_groups=process_groups,
    )
    canonical_data = next(
        item for item in items if str(item.name) == str(canonical_perturbation)
    )
    interpretation = (
        _fit_interpretation(
            canonical_data,
            canonical_selection.candidate,
            robust_candidate,
            candidates,
            process_groups=process_groups,
        )
        if robust_candidate is not None
        else None
    )

    return EmpiricalProductAV2Result(
        canonical_auc_candidate=canonical_auc,
        canonical_ecological_candidate=canonical_selection.candidate,
        robust_ecological_candidate=robust_candidate,
        robustness_error=robustness_error,
        observation_correction_active=global_correction,
        observation_signal_by_perturbation=signal_table,
        observation_admissibility=admissibility,
        candidate_fold_metrics=metrics,
        canonical_selection=canonical_selection,
        robust_selection=robust_selection,
        certificate=certificate,
        interpretation=interpretation,
    )
