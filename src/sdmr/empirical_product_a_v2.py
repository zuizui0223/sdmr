"""Empirical Product-A v2 orchestration without hidden ecological truth.

This module is the bridge from the known-truth development program to real plant
occurrence data. It composes the falsified Product-A v2 pieces without introducing
another score:

1. candidate-independent observation-process evidence across predeclared
   perturbations;
2. one global correction/admissibility decision per taxon;
3. conventional record-prediction diagnostics for every candidate;
4. canonical ecological niche-recovery selection;
5. exogenous-perturbation ecological robustness selection;
6. consensus-first ecological inference certificate;
7. selector-range response interpretation on the canonical audit environment;
8. one final outer-sealed answer check opened only after all tuning decisions.

There is deliberately no hidden-truth input here. For empirical plants the claim
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
from .metrics import continuous_boyce_index, presence_rank_score
from .model import (
    fit_relative_suitability_model,
    score_ecological_suitability,
    score_relative_suitability,
)
from .model_criteria import or10
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
from .observation_corrected_recovery import (
    cross_validated_observation_corrected_niche_recovery,
    observation_weighted_heldout_niche_recovery_profile,
)
from .observation_process import (
    fit_observation_inverse_propensity_weights,
    observation_process_signal_evidence,
)
from .pilot import MODEL_ROLE, OUTER_ROLE_COL, SEALED_ROLE
from .validation import make_spatial_partition


@dataclass(frozen=True)
class EmpiricalNichePerturbation:
    """One predeclared empirical sensitivity condition.

    ``presence`` and ``background`` are **model-pool only** rows. Optional sealed
    rows are carried separately and are never touched by observation testing,
    ecological CV, candidate selection or robustness selection.
    """

    name: str
    perturbation_type: str
    presence: pd.DataFrame
    background: pd.DataFrame
    presence_groups: np.ndarray
    background_groups: np.ndarray
    sealed_presence: pd.DataFrame | None = None
    sealed_background: pd.DataFrame | None = None

    def __post_init__(self) -> None:
        if not str(self.name).strip():
            raise ValueError("perturbation name must be non-empty")
        if not str(self.perturbation_type).strip():
            raise ValueError("perturbation_type must be non-empty")
        p_groups = np.asarray(self.presence_groups)
        b_groups = np.asarray(self.background_groups)
        if len(p_groups) != len(self.presence):
            raise ValueError("presence_groups must align with model-pool presence rows")
        if len(b_groups) != len(self.background):
            raise ValueError("background_groups must align with model-pool background rows")
        one_sealed = (self.sealed_presence is None) ^ (self.sealed_background is None)
        if one_sealed:
            raise ValueError("sealed_presence and sealed_background must be supplied together")

    @property
    def has_sealed_validation(self) -> bool:
        return self.sealed_presence is not None and self.sealed_background is not None

    @classmethod
    def from_preassigned_outer_roles(
        cls,
        name: str,
        perturbation_type: str,
        presence: pd.DataFrame,
        background: pd.DataFrame,
        *,
        n_spatial_blocks: int = 8,
        random_state: int = 42,
        lon_col: str = "longitude",
        lat_col: str = "latitude",
    ) -> "EmpiricalNichePerturbation":
        """Split authoritative prepared tables without reopening sealed rows.

        The upstream ``__sdmr_outer_role`` was assigned before M/background
        construction. Inner model-pool spatial groups are rebuilt using **model
        rows only**, matching the leakage-safe Product-A contract.
        """

        for label, frame in (("presence", presence), ("background", background)):
            if OUTER_ROLE_COL not in frame.columns:
                raise KeyError(f"{label} table lacks authoritative {OUTER_ROLE_COL!r}")
            invalid = set(frame[OUTER_ROLE_COL].astype(str)) - {MODEL_ROLE, SEALED_ROLE}
            if invalid:
                raise ValueError(f"{label} table has invalid outer roles: {sorted(invalid)}")

        p_model = presence.loc[presence[OUTER_ROLE_COL].astype(str).eq(MODEL_ROLE)].reset_index(drop=True)
        p_sealed = presence.loc[presence[OUTER_ROLE_COL].astype(str).eq(SEALED_ROLE)].reset_index(drop=True)
        b_model = background.loc[background[OUTER_ROLE_COL].astype(str).eq(MODEL_ROLE)].reset_index(drop=True)
        b_sealed = background.loc[background[OUTER_ROLE_COL].astype(str).eq(SEALED_ROLE)].reset_index(drop=True)
        if len(p_model) < 4 or len(p_sealed) < 2:
            raise ValueError("preassigned occurrence evidence lacks model/sealed rows")
        if len(b_model) < 5 or len(b_sealed) < 5:
            raise ValueError("preassigned background evidence lacks model/sealed-reference rows")

        partition = make_spatial_partition(
            pd.to_numeric(p_model[lon_col], errors="raise").to_numpy(float),
            pd.to_numeric(p_model[lat_col], errors="raise").to_numpy(float),
            pd.to_numeric(b_model[lon_col], errors="raise").to_numpy(float),
            pd.to_numeric(b_model[lat_col], errors="raise").to_numpy(float),
            n_blocks=int(n_spatial_blocks),
            holdout_fraction=0.20,
            random_state=int(random_state),
        )
        return cls(
            name=str(name),
            perturbation_type=str(perturbation_type),
            presence=p_model,
            background=b_model,
            presence_groups=partition.presence_blocks,
            background_groups=partition.background_blocks,
            sealed_presence=p_sealed,
            sealed_background=b_sealed,
        )


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
    sealed_validation: pd.DataFrame


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


def _sealed_validation(
    perturbations: Sequence[EmpiricalNichePerturbation],
    selector_candidates: Mapping[str, str | None],
    candidates: Mapping[str, RecoveryCandidate],
    audit_predictors: Sequence[str],
    observation_predictors: Sequence[str],
    *,
    observation_correction_active: bool,
    observation_weight_truncation_quantile: float,
) -> pd.DataFrame:
    """Open authoritative outer-sealed rows only after candidate selection."""

    rows: list[dict[str, object]] = []
    for perturbation in perturbations:
        if not perturbation.has_sealed_validation:
            continue
        assert perturbation.sealed_presence is not None
        assert perturbation.sealed_background is not None
        for selector, candidate_name in selector_candidates.items():
            if candidate_name is None:
                continue
            candidate = candidates[candidate_name]
            try:
                model = fit_relative_suitability_model(
                    perturbation.presence,
                    perturbation.background,
                    candidate.predictors,
                    model_spec=candidate.model_spec,
                )
                train_p_scores = score_relative_suitability(
                    model, perturbation.presence, candidate.predictors
                )
                sealed_p_scores = score_relative_suitability(
                    model, perturbation.sealed_presence, candidate.predictors
                )
                sealed_b_scores = score_relative_suitability(
                    model, perturbation.sealed_background, candidate.predictors
                )
                ecological_b_scores = score_ecological_suitability(
                    model,
                    perturbation.sealed_background,
                    candidate.predictors,
                    observation_predictors=candidate.observation_predictors,
                    observation_reference=perturbation.background,
                )
                if observation_correction_active and observation_predictors:
                    weight_model = fit_observation_inverse_propensity_weights(
                        perturbation.presence,
                        perturbation.background,
                        perturbation.sealed_presence,
                        observation_predictors,
                        truncation_quantile=observation_weight_truncation_quantile,
                    )
                    sealed_weights = weight_model.evaluation_weights
                    weight_ess = weight_model.effective_sample_size
                    weight_max = weight_model.max_weight
                else:
                    sealed_weights = np.ones(len(perturbation.sealed_presence), dtype=float)
                    weight_ess = float(len(sealed_weights))
                    weight_max = 1.0
                profile = observation_weighted_heldout_niche_recovery_profile(
                    perturbation.background,
                    perturbation.sealed_background,
                    perturbation.sealed_presence,
                    ecological_b_scores,
                    audit_predictors,
                    presence_weights=sealed_weights,
                )
            except (ValueError, KeyError, np.linalg.LinAlgError):
                continue
            rows.append(
                {
                    "selector": str(selector),
                    "candidate": str(candidate_name),
                    "perturbation": str(perturbation.name),
                    "perturbation_type": str(perturbation.perturbation_type),
                    "presence_rank": presence_rank_score(sealed_p_scores, sealed_b_scores),
                    "continuous_boyce": continuous_boyce_index(sealed_p_scores, sealed_b_scores),
                    "or10": or10(train_p_scores, sealed_p_scores),
                    "n_model_presence": len(perturbation.presence),
                    "n_sealed_presence": len(perturbation.sealed_presence),
                    "n_model_background": len(perturbation.background),
                    "n_sealed_background": len(perturbation.sealed_background),
                    "observation_weight_ess": weight_ess,
                    "observation_weight_max": weight_max,
                    **profile.as_dict(),
                }
            )
    return pd.DataFrame(rows)


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
    """Run empirical Product-A v2 and optionally open a final sealed answer check.

    All tuning operates on ``EmpiricalNichePerturbation.presence/background``
    model-pool rows only. Optional sealed rows are inaccessible until canonical
    AUC, canonical ecology and robust ecology have all chosen their candidates.

    Observation correction is a global per-taxon decision: the same predeclared
    nuisance variables must pass their training-only evidence gate in *every*
    perturbation. If not, identity occurrence weights are used everywhere.
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
    sealed = _sealed_validation(
        items,
        {
            "canonical_auc": canonical_auc,
            "canonical_ecology": canonical_selection.candidate,
            "robust_ecology": robust_candidate,
        },
        candidates,
        audit_predictors,
        observation_predictors,
        observation_correction_active=global_correction,
        observation_weight_truncation_quantile=observation_weight_truncation_quantile,
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
        sealed_validation=sealed,
    )
